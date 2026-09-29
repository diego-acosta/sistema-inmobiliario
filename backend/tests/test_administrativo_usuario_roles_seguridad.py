from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import text

from app.api.authentication import get_authenticated_principal
from app.application.administrativo.authorization import AdministrativeAuthorizationDecision
from tests.test_administrativo_usuarios import _central_headers, _central_request, _payload, _principal

PERMISSION = "ADMIN.SEGURIDAD.GRANTS.ADMINISTRAR"


def _crear_usuario(client, suffix):
    response = _central_request(client, "POST", "/api/v1/administrativo/usuarios",
        json=_payload(f"ROL-{suffix}"), headers=_central_headers())
    assert response.status_code == 201
    return response.json()["data"]


def _crear_rol(db_session, suffix="ROL", estado="ACTIVO"):
    id_rol = db_session.execute(text("""
        INSERT INTO rol_seguridad (codigo_rol,nombre_rol,descripcion,estado_rol)
        VALUES (:codigo,:nombre,'Rol para pruebas',:estado) RETURNING id_rol_seguridad
    """), {"codigo": f"ADM_ASIG_{suffix}_{uuid4().hex[:8]}",
            "nombre": f"Rol asignación {suffix}", "estado": estado}).scalar_one()
    db_session.commit()
    return id_rol


def _grant_request(client, method, url, *, body=None, headers=None, actor=1, granted=True):
    client.app.dependency_overrides[get_authenticated_principal] = lambda: _principal(actor)
    decision = (AdministrativeAuthorizationDecision.GRANTED if granted
                else AdministrativeAuthorizationDecision.DENIED)
    with patch("app.api.administrative_authorization.AdministrativeAuthorizationService.authorize",
               return_value=decision) as authorize:
        response = client.request(method, url, json=body, headers=headers or {})
    if authorize.called:
        assert authorize.call_args.args[1] == PERMISSION
    return response


def _headers(op_id=None, version=None, *, legacy=False):
    result = {"X-Op-Id": str(op_id or uuid4())}
    if version is not None:
        result["If-Match-Version"] = str(version)
    if legacy:
        result |= {"X-Usuario-Id": "987", "X-Sucursal-Id": "876",
                   "X-Instalacion-Id": "765"}
    return result


def _asignar(client, id_usuario, id_rol, *, op_id=None, actor=1, legacy=False):
    return _grant_request(client, "POST",
        f"/api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad",
        body={"id_rol_seguridad": id_rol},
        headers=_headers(op_id, legacy=legacy), actor=actor)


def _revocar(
    client, usuario, asignacion, *, op_id=None, actor=1, version=None,
    legacy=False,
):
    return _grant_request(client, "PATCH",
        f"/api/v1/administrativo/usuarios/{usuario}/roles-seguridad/"
        f"{asignacion['id_usuario_rol_seguridad']}/baja",
        headers=_headers(
            op_id,
            asignacion["version_registro"] if version is None else version,
            legacy=legacy,
        ),
        actor=actor)


def test_assign_central_receipt_provenance_headers_y_sin_outbox(client, db_session):
    usuario = _crear_usuario(client, "CENTRAL")
    rol = _crear_rol(db_session, "CENTRAL")
    op_id = uuid4()
    response = _asignar(client, usuario["id_usuario"], rol, op_id=op_id, legacy=True)
    assert response.status_code == 201
    data = response.json()["data"]
    assert (data["id_usuario"], data["id_rol_seguridad"]) == (usuario["id_usuario"], rol)
    assert data["id_instalacion_origen"] is None
    assert data["id_instalacion_ultima_modificacion"] is None
    assert db_session.execute(text("SELECT id_usuario,id_sucursal,id_instalacion,target_key "
        "FROM operacion_idempotente WHERE op_id=:op"), {"op": op_id}).one() == (
            1, None, None, f"usuario:{usuario['id_usuario']}:rol:{rol}")
    assert db_session.execute(text("SELECT count(*) FROM outbox_event WHERE "
        "event_type='rol_asignado_a_usuario'")).scalar_one() == 0


