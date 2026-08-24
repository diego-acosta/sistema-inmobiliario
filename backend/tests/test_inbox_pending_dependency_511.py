from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.integration.inbox_retry import (
    InboxOutcome, InboxOutcomeKind, InboxRetryProcessor, retry_backoff,
)
from app.application.common.idempotency import NonCanonicalizablePayload
from app.infrastructure.persistence.repositories.inbox_repository import (
    InboxPortableTargetRequired, InboxRepository,
)
from app.infrastructure.persistence.repositories.inbox_repository import InboxOwnershipLost
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


def _committed_pending(*, consumer: str) -> tuple[str, str]:
    event_id = str(uuid4())
    op_id = str(uuid4())
    with Session(engine) as session:
        repo = InboxRepository(session)
        assert repo.claim(
            event_id=event_id, event_type="sucursal_creada", aggregate_type="sucursal",
            aggregate_id=1, consumer=consumer, op_id=op_id,
            payload={"uid_global": "target-visible"}, aggregate_uid=str(uuid4()),
            provenance={"installation_uid": "origin-visible"}, version_registro=1,
        )
        repo.mark_pending_dependency(
            event_id=event_id, consumer=consumer,
            reason_code="SYNC_DEPENDENCY_UNAVAILABLE",
            next_attempt_at=datetime.now(UTC),
        )
        session.commit()
    return event_id, op_id


def _processor(db_session, **kwargs):
    return InboxRetryProcessor(
        db_session, lifecycle_session_factory=lambda: nullcontext(db_session), **kwargs
    )


def test_patch_materializa_contrato(db_session):
    columns = set(db_session.execute(text("""SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='inbox_event'""")).scalars())
    assert {"op_id", "payload", "payload_fingerprint", "provenance", "attempt_count",
            "last_attempt_at", "next_attempt_at", "lease_owner", "lease_expires_at",
            "lease_generation"} <= columns
    constraint = db_session.execute(text("""SELECT pg_get_constraintdef(oid)
        FROM pg_constraint WHERE conrelid='public.inbox_event'::regclass
        AND conname='ck_inbox_event_portable_target_511'""")).scalar_one()
    assert "op_id IS NULL" in constraint and "aggregate_uid IS NOT NULL" in constraint


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


def test_patch_falla_ante_constraint_portable_incompatible():
    database = f"inbox_511_{uuid4().hex}"
    url = engine.url
    connect = dict(host=url.host or "localhost", port=url.port or 5432,
                   user=url.username, password=url.password)
    with psycopg.connect(dbname="postgres", autocommit=True, **connect) as admin:
        admin.execute(f'CREATE DATABASE "{database}"')
    try:
        with psycopg.connect(dbname=database, autocommit=True, **connect) as connection:
            connection.execute("""CREATE TABLE public.inbox_event (
                id bigserial PRIMARY KEY, event_id uuid NOT NULL,
                event_type varchar(100) NOT NULL, aggregate_type varchar(100) NOT NULL,
                aggregate_id bigint NOT NULL, consumer varchar(100) NOT NULL,
                status varchar(20) NOT NULL DEFAULT 'PROCESSING', processed_at timestamp,
                error_detail text, created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, consumer)
            )""")
            patch = Path("database/patch_inbox_pending_dependency_20260822.sql").read_text()
            connection.execute(patch)
            connection.execute("""ALTER TABLE public.inbox_event
                DROP CONSTRAINT ck_inbox_event_portable_target_511,
                ADD CONSTRAINT ck_inbox_event_portable_target_511
                CHECK (op_id IS NULL)""")
            with pytest.raises(psycopg.errors.RaiseException, match="portable_target"):
                connection.execute(patch)
    finally:
        with psycopg.connect(dbname="postgres", autocommit=True, **connect) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                (database,),
            )
            admin.execute(f'DROP DATABASE "{database}"')


