from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
import json
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
from app.application.common.synchronization_policy import (
    InvalidSyncAggregate,
    SensitiveSyncPayload,
    UnknownSyncEvent,
)
from app.infrastructure.persistence.repositories.inbox_repository import (
    InboxInvalidFingerprint, InboxInvalidPortableTarget,
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


def _set_lease_from_db_clock(db, *, event_id, delta):
    db.execute(text("""UPDATE inbox_event
        SET lease_expires_at=(clock_timestamp() AT TIME ZONE 'UTC') + :delta
        WHERE event_id=CAST(:event_id AS uuid)"""), {
            "event_id": event_id, "delta": delta,
        })


def _insert_retained_direct(
    db, *, event_type="sucursal_creada", aggregate_type="sucursal",
    payload=None, provenance=None, version_registro=1, consumer="retained_sql_511",
    op_id=None, aggregate_uid=None, payload_fingerprint=None,
    status="PENDING_DEPENDENCY",
):
    event_id = str(uuid4())
    db.execute(text("""INSERT INTO inbox_event (
        event_id, event_type, aggregate_type, aggregate_id, consumer, status,
        payload, provenance, version_registro, next_attempt_at, op_id,
        aggregate_uid, payload_fingerprint
    ) VALUES (
        CAST(:event_id AS uuid), :event_type, :aggregate_type, 1, :consumer,
        :status, CAST(:payload AS jsonb), CAST(:provenance AS jsonb),
        :version_registro, clock_timestamp() AT TIME ZONE 'UTC',
        CAST(:op_id AS uuid), CAST(:aggregate_uid AS uuid), :payload_fingerprint
    )"""), {
        "event_id": event_id, "event_type": event_type,
        "aggregate_type": aggregate_type, "consumer": consumer,
        "payload": json.dumps(payload) if payload is not None else None,
        "provenance": json.dumps(provenance) if provenance is not None else None,
        "version_registro": version_registro, "status": status,
        "op_id": op_id, "aggregate_uid": aggregate_uid,
        "payload_fingerprint": payload_fingerprint,
    })
    return event_id


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
    scoped_fingerprint = db_session.execute(text("""SELECT pg_get_constraintdef(oid)
        FROM pg_constraint WHERE conrelid='public.inbox_event'::regclass
        AND conname='ck_inbox_event_scoped_fingerprint_511'""")).scalar_one()
    assert "op_id IS NULL" in scoped_fingerprint
    assert "payload_fingerprint IS NOT NULL" in scoped_fingerprint
    scope_pk = db_session.execute(text("""SELECT pg_get_constraintdef(oid)
        FROM pg_constraint WHERE conrelid='public.inbox_operation_scope'::regclass
        AND conname='pk_inbox_operation_scope_511'""")).scalar_one()
    assert "PRIMARY KEY (consumer, op_id)" in scope_pk


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


@pytest.mark.parametrize(
    ("constraint_name", "bad_definition", "error_match"),
    [
        ("ck_inbox_event_portable_target_511", "op_id IS NULL", "portable_target"),
        (
            "ck_inbox_event_scoped_fingerprint_511",
            "payload_fingerprint IS NULL",
            "scoped_fingerprint",
        ),
    ],
)
def test_patch_falla_ante_constraint_511_incompatible(
    constraint_name, bad_definition, error_match,
):
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
            connection.execute(f"""ALTER TABLE public.inbox_event
                DROP CONSTRAINT {constraint_name},
                ADD CONSTRAINT {constraint_name} CHECK ({bad_definition})""")
            with pytest.raises(psycopg.errors.RaiseException, match=error_match):
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


def test_constraint_sql_exige_fingerprint_para_scope(db_session):
    nested = db_session.begin_nested()
    try:
        with pytest.raises(
            IntegrityError, match="ck_inbox_event_scoped_fingerprint_511"
        ):
            db_session.execute(text("""INSERT INTO inbox_event (
                event_id, event_type, aggregate_type, aggregate_id, consumer,
                op_id, aggregate_uid
            ) VALUES (
                :event_id, 'sucursal_creada', 'sucursal', 1, 'sql_fp_511',
                :op_id, :aggregate_uid
            )"""), {
                "event_id": str(uuid4()), "op_id": str(uuid4()),
                "aggregate_uid": str(uuid4()),
            })
    finally:
        nested.rollback()


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
        consumer="fixture_511", now=now + timedelta(days=365)
    ) == 0
    _set_lease_from_db_clock(
        db_session, event_id=event_id, delta=-timedelta(seconds=1),
    )
    assert repo.reclaim_expired(
        consumer="fixture_511", now=now - timedelta(days=365)
    ) == 1
    row = repo.get(event_id=event_id, consumer="fixture_511")
    assert row["status"] == "PENDING_DEPENDENCY" and row["attempt_count"] == 1