def test_assign_replay_actor_payload_y_autorizacion(client, db_session):
    usuario = _crear_usuario(client, "REPLAY")
    rol = _crear_rol(db_session, "REPLAY")
    otro = _crear_rol(db_session, "REPLAY-OTRO")
    op_id = uuid4()
    first = _asignar(client, usuario["id_usuario"], rol, op_id=op_id)
    replay = _asignar(client, usuario["id_usuario"], rol, op_id=op_id)
    cross_actor = _asignar(client, usuario["id_usuario"], rol, op_id=op_id,
                           actor=usuario["id_usuario"])
    other_target = _asignar(client, usuario["id_usuario"], otro, op_id=op_id)
    assert first.status_code == replay.status_code == 201
    assert replay.json() == first.json()
    assert cross_actor.status_code == 409
    assert cross_actor.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert other_target.status_code == 409
    assert other_target.json()["error_code"] == "IDEMPOTENCY_TARGET_CONFLICT"
    denied = _grant_request(client, "POST",
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad",
        body={"id_rol_seguridad": rol}, headers=_headers(), granted=False)
    assert denied.status_code == 403


def test_assign_metadata_targets_states_y_duplicate(client, db_session):
    usuario = _crear_usuario(client, "VALIDATE")
    rol = _crear_rol(db_session, "VALIDATE")
    missing = _grant_request(client, "POST",
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad",
        body={"id_rol_seguridad": rol})
    assert missing.status_code == 400
    assert missing.json()["details"]["header"] == "X-Op-Id"
    assert _asignar(client, 999999999, rol).status_code == 404
    assert _asignar(client, usuario["id_usuario"], 999999999).status_code == 404
    assert _asignar(client, usuario["id_usuario"], rol).status_code == 201
    duplicate = _asignar(client, usuario["id_usuario"], rol)
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "DUPLICATE_ACTIVE_GRANT"
    inactive = _asignar(client, usuario["id_usuario"],
                        _crear_rol(db_session, "INACTIVE", "INACTIVO"))
    assert inactive.status_code == 409
    assert inactive.json()["error_code"] == "INELIGIBLE_TARGET"
    corrupt = _asignar(client, usuario["id_usuario"],
                       _crear_rol(db_session, "CORRUPT", "DESCONOCIDO"))
    assert corrupt.status_code == 500
    assert corrupt.json()["error_code"] == "TECHNICAL_INCONSISTENCY"

    usuario_inactivo = _crear_usuario(client, "INACTIVE-USER")
    db_session.execute(text(
        "UPDATE usuario SET estado_usuario='INACTIVO' WHERE id_usuario=:id"
    ), {"id": usuario_inactivo["id_usuario"]})
    db_session.commit()
    ineligible_user = _asignar(client, usuario_inactivo["id_usuario"], rol)
    assert ineligible_user.status_code == 409
    assert ineligible_user.json()["error_code"] == "INELIGIBLE_TARGET"

    usuario_corrupto = _crear_usuario(client, "CORRUPT-USER")
    db_session.execute(text(
        "UPDATE usuario SET estado_usuario='DESCONOCIDO' WHERE id_usuario=:id"
    ), {"id": usuario_corrupto["id_usuario"]})
    db_session.commit()
    corrupt_user = _asignar(client, usuario_corrupto["id_usuario"], rol)
    assert corrupt_user.status_code == 500
    assert corrupt_user.json()["error_code"] == "TECHNICAL_INCONSISTENCY"


def test_actor_puede_asignarse_a_si_mismo(client, db_session):
    actor = _crear_usuario(client, "SELF")
    rol = _crear_rol(db_session, "SELF")
    assert _asignar(client, actor["id_usuario"], rol,
                    actor=actor["id_usuario"]).status_code == 201