def test_constraint_sql_exige_target_portable_y_permite_legacy(db_session):
    nested = db_session.begin_nested()
    try:
        with pytest.raises(IntegrityError, match="ck_inbox_event_portable_target_511"):
            db_session.execute(text("""INSERT INTO inbox_event (
                event_id, event_type, aggregate_type, aggregate_id, consumer, op_id
            ) VALUES (:event_id, 'test', 'test', 1, 'sql_511', :op_id)"""), {
                "event_id": str(uuid4()), "op_id": str(uuid4()),
            })
    finally:
        nested.rollback()
    legacy_id = str(uuid4())
    db_session.execute(text("""INSERT INTO inbox_event (
        event_id, event_type, aggregate_type, aggregate_id, consumer
    ) VALUES (:event_id, 'test', 'test', 1, 'sql_511')"""), {"event_id": legacy_id})
    assert db_session.execute(text("""SELECT 1 FROM inbox_event
        WHERE event_id=CAST(:event_id AS uuid) AND op_id IS NULL
          AND aggregate_uid IS NULL"""), {"event_id": legacy_id}).scalar_one() == 1


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

    processor = _processor(db_session, consumer="fixture_511")
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
    processor = _processor(db_session, consumer="fixture_511", automatic_attempt_limit=8)
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
    processor = _processor(db_session, consumer="fixture_511")
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
    processor = _processor(db_session, consumer="fixture_511")
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


def test_claim_con_op_id_exige_target_portable_y_no_persiste(db_session):
    event_id = str(uuid4())
    with pytest.raises(
        InboxPortableTargetRequired, match="SYNC_PORTABLE_TARGET_REQUIRED"
    ):
        InboxRepository(db_session).claim(
            event_id=event_id, event_type="sucursal_creada",
            aggregate_type="sucursal", aggregate_id=10,
            consumer="fixture_511", op_id=str(uuid4()), payload={"value": 1},
        )
    assert InboxRepository(db_session).get(
        event_id=event_id, consumer="fixture_511"
    ) is None


def test_target_portable_distinto_conflicta_sin_segundo_efecto(db_session):
    op_id = str(uuid4())
    first = _pending(db_session, op_id=op_id, aggregate_uid=str(uuid4()))
    calls = []

    def apply(event):
        calls.append(event["event_id"])
        return InboxOutcome(InboxOutcomeKind.PROCESSED)

    processor = _processor(db_session, consumer="fixture_511")
    assert processor.run_once(
        apply, worker_id="one", event_id=first, manual=True
    ).kind is InboxOutcomeKind.PROCESSED
    second = _pending(db_session, op_id=op_id, aggregate_uid=str(uuid4()))
    repo = InboxRepository(db_session)
    assert repo.get(event_id=first, consumer="fixture_511")["payload_fingerprint"] != (
        repo.get(event_id=second, consumer="fixture_511")["payload_fingerprint"]
    )
    assert processor.run_once(
        apply, worker_id="two", event_id=second, manual=True
    ).kind is InboxOutcomeKind.CONFLICTO
    assert calls == [first]


