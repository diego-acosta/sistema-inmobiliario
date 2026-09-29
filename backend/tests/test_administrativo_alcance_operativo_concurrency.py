from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.administrativo.services.usuario_sucursal_central_command_service import (
    UsuarioSucursalCentralCommandService,
    UsuarioSucursalCommandError,
)
from app.application.administrativo.services.usuarios_central_command_service import (
    UsuariosCentralCommandService,
    UsuariosCommandError,
)
from app.application.common.central_command import CentralCommandMetadata
from app.config.database import engine


def _targets(suffix: str, *, branches: int = 1) -> tuple[int, list[int]]:
    with Session(engine) as session:
        usuario = UsuariosCentralCommandService(session).create(
            payload={
                "codigo_usuario": f"USR-SCOPE-{suffix}",
                "login": f"usr.scope.{suffix.lower()}",
                "email": None,
                "estado_usuario": "ACTIVO",
                "usuario_sistema_interno": False,
                "observaciones": None,
            },
            metadata=CentralCommandMetadata(uuid4(), None),
            id_usuario_actor=1,
        )["data"]
        branch_ids = []
        for index in range(branches):
            branch_ids.append(
                session.execute(
                    text(
                        """
                        INSERT INTO sucursal(
                            codigo_sucursal, nombre_sucursal, estado_sucursal,
                            es_casa_central, permite_operacion
                        ) VALUES(:codigo, :nombre, 'ACTIVA', false, true)
                        RETURNING id_sucursal
                        """
                    ),
                    {
                        "codigo": f"SUC-SCOPE-{suffix}-{index}",
                        "nombre": f"Sucursal scope {suffix}-{index}",
                    },
                ).scalar_one()
            )
        session.commit()
        return usuario["id_usuario"], branch_ids


def _payload(id_sucursal: int, *, default: bool = False) -> dict:
    return {
        "id_sucursal": id_sucursal,
        "tipo_habilitacion_sucursal": "OPERATIVA_BASICA",
        "es_sucursal_predeterminada": default,
        "puede_operar": True,
        "puede_consultar": True,
        "puede_administrar": False,
        "fecha_desde": datetime.now(UTC).replace(tzinfo=None),
        "fecha_hasta": None,
        "observaciones": None,
    }


def _assign(
    id_usuario: int,
    payload: dict,
    op_id,
    *,
    id_usuario_actor: int = 1,
    barrier: Barrier | None = None,
) -> tuple[str, dict | None]:
    with Session(engine) as session:
        try:
            if barrier is not None:
                barrier.wait()
            result = UsuarioSucursalCentralCommandService(session).assign(
                id_usuario=id_usuario,
                payload=payload,
                metadata=CentralCommandMetadata(op_id, None),
                id_usuario_actor=id_usuario_actor,
            )
            session.commit()
            return "OK", result
        except UsuarioSucursalCommandError as exc:
            session.rollback()
            return exc.code, None


def _deactivate(
    id_usuario: int,
    op_id,
    expected_version: int,
    *,
    id_usuario_actor: int,
    barrier: Barrier,
) -> tuple[str, dict | None]:
    with Session(engine) as session:
        try:
            barrier.wait()
            result = UsuariosCentralCommandService(session).deactivate(
                id_usuario=id_usuario,
                metadata=CentralCommandMetadata(op_id, expected_version),
                id_usuario_actor=id_usuario_actor,
            )
            session.commit()
            return "OK", result
        except UsuariosCommandError as exc:
            session.rollback()
            return exc.code, None


def test_mismo_op_concurrente_ejecuta_una_vez_y_replay(db_session):
    usuario, branches = _targets(uuid4().hex[:8])
    op_id = uuid4()
    payload = _payload(branches[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: _assign(usuario, payload, op_id), range(2))
        )
    assert [code for code, _ in results] == ["OK", "OK"]
    assert results[0][1] == results[1][1]
    assert db_session.execute(
        text(
            "SELECT count(*) FROM usuario_sucursal "
            "WHERE id_usuario=:usuario AND id_sucursal=:sucursal"
        ),
        {"usuario": usuario, "sucursal": branches[0]},
    ).scalar_one() == 1


def test_distintos_op_mismo_usuario_sucursal_uno_conflicta(db_session):
    usuario, branches = _targets(uuid4().hex[:8])
    payload = _payload(branches[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda op: _assign(usuario, payload, op), (uuid4(), uuid4()))
        )
    assert sorted(code for code, _ in results) == ["DUPLICATE_ACTIVE_SCOPE", "OK"]
    assert db_session.execute(
        text(
            "SELECT count(*) FROM usuario_sucursal "
            "WHERE id_usuario=:usuario AND id_sucursal=:sucursal"
        ),
        {"usuario": usuario, "sucursal": branches[0]},
    ).scalar_one() == 1