def test_revoke_cas_replay_receipt_provenance_y_sin_outbox(client, db_session):
    usuario = _crear_usuario(client, "REVOKE")
    rol = _crear_rol(db_session, "REVOKE")
    asignacion = _asignar(client, usuario["id_usuario"], rol).json()["data"]
    op_id = uuid4()
    first = _revocar(
        client, usuario["id_usuario"], asignacion, op_id=op_id, legacy=True
    )
    replay = _revocar(client, usuario["id_usuario"], asignacion, op_id=op_id)
    assert first.status_code == replay.status_code == 200
    assert replay.json() == first.json()
    data = first.json()["data"]
    assert data["fecha_hasta"] is not None and data["deleted_at"] is not None
    assert data["version_registro"] == asignacion["version_registro"] + 1
    assert data["id_instalacion_ultima_modificacion"] is None
    assert db_session.execute(text("SELECT id_usuario,id_sucursal,id_instalacion "
        "FROM operacion_idempotente WHERE op_id=:op"), {"op": op_id}).one() == (1, None, None)
    assert db_session.execute(text("SELECT count(*) FROM outbox_event WHERE "
        "event_type='rol_revocado_de_usuario'")).scalar_one() == 0
    active = client.get(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad"
    )
    assert active.status_code == 200
    assert active.json()["data"] == []


def test_revoke_metadata_stale_conflicts_y_nueva_revocacion(client, db_session):
    usuario = _crear_usuario(client, "REVOKE-ERR")
    rol = _crear_rol(db_session, "REVOKE-ERR")
    asignacion = _asignar(client, usuario["id_usuario"], rol).json()["data"]
    url = (f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad/"
           f"{asignacion['id_usuario_rol_seguridad']}/baja")
    missing = _grant_request(client, "PATCH", url, headers=_headers())
    assert missing.status_code == 400
    stale_op = uuid4()
    stale = _revocar(client, usuario["id_usuario"], asignacion, op_id=stale_op,
                     version=asignacion["version_registro"] + 1)
    assert stale.status_code == 412
    assert stale.json()["error_code"] == "CONCURRENCY_ERROR"
    assert db_session.execute(text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"),
                              {"op": stale_op}).scalar_one() == 0
    op_id = uuid4()
    assert _revocar(client, usuario["id_usuario"], asignacion, op_id=op_id).status_code == 200
    conflict = _revocar(client, usuario["id_usuario"], asignacion, op_id=op_id,
                        version=asignacion["version_registro"] + 1)
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    already = _revocar(client, usuario["id_usuario"],
                       {**asignacion, "version_registro": asignacion["version_registro"] + 1})
    assert already.status_code == 404


