from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, timedelta
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_administrativo_calendario_comercial_sync_486 import (
    _bootstrap_origin,
    _clear_calendar,
    _headers,
    _program_origin,
    _program_origin_v3,
    _rehash,
)

from app.application.administrativo.services.calendario_comercial_sync_service import (
    CALENDARIO_SYNC_CONSUMER,
    CalendarioComercialSyncApplicator,
    register_calendario_outbox_delivery,
    run_calendario_inbox_once,
    transport_calendario_outbox_once,
)
from app.application.administrativo.services.obtener_configuracion_calendario_comercial_query_service import (
    ObtenerConfiguracionCalendarioComercialQueryService,
)
from app.application.administrativo.services.programar_calendario_comercial_service import (
    ProgramarCalendarioComercialError,
    ProgramarCalendarioComercialService,
)
from app.application.integration.inbox_retry import (
    InboxOutcomeKind,
    InboxRetryProcessor,
)
from app.config.database import engine as shared_test_engine
from app.infrastructure.persistence.repositories.calendario_comercial_query_repository import (
    CalendarioComercialQueryRepository,
)
from app.infrastructure.persistence.repositories.inbox_repository import (
    InboxOwnershipLost,
    InboxRepository,
)


def _shared_database_state() -> tuple[tuple[int, str], ...]:
    selections = (
        "SELECT * FROM configuracion_calendario_comercial",
        """
        SELECT v.*
          FROM valor_parametro v
          JOIN parametro_sistema p USING(id_parametro_sistema)
         WHERE p.codigo_parametro IN
           ('DIA_CIERRE_COMERCIAL',
            'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
        """,
        "SELECT * FROM outbox_event",
        "SELECT * FROM inbox_event",
        "SELECT * FROM inbox_operation_scope",
        "SELECT * FROM operacion_idempotente",
    )
    with shared_test_engine.connect() as connection:
        return tuple(
            tuple(
                connection.execute(
                    text(f"""
                    SELECT count(*),
                           md5(COALESCE(string_agg(
                               to_jsonb(snapshot_row)::text,
                               E'\\n' ORDER BY to_jsonb(snapshot_row)::text
                           ), ''))
                      FROM ({selection}) AS snapshot_row
                    """)
                ).one()
            )
            for selection in selections
        )


@pytest.fixture(scope="module", autouse=True)
def isolated_advanced_engine():
    """Ejecuta toda la matriz sobre un clon descartable del baseline TEST."""
    global engine

    database_name = f"inmobiliaria_test_486_advanced_{uuid4().hex[:10]}"
    admin_engine = create_engine(
        shared_test_engine.url.set(database="postgres"), future=True
    )
    shared_state_before = _shared_database_state()
    shared_test_engine.dispose()
    created = False
    isolated_engine = None
    try:
        with admin_engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as admin:
            admin.exec_driver_sql(
                f'CREATE DATABASE "{database_name}" '
                f'TEMPLATE "{shared_test_engine.url.database}"'
            )
        created = True
        isolated_engine = create_engine(
            shared_test_engine.url.set(database=database_name), future=True
        )
        engine = isolated_engine
        yield isolated_engine
    finally:
        if isolated_engine is not None:
            isolated_engine.dispose()
        if created:
            with admin_engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
            ) as admin:
                admin.execute(
                    text("""
                    SELECT pg_terminate_backend(pid)
                      FROM pg_stat_activity
                     WHERE datname=:database AND pid <> pg_backend_pid()
                    """),
                    {"database": database_name},
                )
                admin.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database_name}"')
        admin_engine.dispose()
        assert _shared_database_state() == shared_state_before


