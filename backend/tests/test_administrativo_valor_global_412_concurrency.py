import threading
import time
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.core_ef_headers import AuthenticatedCoreEFHeaders
from app.application.administrativo.services.actualizar_valor_parametro_global_service import (
    ActualizarValorParametroGlobalService,
    ParametroCommandError,
)
from app.config.database import engine
from app.infrastructure.persistence.repositories.valor_parametro_global_command_repository import (
    ValorParametroGlobalCommandRepository,
)

CODE = "PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO"


@pytest.fixture
def concurrency_state_guard():
    with engine.connect() as connection:
        snapshot = (
            connection.execute(
                text("""
                    SELECT v.*
                    FROM valor_parametro v
                    JOIN parametro_sistema p USING (id_parametro_sistema)
                    WHERE p.codigo_parametro = :code
                """),
                {"code": CODE},
            )
            .mappings()
            .one()
        )

    state = {"snapshot": dict(snapshot), "op_ids": []}
    try:
        yield state
    finally:
        op_ids = state["op_ids"]
        target = state["snapshot"]
        with engine.begin() as connection:
            if op_ids:
                connection.execute(
                    text("""
                        DELETE FROM outbox_event
                        WHERE event_type = 'valor_parametro_modificado'
                          AND aggregate_type = 'valor_parametro'
                          AND aggregate_id = :aggregate_id
                          AND payload->'data'->>'uid_global' = :uid_global
                          AND payload->'data'->>'op_id' = ANY(:op_ids)
                    """),
                    {
                        "aggregate_id": target["id_valor_parametro"],
                        "uid_global": str(target["uid_global"]),
                        "op_ids": [str(op_id) for op_id in op_ids],
                    },
                )
                for trigger_name in (
                    "trg_bud_operacion_idempotente_inmutable",
                    "trg_bt_operacion_idempotente_inmutable",
                ):
                    connection.execute(
                        text(
                            "ALTER TABLE operacion_idempotente DISABLE TRIGGER "
                            f"{trigger_name}"
                        )
                    )
                try:
                    connection.execute(
                        text(
                            "DELETE FROM operacion_idempotente "
                            "WHERE op_id = ANY(:op_ids)"
                        ),
                        {"op_ids": op_ids},
                    )
                finally:
                    for trigger_name in (
                        "trg_bud_operacion_idempotente_inmutable",
                        "trg_bt_operacion_idempotente_inmutable",
                    ):
                        connection.execute(
                            text(
                                "ALTER TABLE operacion_idempotente "
                                f"ENABLE ALWAYS TRIGGER {trigger_name}"
                            )
                        )

            connection.execute(
                text(
                    "ALTER TABLE valor_parametro DISABLE TRIGGER "
                    "trg_bu_valor_parametro_core_ef"
                )
            )
            try:
                connection.execute(
                    text("""
                        UPDATE valor_parametro
                        SET id_parametro_sistema = :id_parametro_sistema,
                            id_sucursal = :id_sucursal,
                            id_instalacion = :id_instalacion,
                            valor_parametro = :valor_parametro,
                            es_valor_vigente = :es_valor_vigente,
                            fecha_desde = :fecha_desde,
                            fecha_hasta = :fecha_hasta,
                            uid_global = :uid_global,
                            version_registro = :version_registro,
                            created_at = :created_at,
                            updated_at = :updated_at,
                            deleted_at = :deleted_at,
                            id_instalacion_origen = :id_instalacion_origen,
                            id_instalacion_ultima_modificacion =
                                :id_instalacion_ultima_modificacion,
                            op_id_alta = :op_id_alta,
                            op_id_ultima_modificacion =
                                :op_id_ultima_modificacion
                        WHERE id_valor_parametro = :id_valor_parametro
                    """),
                    target,
                )
            finally:
                connection.execute(
                    text(
                        "ALTER TABLE valor_parametro ENABLE TRIGGER "
                        "trg_bu_valor_parametro_core_ef"
                    )
                )


def _prepare_v3(target_id):
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE valor_parametro SET valor_parametro='15' WHERE id_valor_parametro=:id"
            ),
            {"id": target_id},
        )
        current = connection.execute(
            text(
                "SELECT version_registro FROM valor_parametro WHERE id_valor_parametro=:id"
            ),
            {"id": target_id},
        ).scalar_one()
        while current < 3:
            connection.execute(
                text(
                    "UPDATE valor_parametro SET valor_parametro=valor_parametro WHERE id_valor_parametro=:id"
                ),
                {"id": target_id},
            )
            current += 1
        if current > 3:
            connection.execute(
                text(
                    "ALTER TABLE valor_parametro DISABLE TRIGGER trg_bu_valor_parametro_core_ef"
                )
            )
            try:
                connection.execute(
                    text(
                        "UPDATE valor_parametro SET version_registro=3, "
                        "valor_parametro='15' WHERE id_valor_parametro=:id"
                    ),
                    {"id": target_id},
                )
            finally:
                connection.execute(
                    text(
                        "ALTER TABLE valor_parametro ENABLE TRIGGER "
                        "trg_bu_valor_parametro_core_ef"
                    )
                )


