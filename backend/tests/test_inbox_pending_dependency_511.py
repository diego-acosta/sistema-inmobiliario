from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Event
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.common.idempotency import NonCanonicalizablePayload
from app.application.common.synchronization_policy import SensitiveSyncPayload
from app.application.integration.inbox_retry import (
    InboxOutcome,
    InboxOutcomeKind,
    InboxRetryProcessor,
    retry_backoff,
)
from app.config.database import engine
from app.infrastructure.persistence.repositories.inbox_repository import (
    DeliveryClaim,
    InboxInvalidFingerprint,
    InboxInvalidPortableTarget,
    InboxInvalidVersion,
    InboxOperationIdRequired,
    InboxOwnershipLost,
    InboxPortableTargetRequired,
    InboxRepository,
    OperationClaim,
    OperationDecision,
)


def _register(
    db,
    *,
    consumer: str,
    op_id: str | None = None,
    aggregate_uid: str | None = None,
    payload=None,
    provenance=None,
    event_id: str | None = None,
    version_registro=1,
) -> tuple[str, str]:
    event_id = event_id or str(uuid4())
    op_id = op_id or str(uuid4())
    assert InboxRepository(db).claim(
        event_id=event_id,
        event_type="sucursal_creada",
        aggregate_type="sucursal",
        aggregate_id=1,
        consumer=consumer,
        op_id=op_id,
        aggregate_uid=aggregate_uid or str(uuid4()),
        payload=payload or {"uid_global": "target-511"},
        provenance=provenance or {"installation_uid": "origin-511"},
        version_registro=version_registro,
    )
    return event_id, op_id


def _committed_delivery(*, consumer: str, **kwargs) -> tuple[str, str]:
    with Session(engine) as session:
        result = _register(session, consumer=consumer, **kwargs)
        session.commit()
        return result


def _claim(
    db,
    *,
    consumer: str,
    event_id: str,
    worker_id: str = "worker",
    lease=timedelta(minutes=5),
) -> DeliveryClaim:
    claim = InboxRepository(db).claim_pending(
        consumer=consumer,
        worker_id=worker_id,
        lease_duration=lease,
        automatic_attempt_limit=8,
        event_id=event_id,
        manual=True,
    )
    assert claim is not None
    return claim


def _expire_delivery(db, event_id: str) -> None:
    db.execute(
        text("""
        UPDATE inbox_event
           SET lease_expires_at=(clock_timestamp() AT TIME ZONE 'UTC') - interval '1 second'
         WHERE event_id=CAST(:event_id AS uuid)
    """),
        {"event_id": event_id},
    )


def _expire_scope(db, *, consumer: str, op_id: str) -> None:
    db.execute(
        text("""
        UPDATE inbox_operation_scope
           SET lease_expires_at=(clock_timestamp() AT TIME ZONE 'UTC') - interval '1 second'
         WHERE consumer=:consumer AND op_id=CAST(:op_id AS uuid)
    """),
        {"consumer": consumer, "op_id": op_id},
    )


def test_patch_materializa_identidades_separadas(db_session):
    event_columns = set(
        db_session.execute(
            text("""
        SELECT column_name FROM information_schema.columns
         WHERE table_schema='public' AND table_name='inbox_event'
    """)
        ).scalars()
    )
    assert {
        "op_id",
        "aggregate_uid",
        "payload",
        "payload_fingerprint",
        "attempt_id",
        "worker_id",
        "lease_expires_at",
        "fence_generation",
        "attempt_count",
        "next_attempt_at",
    } <= event_columns
    scope_columns = set(
        db_session.execute(
            text("""
        SELECT column_name FROM information_schema.columns
         WHERE table_schema='public' AND table_name='inbox_operation_scope'
    """)
        ).scalars()
    )
    assert {
        "consumer",
        "op_id",
        "payload_fingerprint",
        "attempt_id",
        "worker_id",
        "lease_expires_at",
        "fence_generation",
        "terminal_status",
    } <= scope_columns


