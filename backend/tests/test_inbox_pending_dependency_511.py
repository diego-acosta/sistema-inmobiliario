from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text

from app.application.integration.inbox_retry import (
    InboxOutcome, InboxOutcomeKind, InboxRetryProcessor, retry_backoff,
)
from app.application.common.idempotency import NonCanonicalizablePayload
from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository
from app.config.database import engine


def _pending(db, *, consumer="fixture_511", attempts=0, when=None, op_id=None,
             payload=None, provenance=None, aggregate_uid=None, version_registro=1):
    repo = InboxRepository(db)
    event_id = str(uuid4())
    assert repo.claim(event_id=event_id, event_type="sucursal_creada",
                      aggregate_type="sucursal", aggregate_id=1,
                      consumer=consumer, op_id=op_id or str(uuid4()),
                      payload=payload or {"uid_global": "target-511"},
                      provenance=provenance or {"installation_uid": "origin-511"},
                      aggregate_uid=aggregate_uid or str(uuid4()),
                      version_registro=version_registro)
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


def test_patch_falla_ante_columna_existente_incompatible():
    database = f"inbox_511_{uuid4().hex}"
    url = engine.url
    connect = dict(host=url.host or "localhost", port=url.port or 5432,
                   user=url.username, password=url.password)
    with psycopg.connect(dbname="postgres", autocommit=True, **connect) as admin:
        admin.execute(f'CREATE DATABASE "{database}"')
    try:
        with psycopg.connect(dbname=database, autocommit=True, **connect) as connection:
            connection.execute("""CREATE TABLE public.inbox_event (
                id bigint PRIMARY KEY, event_id uuid NOT NULL, event_type varchar(100) NOT NULL,
                aggregate_type varchar(100) NOT NULL, aggregate_id bigint NOT NULL,
                consumer varchar(100) NOT NULL, status varchar(20) NOT NULL DEFAULT 'PROCESSING',
                processed_at timestamp, error_detail text,
                created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, consumer), attempt_count bigint NOT NULL DEFAULT 0
            )""")
            patch = Path("database/patch_inbox_pending_dependency_20260822.sql").read_text()
            with pytest.raises(psycopg.errors.RaiseException, match="attempt_count"):
                connection.execute(patch)
    finally:
        with psycopg.connect(dbname="postgres", autocommit=True, **connect) as admin:
            admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s", (database,))
            admin.execute(f'DROP DATABASE "{database}"')


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
    assert claimed and repo.reclaim_expired(
        consumer="fixture_511", now=now + timedelta(minutes=4)
    ) == 0
    assert repo.reclaim_expired(
        consumer="fixture_511", now=now + timedelta(minutes=6)
    ) == 1
    row = repo.get(event_id=event_id, consumer="fixture_511")
    assert row["status"] == "PENDING_DEPENDENCY" and row["attempt_count"] == 1


def test_mismo_op_id_scope_consumer_replay_y_conflicto(db_session):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    first = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    processor = InboxRetryProcessor(db_session, consumer="fixture_511")
    calls = []

    def apply(event):
        calls.append(event["event_id"])
        return InboxOutcome(InboxOutcomeKind.PROCESSED)

    processor.run_once(apply, worker_id="one", event_id=first, manual=True)
    duplicate = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    assert processor.run_once(apply, worker_id="two", event_id=duplicate, manual=True).kind is InboxOutcomeKind.PROCESSED
    conflict = _pending(
        db_session, op_id=op_id, aggregate_uid=aggregate_uid,
        payload={"uid_global": "different-target"},
    )
    assert processor.run_once(apply, worker_id="three", event_id=conflict, manual=True).kind is InboxOutcomeKind.CONFLICTO
    assert calls == [first]
    assert InboxRepository(db_session).get(event_id=conflict, consumer="fixture_511")["status"] == "CONFLICTO"