def _expire_claims(session: Session, *, event_id: str, op_id: str) -> None:
    session.execute(
        text("""
        UPDATE inbox_event
           SET lease_expires_at=clock_timestamp() AT TIME ZONE 'UTC' - interval '1s'
         WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer
        """),
        {"event_id": event_id, "consumer": CALENDARIO_SYNC_CONSUMER},
    )
    session.execute(
        text("""
        UPDATE inbox_operation_scope
           SET lease_expires_at=clock_timestamp() AT TIME ZONE 'UTC' - interval '1s'
         WHERE consumer=:consumer AND op_id=CAST(:op_id AS uuid)
        """),
        {"consumer": CALENDARIO_SYNC_CONSUMER, "op_id": op_id},
    )
    session.commit()


def _calendar_snapshot(session: Session) -> tuple[int | None, list[tuple]]:
    version = session.execute(
        text("SELECT max(version_registro) FROM configuracion_calendario_comercial")
    ).scalar_one()
    history = session.execute(
        text("""
        SELECT p.codigo_parametro, v.valor_parametro, v.fecha_desde::date,
               v.fecha_hasta::date, v.es_valor_vigente, v.version_registro,
               v.uid_global
          FROM valor_parametro v
          JOIN parametro_sistema p USING(id_parametro_sistema)
         WHERE p.codigo_parametro IN
           ('DIA_CIERRE_COMERCIAL',
            'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
           AND v.id_sucursal IS NULL AND v.id_instalacion IS NULL
         ORDER BY p.codigo_parametro, v.fecha_desde, v.id_valor_parametro
        """)
    ).all()
    return version, [tuple(row) for row in history]


def _register_committed(session: Session, event: dict) -> str:
    assert register_calendario_outbox_delivery(session, outbox_event=event)
    session.commit()
    return str(event["event_id"])


def _process_committed(session: Session, event: dict, worker: str):
    event_id = _register_committed(session, event)
    outcome = run_calendario_inbox_once(
        session, worker_id=worker, event_id=event_id, manual=True
    )
    assert outcome is not None
    return outcome


@pytest.fixture
def installation_engines():
    """Clona el baseline TEST en dos bases físicas PostgreSQL independientes."""
    source_name = f"inmobiliaria_test_origen_{uuid4().hex[:10]}"
    destination_name = f"inmobiliaria_test_destino_{uuid4().hex[:10]}"
    admin_engine = create_engine(engine.url.set(database="postgres"), future=True)
    created_names = []
    source = destination = None
    try:
        engine.dispose()
        with admin_engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as admin:
            for name in (source_name, destination_name):
                admin.exec_driver_sql(
                    f'CREATE DATABASE "{name}" TEMPLATE "{engine.url.database}"'
                )
                created_names.append(name)
        source = create_engine(engine.url.set(database=source_name), future=True)
        destination = create_engine(
            engine.url.set(database=destination_name), future=True
        )
        with source.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE instalacion DISABLE TRIGGER trg_bu_instalacion_core_ef"
            )
            connection.execute(
                text(
                    "UPDATE instalacion SET uid_global=CAST(:uid AS uuid) "
                    "WHERE id_instalacion=1"
                ),
                {"uid": str(uuid4())},
            )
            connection.exec_driver_sql(
                "ALTER TABLE instalacion ENABLE TRIGGER trg_bu_instalacion_core_ef"
            )
        yield source, destination
    finally:
        if source is not None:
            source.dispose()
        if destination is not None:
            destination.dispose()
        with admin_engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as admin:
            for name in created_names:
                admin.execute(
                    text("""
                    SELECT pg_terminate_backend(pid)
                      FROM pg_stat_activity
                     WHERE datname=:database AND pid <> pg_backend_pid()
                    """),
                    {"database": name},
                )
                admin.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}"')
        admin_engine.dispose()


