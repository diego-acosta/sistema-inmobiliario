from uuid import uuid4

import pytest
from sqlalchemy import text


CORE_HEADERS = {"X-Usuario-Id": "1", "X-Sucursal-Id": "1", "X-Instalacion-Id": "1"}


def headers(op_id: str | None = None) -> dict[str, str]:
    return {**CORE_HEADERS, "X-Op-Id": op_id or str(uuid4())}


@pytest.fixture(autouse=True)
def usuario_sucursal_core_ef(db_session):
    db_session.execute(text(open("backend/database/patch_usuario_sucursal_core_ef_20260702.sql").read()))
    db_session.commit()


def user_payload(suffix: str) -> dict:
    return {
        "codigo_usuario": f"USR-ALC-{suffix}",
        "login": f"usr.alc.{suffix}",
        "email": f"usr.alc.{suffix}@example.com",
        "estado_usuario": "ACTIVO",
        "usuario_sistema_interno": False,
        "observaciones": "Usuario alcance operativo",
    }


def suc_payload(suffix: str) -> dict:
    return {
        "codigo_sucursal": f"SUC-ALC-{suffix}",
        "nombre_sucursal": f"Sucursal alcance {suffix}",
        "descripcion_sucursal": "Sucursal alcance operativo",
        "estado_sucursal": "ACTIVA",
        "es_casa_central": False,
        "permite_operacion": True,
        "observaciones": "Sucursal test #262",
    }


def crear_usuario(client, suffix: str = "001") -> dict:
    r = client.post("/api/v1/administrativo/usuarios", json=user_payload(suffix), headers=headers())
    assert r.status_code == 201, r.text
    return r.json()["data"]


def crear_sucursal(client, suffix: str = "001") -> dict:
    r = client.post("/api/v1/operativo/sucursales", json=suc_payload(suffix), headers=headers())
    assert r.status_code == 201, r.text
    return r.json()["data"]


def alcance_payload(id_sucursal: int, **overrides) -> dict:
    data = {
        "id_sucursal": id_sucursal,
        "tipo_habilitacion_sucursal": "OPERATIVA_BASICA",
        "es_sucursal_predeterminada": False,
        "puede_operar": True,
        "puede_consultar": True,
        "puede_administrar": False,
        "fecha_desde": "2026-07-02T00:00:00",
        "fecha_hasta": None,
        "observaciones": "Alcance básico #262",
    }
    data.update(overrides)
    return data


def test_consultar_alcance_sin_sucursales_devuelve_lista_vacia(client):
    usuario = crear_usuario(client, "SIN-SUC")
    r = client.get(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/alcance-operativo")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["sucursales_asignadas"] == []
    assert data["sucursal_predeterminada"] is None
    assert data["estado_vigencia"] == "SIN_ALCANCE"


def test_asignar_sucursal_ok_incluye_version_y_metadata_core_ef(client, db_session):
    usuario = crear_usuario(client, "OK")
    sucursal = crear_sucursal(client, "OK")
    op_id = str(uuid4())
    r = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(sucursal["id_sucursal"], es_sucursal_predeterminada=True),
        headers=headers(op_id),
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["version_registro"] == 1
    assert data["deleted_at"] is None
    assert data["id_instalacion_origen"] == 1
    assert data["id_instalacion_ultima_modificacion"] == 1
    assert data["op_id_alta"] == op_id
    assert data["op_id_ultima_modificacion"] == op_id
    row = db_session.execute(text("""
        SELECT uid_global, version_registro, created_at, updated_at, deleted_at,
               id_instalacion_origen, id_instalacion_ultima_modificacion,
               op_id_alta::text AS op_id_alta, op_id_ultima_modificacion::text AS op_id_ultima_modificacion
        FROM usuario_sucursal WHERE id_usuario_sucursal = :id
    """), {"id": data["id_usuario_sucursal"]}).mappings().one()
    assert row["uid_global"] is not None
    assert row["version_registro"] == 1
    assert row["created_at"] is not None
    assert row["updated_at"] is not None
    assert row["deleted_at"] is None
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert row["op_id_alta"] == op_id
    assert row["op_id_ultima_modificacion"] == op_id


def test_replay_idempotente_compatible_no_duplica_vinculo_ni_outbox(client, db_session):
    usuario = crear_usuario(client, "IDEMP")
    sucursal = crear_sucursal(client, "IDEMP")
    op_id = str(uuid4())
    payload = alcance_payload(sucursal["id_sucursal"])
    first = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=payload, headers=headers(op_id))
    second = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=payload, headers=headers(op_id))
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["data"]["id_usuario_sucursal"] == first.json()["data"]["id_usuario_sucursal"]
    assert db_session.execute(text("SELECT COUNT(*) FROM usuario_sucursal WHERE op_id_alta = :op"), {"op": op_id}).scalar() == 1
    assert db_session.execute(text("SELECT COUNT(*) FROM outbox_event WHERE event_type = 'usuario_asociado_a_sucursal' AND aggregate_id = :id"), {"id": first.json()["data"]["id_usuario_sucursal"]}).scalar() == 1


