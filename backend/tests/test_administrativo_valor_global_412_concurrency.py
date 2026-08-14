import threading
import time
from uuid import uuid4

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


def _prepare_v3():
    with engine.begin() as connection:
        baseline_events = connection.execute(
            text(
                "SELECT count(*) FROM outbox_event WHERE event_type='valor_parametro_modificado'"
            )
        ).scalar_one()
        row = connection.execute(
            text("""
          SELECT v.id_valor_parametro FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema)
          WHERE p.codigo_parametro=:code
        """),
            {"code": CODE},
        ).scalar_one()
        connection.execute(
            text(
                "UPDATE valor_parametro SET valor_parametro='15' WHERE id_valor_parametro=:id"
            ),
            {"id": row},
        )
        current = connection.execute(
            text(
                "SELECT version_registro FROM valor_parametro WHERE id_valor_parametro=:id"
            ),
            {"id": row},
        ).scalar_one()
        while current < 3:
            connection.execute(
                text(
                    "UPDATE valor_parametro SET valor_parametro=valor_parametro WHERE id_valor_parametro=:id"
                ),
                {"id": row},
            )
            current += 1
        if current > 3:
            connection.execute(
                text(
                    "ALTER TABLE valor_parametro DISABLE TRIGGER trg_bu_valor_parametro_core_ef"
                )
            )
            connection.execute(
                text(
                    "UPDATE valor_parametro SET version_registro=3, valor_parametro='15' WHERE id_valor_parametro=:id"
                ),
                {"id": row},
            )
            connection.execute(
                text(
                    "ALTER TABLE valor_parametro ENABLE TRIGGER trg_bu_valor_parametro_core_ef"
                )
            )
        return row, baseline_events


def _run_concurrent(monkeypatch, *, holder_value, waiter_value):
    target_id, baseline_events = _prepare_v3()
    holder_locked = threading.Event()
    release = threading.Event()
    outcomes = {}
    pids = {}
    op_ids = {}
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
        op_id = uuid4()
        op_ids[name] = op_id
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
    assert holder_locked.wait(5)
    waiter.start()
    time.sleep(0.2)
    assert waiter.is_alive(), "the second #412 command must wait on SELECT FOR UPDATE"
    release.set()
    holder.join(10)
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
                text(
                    "SELECT count(*) FROM outbox_event WHERE event_type='valor_parametro_modificado'"
                )
            ).scalar_one()
            - baseline_events
        )
    return outcomes, state, receipts, events


def test_noop_holder_commits_then_waiter_materializes(monkeypatch):
    outcomes, state, receipts, events = _run_concurrent(
        monkeypatch, holder_value=15, waiter_value=16
    )
    assert outcomes["holder"]["data"]["version_registro"] == 3
    assert outcomes["waiter"]["data"]["version_registro"] == 4
    assert state == ("16", 4) and receipts == 2 and events == 1


def test_material_holder_makes_waiting_noop_stale(monkeypatch):
    outcomes, state, receipts, events = _run_concurrent(
        monkeypatch, holder_value=16, waiter_value=15
    )
    assert outcomes["holder"]["data"]["version_registro"] == 4
    assert isinstance(outcomes["waiter"], ParametroCommandError)
    assert (outcomes["waiter"].status, outcomes["waiter"].code) == (
        412,
        "CONCURRENCY_ERROR",
    )
    assert state == ("16", 4) and receipts == 1 and events == 1