def test_e2e_dos_instalaciones_bootstrap_programacion_y_fuera_de_orden(
    installation_engines,
):
    source_engine, destination_engine = installation_engines
    with Session(source_engine) as source, Session(destination_engine) as destination:
        assert (
            source.execute(
                text("SELECT uid_global FROM instalacion WHERE id_instalacion=1")
            ).scalar_one()
            != destination.execute(
                text("SELECT uid_global FROM instalacion WHERE id_instalacion=1")
            ).scalar_one()
        )
        created = _bootstrap_origin(source)
        assert transport_calendario_outbox_once(source, destination) == (1, 1)
        created_outcome = run_calendario_inbox_once(
            destination,
            worker_id="destination-v1",
            event_id=str(created["event_id"]),
            manual=True,
        )
        assert created_outcome is not None
        assert created_outcome.kind is InboxOutcomeKind.PROCESSED
        root_v1 = destination.execute(
            text("""
            SELECT uid_global::text, version_registro, op_id_alta::text,
                   op_id_ultima_modificacion::text
              FROM configuracion_calendario_comercial
            """)
        ).one()
        assert root_v1 == (
            created["payload"]["data"]["uid_global"],
            1,
            created["payload"]["data"]["op_id"],
            created["payload"]["data"]["op_id"],
        )
        child_v1 = destination.execute(
            text("""
            SELECT p.codigo_parametro, v.uid_global::text, v.version_registro
              FROM valor_parametro v
              JOIN parametro_sistema p USING(id_parametro_sistema)
             WHERE p.codigo_parametro IN
               ('DIA_CIERRE_COMERCIAL',
                'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
             ORDER BY p.codigo_parametro
            """)
        ).all()
        assert {row[2] for row in child_v1} == {1}
        assert {row[1] for row in child_v1} == {
            created["payload"]["data"]["valor_dia_cierre_comercial"]["uid_global"],
            created["payload"]["data"]["valor_dia_vencimiento_predeterminado_cuotas"][
                "uid_global"
            ],
        }

        source_v1 = ObtenerConfiguracionCalendarioComercialQueryService(
            CalendarioComercialQueryRepository(source)
        ).obtener(date(2026, 9, 1))
        destination_v1 = ObtenerConfiguracionCalendarioComercialQueryService(
            CalendarioComercialQueryRepository(destination)
        ).obtener(date(2026, 9, 1))
        assert destination_v1 == source_v1

        v2 = _program_origin(source)
        v3 = _program_origin_v3(source)
        source.execute(
            text("""
            UPDATE outbox_event
               SET occurred_at=CASE
                   WHEN id=:v3 THEN timestamp '2026-09-01 00:00:00'
                   WHEN id=:v2 THEN timestamp '2026-09-01 00:00:01'
                   ELSE occurred_at END
             WHERE id IN (:v2, :v3)
            """),
            {"v2": v2["id"], "v3": v3["id"]},
        )
        source.commit()
        assert transport_calendario_outbox_once(source, destination, limit=1) == (1, 1)
        pending = run_calendario_inbox_once(
            destination,
            worker_id="destination-v3-early",
            event_id=str(v3["event_id"]),
            manual=True,
        )
        assert pending is not None
        assert pending.kind is InboxOutcomeKind.PENDING_DEPENDENCY
        pending_delivery = InboxRepository(destination).get(
            event_id=str(v3["event_id"]), consumer=CALENDARIO_SYNC_CONSUMER
        )
        pending_scope = InboxRepository(destination).get_operation_scope(
            consumer=CALENDARIO_SYNC_CONSUMER,
            op_id=v3["payload"]["data"]["op_id"],
        )
        assert pending_delivery["status"] == "PENDING_DEPENDENCY"
        assert pending_delivery["payload"] == v3["payload"]["data"]
        assert pending_scope["terminal_status"] is None
        assert pending_scope["attempt_id"] is None
        assert _calendar_snapshot(destination)[0] == 1

        assert transport_calendario_outbox_once(source, destination, limit=1) == (1, 1)
        applied_v2 = run_calendario_inbox_once(
            destination,
            worker_id="destination-v2",
            event_id=str(v2["event_id"]),
            manual=True,
        )
        assert applied_v2 is not None
        assert applied_v2.kind is InboxOutcomeKind.PROCESSED
        applied_v3 = run_calendario_inbox_once(
            destination,
            worker_id="destination-v3-retry",
            event_id=str(v3["event_id"]),
            manual=True,
        )
        assert applied_v3 is not None
        assert applied_v3.kind is InboxOutcomeKind.PROCESSED

        query = ObtenerConfiguracionCalendarioComercialQueryService(
            CalendarioComercialQueryRepository(destination)
        )
        assert query.obtener(date(2026, 9, 1)).dia_cierre_comercial == 20
        assert query.obtener(date(2026, 10, 1)).dia_cierre_comercial == 21
        assert query.obtener(date(2026, 11, 1)).dia_cierre_comercial == 22
        version, history = _calendar_snapshot(destination)
        assert version == 3
        assert [row[5] for row in history] == [2, 2, 1, 2, 2, 1]
        expected_uids = {
            v3["payload"]["data"]["uid_global"],
            v3["payload"]["data"]["valor_dia_cierre_comercial"]["uid_global"],
            v3["payload"]["data"]["valor_dia_vencimiento_predeterminado_cuotas"][
                "uid_global"
            ],
        }
        persisted_uids = {str(row[6]) for row in history}
        persisted_uids.add(
            str(
                destination.execute(
                    text("SELECT uid_global FROM configuracion_calendario_comercial")
                ).scalar_one()
            )
        )
        assert expected_uids <= persisted_uids


