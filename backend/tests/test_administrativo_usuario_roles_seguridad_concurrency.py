from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.administrativo.services.usuario_rol_seguridad_central_command_service import (
    UsuarioRolSeguridadCentralCommandService,
    UsuarioRolSeguridadCommandError,
)
from app.application.administrativo.services.usuarios_central_command_service import (
    UsuariosCentralCommandService,
)
from app.application.common.central_command import CentralCommandMetadata
from app.config.database import engine


def _create_targets(suffix):
    with Session(engine) as session:
        usuario = UsuariosCentralCommandService(session).create(
            payload={
                "codigo_usuario": f"USR-GRANT-{suffix}",
                "login": f"usr.grant.{suffix.lower()}",
                "email": None,
                "estado_usuario": "ACTIVO",
                "usuario_sistema_interno": False,
                "observaciones": None,
            },
            metadata=CentralCommandMetadata(uuid4(), None),
            id_usuario_actor=1,
        )["data"]
        rol = session.execute(
            text(
                "INSERT INTO rol_seguridad(codigo_rol,nombre_rol,estado_rol) "
                "VALUES(:codigo,:nombre,'ACTIVO') RETURNING id_rol_seguridad"
            ),
            {"codigo": f"ROL-GRANT-{suffix}", "nombre": f"Rol {suffix}"},
        ).scalar_one()
        session.commit()
        return usuario["id_usuario"], rol


def _assign(id_usuario, id_rol, op_id):
    with Session(engine) as session:
        try:
            result = UsuarioRolSeguridadCentralCommandService(session).assign(
                id_usuario=id_usuario,
                id_rol_seguridad=id_rol,
                metadata=CentralCommandMetadata(op_id, None),
                id_usuario_actor=1,
            )
            session.commit()
            return "OK", result
        except UsuarioRolSeguridadCommandError as exc:
            session.rollback()
            return exc.code, None


def _revoke(id_usuario, id_asignacion, version, op_id):
    with Session(engine) as session:
        try:
            result = UsuarioRolSeguridadCentralCommandService(session).revoke(
                id_usuario=id_usuario,
                id_asignacion=id_asignacion,
                metadata=CentralCommandMetadata(op_id, version),
                id_usuario_actor=1,
            )
            session.commit()
            return "OK", result
        except UsuarioRolSeguridadCommandError as exc:
            session.rollback()
            return exc.code, None


def test_assign_mismo_op_concurrente_ejecuta_una_vez_y_replay(db_session):
    usuario, rol = _create_targets(uuid4().hex[:8])
    op_id = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _assign(usuario, rol, op_id), range(2)))
    assert [code for code, _ in results] == ["OK", "OK"]
    assert results[0][1] == results[1][1]
    assert db_session.execute(text(
        "SELECT count(*) FROM usuario_rol_seguridad WHERE id_usuario=:u AND id_rol_seguridad=:r"
    ), {"u": usuario, "r": rol}).scalar_one() == 1


def test_assign_distintos_op_mismo_usuario_rol_uno_duplica(db_session):
    usuario, rol = _create_targets(uuid4().hex[:8])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda op: _assign(usuario, rol, op), (uuid4(), uuid4())))
    assert sorted(code for code, _ in results) == ["DUPLICATE_ACTIVE_GRANT", "OK"]
    assert db_session.execute(text(
        "SELECT count(*) FROM usuario_rol_seguridad WHERE id_usuario=:u AND id_rol_seguridad=:r"
    ), {"u": usuario, "r": rol}).scalar_one() == 1


def test_revoke_concurrente_misma_version_uno_412_nunca_404(db_session):
    usuario, rol = _create_targets(uuid4().hex[:8])
    assigned = _assign(usuario, rol, uuid4())[1]["data"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda op: _revoke(usuario, assigned["id_usuario_rol_seguridad"],
                               assigned["version_registro"], op),
            (uuid4(), uuid4()),
        ))
    assert sorted(code for code, _ in results) == ["CONCURRENCY_ERROR", "OK"]
    assert "NOT_FOUND" not in {code for code, _ in results}
    row = db_session.execute(text(
        "SELECT deleted_at,fecha_hasta,version_registro FROM usuario_rol_seguridad "
        "WHERE id_usuario_rol_seguridad=:id"
    ), {"id": assigned["id_usuario_rol_seguridad"]}).one()
    assert row.deleted_at is not None and row.fecha_hasta is not None
    assert row.version_registro == assigned["version_registro"] + 1