@pytest.mark.parametrize("caller_offset", [timedelta(days=-365), timedelta(days=365)])
def test_claim_lease_usa_reloj_db_y_no_now_del_caller(db_session, caller_offset):
    event_id = _pending(db_session)
    duration = timedelta(minutes=5)
    db_before = db_session.execute(text(
        "SELECT clock_timestamp() AT TIME ZONE 'UTC'"
    )).scalar_one()
    claimed = InboxRepository(db_session).claim_pending(
        consumer="fixture_511", lease_owner="db-clock",
        lease_duration=duration, automatic_attempt_limit=8,
        event_id=event_id, manual=True,
        now=datetime.now(UTC) + caller_offset,
    )
    db_after = db_session.execute(text(
        "SELECT clock_timestamp() AT TIME ZONE 'UTC'"
    )).scalar_one()
    assert db_before + duration <= claimed["lease_expires_at"] <= db_after + duration
    assert db_before <= claimed["last_attempt_at"] <= db_after


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


def _claim_portable(db_session, *, event_type="sucursal_creada",
                    aggregate_type="sucursal", payload=None, provenance=None):
    event_id = str(uuid4())
    InboxRepository(db_session).claim(
        event_id=event_id, event_type=event_type, aggregate_type=aggregate_type,
        aggregate_id=1, consumer="policy_511", op_id=str(uuid4()),
        aggregate_uid=str(uuid4()), payload=payload, provenance=provenance,
    )
    return event_id


@pytest.mark.parametrize(
    ("event_type", "aggregate_type", "expected"),
    [
        ("evento_no_registrado", "sucursal", UnknownSyncEvent),
        ("sucursal_creada", "instalacion", InvalidSyncAggregate),
        ("sucursal_creada", "credencial_usuario", InvalidSyncAggregate),
        ("sucursal_creada", "sesion_usuario", InvalidSyncAggregate),
    ],
)
def test_claim_portable_rechaza_evento_o_aggregate_fuera_de_policy(
    db_session, event_type, aggregate_type, expected,
):
    with pytest.raises(expected):
        _claim_portable(
            db_session, event_type=event_type, aggregate_type=aggregate_type,
            payload={"uid_global": "portable"},
        )
    assert db_session.execute(text(
        "SELECT count(*) FROM inbox_event WHERE consumer='policy_511'"
    )).scalar_one() == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"password": "secret"},
        {"data": {"refresh_token": "secret"}},
    ],
)
def test_claim_portable_rechaza_payload_sensible_sin_persistir(db_session, payload):
    with pytest.raises(SensitiveSyncPayload) as raised:
        _claim_portable(db_session, payload=payload)
    assert raised.value.code == "SYNC_SENSITIVE_PAYLOAD"
    assert "secret" not in str(raised.value)
    assert db_session.execute(text(
        "SELECT count(*) FROM inbox_event WHERE consumer='policy_511'"
    )).scalar_one() == 0


def test_claim_portable_rechaza_provenance_sensible_sin_persistir(db_session):
    with pytest.raises(SensitiveSyncPayload) as raised:
        _claim_portable(
            db_session, payload={"uid_global": "portable"},
            provenance={"origin": {"token": "secret"}},
        )
    assert raised.value.code == "SYNC_SENSITIVE_PAYLOAD"
    assert "secret" not in str(raised.value)
    assert db_session.execute(text(
        "SELECT count(*) FROM inbox_event WHERE consumer='policy_511'"
    )).scalar_one() == 0


def test_claim_portable_exige_payload_dict_y_valido_persiste_fingerprint(db_session):
    with pytest.raises(SensitiveSyncPayload, match="SYNC_INVALID_PAYLOAD"):
        _claim_portable(db_session, payload=None)
    event_id = _claim_portable(
        db_session, payload={"uid_global": "portable"}, provenance=None,
    )
    row = InboxRepository(db_session).get(event_id=event_id, consumer="policy_511")
    assert row["status"] == "PROCESSING"
    assert row["payload_fingerprint"] is not None