def test_transporte_dos_bases_ack_perdido_es_at_least_once(
    installation_engines, monkeypatch
):
    source_engine, destination_engine = installation_engines
    with Session(source_engine) as source, Session(destination_engine) as destination:
        _clear_calendar(source)
        _clear_calendar(destination)
        event = _bootstrap_origin(source)
        destination_commit = destination.commit

        def fail_destination_commit():
            raise RuntimeError("forced destination failure")

        monkeypatch.setattr(destination, "commit", fail_destination_commit)
        with pytest.raises(RuntimeError, match="forced destination failure"):
            transport_calendario_outbox_once(source, destination)
        monkeypatch.setattr(destination, "commit", destination_commit)
        assert _outbox_status(source, int(event["id"])) == "PENDING"
        assert (
            InboxRepository(destination).get(
                event_id=str(event["event_id"]), consumer=CALENDARIO_SYNC_CONSUMER
            )
            is None
        )

        real_commit = source.commit
        commit_calls = 0

        def fail_first_source_commit():
            nonlocal commit_calls
            commit_calls += 1
            if commit_calls == 1:
                raise RuntimeError("forced source ack failure")
            real_commit()

        monkeypatch.setattr(source, "commit", fail_first_source_commit)
        with pytest.raises(RuntimeError, match="forced source ack failure"):
            transport_calendario_outbox_once(source, destination)
        monkeypatch.setattr(source, "commit", real_commit)
        source.rollback()

        assert (
            InboxRepository(destination).get(
                event_id=str(event["event_id"]), consumer=CALENDARIO_SYNC_CONSUMER
            )
            is not None
        )
        assert _outbox_status(source, int(event["id"])) == "PENDING"
        assert transport_calendario_outbox_once(source, destination) == (1, 0)
        assert _outbox_status(source, int(event["id"])) == "PUBLISHED"
        assert (
            destination.execute(
                text("""
            SELECT count(*) FROM inbox_event
             WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer
            """),
                {
                    "event_id": str(event["event_id"]),
                    "consumer": CALENDARIO_SYNC_CONSUMER,
                },
            ).scalar_one()
            == 1
        )


def _outbox_status(session: Session, event_id: int) -> str:
    return session.execute(
        text("SELECT status FROM outbox_event WHERE id=:id"), {"id": event_id}
    ).scalar_one()