def test_fingerprint_canonico_ignora_orden_json_y_metadata_material_conflicta(db_session):
    repo = InboxRepository(db_session)
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    first = _pending(
        db_session, op_id=op_id, aggregate_uid=aggregate_uid,
        payload={"a": 1, "nested": {"x": 2, "y": 3}},
        provenance={"installation_uid": "origin", "branch_uid": "branch"},
    )
    second = _pending(
        db_session, op_id=op_id, aggregate_uid=aggregate_uid,
        payload={"nested": {"y": 3, "x": 2}, "a": 1},
        provenance={"branch_uid": "branch", "installation_uid": "origin"},
    )
    assert repo.get(event_id=first, consumer="fixture_511")["payload_fingerprint"] == (
        repo.get(event_id=second, consumer="fixture_511")["payload_fingerprint"]
    )
    processor = InboxRetryProcessor(db_session, consumer="fixture_511")
    calls = []

    def apply(event):
        calls.append(event["event_id"])
        return InboxOutcome(InboxOutcomeKind.PROCESSED)

    processor.run_once(apply, worker_id="one", event_id=first, manual=True)
    assert processor.run_once(
        apply, worker_id="two", event_id=second, manual=True
    ).kind is InboxOutcomeKind.PROCESSED
    metadata_conflict = _pending(
        db_session, op_id=op_id, aggregate_uid=aggregate_uid,
        payload={"a": 1, "nested": {"x": 2, "y": 3}},
        provenance={"installation_uid": "other", "branch_uid": "branch"},
    )
    assert processor.run_once(
        apply, worker_id="three", event_id=metadata_conflict, manual=True
    ).kind is InboxOutcomeKind.CONFLICTO
    assert calls == [first]


def test_claim_legacy_sin_envelope_no_inventa_fingerprint(db_session):
    event_id = str(uuid4())
    assert InboxRepository(db_session).claim(
        event_id=event_id, event_type="sucursal_creada", aggregate_type="sucursal",
        aggregate_id=1, consumer="legacy",
    )
    assert InboxRepository(db_session).get(
        event_id=event_id, consumer="legacy"
    )["payload_fingerprint"] is None


def test_error_de_canonicalizacion_es_tipado_y_no_persiste_payload(db_session):
    event_id = str(uuid4())
    with pytest.raises(NonCanonicalizablePayload):
        InboxRepository(db_session).claim(
            event_id=event_id, event_type="sucursal_creada",
            aggregate_type="sucursal", aggregate_id=1, consumer="fixture_511",
            op_id=str(uuid4()), payload={"value": float("nan")},
        )
    assert InboxRepository(db_session).get(
        event_id=event_id, consumer="fixture_511"
    ) is None


def test_reclaim_esta_aislado_por_consumer(db_session):
    now = datetime.now(UTC)
    event_a = _pending(db_session, consumer="consumer_a")
    event_b = _pending(db_session, consumer="consumer_b")
    repo = InboxRepository(db_session)
    for consumer in ("consumer_a", "consumer_b"):
        assert repo.claim_pending(
            consumer=consumer, lease_owner="dead", lease_duration=timedelta(minutes=1),
            automatic_attempt_limit=8, now=now, manual=True,
        )
    processor = InboxRetryProcessor(db_session, consumer="consumer_a")
    processor.run_once(
        lambda _: InboxOutcome(InboxOutcomeKind.PENDING_DEPENDENCY),
        worker_id="worker-a", now=now + timedelta(minutes=2),
    )
    assert repo.get(event_id=event_a, consumer="consumer_a")["status"] == "PENDING_DEPENDENCY"
    assert repo.get(event_id=event_b, consumer="consumer_b")["status"] == "PROCESSING"


def test_reason_no_allowlisted_se_sanitiza_y_rejected_es_terminal(db_session):
    event_id = _pending(db_session)
    processor = InboxRetryProcessor(db_session, consumer="fixture_511")
    processor.run_once(lambda _: InboxOutcome(InboxOutcomeKind.REJECTED, "password=secret"),
                       worker_id="worker", event_id=event_id, manual=True)
    row = InboxRepository(db_session).get(event_id=event_id, consumer="fixture_511")
    assert row["status"] == "REJECTED" and row["error_detail"] == "SYNC_FUNCTIONAL_FAILURE"
    assert processor.run_once(lambda _: InboxOutcome(InboxOutcomeKind.PROCESSED),
                              worker_id="worker", event_id=event_id, manual=True) is None
