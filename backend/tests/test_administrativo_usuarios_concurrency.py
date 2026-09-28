from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.administrativo.services.usuarios_central_command_service import (
    UsuariosCentralCommandService,
    UsuariosCommandError,
)
from app.application.common.central_command import CentralCommandMetadata
from app.config.database import engine


def _payload(suffix: str) -> dict:
    return {
        "codigo_usuario": f"USR-CONC-{suffix}",
        "login": f"usr.conc.{suffix.lower()}",
        "email": None,
        "estado_usuario": "ACTIVO",
        "usuario_sistema_interno": False,
        "observaciones": None,
    }


def _create(payload: dict, op_id) -> tuple[str, dict | None]:
    with Session(engine) as session:
        try:
            result = UsuariosCentralCommandService(session).create(
                payload=payload,
                metadata=CentralCommandMetadata(op_id=op_id, expected_version=None),
                id_usuario_actor=1,
            )
            session.commit()
            return "OK", result
        except UsuariosCommandError as exc:
            session.rollback()
            return exc.code, None


def test_same_op_concurrente_ejecuta_una_vez_y_replay(db_session):
    suffix = uuid4().hex[:8]
    payload = _payload(suffix)
    op_id = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _create(payload, op_id), range(2)))
    assert [code for code, _ in results] == ["OK", "OK"]
    assert results[0][1] == results[1][1]
    assert db_session.execute(
        text("SELECT count(*) FROM usuario WHERE codigo_usuario=:code"),
        {"code": payload["codigo_usuario"]},
    ).scalar_one() == 1
    assert db_session.execute(
        text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"),
        {"op": op_id},
    ).scalar_one() == 1


def test_distintos_op_create_duplicado_materializa_una_fila(db_session):
    suffix = uuid4().hex[:8]
    payload = _payload(suffix)
    op_ids = (uuid4(), uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda op: _create(payload, op), op_ids))
    assert sorted(code for code, _ in results) == ["DUPLICATE_USER", "OK"]
    assert db_session.execute(
        text("SELECT count(*) FROM usuario WHERE codigo_usuario=:code"),
        {"code": payload["codigo_usuario"]},
    ).scalar_one() == 1