def _claim_retained_without_op(
    db_session, *, event_type="sucursal_creada", aggregate_type="sucursal",
    payload=None, provenance=None,
):
    event_id = str(uuid4())
    InboxRepository(db_session).claim(
        event_id=event_id, event_type=event_type, aggregate_type=aggregate_type,
        aggregate_id=1, consumer="retained_without_op_511",
        payload=payload, provenance=provenance,
    )
    return event_id


@pytest.mark.parametrize(
    "payload",
    [
        {"password": "secret"},
        {"data": {"refresh_token": "secret"}},
    ],
)
def test_envelope_sin_op_id_rechaza_payload_sensible(db_session, payload):
    with pytest.raises(SensitiveSyncPayload) as raised:
        _claim_retained_without_op(db_session, payload=payload)
    assert raised.value.code == "SYNC_SENSITIVE_PAYLOAD"
    assert "secret" not in str(raised.value)
    assert db_session.execute(text("""SELECT count(*) FROM inbox_event
        WHERE consumer='retained_without_op_511'""")).scalar_one() == 0


def test_envelope_sin_op_id_rechaza_provenance_sensible(db_session):
    with pytest.raises(SensitiveSyncPayload) as raised:
        _claim_retained_without_op(
            db_session, payload={"uid_global": "retained"},
            provenance={"origin": {"token": "secret"}},
        )
    assert raised.value.code == "SYNC_SENSITIVE_PAYLOAD"
    assert "secret" not in str(raised.value)
    assert db_session.execute(text("""SELECT count(*) FROM inbox_event
        WHERE consumer='retained_without_op_511'""")).scalar_one() == 0


@pytest.mark.parametrize(
    ("event_type", "aggregate_type", "expected"),
    [
        ("evento_no_registrado", "sucursal", UnknownSyncEvent),
        ("sucursal_creada", "instalacion", InvalidSyncAggregate),
    ],
)
def test_envelope_sin_op_id_aplica_allowlist_default_deny(
    db_session, event_type, aggregate_type, expected,
):
    with pytest.raises(expected):
        _claim_retained_without_op(
            db_session, event_type=event_type, aggregate_type=aggregate_type,
            payload={"uid_global": "retained"},
        )
    assert db_session.execute(text("""SELECT count(*) FROM inbox_event
        WHERE consumer='retained_without_op_511'""")).scalar_one() == 0


def test_envelope_valido_sin_op_id_se_valida_y_conserva_fingerprint(db_session):
    event_id = _claim_retained_without_op(
        db_session, payload={"uid_global": "retained"},
        provenance={"origin": {"installation_uid": "origin"}},
    )
    row = InboxRepository(db_session).get(
        event_id=event_id, consumer="retained_without_op_511",
    )
    assert row["op_id"] is None
    assert row["payload_fingerprint"] is not None


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