@pytest.mark.parametrize("stage", ["root", "child_1", "child_2"])
def test_rollback_creacion_remota_y_retry(monkeypatch, stage):
    with Session(engine) as session:
        _clear_calendar(session)
        event = _bootstrap_origin(session)
        _clear_calendar(session)
        event_id = _register_committed(session, event)
        real_execute = session.execute
        child_count = 0

        def fail_after_statement(statement, *args, **kwargs):
            nonlocal child_count
            result = real_execute(statement, *args, **kwargs)
            sql = str(statement)
            if (
                "INSERT INTO configuracion_calendario_comercial" in sql
                and stage == "root"
            ):
                raise RuntimeError("forced after root")
            if "INSERT INTO valor_parametro" in sql:
                child_count += 1
                if stage == f"child_{child_count}":
                    raise RuntimeError(f"forced after child {child_count}")
            return result

        monkeypatch.setattr(session, "execute", fail_after_statement)
        with pytest.raises(RuntimeError, match="forced after"):
            run_calendario_inbox_once(
                session, worker_id="rollback-create", event_id=event_id, manual=True
            )
        monkeypatch.setattr(session, "execute", real_execute)
    with Session(engine) as verify:
        assert _calendar_snapshot(verify) == (None, [])
        delivery = InboxRepository(verify).get(
            event_id=event_id, consumer=CALENDARIO_SYNC_CONSUMER
        )
        scope = InboxRepository(verify).get_operation_scope(
            consumer=CALENDARIO_SYNC_CONSUMER,
            op_id=event["payload"]["data"]["op_id"],
        )
        assert delivery["status"] == "PROCESSING"
        assert scope["terminal_status"] is None
        _expire_claims(
            verify,
            event_id=event_id,
            op_id=event["payload"]["data"]["op_id"],
        )
    with Session(engine) as retry_session:
        retry = run_calendario_inbox_once(
            retry_session,
            worker_id="rollback-create-retry",
            event_id=event_id,
            manual=True,
        )
        assert retry is not None
        assert retry.kind is InboxOutcomeKind.PROCESSED


@pytest.mark.parametrize(
    "stage", ["close_1", "close_2", "new_1", "new_2", "root_update"]
)
def test_rollback_programacion_remota_y_retry(monkeypatch, stage):
    with Session(engine) as session:
        _clear_calendar(session)
        created = _bootstrap_origin(session)
        programmed = _program_origin(session)
        _clear_calendar(session)
        assert (
            _process_committed(session, created, "program-setup").kind
            is InboxOutcomeKind.PROCESSED
        )
        before = _calendar_snapshot(session)
        event_id = _register_committed(session, programmed)
        real_execute = session.execute
        closes = inserts = 0

        def fail_after_statement(statement, *args, **kwargs):
            nonlocal closes, inserts
            result = real_execute(statement, *args, **kwargs)
            sql = str(statement)
            if "UPDATE valor_parametro" in sql:
                closes += 1
                if stage == f"close_{closes}":
                    raise RuntimeError(f"forced after close {closes}")
            elif "INSERT INTO valor_parametro" in sql:
                inserts += 1
                if stage == f"new_{inserts}":
                    raise RuntimeError(f"forced after new {inserts}")
            elif (
                "UPDATE configuracion_calendario_comercial" in sql
                and stage == "root_update"
            ):
                raise RuntimeError("forced after root update")
            return result

        monkeypatch.setattr(session, "execute", fail_after_statement)
        with pytest.raises(RuntimeError, match="forced after"):
            run_calendario_inbox_once(
                session, worker_id="rollback-program", event_id=event_id, manual=True
            )
        monkeypatch.setattr(session, "execute", real_execute)
        assert _calendar_snapshot(session) == before
        _expire_claims(
            session,
            event_id=event_id,
            op_id=programmed["payload"]["data"]["op_id"],
        )
    with Session(engine) as retry_session:
        retry = run_calendario_inbox_once(
            retry_session,
            worker_id="rollback-program-retry",
            event_id=event_id,
            manual=True,
        )
        assert retry is not None
        assert retry.kind is InboxOutcomeKind.PROCESSED
        assert _calendar_snapshot(retry_session)[0] == 2