def test_command_conflict_entre_assign_y_revoke(client, db_session):
    usuario = _crear_usuario(client, "COMMAND-CONFLICT")
    rol = _crear_rol(db_session, "COMMAND-CONFLICT")
    op_id = uuid4()
    asignacion = _asignar(
        client, usuario["id_usuario"], rol, op_id=op_id
    ).json()["data"]
    response = _revocar(
        client, usuario["id_usuario"], asignacion, op_id=op_id
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENCY_COMMAND_CONFLICT"


def test_fallo_completion_revierte_mutacion_y_permite_retry(
    client, db_session,
):
    usuario = _crear_usuario(client, "ROLLBACK")
    rol = _crear_rol(db_session, "ROLLBACK")
    op_id = uuid4()
    with patch(
        "app.application.administrativo.services."
        "usuario_rol_seguridad_central_command_service.complete_operation",
        side_effect=RuntimeError("fallo inyectado"),
    ):
        failed = _asignar(client, usuario["id_usuario"], rol, op_id=op_id)
    assert failed.status_code == 500
    assert db_session.execute(text(
        "SELECT count(*) FROM usuario_rol_seguridad "
        "WHERE id_usuario=:usuario AND id_rol_seguridad=:rol"
    ), {"usuario": usuario["id_usuario"], "rol": rol}).scalar_one() == 0
    assert db_session.execute(text(
        "SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"
    ), {"op": op_id}).scalar_one() == 0
    retry = _asignar(client, usuario["id_usuario"], rol, op_id=op_id)
    assert retry.status_code == 201


def test_fallo_completion_revierte_revocacion_y_permite_retry(
    client, db_session,
):
    usuario = _crear_usuario(client, "ROLLBACK-REVOKE")
    rol = _crear_rol(db_session, "ROLLBACK-REVOKE")
    asignacion = _asignar(client, usuario["id_usuario"], rol).json()["data"]
    op_id = uuid4()
    with patch(
        "app.application.administrativo.services."
        "usuario_rol_seguridad_central_command_service.complete_operation",
        side_effect=RuntimeError("fallo inyectado"),
    ):
        failed = _revocar(
            client, usuario["id_usuario"], asignacion, op_id=op_id
        )
    assert failed.status_code == 500
    row = db_session.execute(text(
        "SELECT deleted_at,fecha_hasta,version_registro "
        "FROM usuario_rol_seguridad WHERE id_usuario_rol_seguridad=:id"
    ), {"id": asignacion["id_usuario_rol_seguridad"]}).one()
    assert row.deleted_at is None and row.fecha_hasta is None
    assert row.version_registro == asignacion["version_registro"]
    assert db_session.execute(text(
        "SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"
    ), {"op": op_id}).scalar_one() == 0
    retry = _revocar(client, usuario["id_usuario"], asignacion, op_id=op_id)
    assert retry.status_code == 200


def test_autorrevocacion_y_d1_antes_de_replay(client, db_session):
    actor = _crear_usuario(client, "SELF-REVOKE")
    rol = _crear_rol(db_session, "SELF-REVOKE")
    asignacion = _asignar(client, actor["id_usuario"], rol,
                          actor=actor["id_usuario"]).json()["data"]
    op_id = uuid4()
    assert _revocar(client, actor["id_usuario"], asignacion, op_id=op_id,
                    actor=actor["id_usuario"]).status_code == 200
    denied = _grant_request(client, "PATCH",
        f"/api/v1/administrativo/usuarios/{actor['id_usuario']}/roles-seguridad/"
        f"{asignacion['id_usuario_rol_seguridad']}/baja",
        headers=_headers(op_id, asignacion["version_registro"]),
        actor=actor["id_usuario"], granted=False)
    assert denied.status_code == 403


def test_revoke_lifecycle_incoherente_es_tecnico(client, db_session):
    usuario = _crear_usuario(client, "CORRUPT")
    rol = _crear_rol(db_session, "CORRUPT")
    asignacion = _asignar(client, usuario["id_usuario"], rol).json()["data"]
    db_session.execute(text("UPDATE usuario_rol_seguridad SET deleted_at=clock_timestamp() "
                            "WHERE id_usuario_rol_seguridad=:id"),
                       {"id": asignacion["id_usuario_rol_seguridad"]})
    response = _revocar(client, usuario["id_usuario"], asignacion)
    assert response.status_code == 500
    assert response.json()["error_code"] == "TECHNICAL_INCONSISTENCY"


def test_openapi_grants_centrales(client):
    paths = client.get("/openapi.json").json()["paths"]
    base = "/api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad"
    assign, revoke = paths[base]["post"], paths[f"{base}/{{id_asignacion}}/baja"]["patch"]
    assert {p["name"] for p in assign["parameters"] if p.get("required")} >= {"X-Op-Id"}
    assert {p["name"] for p in revoke["parameters"] if p.get("required")} >= {
        "X-Op-Id", "If-Match-Version"}
    names = {p["name"] for p in assign["parameters"] + revoke["parameters"]}
    assert not {"X-Usuario-Id", "X-Sucursal-Id", "X-Instalacion-Id"} & names
    assert "412" in revoke["responses"]


def test_reads_asociados_siguen_funcionando(client, db_session):
    usuario = _crear_usuario(client, "READS")
    rol = _crear_rol(db_session, "READS")
    asignacion = _asignar(client, usuario["id_usuario"], rol).json()["data"]
    by_user = client.get(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad")
    by_role = client.get(f"/api/v1/administrativo/roles-seguridad/{rol}/usuarios")
    assert by_user.status_code == by_role.status_code == 200
    wanted = asignacion["id_usuario_rol_seguridad"]
    assert wanted in {row["id_usuario_rol_seguridad"] for row in by_user.json()["data"]}
    assert wanted in {row["id_usuario_rol_seguridad"] for row in by_role.json()["data"]}
    assert client.get(
        "/api/v1/administrativo/usuarios/999999999/roles-seguridad"
    ).status_code == 404
    assert client.get(
        "/api/v1/administrativo/roles-seguridad/999999999/usuarios"
    ).status_code == 404
