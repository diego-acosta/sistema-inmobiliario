from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

from app.application.integration.inbox_retry import (
    InboxOutcome, InboxOutcomeKind, InboxRetryProcessor, retry_backoff,
)
from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository


def _pending(db, *, consumer="fixture_511", attempts=0, when=None, op_id=None,
             fingerprint="a" * 64):
    repo = InboxRepository(db)
    event_id = str(uuid4())
    assert repo.claim(event_id=event_id, event_type="sucursal_creada",
                      aggregate_type="sucursal", aggregate_id=1,
                      consumer=consumer, op_id=op_id or str(uuid4()),
                      payload={"uid_global": str(uuid4())},
                      payload_fingerprint=fingerprint,
                      provenance={"installation_uid": str(uuid4())})
    repo.mark_pending_dependency(event_id=event_id, consumer=consumer,
                                 reason_code="SYNC_DEPENDENCY_UNAVAILABLE",
                                 next_attempt_at=when or datetime.now(UTC))
    if attempts:
        db.execute(text("UPDATE inbox_event SET attempt_count=:n WHERE event_id=:id"),
                   {"n": attempts, "id": event_id})
    db.flush()
    return event_id


def test_patch_materializa_contrato(db_session):
    columns = set(db_session.execute(text("""SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='inbox_event'""")).scalars())
    assert {"op_id", "payload", "payload_fingerprint", "provenance", "attempt_count",
            "last_attempt_at", "next_attempt_at", "lease_owner", "lease_expires_at"} <= columns


def test_dependencia_ausente_preserva_envelope_y_retry_aplica_una_vez(db_session):
    op_id = str(uuid4())
    event_id = _pending(db_session, op_id=op_id)
    effects = []
    available = False
    db_session.execute(text("CREATE TEMP TABLE effect_511 (op_id uuid) ON COMMIT DROP"))

    def consumer(event):
        effects.append(event["op_id"])
        db_session.execute(text("INSERT INTO effect_511 (op_id) VALUES (CAST(:op AS uuid))"), {"op": event["op_id"]})
        return InboxOutcome(InboxOutcomeKind.PROCESSED) if available else InboxOutcome(
            InboxOutcomeKind.PENDING_DEPENDENCY, "SYNC_DEPENDENCY_UNAVAILABLE")

    processor = InboxRetryProcessor(db_session, consumer="fixture_511")
    first = processor.run_once(consumer, worker_id="w1", event_id=event_id, manual=True)
    row = InboxRepository(db_session).get(event_id=event_id, consumer="fixture_511")
    assert first.kind is InboxOutcomeKind.PENDING_DEPENDENCY
    assert row["status"] == "PENDING_DEPENDENCY" and row["op_id"] == op_id
    assert db_session.execute(text("SELECT count(*) FROM effect_511")).scalar_one() == 0

    available = True
    second = processor.run_once(consumer, worker_id="w2", event_id=event_id, manual=True)
    row = InboxRepository(db_session).get(event_id=event_id, consumer="fixture_511")
    assert second.kind is InboxOutcomeKind.PROCESSED and row["status"] == "PROCESSED"
    assert effects == [op_id, op_id]
    assert db_session.execute(text("SELECT count(*) FROM effect_511")).scalar_one() == 1


def test_elegibilidad_limite_y_reanudacion_manual(db_session):
    future = datetime.now(UTC) + timedelta(hours=1)
    event_id = _pending(db_session, attempts=8, when=future)
    processor = InboxRetryProcessor(db_session, consumer="fixture_511", automatic_attempt_limit=8)
    assert processor.run_once(lambda _: InboxOutcome(InboxOutcomeKind.PROCESSED), worker_id="auto") is None
    assert InboxRepository(db_session).get(event_id=event_id, consumer="fixture_511")["status"] == "PENDING_DEPENDENCY"
    assert processor.run_once(lambda _: InboxOutcome(InboxOutcomeKind.PROCESSED),
                              worker_id="manual", event_id=event_id, manual=True).kind is InboxOutcomeKind.PROCESSED
    assert retry_backoff(1) < retry_backoff(8) <= timedelta(hours=6)


def test_lease_no_vencido_no_reclaim_y_vencido_si(db_session):
    now = datetime.now(UTC)
    event_id = _pending(db_session)
    repo = InboxRepository(db_session)
    claimed = repo.claim_pending(consumer="fixture_511", lease_owner="dead",
                                 lease_duration=timedelta(minutes=5),
                                 automatic_attempt_limit=8, now=now, manual=True)
    assert claimed and repo.reclaim_expired(now=now + timedelta(minutes=4)) == 0
    assert repo.reclaim_expired(now=now + timedelta(minutes=6)) == 1
    row = repo.get(event_id=event_id, consumer="fixture_511")
    assert row["status"] == "PENDING_DEPENDENCY" and row["attempt_count"] == 1


def test_mismo_op_id_scope_consumer_replay_y_conflicto(db_session):
    op_id = str(uuid4())
    first = _pending(db_session, op_id=op_id, fingerprint="a" * 64)
    processor = InboxRetryProcessor(db_session, consumer="fixture_511")
    calls = []

    def apply(event):
        calls.append(event["event_id"])
        return InboxOutcome(InboxOutcomeKind.PROCESSED)

    processor.run_once(apply, worker_id="one", event_id=first, manual=True)
    duplicate = _pending(db_session, op_id=op_id, fingerprint="a" * 64)
    assert processor.run_once(apply, worker_id="two", event_id=duplicate, manual=True).kind is InboxOutcomeKind.PROCESSED
    conflict = _pending(db_session, op_id=op_id, fingerprint="b" * 64)
    assert processor.run_once(apply, worker_id="three", event_id=conflict, manual=True).kind is InboxOutcomeKind.CONFLICTO
    assert calls == [first]
    assert InboxRepository(db_session).get(event_id=conflict, consumer="fixture_511")["status"] == "CONFLICTO"


def test_reason_no_allowlisted_se_sanitiza_y_rejected_es_terminal(db_session):
    event_id = _pending(db_session)
    processor = InboxRetryProcessor(db_session, consumer="fixture_511")
    processor.run_once(lambda _: InboxOutcome(InboxOutcomeKind.REJECTED, "password=secret"),
                       worker_id="worker", event_id=event_id, manual=True)
    row = InboxRepository(db_session).get(event_id=event_id, consumer="fixture_511")
    assert row["status"] == "REJECTED" and row["error_detail"] == "SYNC_FUNCTIONAL_FAILURE"
    assert processor.run_once(lambda _: InboxOutcome(InboxOutcomeKind.PROCESSED),
                              worker_id="worker", event_id=event_id, manual=True) is None
