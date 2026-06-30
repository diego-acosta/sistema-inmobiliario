from uuid import uuid4

from sqlalchemy import text


CORE_HEADERS = {
    "X-Op-Id": str(uuid4()),
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _payload(suffix: str = "001") -> dict:
    return {
        "codigo_usuario": f"USR-ADM-{suffix}",
        "login": f"usr.adm.{suffix}",
        "email": f"usr.adm.{suffix}@example.com",
        "estado_usuario": "ACTIVO",
        "usuario_sistema_interno": False,
        "observaciones": "Usuario administrativo de prueba",
    }


def test_create_usuario_sistema_requiere_headers_core_ef(client):
    response = client.post("/api/v1/administrativo/usuarios", json=_payload())

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "CORE_EF_HEADERS_INVALIDOS"
    assert body["details"]["header"] == "X-Op-Id"


def test_create_list_get_y_baja_usuario_sistema(client, db_session):
    payload = _payload("CRUD")

    create_response = client.post(
        "/api/v1/administrativo/usuarios",
        json=payload,
        headers={**CORE_HEADERS, "X-Op-Id": str(uuid4())},
    )

    assert create_response.status_code == 201
    created = create_response.json()["data"]
    assert created["codigo_usuario"] == payload["codigo_usuario"]
    assert created["login"] == payload["login"]
    assert created["estado_usuario"] == "ACTIVO"
    assert created["fecha_baja"] is None

    id_usuario = created["id_usuario"]

    list_response = client.get("/api/v1/administrativo/usuarios")
    assert list_response.status_code == 200
    assert any(item["id_usuario"] == id_usuario for item in list_response.json()["data"])

    detail_response = client.get(f"/api/v1/administrativo/usuarios/{id_usuario}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id_usuario"] == id_usuario

    baja_response = client.patch(
        f"/api/v1/administrativo/usuarios/{id_usuario}/baja",
        headers={**CORE_HEADERS, "X-Op-Id": str(uuid4())},
    )
    assert baja_response.status_code == 200
    baja_data = baja_response.json()["data"]
    assert baja_data["estado_usuario"] == "INACTIVO"
    assert baja_data["fecha_baja"] is not None

    list_active_response = client.get("/api/v1/administrativo/usuarios")
    assert all(item["id_usuario"] != id_usuario for item in list_active_response.json()["data"])

    list_all_response = client.get("/api/v1/administrativo/usuarios?incluir_bajas=true")
    assert any(item["id_usuario"] == id_usuario for item in list_all_response.json()["data"])

    row = db_session.execute(
        text("SELECT estado_usuario, fecha_baja FROM usuario WHERE id_usuario = :id"),
        {"id": id_usuario},
    ).mappings().one()
    assert row["estado_usuario"] == "INACTIVO"
    assert row["fecha_baja"] is not None


def test_baja_usuario_sistema_requiere_headers_core_ef(client):
    response = client.patch("/api/v1/administrativo/usuarios/999999/baja")

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "CORE_EF_HEADERS_INVALIDOS"
