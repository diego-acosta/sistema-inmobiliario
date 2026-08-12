from uuid import uuid4

import pytest
from sqlalchemy import event, text

from app.application.common.idempotency import (
    ClaimDecision,
    ConflictKind,
    OperationClaim,
    OperationCompletion,
    UnexpectedOperationReceiptConflict,
    canonical_payload_hash,
    claim_operation,
    complete_operation,
)


def values(**changes):
    payload = {"name": "original", "items": [1, True, None]}
    result = dict(
        op_id=uuid4(), command_code="TEST.CREATE", target_type="TEST_FIXTURE",
        target_uid=uuid4(), target_key=None, payload_hash=canonical_payload_hash(payload),
        canonicalization_version=1, result_code="CREATED", result_http_status=201,
        result_target_uid=uuid4(), result_version=1, response_snapshot=payload,
        id_usuario=None, id_sucursal=1, id_instalacion=1,
    )
    result.update(changes)
    return result


def as_claim(data, **changes):
    fields = {name: data[name] for name in OperationClaim.__dataclass_fields__}
    fields.update(changes)
    return OperationClaim(**fields)


def test_claim_complete_replay_jsonb_and_sql_order(db_session):
    data = values()
    statements = []

    def capture(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", capture)
    try:
        assert claim_operation(db_session, as_claim(data)).decision is ClaimDecision.EXECUTE
        completed = complete_operation(db_session, OperationCompletion(**data))
        replay = claim_operation(db_session, as_claim(data))
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture)

    relevant = [sql.lower() for sql in statements if "advisory_xact_lock" in sql.lower() or "operacion_idempotente" in sql.lower()]
    assert "pg_catalog.pg_advisory_xact_lock" in relevant[0]
    assert "from public.operacion_idempotente" in relevant[1]
    assert completed.response_snapshot == data["response_snapshot"]
    assert replay.decision is ClaimDecision.REPLAY
    snapshot = replay.replay.response_snapshot
    snapshot["name"] = "changed"
    assert replay.replay.response_snapshot["name"] == "original"
    assert db_session.execute(text("SELECT jsonb_typeof(response_snapshot) FROM operacion_idempotente WHERE op_id=:op"), {"op": data["op_id"]}).scalar_one() == "object"


@pytest.mark.parametrize(
    ("changes", "kind"),
    [
        ({"command_code": "OTHER"}, ConflictKind.COMMAND),
        ({"target_key": "different"}, ConflictKind.TARGET),
        ({"payload_hash": "b" * 64}, ConflictKind.PAYLOAD),
        ({"canonicalization_version": 2}, ConflictKind.PAYLOAD),
    ],
)
def test_conflicts(db_session, changes, kind):
    data = values()
    complete_operation(db_session, OperationCompletion(**data))
    assert claim_operation(db_session, as_claim(data, **changes)).conflict is kind


def test_unique_is_technical_error_and_requires_external_rollback(db_session):
    data = values()
    complete_operation(db_session, OperationCompletion(**data))
    with pytest.raises(UnexpectedOperationReceiptConflict):
        complete_operation(db_session, OperationCompletion(**data))
    assert not db_session.is_active
    db_session.rollback()


def test_invalid_context_is_not_semantic_conflict(db_session):
    data = values(id_instalacion=-999999)
    with pytest.raises(UnexpectedOperationReceiptConflict):
        complete_operation(db_session, OperationCompletion(**data))
    db_session.rollback()


def test_external_rollback_removes_business_and_receipt_and_allows_retry(db_session, monkeypatch):
    data = values()
    commits = []
    rollbacks = []
    monkeypatch.setattr(db_session, "commit", lambda: commits.append(True))
    original_rollback = db_session.rollback
    monkeypatch.setattr(db_session, "rollback", lambda: rollbacks.append(True))
    assert claim_operation(db_session, as_claim(data)).decision is ClaimDecision.EXECUTE
    db_session.execute(text("CREATE TEMP TABLE idempotency_fixture(value text) ON COMMIT DROP"))
    db_session.execute(text("INSERT INTO idempotency_fixture VALUES ('business')"))
    complete_operation(db_session, OperationCompletion(**data))
    assert commits == [] and rollbacks == []
    # Invoke the real exterior rollback after restoring the spy.
    monkeypatch.setattr(db_session, "rollback", original_rollback)
    db_session.rollback()
    assert db_session.execute(text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"), {"op": data["op_id"]}).scalar_one() == 0
    assert claim_operation(db_session, as_claim(data)).decision is ClaimDecision.EXECUTE