def test_commit_failure_exterior_revierte_todo_y_reintenta(monkeypatch):
    with Session(engine) as session:
        _clear_calendar(session)
        event = _bootstrap_origin(session)
        _clear_calendar(session)
        event_id = _register_committed(session, event)
        real_commit = session.commit

        def fail_commit():
            raise RuntimeError("forced outer commit failure")

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="forced outer commit failure"):
            run_calendario_inbox_once(
                session, worker_id="commit-failure", event_id=event_id, manual=True
            )
        monkeypatch.setattr(session, "commit", real_commit)
    with Session(engine) as verify:
        assert _calendar_snapshot(verify) == (None, [])
        delivery = InboxRepository(verify).get(
            event_id=event_id, consumer=CALENDARIO_SYNC_CONSUMER
        )
        scope = InboxRepository(verify).get_operation_scope(
            consumer=CALENDARIO_SYNC_CONSUMER,
            op_id=event["payload"]["data"]["op_id"],
        )
        assert delivery["status"] == "PROCESSING"
        assert scope["terminal_status"] is None
        _expire_claims(
            verify,
            event_id=event_id,
            op_id=event["payload"]["data"]["op_id"],
        )
    with Session(engine) as retry_session:
        retry = run_calendario_inbox_once(
            retry_session,
            worker_id="commit-retry",
            event_id=event_id,
            manual=True,
        )
        assert retry is not None
        assert retry.kind is InboxOutcomeKind.PROCESSED


@pytest.mark.parametrize("divergent", [False, True])
def test_remoto_vs_remoto_serializa_y_clasifica(divergent):
    with Session(engine) as setup:
        _clear_calendar(setup)
        created = _bootstrap_origin(setup)
        programmed = _program_origin(setup)
        _clear_calendar(setup)
        assert (
            _process_committed(setup, created, "remote-race-setup").kind
            is InboxOutcomeKind.PROCESSED
        )
        candidate = deepcopy(programmed)
        candidate["event_id"] = uuid4()
        candidate["payload"]["data"]["op_id"] = str(uuid4())
        if divergent:
            candidate["payload"]["data"]["dia_cierre_comercial"] = 31
        _rehash(candidate["payload"])
        first_id = _register_committed(setup, programmed)
        second_id = _register_committed(setup, candidate)
        operation_ids = {
            programmed["payload"]["data"]["op_id"],
            candidate["payload"]["data"]["op_id"],
        }

    barrier = Barrier(2)

    def worker(event_id: str, name: str):
        with Session(engine) as session:
            session.execute(text("SET LOCAL lock_timeout='8s'"))
            barrier.wait(timeout=5)
            outcome = run_calendario_inbox_once(
                session, worker_id=name, event_id=event_id, manual=True
            )
            assert outcome is not None
            return outcome.kind

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(worker, first_id, "remote-A"),
            pool.submit(worker, second_id, "remote-B"),
        ]
        outcomes = [future.result(timeout=15) for future in futures]
    expected = (
        [InboxOutcomeKind.PROCESSED, InboxOutcomeKind.PROCESSED]
        if not divergent
        else [InboxOutcomeKind.PROCESSED, InboxOutcomeKind.CONFLICTO]
    )
    assert sorted(outcomes) == sorted(expected)
    with Session(engine) as verify:
        assert _calendar_snapshot(verify)[0] == 2
        scopes = verify.execute(
            text("""
            SELECT op_id::text, terminal_status FROM inbox_operation_scope
             WHERE consumer=:consumer
               AND op_id=ANY(CAST(:operation_ids AS uuid[]))
            """),
            {
                "consumer": CALENDARIO_SYNC_CONSUMER,
                "operation_ids": sorted(operation_ids),
            },
        ).all()
        assert {row[0] for row in scopes} == operation_ids
        expected_terminals = (
            {"PROCESSED"} if not divergent else {"PROCESSED", "CONFLICTO"}
        )
        assert {row[1] for row in scopes} == expected_terminals