def test_replay_idempotente_incompatible_devuelve_409(client):
    usuario = crear_usuario(client, "IDEMP-DIFF")
    sucursal = crear_sucursal(client, "IDEMP-DIFF")
    op_id = str(uuid4())
    first = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers(op_id))
    second = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"], puede_administrar=True), headers=headers(op_id))
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENT_DUPLICATE"


def test_duplicado_activo_distinto_op_id_devuelve_409(client):
    usuario = crear_usuario(client, "DUP")
    sucursal = crear_sucursal(client, "DUP")
    first = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers())
    second = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers())
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "TECHNICAL_INCONSISTENCY"


def test_usuario_o_sucursal_inexistente_y_sucursal_baja_devuelven_404(client, db_session):
    sucursal = crear_sucursal(client, "404")
    assert client.post("/api/v1/administrativo/usuarios/999999/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers()).status_code == 404
    usuario = crear_usuario(client, "404")
    assert client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(999999), headers=headers()).status_code == 404
    db_session.execute(text("UPDATE sucursal SET deleted_at = CURRENT_TIMESTAMP, fecha_baja = CURRENT_TIMESTAMP WHERE id_sucursal = :id"), {"id": sucursal["id_sucursal"]})
    db_session.commit()
    assert client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]), headers=headers()).status_code == 404


def test_falta_headers_core_ef_en_post_devuelve_400(client):
    usuario = crear_usuario(client, "HEAD")
    sucursal = crear_sucursal(client, "HEAD")
    r = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"]))
    assert r.status_code == 400
    assert r.json()["error_code"] == "VALIDATION_ERROR"


def test_get_lista_y_alcance_consolidado_incluyen_sucursales_y_flags(client):
    usuario = crear_usuario(client, "GET")
    sucursal = crear_sucursal(client, "GET")
    r = client.post(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales", json=alcance_payload(sucursal["id_sucursal"], puede_administrar=True), headers=headers())
    assert r.status_code == 201
    lista = client.get(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales")
    alcance = client.get(f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/alcance-operativo")
    assert lista.status_code == 200
    assert len(lista.json()["data"]) == 1
    assert alcance.status_code == 200
    data = alcance.json()["data"]
    assert len(data["sucursales_asignadas"]) == 1
    assert data["puede_operar"] is True
    assert data["puede_consultar"] is True
    assert data["puede_administrar"] is True


def test_post_sin_fecha_desde_devuelve_422(client):
    usuario = crear_usuario(client, "SIN-FECHA")
    sucursal = crear_sucursal(client, "SIN-FECHA")
    payload = alcance_payload(sucursal["id_sucursal"])
    payload.pop("fecha_desde")

    response = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=payload,
        headers=headers(),
    )

    assert response.status_code == 422


def test_segunda_sucursal_predeterminada_devuelve_409_y_preserva_primera(client, db_session):
    usuario = crear_usuario(client, "PRED")
    suc1 = crear_sucursal(client, "PRED1")
    suc2 = crear_sucursal(client, "PRED2")
    first = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(suc1["id_sucursal"], es_sucursal_predeterminada=True),
        headers=headers(),
    )
    second = client.post(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/sucursales",
        json=alcance_payload(suc2["id_sucursal"], es_sucursal_predeterminada=True),
        headers=headers(),
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "TECHNICAL_INCONSISTENCY"
    row = db_session.execute(text("""
        SELECT es_sucursal_predeterminada, version_registro
        FROM usuario_sucursal
        WHERE id_usuario_sucursal = :id
    """), {"id": first.json()["data"]["id_usuario_sucursal"]}).mappings().one()
    assert row["es_sucursal_predeterminada"] is True
    assert row["version_registro"] == 1


def test_existen_indices_unicos_usuario_sucursal_core_ef(db_session):
    assert db_session.execute(text("SELECT to_regclass('public.ux_usuario_sucursal_op_id_alta')")).scalar() == "ux_usuario_sucursal_op_id_alta"
    assert db_session.execute(text("SELECT to_regclass('public.ux_usuario_sucursal_uid_global')")).scalar() == "ux_usuario_sucursal_uid_global"
    assert db_session.execute(text("SELECT to_regclass('public.ux_usuario_sucursal_predeterminada_activa')")).scalar() == "ux_usuario_sucursal_predeterminada_activa"