def _run_concurrent(monkeypatch, concurrency_state_guard, *, holder_value, waiter_value):
    target_id = concurrency_state_guard["snapshot"]["id_valor_parametro"]
    _prepare_v3(target_id)
    holder_locked = threading.Event()
    release = threading.Event()
    outcomes = {}
    pids = {}
    op_ids = {"holder": uuid4(), "waiter": uuid4()}
    concurrency_state_guard["op_ids"].extend(op_ids.values())
    original = ValorParametroGlobalCommandRepository.lock_target

    def controlled_lock(self, target):
        row = original(self, target)
        if threading.current_thread().name == "holder":
            holder_locked.set()
            assert release.wait(5)
        return row

    monkeypatch.setattr(
        ValorParametroGlobalCommandRepository, "lock_target", controlled_lock
    )

    def worker(name, value):
        op_id = op_ids[name]
        with Session(engine) as session:
            pids[name] = session.execute(text("SELECT pg_backend_pid() ")).scalar_one()
            try:
                outcomes[name] = ActualizarValorParametroGlobalService(session).execute(
                    codigo_parametro=CODE,
                    valor_tipado=value,
                    headers=AuthenticatedCoreEFHeaders(op_id, 1, 1, 3),
                    id_usuario=1,
                )
                session.commit()
            except ParametroCommandError as exc:
                session.rollback()
                outcomes[name] = exc

    holder = threading.Thread(
        target=worker, name="holder", args=("holder", holder_value)
    )
    waiter = threading.Thread(
        target=worker, name="waiter", args=("waiter", waiter_value)
    )
    holder.start()
    try:
        assert holder_locked.wait(5)
        waiter.start()
        time.sleep(0.2)
        assert (
            waiter.is_alive()
        ), "the second #412 command must wait on SELECT FOR UPDATE"
    finally:
        release.set()
        holder.join(10)
        if waiter.ident is not None:
            waiter.join(10)
    assert (
        not holder.is_alive() and not waiter.is_alive() and len(set(pids.values())) == 2
    )
    with Session(engine) as session:
        state = session.execute(
            text(
                "SELECT valor_parametro,version_registro FROM valor_parametro WHERE id_valor_parametro=:id"
            ),
            {"id": target_id},
        ).one()
        receipts = session.execute(
            text(
                "SELECT count(*) FROM operacion_idempotente WHERE op_id IN (:holder,:waiter)"
            ),
            op_ids,
        ).scalar_one()
        events = (
            session.execute(
                text("""
                    SELECT count(*) FROM outbox_event
                    WHERE event_type = 'valor_parametro_modificado'
                      AND aggregate_type = 'valor_parametro'
                      AND aggregate_id = :target_id
                      AND payload->'data'->>'op_id' = ANY(:op_ids)
                """),
                {
                    "target_id": target_id,
                    "op_ids": [str(op_id) for op_id in op_ids.values()],
                },
            ).scalar_one()
        )
    return outcomes, state, receipts, events


def test_noop_holder_commits_then_waiter_materializes(
    monkeypatch, concurrency_state_guard
):
    outcomes, state, receipts, events = _run_concurrent(
        monkeypatch,
        concurrency_state_guard,
        holder_value=15,
        waiter_value=16,
    )
    assert outcomes["holder"]["data"]["version_registro"] == 3
    assert outcomes["waiter"]["data"]["version_registro"] == 4
    assert state == ("16", 4) and receipts == 2 and events == 1


def test_material_holder_makes_waiting_noop_stale(
    monkeypatch, concurrency_state_guard
):
    outcomes, state, receipts, events = _run_concurrent(
        monkeypatch,
        concurrency_state_guard,
        holder_value=16,
        waiter_value=15,
    )
    assert outcomes["holder"]["data"]["version_registro"] == 4
    assert isinstance(outcomes["waiter"], ParametroCommandError)
    assert (outcomes["waiter"].status, outcomes["waiter"].code) == (
        412,
        "CONCURRENCY_ERROR",
    )
    assert state == ("16", 4) and receipts == 1 and events == 1