def test_dos_predeterminadas_concurrentes_se_serializan_por_usuario(db_session):
    usuario, branches = _targets(uuid4().hex[:8], branches=2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda args: _assign(
                    usuario, _payload(args[0], default=True), args[1]
                ),
                ((branches[0], uuid4()), (branches[1], uuid4())),
            )
        )
    assert sorted(code for code, _ in results) == ["DUPLICATE_ACTIVE_SCOPE", "OK"]
    assert db_session.execute(
        text(
            """
            SELECT count(*) FROM usuario_sucursal
            WHERE id_usuario=:usuario
              AND es_sucursal_predeterminada=true
              AND deleted_at IS NULL
              AND estado_vinculo='ACTIVO'
              AND fecha_hasta IS NULL
            """
        ),
        {"usuario": usuario},
    ).scalar_one() == 1


def test_usuarios_distintos_pueden_asignarse_en_paralelo(db_session):
    first_user, first_branches = _targets(uuid4().hex[:8])
    second_user, second_branches = _targets(uuid4().hex[:8])
    commands = (
        (first_user, _payload(first_branches[0]), uuid4()),
        (second_user, _payload(second_branches[0]), uuid4()),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda args: _assign(args[0], args[1], args[2]), commands)
        )
    assert [code for code, _ in results] == ["OK", "OK"]
    assert db_session.execute(
        text(
            "SELECT count(*) FROM usuario_sucursal "
            "WHERE id_usuario IN (:first_user, :second_user)"
        ),
        {"first_user": first_user, "second_user": second_user},
    ).scalar_one() == 2


def test_actores_y_targets_cruzados_bloquean_usuarios_en_orden(db_session):
    first_user, first_branches = _targets(uuid4().hex[:8])
    second_user, second_branches = _targets(uuid4().hex[:8])
    first_op_id = uuid4()
    second_op_id = uuid4()
    barrier = Barrier(2)
    commands = (
        (
            second_user,
            _payload(first_branches[0]),
            first_op_id,
            first_user,
        ),
        (
            first_user,
            _payload(second_branches[0]),
            second_op_id,
            second_user,
        ),
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda args: _assign(
                    args[0],
                    args[1],
                    args[2],
                    id_usuario_actor=args[3],
                    barrier=barrier,
                ),
                commands,
            )
        )

    assert [code for code, _ in results] == ["OK", "OK"]
    assert db_session.execute(
        text(
            """
            SELECT count(*)
            FROM usuario_sucursal
            WHERE (id_usuario=:first_target AND id_sucursal=:first_branch)
               OR (id_usuario=:second_target AND id_sucursal=:second_branch)
            """
        ),
        {
            "first_target": second_user,
            "first_branch": first_branches[0],
            "second_target": first_user,
            "second_branch": second_branches[0],
        },
    ).scalar_one() == 2
    receipts = db_session.execute(
        text(
            """
            SELECT op_id::text AS op_id, id_usuario
            FROM operacion_idempotente
            WHERE op_id IN (:first_op_id, :second_op_id)
            """
        ),
        {
            "first_op_id": str(first_op_id),
            "second_op_id": str(second_op_id),
        },
    ).mappings().all()
    assert {row["op_id"]: row["id_usuario"] for row in receipts} == {
        str(first_op_id): first_user,
        str(second_op_id): second_user,
    }


def test_b1_y_b3_bloquean_actor_y_target_en_el_mismo_orden(db_session):
    actor_a, branches_a = _targets(uuid4().hex[:8])
    target_b, _ = _targets(uuid4().hex[:8])
    assert actor_a < target_b
    target_b_version = db_session.execute(
        text("SELECT version_registro FROM usuario WHERE id_usuario=:id_usuario"),
        {"id_usuario": target_b},
    ).scalar_one()
    deactivate_op_id = uuid4()
    assign_op_id = uuid4()
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        deactivate_future = pool.submit(
            _deactivate,
            target_b,
            deactivate_op_id,
            target_b_version,
            id_usuario_actor=actor_a,
            barrier=barrier,
        )
        assign_future = pool.submit(
            _assign,
            actor_a,
            _payload(branches_a[0]),
            assign_op_id,
            id_usuario_actor=target_b,
            barrier=barrier,
        )
        results = (deactivate_future.result(), assign_future.result())

    assert [code for code, _ in results] == ["OK", "OK"]
    assert db_session.execute(
        text(
            "SELECT count(*) FROM usuario_sucursal "
            "WHERE id_usuario=:id_usuario AND id_sucursal=:id_sucursal"
        ),
        {"id_usuario": actor_a, "id_sucursal": branches_a[0]},
    ).scalar_one() == 1
    receipts = db_session.execute(
        text(
            "SELECT op_id::text AS op_id, id_usuario "
            "FROM operacion_idempotente "
            "WHERE op_id IN (:deactivate_op_id, :assign_op_id)"
        ),
        {
            "deactivate_op_id": str(deactivate_op_id),
            "assign_op_id": str(assign_op_id),
        },
    ).mappings().all()
    assert {row["op_id"]: row["id_usuario"] for row in receipts} == {
        str(deactivate_op_id): actor_a,
        str(assign_op_id): target_b,
    }