@pytest.mark.parametrize("divergent_values", [False, True])
def test_local_vs_remoto_serializa_sin_deadlock_y_preserva_un_solo_v2(
    divergent_values,
):
    with Session(engine) as origin:
        _clear_calendar(origin)
        created = _bootstrap_origin(origin)
        programmed = _program_origin(origin)
        if divergent_values:
            programmed["payload"]["data"]["dia_cierre_comercial"] = 31
            _rehash(programmed["payload"])
    with Session(engine) as setup:
        _clear_calendar(setup)
        assert (
            _process_committed(setup, created, "local-remote-setup").kind
            is InboxOutcomeKind.PROCESSED
        )
        event_id = _register_committed(setup, programmed)

    barrier = Barrier(2)
    local_op_id = uuid4()

    def local_writer():
        with Session(engine) as session:
            session.execute(text("SET LOCAL lock_timeout='8s'"))
            barrier.wait(timeout=5)
            try:
                ProgramarCalendarioComercialService(session).execute(
                    dia_cierre_comercial=21,
                    dia_vencimiento_predeterminado_cuotas=11,
                    vigente_desde=date(2026, 10, 1),
                    headers=_headers(local_op_id, 1),
                    id_usuario=1,
                )
                session.commit()
                return "LOCAL_PROCESSED"
            except ProgramarCalendarioComercialError as exc:
                session.rollback()
                return exc.code

    def remote_writer():
        with Session(engine) as session:
            session.execute(text("SET LOCAL lock_timeout='8s'"))
            barrier.wait(timeout=5)
            outcome = run_calendario_inbox_once(
                session,
                worker_id="local-vs-remote",
                event_id=event_id,
                manual=True,
            )
            assert outcome is not None
            return outcome.kind

    with ThreadPoolExecutor(max_workers=2) as pool:
        local_future = pool.submit(local_writer)
        remote_future = pool.submit(remote_writer)
        local_result = local_future.result(timeout=15)
        remote_result = remote_future.result(timeout=15)
    assert (local_result, remote_result) in {
        ("LOCAL_PROCESSED", InboxOutcomeKind.CONFLICTO),
        ("CONCURRENCY_ERROR", InboxOutcomeKind.PROCESSED),
    }
    with Session(engine) as verify:
        version, history = _calendar_snapshot(verify)
        assert version == 2
        assert len(history) == 4
        remote_delivery = InboxRepository(verify).get(
            event_id=event_id, consumer=CALENDARIO_SYNC_CONSUMER
        )
        assert remote_delivery["status"] == str(remote_result)
        local_receipts = verify.execute(
            text(
                "SELECT count(*) FROM operacion_idempotente "
                "WHERE op_id=CAST(:op_id AS uuid)"
            ),
            {"op_id": str(local_op_id)},
        ).scalar_one()
        assert local_receipts == int(local_result == "LOCAL_PROCESSED")