def test_uuid_portable_equivalente_canonicaliza_fingerprint_y_hace_replay(db_session):
    op_id = str(uuid4())
    uppercase_uid = "ABCDEF12-3456-7890-ABCD-EF1234567890"
    lowercase_uid = uppercase_uid.lower()
    first = _pending(db_session, op_id=op_id, aggregate_uid=uppercase_uid)
    second = _pending(db_session, op_id=op_id, aggregate_uid=lowercase_uid)
    repo = InboxRepository(db_session)
    first_row = repo.get(event_id=first, consumer="fixture_511")
    second_row = repo.get(event_id=second, consumer="fixture_511")
    assert first_row["payload_fingerprint"] == second_row["payload_fingerprint"]
    assert str(first_row["aggregate_uid"]) == lowercase_uid
    assert str(second_row["aggregate_uid"]) == lowercase_uid
    calls = []

    def apply(event):
        calls.append(event["event_id"])
        return InboxOutcome(InboxOutcomeKind.PROCESSED)

    processor = _processor(db_session, consumer="fixture_511")
    assert processor.run_once(
        apply, worker_id="first", event_id=first, manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert processor.run_once(
        apply, worker_id="replay", event_id=second, manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert calls == [first]


def test_aggregate_uid_invalido_se_rechaza_antes_de_sql(db_session):
    event_id = str(uuid4())
    with pytest.raises(
        InboxInvalidPortableTarget, match="SYNC_INVALID_PORTABLE_TARGET"
    ):
        InboxRepository(db_session).claim(
            event_id=event_id, event_type="sucursal_creada",
            aggregate_type="sucursal", aggregate_id=1, consumer="fixture_511",
            op_id=str(uuid4()), aggregate_uid="not-a-uuid",
            payload={"uid_global": "target"},
        )
    assert InboxRepository(db_session).get(
        event_id=event_id, consumer="fixture_511"
    ) is None


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
    _set_lease_from_db_clock(
        db_session, event_id=event_a, delta=-timedelta(seconds=1),
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


@pytest.mark.parametrize(
    ("event_type", "aggregate_type", "payload", "provenance", "reason"),
    [
        (
            "evento_desconocido", "sucursal", {"password": "secret"}, None,
            "SYNC_EVENT_NOT_ALLOWED",
        ),
        (
            "sucursal_creada", "instalacion", {"uid_global": "target"}, None,
            "SYNC_AGGREGATE_NOT_ALLOWED",
        ),
        (
            "sucursal_creada", "sucursal", {"uid_global": "target"},
            {"origin": {"token": "secret"}}, "SYNC_SENSITIVE_PAYLOAD",
        ),
        (
            "sucursal_creada", "sucursal", None, None, "SYNC_INVALID_PAYLOAD",
        ),
    ],
)
def test_run_once_revalida_fila_sql_y_rechaza_sin_exponerla_al_applicator(
    db_session, event_type, aggregate_type, payload, provenance, reason,
):
    event_id = _insert_retained_direct(
        db_session, event_type=event_type, aggregate_type=aggregate_type,
        payload=payload, provenance=provenance,
    )
    calls = []
    outcome = _processor(db_session, consumer="retained_sql_511").run_once(
        lambda event: calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="policy-worker", event_id=event_id, manual=True,
    )
    row = InboxRepository(db_session).get(
        event_id=event_id, consumer="retained_sql_511",
    )
    assert outcome == InboxOutcome(InboxOutcomeKind.REJECTED, reason)
    assert calls == []
    assert row["status"] == "REJECTED"
    assert row["error_detail"] == reason
    assert "secret" not in row["error_detail"]


@pytest.mark.parametrize("legacy", [False, True])
def test_run_once_permite_fila_sql_valida_y_legacy_payloadless(db_session, legacy):
    event_id = _insert_retained_direct(
        db_session,
        payload=None if legacy else {"uid_global": "target"},
        provenance=None if legacy else {"installation_uid": "origin"},
        version_registro=None if legacy else 1,
    )
    calls = []
    outcome = _processor(db_session, consumer="retained_sql_511").run_once(
        lambda event: calls.append(event["event_id"])
        or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="valid-worker", event_id=event_id, manual=True,
    )
    assert outcome.kind is InboxOutcomeKind.PROCESSED
    assert calls == [event_id]


def test_rechazo_por_policy_respeta_fencing_y_no_pisa_nuevo_owner(
    db_session, monkeypatch,
):
    event_id = _insert_retained_direct(
        db_session, event_type="evento_desconocido", payload={"value": 1},
    )

    def lose_ownership(**_):
        _set_lease_from_db_clock(
            db_session, event_id=event_id, delta=-timedelta(seconds=1),
        )
        repo = InboxRepository(db_session)
        assert repo.reclaim_expired(consumer="retained_sql_511") == 1
        assert repo.claim_pending(
            consumer="retained_sql_511", lease_owner="new-owner",
            lease_duration=timedelta(minutes=5), automatic_attempt_limit=8,
            event_id=event_id, manual=True,
        )
        raise UnknownSyncEvent(UnknownSyncEvent.code)

    monkeypatch.setattr(
        "app.application.integration.inbox_retry.validate_retained_sync_envelope",
        lose_ownership,
    )
    with pytest.raises(InboxOwnershipLost):
        _processor(db_session, consumer="retained_sql_511").run_once(
            lambda _: InboxOutcome(InboxOutcomeKind.PROCESSED),
            worker_id="stale-owner", event_id=event_id, manual=True,
        )
    row = InboxRepository(db_session).get(
        event_id=event_id, consumer="retained_sql_511",
    )
    assert row["status"] == "PROCESSING"
    assert row["lease_owner"] == "new-owner"


def test_current_valido_ignora_sibling_pending_invalido_y_luego_lo_rechaza(
    db_session,
):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    sibling = _insert_retained_direct(
        db_session, consumer="fixture_511", event_type="evento_desconocido",
        payload={"password": "secret"}, op_id=op_id,
        aggregate_uid=aggregate_uid, payload_fingerprint="b" * 64,
    )
    current = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    calls = []
    processor = _processor(db_session, consumer="fixture_511")
    assert processor.run_once(
        lambda event: calls.append(event["event_id"])
        or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="current", event_id=current, manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert calls == [current]
    assert InboxRepository(db_session).get(
        event_id=sibling, consumer="fixture_511",
    )["status"] == "PENDING_DEPENDENCY"

    sibling_calls = []
    rejected = processor.run_once(
        lambda event: sibling_calls.append(event)
        or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="sibling", event_id=sibling, manual=True,
    )
    assert rejected == InboxOutcome(
        InboxOutcomeKind.REJECTED, "SYNC_EVENT_NOT_ALLOWED"
    )
    assert sibling_calls == []


def test_orden_inverso_sibling_invalido_no_cambia_resultado_del_current(db_session):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    sibling = _insert_retained_direct(
        db_session, consumer="fixture_511", event_type="evento_desconocido",
        payload={"value": 1}, op_id=op_id, aggregate_uid=aggregate_uid,
        payload_fingerprint="c" * 64,
    )
    current = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    processor = _processor(db_session, consumer="fixture_511")
    assert processor.run_once(
        lambda _: pytest.fail("invalid sibling reached applicator"),
        worker_id="sibling", event_id=sibling, manual=True,
    ).kind is InboxOutcomeKind.REJECTED
    calls = []
    assert processor.run_once(
        lambda event: calls.append(event["event_id"])
        or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="current", event_id=current, manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert calls == [current]


@pytest.mark.parametrize("sibling_status", ["PROCESSING", "PROCESSED", "CONFLICTO"])
def test_current_no_usa_sibling_invalido_como_block_replay_o_conflicto(
    db_session, sibling_status,
):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    sibling = _insert_retained_direct(
        db_session, consumer="fixture_511", event_type="evento_desconocido",
        payload={"value": 1}, op_id=op_id, aggregate_uid=aggregate_uid,
        payload_fingerprint="d" * 64, status=sibling_status,
    )
    current = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    calls = []
    assert _processor(db_session, consumer="fixture_511").run_once(
        lambda event: calls.append(event["event_id"])
        or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="current", event_id=current, manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert calls == [current]
    sibling_row = InboxRepository(db_session).get(
        event_id=sibling, consumer="fixture_511",
    )
    assert sibling_row["status"] == sibling_status
    assert sibling_row["error_detail"] is None


@pytest.mark.parametrize("stored_fingerprint", [None, "a" * 64])
def test_current_scoped_rechaza_fingerprint_no_verificable(
    db_session, stored_fingerprint,
):
    if stored_fingerprint is None:
        db_session.execute(text("""ALTER TABLE inbox_event
            DROP CONSTRAINT ck_inbox_event_scoped_fingerprint_511"""))
    event_id = _insert_retained_direct(
        db_session, consumer="fixture_511", payload={"uid_global": "target"},
        op_id=str(uuid4()), aggregate_uid=str(uuid4()),
        payload_fingerprint=stored_fingerprint,
    )
    calls = []
    outcome = _processor(db_session, consumer="fixture_511").run_once(
        lambda event: calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="corrupt-current", event_id=event_id, manual=True,
    )
    assert outcome == InboxOutcome(
        InboxOutcomeKind.REJECTED, InboxInvalidFingerprint.code
    )
    assert calls == []
    row = InboxRepository(db_session).get(event_id=event_id, consumer="fixture_511")
    assert row["status"] == "REJECTED"
    assert row["error_detail"] == InboxInvalidFingerprint.code


@pytest.mark.parametrize("stored_fingerprint", [None, "e" * 64])
def test_current_ignora_sibling_con_fingerprint_no_verificable(
    db_session, stored_fingerprint,
):
    if stored_fingerprint is None:
        db_session.execute(text("""ALTER TABLE inbox_event
            DROP CONSTRAINT ck_inbox_event_scoped_fingerprint_511"""))
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    sibling = _insert_retained_direct(
        db_session, consumer="fixture_511", payload={"uid_global": "other"},
        op_id=op_id, aggregate_uid=aggregate_uid,
        payload_fingerprint=stored_fingerprint, status="PROCESSED",
    )
    current = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    calls = []
    assert _processor(db_session, consumer="fixture_511").run_once(
        lambda event: calls.append(event["event_id"])
        or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="valid-current", event_id=current, manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert calls == [current]
    assert InboxRepository(db_session).get(
        event_id=sibling, consumer="fixture_511",
    )["status"] == "PROCESSED"


def test_current_scoped_rechaza_fingerprint_no_canonicalizable(db_session):
    event_id = _insert_retained_direct(
        db_session, consumer="fixture_511", payload={"value": 1.25},
        op_id=str(uuid4()), aggregate_uid=str(uuid4()),
        payload_fingerprint="a" * 64,
    )
    calls = []
    outcome = _processor(db_session, consumer="fixture_511").run_once(
        lambda event: calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="non-canonical-current", event_id=event_id, manual=True,
    )
    assert outcome == InboxOutcome(
        InboxOutcomeKind.REJECTED, InboxInvalidFingerprint.code
    )
    assert calls == []
    row = InboxRepository(db_session).get(event_id=event_id, consumer="fixture_511")
    assert row["status"] == "REJECTED"
    assert row["error_detail"] == InboxInvalidFingerprint.code
    assert row["lease_owner"] is None


def test_current_ignora_sibling_con_fingerprint_no_canonicalizable(db_session):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    sibling = _insert_retained_direct(
        db_session, consumer="fixture_511", payload={"value": 1.25},
        op_id=op_id, aggregate_uid=aggregate_uid,
        payload_fingerprint="b" * 64, status="PROCESSED",
    )
    current = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    calls = []
    outcome = _processor(db_session, consumer="fixture_511").run_once(
        lambda event: calls.append(event["event_id"])
        or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="canonical-current", event_id=current, manual=True,
    )
    assert outcome.kind is InboxOutcomeKind.PROCESSED
    assert calls == [current]
    sibling_row = InboxRepository(db_session).get(
        event_id=sibling, consumer="fixture_511"
    )
    assert sibling_row["status"] == "PROCESSED"
    assert sibling_row["error_detail"] is None


def test_duplicate_compatible_reutiliza_conflicto_terminal(db_session):
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    first = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    calls = []
    processor = _processor(db_session, consumer="fixture_511")

    def conflict_applicator(event):
        calls.append(event["event_id"])
        return InboxOutcome(InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT")

    assert processor.run_once(
        conflict_applicator, worker_id="first-conflict", event_id=first, manual=True,
    ) == InboxOutcome(InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT")
    duplicate = _pending(db_session, op_id=op_id, aggregate_uid=aggregate_uid)
    outcome = processor.run_once(
        lambda event: calls.append(event["event_id"])
        or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="conflict-replay", event_id=duplicate, manual=True,
    )
    assert outcome == InboxOutcome(
        InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT"
    )
    assert calls == [first]
    assert InboxRepository(db_session).get(
        event_id=duplicate, consumer="fixture_511"
    )["status"] == "CONFLICTO"


def test_dos_deliveries_scoped_se_retienen_pero_producen_un_efecto(db_session):
    repo = InboxRepository(db_session)
    op_id = str(uuid4())
    aggregate_uid = str(uuid4())
    deliveries = [str(uuid4()), str(uuid4())]
    for event_id in deliveries:
        assert repo.claim(
            event_id=event_id, event_type="sucursal_creada",
            aggregate_type="sucursal", aggregate_id=1, consumer="fixture_511",
            op_id=op_id, aggregate_uid=aggregate_uid,
            payload={"uid_global": "same"},
            provenance={"installation_uid": "origin"}, version_registro=1,
        )
        repo.mark_pending_dependency(
            event_id=event_id, consumer="fixture_511",
            reason_code="SYNC_DEPENDENCY_UNAVAILABLE",
            next_attempt_at=datetime.now(UTC),
        )
    calls = []
    processor = _processor(db_session, consumer="fixture_511")
    for index, event_id in enumerate(deliveries):
        processor.run_once(
            lambda event: calls.append(event["event_id"])
            or InboxOutcome(InboxOutcomeKind.PROCESSED),
            worker_id=f"initial-{index}", event_id=event_id, manual=True,
        )
    assert calls == [deliveries[0]]
    assert [repo.get(event_id=item, consumer="fixture_511")["status"]
            for item in deliveries] == ["PROCESSED", "PROCESSED"]


def test_operation_scope_takeover_no_depende_de_lock_stale():
    consumer = f"scope-takeover-{uuid4()}"
    event_id, op_id = _committed_pending(consumer=consumer)
    with Session(engine) as first:
        repo_a = InboxRepository(first)
        delivery_a = repo_a.claim_pending(
            consumer=consumer, lease_owner="worker-a", lease_duration=timedelta(minutes=5),
            automatic_attempt_limit=8, event_id=event_id, manual=True,
        )
        first.commit()
        scope_a = repo_a.claim_operation_scope(
            consumer=consumer, op_id=op_id,
            payload_fingerprint=delivery_a["payload_fingerprint"],
            lease_owner="worker-a", lease_expires_at=delivery_a["lease_expires_at"],
        )
        first.commit()
    with Session(engine) as expire:
        expire.execute(text("""UPDATE inbox_event SET lease_expires_at=
            (clock_timestamp() AT TIME ZONE 'UTC') - interval '1 second'
            WHERE event_id=CAST(:event_id AS uuid)"""), {"event_id": event_id})
        expire.execute(text("""UPDATE inbox_operation_scope SET lease_expires_at=
            (clock_timestamp() AT TIME ZONE 'UTC') - interval '1 second'
            WHERE consumer=:consumer AND op_id=CAST(:op_id AS uuid)"""),
            {"consumer": consumer, "op_id": op_id})
        expire.commit()
    with Session(engine) as second:
        repo_b = InboxRepository(second)
        assert repo_b.reclaim_expired(consumer=consumer) == 1
        second.commit()
        delivery_b = repo_b.claim_pending(
            consumer=consumer, lease_owner="worker-b", lease_duration=timedelta(minutes=5),
            automatic_attempt_limit=8, event_id=event_id, manual=True,
        )
        second.commit()
        scope_b = repo_b.claim_operation_scope(
            consumer=consumer, op_id=op_id,
            payload_fingerprint=delivery_b["payload_fingerprint"],
            lease_owner="worker-b", lease_expires_at=delivery_b["lease_expires_at"],
        )
        second.commit()
        assert scope_b["acquired"] is True
        assert scope_b["lease_generation"] == scope_a["lease_generation"] + 1
        repo_b.finish_operation_scope(
            consumer=consumer, op_id=op_id, lease_owner="worker-b",
            lease_generation=scope_b["lease_generation"], terminal_status="PROCESSED",
        )
        second.commit()
    with Session(engine) as stale:
        with pytest.raises(InboxOwnershipLost):
            InboxRepository(stale).finish_operation_scope(
                consumer=consumer, op_id=op_id, lease_owner="worker-a",
                lease_generation=scope_a["lease_generation"],
                terminal_status="PROCESSED",
            )


def test_backoff_se_programa_desde_finalizacion_db(db_session):
    event_id = _pending(db_session)
    processor = _processor(db_session, consumer="fixture_511")
    db_before = db_session.execute(text(
        "SELECT clock_timestamp() AT TIME ZONE 'UTC'"
    )).scalar_one()
    outcome = processor.run_once(
        lambda _: InboxOutcome(
            InboxOutcomeKind.PENDING_DEPENDENCY, "SYNC_DEPENDENCY_UNAVAILABLE"
        ),
        worker_id="completion-clock", event_id=event_id, manual=True,
        now=datetime.now(UTC) - timedelta(days=1),
    )
    row = InboxRepository(db_session).get(event_id=event_id, consumer="fixture_511")
    assert outcome.kind is InboxOutcomeKind.PENDING_DEPENDENCY
    assert row["next_attempt_at"] >= db_before + retry_backoff(row["attempt_count"])
    assert InboxRepository(db_session).claim_pending(
        consumer="fixture_511", lease_owner="automatic",
        lease_duration=timedelta(minutes=5), automatic_attempt_limit=8,
        event_id=event_id,
    ) is None
    assert InboxRepository(db_session).claim_pending(
        consumer="fixture_511", lease_owner="manual",
        lease_duration=timedelta(minutes=5), automatic_attempt_limit=8,
        event_id=event_id, manual=True,
    ) is not None


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
        _set_lease_from_db_clock(
            second, event_id=event_id, delta=-timedelta(seconds=1),
        )
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
                    _set_lease_from_db_clock(
                        takeover, event_id=event_id, delta=-timedelta(seconds=1),
                    )
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
        _set_lease_from_db_clock(
            session, event_id=event_id, delta=-timedelta(seconds=1),
        )
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
        _set_lease_from_db_clock(
            claim_session, event_id=expired_event, delta=-timedelta(seconds=1),
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
