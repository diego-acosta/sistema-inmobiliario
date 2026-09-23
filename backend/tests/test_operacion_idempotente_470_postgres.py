from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

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
from app.config.database import engine


def values(**changes):
    payload = {"name": "original", "items": [1, True, None]}
    result = {
        "op_id": uuid4(),
        "command_code": "TEST.CREATE",
        "target_type": "TEST_FIXTURE",
        "target_uid": uuid4(),
        "target_key": None,
        "payload_hash": canonical_payload_hash(payload),
        "canonicalization_version": 1,
        "result_code": "CREATED",
        "result_http_status": 201,
        "result_target_uid": uuid4(),
        "result_version": 1,
        "response_snapshot": payload,
        "id_usuario": None,
        "id_sucursal": 1,
        "id_instalacion": 1,
    }
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
    ("id_sucursal", "id_instalacion"),
    [(None, None), (1, None), (1, 1)],
    ids=["central_global", "central_contextual", "legacy"],
)
def test_central_y_legacy_claim_complete_commit_replay(
    id_sucursal, id_instalacion
):
    data = values(
        id_sucursal=id_sucursal,
        id_instalacion=id_instalacion,
    )
    with Session(engine) as writer:
        assert claim_operation(writer, as_claim(data)).decision is ClaimDecision.EXECUTE
        complete_operation(writer, OperationCompletion(**data))
        writer.commit()

    with Session(engine) as reader:
        replay = claim_operation(reader, as_claim(data))
        assert replay.decision is ClaimDecision.REPLAY
        assert replay.replay.response_snapshot == data["response_snapshot"]
        reader.rollback()


def test_central_contextual_mantiene_fk_de_sucursal(db_session):
    data = values(id_sucursal=999999999, id_instalacion=None)
    with pytest.raises(UnexpectedOperationReceiptConflict):
        complete_operation(db_session, OperationCompletion(**data))
    db_session.rollback()


def test_legacy_mismatch_sucursal_instalacion_sigue_rechazado(db_session):
    installation = db_session.execute(text("""
        SELECT id_instalacion, id_sucursal
        FROM public.instalacion
        ORDER BY id_instalacion
        LIMIT 1
    """)).one()
    other_branch = db_session.execute(text("""
        INSERT INTO public.sucursal (
            codigo_sucursal, nombre_sucursal, estado_sucursal
        ) VALUES (
            :code, 'Sucursal ajena runtime #470', 'ACTIVA'
        ) RETURNING id_sucursal
    """), {"code": f"SUC_470_{uuid4().hex[:12]}"}).scalar_one()
    assert other_branch != installation.id_sucursal
    data = values(
        id_sucursal=other_branch,
        id_instalacion=installation.id_instalacion,
    )
    with pytest.raises(UnexpectedOperationReceiptConflict):
        complete_operation(db_session, OperationCompletion(**data))
    db_session.rollback()


def test_central_payload_distinto_es_conflicto(db_session):
    data = values(id_sucursal=None, id_instalacion=None)
    complete_operation(db_session, OperationCompletion(**data))
    conflict = claim_operation(
        db_session,
        as_claim(data, payload_hash="b" * 64),
    )
    assert conflict.decision is ClaimDecision.CONFLICT
    assert conflict.conflict is ConflictKind.PAYLOAD


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


def test_unique_is_technical_error_and_preserves_committed_receipt():
    data = values()

    with Session(engine) as first_session:
        complete_operation(first_session, OperationCompletion(**data))
        first_session.commit()

    with Session(engine) as second_session:
        with pytest.raises(UnexpectedOperationReceiptConflict):
            complete_operation(second_session, OperationCompletion(**data))
        second_session.rollback()

    with Session(engine) as verification_session:
        receipt_count = verification_session.execute(
            text(
                """
                SELECT count(*)
                  FROM public.operacion_idempotente
                 WHERE op_id = :op_id
                """
            ),
            {"op_id": data["op_id"]},
        ).scalar_one()
    assert receipt_count == 1


def test_invalid_context_is_not_semantic_conflict(db_session):
    data = values(id_instalacion=-999999)
    with pytest.raises(UnexpectedOperationReceiptConflict):
        complete_operation(db_session, OperationCompletion(**data))
    db_session.rollback()


def test_external_rollback_removes_business_and_receipt_and_allows_retry(db_session, monkeypatch):
    data = values(id_sucursal=None, id_instalacion=None)
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