def test_takeover_fencea_attempt_viejo_y_unico_efecto():
    with Session(engine) as setup:
        _clear_calendar(setup)
        event = _bootstrap_origin(setup)
        event_id = _register_committed(setup, event)
    applicator_started = Event()
    allow_stale_finish = Event()
    stale_fenced = Event()

    def stale_worker():
        with Session(engine) as session:
            applicator = CalendarioComercialSyncApplicator(session)

            def delayed(event_row):
                outcome = applicator.apply(event_row)
                applicator_started.set()
                assert allow_stale_finish.wait(timeout=10)
                return outcome

            try:
                _run_delayed(session, delayed, event_id)
            except InboxOwnershipLost:
                stale_fenced.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        stale = pool.submit(stale_worker)
        assert applicator_started.wait(timeout=10)
        with Session(engine) as takeover:
            op_id = event["payload"]["data"]["op_id"]
            stale_delivery = InboxRepository(takeover).get(
                event_id=event_id, consumer=CALENDARIO_SYNC_CONSUMER
            )
            assert stale_delivery is not None
            attempt_a = stale_delivery["attempt_id"]
            fence_a = stale_delivery["fence_generation"]
            _expire_claims(takeover, event_id=event_id, op_id=op_id)
            repo = InboxRepository(takeover)
            claim_b = repo.claim_pending(
                consumer=CALENDARIO_SYNC_CONSUMER,
                worker_id="owner-B",
                lease_duration=timedelta(minutes=5),
                automatic_attempt_limit=8,
                event_id=event_id,
                manual=True,
            )
            assert claim_b is not None
            takeover.commit()
            operation_b = repo.acquire_operation_scope(delivery=claim_b)
            takeover.commit()
            assert operation_b.claim is not None
            assert claim_b.attempt_id != str(attempt_a)
            assert claim_b.fence_generation == fence_a + 1
        allow_stale_finish.set()
        stale.result(timeout=15)
    assert stale_fenced.is_set()
    with Session(engine) as owner:
        outcome = CalendarioComercialSyncApplicator(owner).apply(claim_b.event)
        assert outcome.kind is InboxOutcomeKind.PROCESSED
        InboxRepository(owner).finish_operation_scope(
            claim=operation_b.claim, terminal_status="PROCESSED"
        )
        InboxRepository(owner).mark_as_processed(claim=claim_b)
        owner.commit()
    with Session(engine) as verify:
        assert _calendar_snapshot(verify)[0] == 1
        delivery = InboxRepository(verify).get(
            event_id=event_id, consumer=CALENDARIO_SYNC_CONSUMER
        )
        assert delivery["status"] == "PROCESSED"
        assert delivery["attempt_id"] is None
        assert delivery["fence_generation"] == claim_b.fence_generation


@pytest.mark.parametrize("with_active", [False, True])
def test_singleton_con_raiz_deleted_es_conflicto(with_active):
    with Session(engine) as session:
        _clear_calendar(session)
        event = _bootstrap_origin(session)
        _clear_calendar(session)
        if with_active:
            assert (
                _process_committed(session, event, "singleton-active").kind
                is InboxOutcomeKind.PROCESSED
            )
        session.execute(
            text("""
            INSERT INTO configuracion_calendario_comercial(
                uid_global, version_registro, deleted_at,
                op_id_alta, op_id_ultima_modificacion)
            VALUES (CAST(:uid AS uuid), 1, clock_timestamp(),
                    CAST(:op AS uuid), CAST(:op AS uuid))
            """),
            {"uid": str(uuid4()), "op": str(uuid4())},
        )
        session.commit()
        candidate = deepcopy(event)
        candidate["event_id"] = uuid4()
        candidate["payload"]["data"]["op_id"] = str(uuid4())
        _rehash(candidate["payload"])
        outcome = _process_committed(session, candidate, "singleton-corrupt")
        assert outcome.kind is InboxOutcomeKind.CONFLICTO


def test_singleton_dos_raices_activas_es_imposible_fisicamente():
    with Session(engine) as session:
        _clear_calendar(session)
        session.execute(
            text("INSERT INTO configuracion_calendario_comercial DEFAULT VALUES")
        )
        session.commit()
        with pytest.raises(IntegrityError):
            session.execute(
                text("INSERT INTO configuracion_calendario_comercial DEFAULT VALUES")
            )
            session.flush()
        session.rollback()


def _run_delayed(session: Session, applicator, event_id: str):
    return InboxRetryProcessor(session, consumer=CALENDARIO_SYNC_CONSUMER).run_once(
        applicator, worker_id="stale-A", event_id=event_id, manual=True
    )