def test_error_de_canonicalizacion_es_tipado_y_no_persiste_payload(db_session):
    event_id = str(uuid4())
    with pytest.raises(NonCanonicalizablePayload):
        InboxRepository(db_session).claim(
            event_id=event_id, event_type="sucursal_creada",
            aggregate_type="sucursal", aggregate_id=1, consumer="fixture_511",
            op_id=str(uuid4()), aggregate_uid=str(uuid4()),
            payload={"value": float("nan")},
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
    processor = _processor(db_session, consumer="consumer_a")
    processor.run_once(
        lambda _: InboxOutcome(InboxOutcomeKind.PENDING_DEPENDENCY),
        worker_id="worker-a", now=now + timedelta(minutes=2),
    )
    assert repo.get(event_id=event_a, consumer="consumer_a")["status"] == "PENDING_DEPENDENCY"
    assert repo.get(event_id=event_b, consumer="consumer_b")["status"] == "PROCESSING"


def test_pending_incompatible_bloquea_applicator(db_session):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    current = _pending(
        db_session, op_id=op_id, aggregate_uid=aggregate_uid,
        payload={"uid_global": "incompatible"},
    )
    calls = []
    outcome = _processor(db_session, consumer="fixture_511").run_once(
        lambda event: calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="worker", event_id=current, manual=True,
    )
    assert outcome.kind is InboxOutcomeKind.CONFLICTO
    assert calls == []


def test_processing_incompatible_bloquea_applicator(db_session):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    prior = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    repo = InboxRepository(db_session)
    assert repo.claim_pending(
        consumer="fixture_511", lease_owner="other-worker",
        lease_duration=timedelta(minutes=5), automatic_attempt_limit=8,
        event_id=prior, manual=True,
    )
    current = _pending(
        db_session, op_id=op_id, aggregate_uid=aggregate_uid,
        version_registro=2,
    )
    calls = []
    outcome = _processor(db_session, consumer="fixture_511").run_once(
        lambda event: calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="worker", event_id=current, manual=True,
    )
    assert outcome.kind is InboxOutcomeKind.CONFLICTO
    assert calls == []


def test_pending_compatible_elige_una_sola_entrega_para_el_efecto(db_session):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    leader = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    follower = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    calls = []

    def apply(event):
        calls.append(event["event_id"])
        return InboxOutcome(InboxOutcomeKind.PROCESSED)

    processor = _processor(db_session, consumer="fixture_511")
    deferred = processor.run_once(
        apply, worker_id="follower", event_id=follower, manual=True,
    )
    assert deferred.kind is InboxOutcomeKind.PENDING_DEPENDENCY
    assert calls == []
    assert processor.run_once(
        apply, worker_id="leader", event_id=leader, manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert processor.run_once(
        apply, worker_id="follower-retry", event_id=follower, manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert calls == [leader]


def test_leader_menor_progresa_aunque_otro_compatible_este_processing(db_session):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    leader = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    follower = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    repo = InboxRepository(db_session)
    claimed_follower = repo.claim_pending(
        consumer="fixture_511", lease_owner="other-worker",
        lease_duration=timedelta(minutes=5), automatic_attempt_limit=8,
        event_id=follower, manual=True,
    )
    assert claimed_follower["status"] == "PROCESSING"
    calls = []
    outcome = _processor(db_session, consumer="fixture_511").run_once(
        lambda event: calls.append(event["event_id"])
        or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="leader-worker", event_id=leader, manual=True,
    )
    assert outcome.kind is InboxOutcomeKind.PROCESSED
    assert calls == [leader]
    assert repo.get(event_id=leader, consumer="fixture_511")["status"] == "PROCESSED"
    scope = repo.get_operation_scope_deliveries(
        consumer="fixture_511", op_id=op_id, exclude_id=claimed_follower["id"],
    )
    assert any(delivery["status"] == "PROCESSED" for delivery in scope)
    repo.mark_as_processed(
        event_id=follower, consumer="fixture_511", lease_owner="other-worker",
        lease_generation=claimed_follower["lease_generation"],
    )
    assert repo.get(event_id=follower, consumer="fixture_511")["status"] == "PROCESSED"
    assert calls == [leader]


def test_dos_processing_compatibles_eligen_el_menor_id_sin_doble_defer():
    event = {"id": 10, "status": "PROCESSING"}
    deliveries = [{"id": 20, "status": "PROCESSING"}]
    assert InboxRetryProcessor._scope_leader_id(event, deliveries) == 10
    assert InboxRetryProcessor._scope_leader_id(
        deliveries[0], [event]
    ) == 10


def test_processed_compatible_no_oculta_pending_incompatible(db_session):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    processed = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    processor = _processor(db_session, consumer="fixture_511")
    assert processor.run_once(
        lambda _: InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="first", event_id=processed, manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    _pending(
        db_session, op_id=op_id, aggregate_uid=aggregate_uid,
        provenance={"installation_uid": "incompatible-origin"},
    )
    current = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    calls = []
    outcome = processor.run_once(
        lambda event: calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="current", event_id=current, manual=True,
    )
    assert outcome.kind is InboxOutcomeKind.CONFLICTO
    assert calls == []


def test_reason_no_allowlisted_se_sanitiza_y_rejected_es_terminal(db_session):
    event_id = _pending(db_session)
    processor = _processor(db_session, consumer="fixture_511")
    processor.run_once(lambda _: InboxOutcome(InboxOutcomeKind.REJECTED, "password=secret"),
                       worker_id="worker", event_id=event_id, manual=True)
    row = InboxRepository(db_session).get(event_id=event_id, consumer="fixture_511")
    assert row["status"] == "REJECTED" and row["error_detail"] == "SYNC_FUNCTIONAL_FAILURE"
    assert processor.run_once(lambda _: InboxOutcome(InboxOutcomeKind.PROCESSED),
                              worker_id="worker", event_id=event_id, manual=True) is None


def test_claim_es_visible_desde_otra_conexion_antes_del_applicator():
    consumer = f"visibility-{uuid4()}"
    event_id, _ = _committed_pending(consumer=consumer)
    observed = {}
    with Session(engine) as functional:
        processor = InboxRetryProcessor(functional, consumer=consumer)

        def applicator(_):
            with Session(engine) as observer:
                observed.update(InboxRepository(observer).get(
                    event_id=event_id, consumer=consumer
                ))
            return InboxOutcome(
                InboxOutcomeKind.PENDING_DEPENDENCY,
                "SYNC_DEPENDENCY_UNAVAILABLE",
            )

        processor.run_once(
            applicator, worker_id="visible-owner", event_id=event_id, manual=True
        )
        functional.commit()
    assert observed["status"] == "PROCESSING"
    assert observed["lease_owner"] == "visible-owner"
    assert observed["lease_expires_at"] is not None
    assert observed["lease_generation"] == 1


def test_lease_visible_vigente_no_reclaim_y_vencido_genera_nuevo_fence():
    consumer = f"reclaim-{uuid4()}"
    event_id, _ = _committed_pending(consumer=consumer)
    now = datetime.now(UTC)
    with Session(engine) as first:
        claimed_a = InboxRepository(first).claim_pending(
            consumer=consumer, lease_owner="worker-a", lease_duration=timedelta(minutes=5),
            automatic_attempt_limit=8, event_id=event_id, manual=True, now=now,
        )
        first.commit()
    with Session(engine) as second:
        repo = InboxRepository(second)
        assert repo.reclaim_expired(consumer=consumer, now=now + timedelta(minutes=4)) == 0
        assert repo.reclaim_expired(consumer=consumer, now=now + timedelta(minutes=6)) == 1
        second.commit()
    with Session(engine) as third:
        claimed_b = InboxRepository(third).claim_pending(
            consumer=consumer, lease_owner="worker-b", lease_duration=timedelta(minutes=5),
            automatic_attempt_limit=8, event_id=event_id, manual=True,
            now=now + timedelta(minutes=6),
        )
        third.commit()
    assert claimed_a["lease_generation"] == 1
    assert claimed_b["lease_generation"] == 2


def test_worker_stale_revierte_efecto_y_nuevo_owner_completa_una_vez():
    consumer = f"stale-{uuid4()}"
    event_id, op_id = _committed_pending(consumer=consumer)
    now = datetime.now(UTC)
    claimed_b = {}
    effect_table = f"inbox_effect_{uuid4().hex}"
    with Session(engine) as setup:
        setup.execute(text(f"CREATE TABLE {effect_table} (op_id uuid PRIMARY KEY)"))
        setup.commit()
    try:
        with Session(engine) as stale_functional:
            processor = InboxRetryProcessor(
                stale_functional, consumer=consumer, lease_duration=timedelta(minutes=1)
            )

            def stale_applicator(_):
                stale_functional.execute(text(
                    f"INSERT INTO {effect_table} (op_id) VALUES (CAST(:op AS uuid))"
                ), {"op": op_id})
                with Session(engine) as takeover:
                    repo = InboxRepository(takeover)
                    assert repo.reclaim_expired(
                        consumer=consumer, now=now + timedelta(minutes=2)
                    ) == 1
                    takeover.commit()
                with Session(engine) as takeover:
                    row = InboxRepository(takeover).claim_pending(
                        consumer=consumer, lease_owner="worker-b",
                        lease_duration=timedelta(minutes=5), automatic_attempt_limit=8,
                        event_id=event_id, manual=True, now=now + timedelta(minutes=2),
                    )
                    claimed_b.update(row)
                    takeover.commit()
                return InboxOutcome(InboxOutcomeKind.PROCESSED)

            with pytest.raises(InboxOwnershipLost):
                processor.run_once(
                    stale_applicator, worker_id="worker-a", event_id=event_id,
                    manual=True, now=now,
                )
            stale_functional.rollback()

        with Session(engine) as new_functional:
            new_functional.execute(text(
                "SELECT pg_advisory_xact_lock(hashtext(:scope), hashtext(:op))"
            ), {"scope": consumer, "op": op_id})
            new_functional.execute(text(
                f"INSERT INTO {effect_table} (op_id) VALUES (CAST(:op AS uuid))"
            ), {"op": op_id})
            InboxRepository(new_functional).mark_as_processed(
                event_id=event_id, consumer=consumer, lease_owner="worker-b",
                lease_generation=claimed_b["lease_generation"],
            )
            new_functional.commit()
        with Session(engine) as verify:
            assert verify.execute(text(
                f"SELECT count(*) FROM {effect_table} WHERE op_id=CAST(:op AS uuid)"
            ), {"op": op_id}).scalar_one() == 1
            assert InboxRepository(verify).get(
                event_id=event_id, consumer=consumer
            )["status"] == "PROCESSED"
    finally:
        with Session(engine) as cleanup:
            cleanup.execute(text(f"DROP TABLE IF EXISTS {effect_table}"))
            cleanup.commit()


@pytest.mark.parametrize("transition", ["processed", "pending", "rejected", "conflict"])
def test_todas_las_transiciones_rechazan_generation_stale(transition):
    consumer = f"stale-transition-{uuid4()}"
    event_id, _ = _committed_pending(consumer=consumer)
    now = datetime.now(UTC)
    with Session(engine) as session:
        first = InboxRepository(session).claim_pending(
            consumer=consumer, lease_owner="owner-a", lease_duration=timedelta(minutes=1),
            automatic_attempt_limit=8, event_id=event_id, manual=True, now=now,
        )
        session.commit()
    with Session(engine) as session:
        repo = InboxRepository(session)
        assert repo.reclaim_expired(consumer=consumer, now=now + timedelta(minutes=2)) == 1
        session.commit()
    with Session(engine) as session:
        second = InboxRepository(session).claim_pending(
            consumer=consumer, lease_owner="owner-b", lease_duration=timedelta(minutes=5),
            automatic_attempt_limit=8, event_id=event_id, manual=True,
            now=now + timedelta(minutes=2),
        )
        session.commit()
    assert second["lease_generation"] > first["lease_generation"]
    with Session(engine) as stale:
        repo = InboxRepository(stale)
        common = {
            "event_id": event_id, "consumer": consumer, "lease_owner": "owner-a",
            "lease_generation": first["lease_generation"],
        }
        with pytest.raises(InboxOwnershipLost):
            if transition == "processed":
                repo.mark_as_processed(**common)
            elif transition == "pending":
                repo.mark_pending_dependency(
                    **common, reason_code="SYNC_DEPENDENCY_UNAVAILABLE",
                    next_attempt_at=now + timedelta(minutes=3),
                )
            elif transition == "rejected":
                repo.mark_as_rejected(**common, error_detail="SYNC_PAYLOAD_INVALID")
            else:
                repo.mark_conflict(**common)
        stale.rollback()
    with Session(engine) as verify:
        row = InboxRepository(verify).get(event_id=event_id, consumer=consumer)
        assert row["status"] == "PROCESSING"
        assert row["lease_owner"] == "owner-b"


def _apply_transition(repo, transition, *, event_id, consumer, **ownership):
    common = {"event_id": event_id, "consumer": consumer, **ownership}
    if transition == "processed":
        repo.mark_as_processed(**common)
    elif transition == "pending":
        repo.mark_pending_dependency(
            **common, reason_code="SYNC_DEPENDENCY_UNAVAILABLE",
            next_attempt_at=datetime.now(UTC) + timedelta(minutes=1),
        )
    elif transition == "rejected":
        repo.mark_as_rejected(**common, error_detail="SYNC_PAYLOAD_INVALID")
    else:
        repo.mark_conflict(**common)


@pytest.mark.parametrize("transition", ["processed", "pending", "rejected", "conflict"])
def test_fila_con_lease_rechaza_transicion_sin_fencing(transition):
    consumer = f"missing-fence-{uuid4()}"
    event_id, _ = _committed_pending(consumer=consumer)
    with Session(engine) as claim_session:
        claimed = InboxRepository(claim_session).claim_pending(
            consumer=consumer, lease_owner="leased-owner",
            lease_duration=timedelta(minutes=5), automatic_attempt_limit=8,
            event_id=event_id, manual=True,
        )
        claim_session.commit()
    with Session(engine) as unfenced:
        with pytest.raises(InboxOwnershipLost):
            _apply_transition(
                InboxRepository(unfenced), transition,
                event_id=event_id, consumer=consumer,
            )
        unfenced.rollback()
    with Session(engine) as verify:
        row = InboxRepository(verify).get(event_id=event_id, consumer=consumer)
        assert row["status"] == "PROCESSING"
        assert row["lease_owner"] == "leased-owner"
        assert row["lease_generation"] == claimed["lease_generation"]
        assert row["lease_expires_at"] == claimed["lease_expires_at"]


@pytest.mark.parametrize("transition", ["processed", "pending", "rejected", "conflict"])
def test_fila_legacy_sin_lease_acepta_transicion_historica(transition):
    consumer = f"legacy-transition-{uuid4()}"
    event_id = str(uuid4())
    with Session(engine) as legacy:
        repo = InboxRepository(legacy)
        assert repo.claim(
            event_id=event_id, event_type="sucursal_creada", aggregate_type="sucursal",
            aggregate_id=1, consumer=consumer,
        )
        legacy.commit()
    with Session(engine) as transition_session:
        _apply_transition(
            InboxRepository(transition_session), transition,
            event_id=event_id, consumer=consumer,
        )
        transition_session.commit()
    expected = {
        "processed": "PROCESSED", "pending": "PENDING_DEPENDENCY",
        "rejected": "REJECTED", "conflict": "CONFLICTO",
    }[transition]
    with Session(engine) as verify:
        assert InboxRepository(verify).get(
            event_id=event_id, consumer=consumer
        )["status"] == expected


@pytest.mark.parametrize("partial", ["owner", "generation"])
def test_argumentos_de_fencing_parciales_se_rechazan_sin_modificar_fila(partial):
    consumer = f"partial-fence-{uuid4()}"
    event_id, _ = _committed_pending(consumer=consumer)
    with Session(engine) as claim_session:
        claimed = InboxRepository(claim_session).claim_pending(
            consumer=consumer, lease_owner="owner", lease_duration=timedelta(minutes=5),
            automatic_attempt_limit=8, event_id=event_id, manual=True,
        )
        claim_session.commit()
    ownership = (
        {"lease_owner": "owner"} if partial == "owner"
        else {"lease_generation": claimed["lease_generation"]}
    )
    with Session(engine) as partial_session:
        with pytest.raises(InboxOwnershipLost):
            InboxRepository(partial_session).mark_as_processed(
                event_id=event_id, consumer=consumer, **ownership,
            )
        partial_session.rollback()
    with Session(engine) as verify:
        row = InboxRepository(verify).get(event_id=event_id, consumer=consumer)
        assert row["status"] == "PROCESSING"
        assert row["lease_owner"] == "owner"
        assert row["lease_generation"] == claimed["lease_generation"]


def test_fencing_correcto_permite_transicion_y_lease_vencido_la_rechaza():
    current = datetime.now(UTC)
    valid_consumer = f"valid-fence-{uuid4()}"
    valid_event, _ = _committed_pending(consumer=valid_consumer)
    with Session(engine) as claim_session:
        valid = InboxRepository(claim_session).claim_pending(
            consumer=valid_consumer, lease_owner="owner",
            lease_duration=timedelta(minutes=5), automatic_attempt_limit=8,
            event_id=valid_event, manual=True, now=current,
        )
        claim_session.commit()
    with Session(engine) as transition_session:
        InboxRepository(transition_session).mark_as_processed(
            event_id=valid_event, consumer=valid_consumer, lease_owner="owner",
            lease_generation=valid["lease_generation"],
        )
        transition_session.commit()

    expired_consumer = f"expired-fence-{uuid4()}"
    expired_event, _ = _committed_pending(consumer=expired_consumer)
    with Session(engine) as claim_session:
        expired = InboxRepository(claim_session).claim_pending(
            consumer=expired_consumer, lease_owner="owner",
            lease_duration=timedelta(seconds=1), automatic_attempt_limit=8,
            event_id=expired_event, manual=True, now=current - timedelta(minutes=2),
        )
        claim_session.commit()
    with Session(engine) as transition_session:
        with pytest.raises(InboxOwnershipLost):
            InboxRepository(transition_session).mark_as_processed(
                event_id=expired_event, consumer=expired_consumer,
                lease_owner="owner", lease_generation=expired["lease_generation"],
            )
        transition_session.rollback()
    with Session(engine) as verify:
        assert InboxRepository(verify).get(
            event_id=expired_event, consumer=expired_consumer
        )["status"] == "PROCESSING"