def test_patch_migra_scope_historico_y_falla_ante_constraint_desconocido():
    patch = Path("database/patch_inbox_pending_dependency_20260822.sql").read_text()
    conninfo = engine.url.render_as_string(hide_password=False).replace(
        "postgresql+psycopg", "postgresql"
    )
    constraint_name = "ck_inbox_operation_scope_terminal_511"
    final_constraint_sql = f"""
        ALTER TABLE inbox_operation_scope
        ADD CONSTRAINT {constraint_name}
        CHECK (
            terminal_status IS NULL
            OR terminal_status IN ('PROCESSED', 'CONFLICTO')
        )
    """

    with psycopg.connect(conninfo, autocommit=True) as connection:
        connection.execute(patch)
        connection.execute(patch)
        terminal_rows = connection.execute("""
            SELECT consumer, op_id, terminal_status
              FROM inbox_operation_scope
             WHERE terminal_status IS NOT NULL
        """).fetchall()

        try:
            # La variante historica solo admite NULL. Los receipts ajenos se
            # preservan y se restauran exactamente despues de mutar el schema.
            connection.execute("""
                UPDATE inbox_operation_scope
                   SET terminal_status = NULL
                 WHERE terminal_status IS NOT NULL
            """)
            connection.execute(
                f"ALTER TABLE inbox_operation_scope "
                f"DROP CONSTRAINT {constraint_name}"
            )
            connection.execute(
                f"ALTER TABLE inbox_operation_scope "
                f"ADD CONSTRAINT {constraint_name} "
                "CHECK (terminal_status IS NULL)"
            )
            connection.execute(patch)
            definition = connection.execute(
                """
                SELECT pg_get_constraintdef(oid)
                  FROM pg_constraint
                 WHERE conrelid='inbox_operation_scope'::regclass
                   AND conname=%s
                """,
                (constraint_name,),
            ).fetchone()[0]
            assert "PROCESSED" in definition
            assert "CONFLICTO" in definition

            connection.execute(
                f"ALTER TABLE inbox_operation_scope "
                f"DROP CONSTRAINT {constraint_name}"
            )
            connection.execute(
                f"ALTER TABLE inbox_operation_scope "
                f"ADD CONSTRAINT {constraint_name} "
                "CHECK (terminal_status IS NULL "
                "OR terminal_status = 'PROCESSED')"
            )
            with pytest.raises(psycopg.Error):
                connection.execute(patch)
        finally:
            # El patch fallido deja su BEGIN abortado aun con autocommit.
            # Recuperar primero la conexion y restaurar siempre el contrato final.
            connection.execute("ROLLBACK")
            connection.execute(
                f"ALTER TABLE inbox_operation_scope "
                f"DROP CONSTRAINT IF EXISTS {constraint_name}"
            )
            connection.execute(final_constraint_sql)
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    UPDATE inbox_operation_scope
                       SET terminal_status = %s
                     WHERE consumer = %s
                       AND op_id = %s
                    """,
                    [
                        (terminal_status, consumer, op_id)
                        for consumer, op_id, terminal_status in terminal_rows
                    ],
                )

        definition = connection.execute(
            """
            SELECT pg_get_constraintdef(oid)
              FROM pg_constraint
             WHERE conrelid='inbox_operation_scope'::regclass
               AND conname=%s
            """,
            (constraint_name,),
        ).fetchone()[0]
        assert "PROCESSED" in definition
        assert "CONFLICTO" in definition


def test_scope_terminal_acepta_conjunto_cerrado_y_rechaza_otro(db_session):
    for terminal in (None, "PROCESSED", "CONFLICTO"):
        db_session.execute(
            text("""
                INSERT INTO inbox_operation_scope (
                    consumer, op_id, payload_fingerprint, terminal_status
                ) VALUES (
                    :consumer, CAST(:op_id AS uuid), :fingerprint,
                    CAST(:terminal AS varchar)
                )
            """),
            {
                "consumer": f"terminal-{terminal}",
                "op_id": str(uuid4()),
                "fingerprint": "a" * 64,
                "terminal": terminal,
            },
        )
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text("""
                INSERT INTO inbox_operation_scope (
                    consumer, op_id, payload_fingerprint, terminal_status
                ) VALUES (
                    'terminal-invalid', CAST(:op_id AS uuid), :fingerprint, 'REJECTED'
                )
            """),
            {"op_id": str(uuid4()), "fingerprint": "b" * 64},
        )


@pytest.mark.parametrize(
    "terminal",
    ["PENDING_DEPENDENCY", "PROCESSED", "REJECTED", "CONFLICTO"],
)
def test_transition_tipado_funciona_para_todos_los_estados(terminal):
    consumer = f"transition-{terminal}-{uuid4()}"
    event_id, _ = _committed_delivery(consumer=consumer)
    with Session(engine) as session:
        repo = InboxRepository(session)
        claim = _claim(session, consumer=consumer, event_id=event_id)
        session.commit()
        if terminal == "PENDING_DEPENDENCY":
            repo.mark_pending_dependency(
                claim=claim,
                reason_code="SYNC_DEPENDENCY_UNAVAILABLE",
                retry_delay=timedelta(seconds=30),
            )
        elif terminal == "PROCESSED":
            repo.mark_as_processed(claim=claim)
        elif terminal == "REJECTED":
            repo.mark_as_rejected(claim=claim, error_detail="SYNC_PAYLOAD_INVALID")
        else:
            repo.mark_conflict(claim=claim)
        session.commit()
    with Session(engine) as verify:
        assert InboxRepository(verify).get(
            event_id=event_id, consumer=consumer
        )["status"] == terminal


def test_claim_portable_registra_pending_sin_otorgar_ownership(db_session):
    event_id, _ = _register(db_session, consumer="registration")
    row = InboxRepository(db_session).get(event_id=event_id, consumer="registration")
    assert row["status"] == "PENDING_DEPENDENCY"
    assert row["attempt_id"] is None
    assert row["worker_id"] is None


def test_claim_legacy_payloadless_preserva_compatibilidad(db_session):
    event_id = str(uuid4())
    repo = InboxRepository(db_session)
    assert repo.claim(
        event_id=event_id,
        event_type="sucursal_creada",
        aggregate_type="sucursal",
        aggregate_id=1,
        consumer="legacy",
    )
    row = repo.get(event_id=event_id, consumer="legacy")
    assert row["status"] == "PROCESSING"
    assert all(
        row[field] is None
        for field in (
            "op_id",
            "aggregate_uid",
            "version_registro",
            "payload",
            "payload_fingerprint",
            "provenance",
        )
    )
    repo.mark_as_processed(event_id=event_id, consumer="legacy")
    assert repo.is_processed(event_id=event_id, consumer="legacy")


@pytest.mark.parametrize(
    "retained",
    [
        {"payload": {}},
        {"provenance": {}},
        {"aggregate_uid": "00000000-0000-0000-0000-000000000001"},
        {"version_registro": 1},
        {"payload": {}, "provenance": {}},
    ],
)
def test_claim_legacy_parcial_sin_op_id_se_rechaza_y_no_persiste(
    retained, db_session
):
    event_id = str(uuid4())
    with pytest.raises(InboxOperationIdRequired):
        InboxRepository(db_session).claim(
            event_id=event_id,
            event_type="sucursal_creada",
            aggregate_type="sucursal",
            aggregate_id=1,
            consumer="partial-legacy",
            **retained,
        )
    assert (
        InboxRepository(db_session).get(
            event_id=event_id, consumer="partial-legacy"
        )
        is None
    )


def test_constraint_rechaza_legacy_parcial_insertado_por_sql(db_session):
    event_id = str(uuid4())
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text("""
                INSERT INTO inbox_event (
                    event_id, event_type, aggregate_type, aggregate_id,
                    consumer, status, created_at, payload
                ) VALUES (
                    CAST(:event_id AS uuid), 'sucursal_creada', 'sucursal', 1,
                    'partial-legacy-sql', 'PROCESSING', now(), '{}'::jsonb
                )
            """),
            {"event_id": event_id},
        )


def test_envelope_canonicaliza_uuid_version_y_orden_json(db_session):
    op_id = str(uuid4())
    uid = str(uuid4())
    first, _ = _register(
        db_session,
        consumer="canonical",
        op_id=op_id,
        aggregate_uid=uid.upper(),
        version_registro="1",
        payload={"uid_global": "same", "nested": {"b": 2, "a": 1}},
    )
    second, _ = _register(
        db_session,
        consumer="canonical",
        op_id=op_id,
        aggregate_uid=uid,
        version_registro=1,
        payload={"nested": {"a": 1, "b": 2}, "uid_global": "same"},
    )
    repo = InboxRepository(db_session)
    assert repo.get(event_id=first, consumer="canonical")["version_registro"] == 1
    assert repo.get(event_id=second, consumer="canonical")["version_registro"] == 1
    assert (
        repo.get(event_id=first, consumer="canonical")["payload_fingerprint"]
        == repo.get(event_id=second, consumer="canonical")["payload_fingerprint"]
    )


@pytest.mark.parametrize("value", [True, 1.5, "1.5", "abc", ""])
def test_version_ambigua_se_rechaza(value, db_session):
    event_id = str(uuid4())
    with pytest.raises(InboxInvalidVersion):
        _register(
            db_session,
            consumer="bad-version",
            event_id=event_id,
            version_registro=value,
        )
    assert (
        InboxRepository(db_session).get(
            event_id=event_id, consumer="bad-version"
        )
        is None
    )


@pytest.mark.parametrize("value", [0, -1, "0", "-1"])
def test_version_no_positiva_no_persiste_ni_invoca_applicator(value, db_session):
    consumer = f"non-positive-version-{uuid4()}"
    event_id = str(uuid4())
    with pytest.raises(InboxInvalidVersion):
        _register(
            db_session,
            consumer=consumer,
            event_id=event_id,
            version_registro=value,
        )
    assert InboxRepository(db_session).get(event_id=event_id, consumer=consumer) is None

    calls = []
    outcome = InboxRetryProcessor(db_session, consumer=consumer).run_once(
        lambda event: (
            calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED)
        ),
        worker_id="worker",
        event_id=event_id,
        manual=True,
    )
    assert outcome is None
    assert calls == []


def test_constraint_rechaza_version_registro_no_positiva(db_session):
    event_id, _ = _register(db_session, consumer="version-constraint")
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text("""
                UPDATE inbox_event
                   SET version_registro = 0
                 WHERE event_id = CAST(:event_id AS uuid)
                   AND consumer = 'version-constraint'
            """),
            {"event_id": event_id},
        )


def test_sin_delivery_cierra_autobegin_sin_invocar_applicator():
    consumer = f"no-delivery-{uuid4()}"
    calls = []
    with Session(engine) as session:
        session.execute(text("SELECT 1"))
        assert session.in_transaction()

        outcome = InboxRetryProcessor(session, consumer=consumer).run_once(
            lambda event: (
                calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED)
            ),
            worker_id="worker",
            manual=True,
        )

        assert outcome is None
        assert not session.in_transaction()
    assert calls == []


def test_target_portable_es_obligatorio_y_uuid_valido(db_session):
    with pytest.raises(InboxPortableTargetRequired):
        InboxRepository(db_session).claim(
            event_id=str(uuid4()),
            event_type="sucursal_creada",
            aggregate_type="sucursal",
            aggregate_id=1,
            consumer="target",
            op_id=str(uuid4()),
            payload={"uid_global": "x"},
        )
    with pytest.raises(InboxInvalidPortableTarget):
        _register(db_session, consumer="target", aggregate_uid="not-a-uuid")


def test_payload_sensible_y_no_canonicalizable_no_se_persisten(db_session):
    with pytest.raises(SensitiveSyncPayload):
        _register(db_session, consumer="sensitive", payload={"password": "secret"})
    with pytest.raises(NonCanonicalizablePayload):
        _register(
            db_session, consumer="float", payload={"uid_global": "x", "value": 1.2}
        )


def test_fingerprint_adulterado_se_rechaza_antes_del_applicator(db_session):
    event_id, _ = _register(db_session, consumer="fingerprint")
    db_session.execute(
        text("""
        UPDATE inbox_event SET payload_fingerprint=:fingerprint
         WHERE event_id=CAST(:event_id AS uuid)
    """),
        {"fingerprint": "a" * 64, "event_id": event_id},
    )
    calls = []
    outcome = InboxRetryProcessor(
        db_session,
        consumer="fingerprint",
        lifecycle_session_factory=lambda: _NullSession(db_session),
    ).run_once(
        lambda event: calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED),
        worker_id="worker",
        event_id=event_id,
        manual=True,
    )
    assert outcome == InboxOutcome(
        InboxOutcomeKind.REJECTED, InboxInvalidFingerprint.code
    )
    assert calls == []


def test_dos_workers_misma_delivery_solo_un_claim_real():
    consumer = f"one-delivery-{uuid4()}"
    event_id, _ = _committed_delivery(consumer=consumer)
    barrier = Barrier(2)

    def claim(worker):
        with Session(engine) as session:
            barrier.wait(timeout=5)
            result = InboxRepository(session).claim_pending(
                consumer=consumer,
                worker_id=worker,
                lease_duration=timedelta(minutes=5),
                automatic_attempt_limit=8,
                event_id=event_id,
                manual=True,
            )
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ["a", "b"]))
    winners = [item for item in results if item is not None]
    assert len(winners) == 1
    assert winners[0].attempt_id


def test_mismo_worker_dos_attempts_no_comparten_ownership():
    consumer = f"same-worker-{uuid4()}"
    op_id = str(uuid4())
    uid = str(uuid4())
    first, _ = _committed_delivery(consumer=consumer, op_id=op_id, aggregate_uid=uid)
    second, _ = _committed_delivery(consumer=consumer, op_id=op_id, aggregate_uid=uid)
    with Session(engine) as session:
        repo = InboxRepository(session)
        attempt_a = _claim(session, consumer=consumer, event_id=first, worker_id="W")
        session.commit()
        acquired = repo.acquire_operation_scope(delivery=attempt_a)
        session.commit()
        attempt_b = _claim(session, consumer=consumer, event_id=second, worker_id="W")
        session.commit()
        busy = repo.acquire_operation_scope(delivery=attempt_b)
        session.commit()
        assert attempt_a.attempt_id != attempt_b.attempt_id
        assert acquired.decision is OperationDecision.ACQUIRED
        assert busy.decision is OperationDecision.BUSY
        assert acquired.claim is not None
        foreign = OperationClaim(
            consumer, op_id, attempt_b.attempt_id, acquired.claim.fence_generation
        )
        with pytest.raises(InboxOwnershipLost):
            repo.finish_operation_scope(claim=foreign, terminal_status=None)
        session.rollback()


def test_busy_no_toca_scope_ni_consume_attempt_budget():
    consumer = f"busy-{uuid4()}"
    op_id = str(uuid4())
    uid = str(uuid4())
    owner, _ = _committed_delivery(consumer=consumer, op_id=op_id, aggregate_uid=uid)
    follower, _ = _committed_delivery(consumer=consumer, op_id=op_id, aggregate_uid=uid)
    with Session(engine) as session:
        repo = InboxRepository(session)
        owner_claim = _claim(
            session, consumer=consumer, event_id=owner, worker_id="owner"
        )
        session.commit()
        decision = repo.acquire_operation_scope(delivery=owner_claim)
        session.commit()
        before = repo.get_operation_scope(consumer=consumer, op_id=op_id)
    calls = []
    with Session(engine) as follower_session:
        result = InboxRetryProcessor(follower_session, consumer=consumer).run_once(
            lambda event: (
                calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED)
            ),
            worker_id="follower",
            event_id=follower,
            manual=True,
        )
    with Session(engine) as verify:
        after = InboxRepository(verify).get_operation_scope(
            consumer=consumer, op_id=op_id
        )
        follower_row = InboxRepository(verify).get(event_id=follower, consumer=consumer)
    assert result.kind is InboxOutcomeKind.PENDING_DEPENDENCY
    assert calls == []
    assert after["attempt_id"] == before["attempt_id"]
    assert after["fence_generation"] == before["fence_generation"]
    assert follower_row["attempt_count"] == 0
    assert decision.claim is not None


@pytest.mark.parametrize(
    "terminal", [InboxOutcomeKind.PROCESSED, InboxOutcomeKind.CONFLICTO]
)
def test_compatible_processed_y_conflict_se_replayan_sin_applicator(
    db_session, terminal
):
    consumer = f"replay-{terminal}-{uuid4()}"
    op_id = str(uuid4())
    uid = str(uuid4())
    first, _ = _register(db_session, consumer=consumer, op_id=op_id, aggregate_uid=uid)
    second, _ = _register(db_session, consumer=consumer, op_id=op_id, aggregate_uid=uid)
    processor = InboxRetryProcessor(
        db_session,
        consumer=consumer,
        lifecycle_session_factory=lambda: _NullSession(db_session),
    )
    calls = []
    requested = InboxOutcome(
        terminal,
        "SYNC_OPERATION_CONFLICT" if terminal is InboxOutcomeKind.CONFLICTO else None,
    )
    assert (
        processor.run_once(
            lambda event: calls.append(event) or requested,
            worker_id="first",
            event_id=first,
            manual=True,
        ).kind
        is terminal
    )
    assert (
        processor.run_once(
            lambda event: (
                calls.append(event) or InboxOutcome(InboxOutcomeKind.PROCESSED)
            ),
            worker_id="replay",
            event_id=second,
            manual=True,
        ).kind
        is terminal
    )
    assert len(calls) == 1


class _NullSession:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, *_):
        return False


def test_incompatible_no_ejecuta_segundo_applicator(db_session):
    consumer = "incompatible"
    op_id = str(uuid4())
    uid = str(uuid4())
    first, _ = _register(
        db_session,
        consumer=consumer,
        op_id=op_id,
        aggregate_uid=uid,
        payload={"uid_global": "a"},
    )
    second, _ = _register(
        db_session,
        consumer=consumer,
        op_id=op_id,
        aggregate_uid=uid,
        payload={"uid_global": "b"},
    )
    processor = InboxRetryProcessor(
        db_session,
        consumer=consumer,
        lifecycle_session_factory=lambda: _NullSession(db_session),
    )
    calls = []
    processor.run_once(
        lambda event: (
            calls.append(event["event_id"]) or InboxOutcome(InboxOutcomeKind.PROCESSED)
        ),
        worker_id="first",
        event_id=first,
        manual=True,
    )
    outcome = processor.run_once(
        lambda event: (
            calls.append(event["event_id"]) or InboxOutcome(InboxOutcomeKind.PROCESSED)
        ),
        worker_id="second",
        event_id=second,
        manual=True,
    )
    assert outcome.kind is InboxOutcomeKind.CONFLICTO
    assert calls == [first]


def test_same_worker_takeover_genera_attempt_y_fence_nuevos():
    consumer = f"takeover-{uuid4()}"
    event_id, op_id = _committed_delivery(consumer=consumer)
    with Session(engine) as first_session:
        repo = InboxRepository(first_session)
        attempt_a = _claim(
            first_session, consumer=consumer, event_id=event_id, worker_id="W"
        )
        first_session.commit()
        operation_a = repo.acquire_operation_scope(delivery=attempt_a)
        first_session.commit()
    with Session(engine) as expire:
        _expire_delivery(expire, event_id)
        _expire_scope(expire, consumer=consumer, op_id=op_id)
        expire.commit()
    with Session(engine) as second_session:
        repo = InboxRepository(second_session)
        attempt_b = _claim(
            second_session, consumer=consumer, event_id=event_id, worker_id="W"
        )
        second_session.commit()
        operation_b = repo.acquire_operation_scope(delivery=attempt_b)
        second_session.commit()
    assert operation_a.claim and operation_b.claim
    assert attempt_a.attempt_id != attempt_b.attempt_id
    assert operation_b.claim.fence_generation == operation_a.claim.fence_generation + 1
    with Session(engine) as stale, pytest.raises(InboxOwnershipLost):
        InboxRepository(stale).finish_operation_scope(
            claim=operation_a.claim, terminal_status="PROCESSED"
        )
    with Session(engine) as stale, pytest.raises(InboxOwnershipLost):
        InboxRepository(stale).mark_as_processed(claim=attempt_a)


def test_otra_delivery_no_revoca_owner_vencido_sin_takeover():
    consumer = f"targeted-{uuid4()}"
    owned_event, owned_op = _committed_delivery(consumer=consumer)
    other_event, _ = _committed_delivery(consumer=consumer)
    applicator_started = Event()
    allow_owner_finish = Event()
    owner_result = {}

    def owner_worker():
        with Session(engine) as session:
            def applicator(_):
                applicator_started.set()
                assert allow_owner_finish.wait(timeout=10)
                return InboxOutcome(InboxOutcomeKind.PROCESSED)

            owner_result["outcome"] = InboxRetryProcessor(
                session, consumer=consumer
            ).run_once(
                applicator, worker_id="owner", event_id=owned_event, manual=True
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(owner_worker)
        assert applicator_started.wait(timeout=10)
        with Session(engine) as expire:
            before = InboxRepository(expire).get(
                event_id=owned_event, consumer=consumer
            )
            _expire_delivery(expire, owned_event)
            _expire_scope(expire, consumer=consumer, op_id=owned_op)
            expire.commit()
        with Session(engine) as other:
            outcome = InboxRetryProcessor(other, consumer=consumer).run_once(
                lambda _: InboxOutcome(InboxOutcomeKind.PROCESSED),
                worker_id="other",
                event_id=other_event,
                manual=True,
            )
        assert outcome.kind is InboxOutcomeKind.PROCESSED
        with Session(engine) as verify:
            current = InboxRepository(verify).get(
                event_id=owned_event, consumer=consumer
            )
            assert current["status"] == "PROCESSING"
            assert current["attempt_id"] == before["attempt_id"]
            assert current["fence_generation"] == before["fence_generation"]
        allow_owner_finish.set()
        future.result(timeout=10)
    assert owner_result["outcome"].kind is InboxOutcomeKind.PROCESSED


def test_dos_threads_compiten_por_takeover_y_solo_uno_adquiere():
    consumer = f"takeover-race-{uuid4()}"
    event_id, _ = _committed_delivery(consumer=consumer)
    with Session(engine) as first:
        attempt_a = _claim(first, consumer=consumer, event_id=event_id)
        first.commit()
    with Session(engine) as expire:
        _expire_delivery(expire, event_id)
        expire.commit()
    barrier = Barrier(2)

    def takeover(worker_id):
        with Session(engine) as session:
            barrier.wait(timeout=5)
            claim = InboxRepository(session).claim_pending(
                consumer=consumer,
                worker_id=worker_id,
                lease_duration=timedelta(minutes=5),
                automatic_attempt_limit=8,
                event_id=event_id,
                manual=True,
            )
            session.commit()
            return claim

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(takeover, ["B", "C"]))
    winners = [claim for claim in results if claim is not None]
    assert len(winners) == 1
    assert winners[0].attempt_id != attempt_a.attempt_id
    assert winners[0].fence_generation == attempt_a.fence_generation + 1


def test_takeover_automatico_respeta_limite_y_manual_lo_sobrepasa():
    consumer = f"takeover-limit-{uuid4()}"
    event_id, _ = _committed_delivery(consumer=consumer)
    with Session(engine) as first:
        attempt_a = _claim(first, consumer=consumer, event_id=event_id)
        first.commit()
    with Session(engine) as expire:
        _expire_delivery(expire, event_id)
        expire.commit()
    with Session(engine) as automatic:
        assert (
            InboxRepository(automatic).claim_pending(
                consumer=consumer,
                worker_id="automatic",
                lease_duration=timedelta(minutes=5),
                automatic_attempt_limit=1,
                event_id=event_id,
                manual=False,
            )
            is None
        )
        automatic.commit()
    with Session(engine) as manual:
        attempt_b = InboxRepository(manual).claim_pending(
            consumer=consumer,
            worker_id="manual",
            lease_duration=timedelta(minutes=5),
            automatic_attempt_limit=1,
            event_id=event_id,
            manual=True,
        )
        manual.commit()
    assert attempt_b is not None
    assert attempt_b.attempt_id != attempt_a.attempt_id
    assert attempt_b["attempt_count"] == 2


def test_takeover_no_expone_pending_sin_owner_entre_update_y_commit():
    consumer = f"takeover-visible-{uuid4()}"
    event_id, _ = _committed_delivery(consumer=consumer)
    with Session(engine) as first:
        attempt_a = _claim(first, consumer=consumer, event_id=event_id)
        first.commit()
    with Session(engine) as expire:
        _expire_delivery(expire, event_id)
        expire.commit()
    update_done = Event()
    allow_commit = Event()
    successor = {}

    def takeover():
        with Session(engine) as session:
            successor["claim"] = _claim(
                session, consumer=consumer, event_id=event_id, worker_id="B"
            )
            update_done.set()
            assert allow_commit.wait(timeout=10)
            session.commit()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(takeover)
        assert update_done.wait(timeout=10)
        with Session(engine) as observer:
            visible = InboxRepository(observer).get(
                event_id=event_id, consumer=consumer
            )
            assert visible["status"] == "PROCESSING"
            assert visible["attempt_id"] == attempt_a.attempt_id
        allow_commit.set()
        future.result(timeout=10)
    with Session(engine) as observer:
        visible = InboxRepository(observer).get(event_id=event_id, consumer=consumer)
    assert visible["status"] == "PROCESSING"
    assert visible["attempt_id"] == successor["claim"].attempt_id
    assert visible["attempt_id"] != attempt_a.attempt_id
    assert visible["fence_generation"] == attempt_a.fence_generation + 1


def test_takeover_fencea_effect_receipt_y_delivery_del_attempt_anterior():
    consumer = f"real-fence-{uuid4()}"
    event_id, op_id = _committed_delivery(consumer=consumer)
    table = f"effect_{uuid4().hex}"
    with engine.begin() as setup:
        setup.execute(text(f"CREATE TABLE {table} (op_id uuid PRIMARY KEY)"))
    applicator_started = Event()
    allow_stale_finish = Event()
    stale_result = {}

    def stale_worker():
        with Session(engine) as session:
            processor = InboxRetryProcessor(session, consumer=consumer)

            def applicator(_):
                session.execute(
                    text(f"INSERT INTO {table} VALUES (CAST(:op AS uuid))"),
                    {"op": op_id},
                )
                applicator_started.set()
                assert allow_stale_finish.wait(timeout=10)
                return InboxOutcome(InboxOutcomeKind.PROCESSED)

            try:
                processor.run_once(
                    applicator, worker_id="W", event_id=event_id, manual=True
                )
            except InboxOwnershipLost:
                stale_result["fenced"] = True

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(stale_worker)
            assert applicator_started.wait(timeout=10)
            with Session(engine) as takeover:
                _expire_delivery(takeover, event_id)
                _expire_scope(takeover, consumer=consumer, op_id=op_id)
                takeover.commit()
                repo = InboxRepository(takeover)
                attempt_b = _claim(
                    takeover, consumer=consumer, event_id=event_id, worker_id="W"
                )
                takeover.commit()
                operation_b = repo.acquire_operation_scope(delivery=attempt_b)
                takeover.commit()
                assert operation_b.decision is OperationDecision.ACQUIRED
            allow_stale_finish.set()
            future.result(timeout=10)
        assert stale_result == {"fenced": True}
        with Session(engine) as owner:
            # B ya posee ambos claims; finaliza directamente en la misma transacción funcional.
            owner.execute(
                text(f"INSERT INTO {table} VALUES (CAST(:op AS uuid))"), {"op": op_id}
            )
            assert operation_b.claim is not None
            InboxRepository(owner).finish_operation_scope(
                claim=operation_b.claim, terminal_status="PROCESSED"
            )
            InboxRepository(owner).mark_as_processed(claim=attempt_b)
            owner.commit()
        with Session(engine) as verify:
            assert (
                verify.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 1
            )
            assert (
                InboxRepository(verify).get(event_id=event_id, consumer=consumer)[
                    "status"
                ]
                == "PROCESSED"
            )
    finally:
        with engine.begin() as cleanup:
            cleanup.execute(text(f"DROP TABLE IF EXISTS {table}"))


def test_pending_revierte_efecto_y_programa_backoff_desde_db():
    consumer = f"pending-{uuid4()}"
    event_id, op_id = _committed_delivery(consumer=consumer)
    table = f"effect_{uuid4().hex}"
    with engine.begin() as setup:
        setup.execute(text(f"CREATE TABLE {table} (op_id uuid PRIMARY KEY)"))
    try:
        with Session(engine) as session:

            def applicator(_):
                session.execute(
                    text(f"INSERT INTO {table} VALUES (CAST(:op AS uuid))"),
                    {"op": op_id},
                )
                return InboxOutcome(
                    InboxOutcomeKind.PENDING_DEPENDENCY,
                    "SYNC_DEPENDENCY_UNAVAILABLE",
                )

            before = session.execute(
                text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")
            ).scalar_one()
            outcome = InboxRetryProcessor(session, consumer=consumer).run_once(
                applicator, worker_id="worker", event_id=event_id, manual=True
            )
        with Session(engine) as verify:
            row = InboxRepository(verify).get(event_id=event_id, consumer=consumer)
            assert (
                verify.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
            )
        assert outcome.kind is InboxOutcomeKind.PENDING_DEPENDENCY
        assert row["next_attempt_at"] >= before + retry_backoff(1)
    finally:
        with engine.begin() as cleanup:
            cleanup.execute(text(f"DROP TABLE IF EXISTS {table}"))


def test_applicator_exception_rollbackea_y_no_deja_transaccion_abierta():
    consumer = f"exception-{uuid4()}"
    event_id, op_id = _committed_delivery(consumer=consumer)
    table = f"effect_{uuid4().hex}"
    with engine.begin() as setup:
        setup.execute(text(f"CREATE TABLE {table} (op_id uuid PRIMARY KEY)"))
    try:
        with Session(engine) as session:

            def applicator(_):
                session.execute(
                    text(f"INSERT INTO {table} VALUES (CAST(:op AS uuid))"),
                    {"op": op_id},
                )
                raise RuntimeError("boom")

            with pytest.raises(RuntimeError, match="boom"):
                InboxRetryProcessor(session, consumer=consumer).run_once(
                    applicator, worker_id="worker", event_id=event_id, manual=True
                )
            assert session.in_transaction() is False
        with Session(engine) as verify:
            assert (
                verify.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
            )
    finally:
        with engine.begin() as cleanup:
            cleanup.execute(text(f"DROP TABLE IF EXISTS {table}"))


def test_commit_exterior_fallido_no_deja_efecto_receipt_ni_delivery_terminal(
    monkeypatch,
):
    consumer = f"commit-failure-{uuid4()}"
    event_id, op_id = _committed_delivery(consumer=consumer)
    table = f"effect_{uuid4().hex}"
    with engine.begin() as setup:
        setup.execute(text(f"CREATE TABLE {table} (op_id uuid PRIMARY KEY)"))
    try:
        with Session(engine) as session:
            real_commit = session.commit
            commit_calls = 0

            def fail_functional_commit():
                nonlocal commit_calls
                commit_calls += 1
                raise RuntimeError("forced commit failure")

            monkeypatch.setattr(session, "commit", fail_functional_commit)

            def applicator(_):
                session.execute(
                    text(f"INSERT INTO {table} VALUES (CAST(:op AS uuid))"),
                    {"op": op_id},
                )
                return InboxOutcome(InboxOutcomeKind.PROCESSED)

            with pytest.raises(RuntimeError, match="forced commit failure"):
                InboxRetryProcessor(session, consumer=consumer).run_once(
                    applicator, worker_id="worker", event_id=event_id, manual=True
                )
            assert commit_calls == 1
            assert session.in_transaction() is False
            monkeypatch.setattr(session, "commit", real_commit)
        with Session(engine) as verify:
            assert (
                verify.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
            )
            delivery = InboxRepository(verify).get(event_id=event_id, consumer=consumer)
            scope = InboxRepository(verify).get_operation_scope(
                consumer=consumer, op_id=op_id
            )
            assert delivery["status"] == "PROCESSING"
            assert scope["terminal_status"] is None
    finally:
        with engine.begin() as cleanup:
            cleanup.execute(text(f"DROP TABLE IF EXISTS {table}"))


def test_crash_despues_del_delivery_claim_es_reclaimable_por_mismo_worker():
    consumer = f"crash-claim-{uuid4()}"
    event_id, _ = _committed_delivery(consumer=consumer)
    with Session(engine) as crashed:
        attempt_a = _claim(crashed, consumer=consumer, event_id=event_id, worker_id="W")
        crashed.commit()
    with Session(engine) as recover:
        _expire_delivery(recover, event_id)
        recover.commit()
        attempt_b = _claim(recover, consumer=consumer, event_id=event_id, worker_id="W")
        recover.commit()
    assert attempt_a.attempt_id != attempt_b.attempt_id


def test_dos_deliveries_iniciales_concurrentes_un_solo_applicator():
    consumer = f"initial-{uuid4()}"
    op_id = str(uuid4())
    uid = str(uuid4())
    first, _ = _committed_delivery(consumer=consumer, op_id=op_id, aggregate_uid=uid)
    second, _ = _committed_delivery(consumer=consumer, op_id=op_id, aggregate_uid=uid)
    table = f"effect_{uuid4().hex}"
    with engine.begin() as setup:
        setup.execute(text(f"CREATE TABLE {table} (op_id uuid PRIMARY KEY)"))
    barrier = Barrier(2)

    def run(event_id):
        with Session(engine) as session:
            barrier.wait(timeout=5)

            def applicator(_):
                session.execute(
                    text(f"INSERT INTO {table} VALUES (CAST(:op AS uuid))"),
                    {"op": op_id},
                )
                return InboxOutcome(InboxOutcomeKind.PROCESSED)

            return InboxRetryProcessor(session, consumer=consumer).run_once(
                applicator, worker_id="W", event_id=event_id, manual=True
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(run, [first, second]))
        with Session(engine) as verify:
            assert (
                verify.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 1
            )
        assert {outcome.kind for outcome in outcomes} <= {
            InboxOutcomeKind.PROCESSED,
            InboxOutcomeKind.PENDING_DEPENDENCY,
        }
    finally:
        with engine.begin() as cleanup:
            cleanup.execute(text(f"DROP TABLE IF EXISTS {table}"))


def test_expiry_sin_takeover_no_revoca_magicamente(db_session):
    consumer = "expiry-only"
    event_id, _ = _register(db_session, consumer=consumer)
    delivery = _claim(
        db_session,
        consumer=consumer,
        event_id=event_id,
        lease=timedelta(seconds=1),
    )
    decision = InboxRepository(db_session).acquire_operation_scope(delivery=delivery)
    assert decision.claim is not None
    _expire_delivery(db_session, event_id)
    _expire_scope(db_session, consumer=consumer, op_id=delivery["op_id"])
    # Sin takeover el token/fence siguen siendo los mismos y el owner puede ganar.
    InboxRepository(db_session).finish_operation_scope(
        claim=decision.claim, terminal_status="PROCESSED"
    )
    InboxRepository(db_session).mark_as_processed(claim=delivery)


def test_lease_y_backoff_usan_reloj_db_no_now_del_worker(db_session):
    consumer = "db-clock"
    event_id, _ = _register(db_session, consumer=consumer)
    claim = InboxRepository(db_session).claim_pending(
        consumer=consumer,
        worker_id="worker",
        lease_duration=timedelta(minutes=5),
        automatic_attempt_limit=8,
        event_id=event_id,
        manual=True,
        now=datetime.now(UTC) + timedelta(days=365),
    )
    db_now = db_session.execute(
        text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")
    ).scalar_one()
    assert claim is not None
    assert (
        timedelta(minutes=4, seconds=50)
        <= claim["lease_expires_at"] - db_now
        <= timedelta(minutes=5)
    )
