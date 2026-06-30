from uuid import uuid4

from sqlalchemy import text


CORE_HEADERS = {
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _headers(op_id: str | None = None, *, version: int | None = None) -> dict[str, str]:
    headers = {**CORE_HEADERS, "X-Op-Id": op_id or str(uuid4())}
    if version is not None:
        headers["If-Match-Version"] = str(version)
    return headers


def _payload(suffix: str = "001") -> dict:
    return {
        "codigo_usuario": f"USR-ADM-{suffix}",
        "login": f"usr.adm.{suffix}",
        "email": f"usr.adm.{suffix}@example.com",
        "estado_usuario": "ACTIVO",
        "usuario_sistema_interno": False,
        "observaciones": "Usuario administrativo de prueba",
    }


def _crear_usuario(client, suffix: str = "CRUD", op_id: str | None = None) -> dict:
    response = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload(suffix),
        headers=_headers(op_id),
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_create_usuario_sistema_requiere_headers_core_ef(client):
    response = client.post("/api/v1/administrativo/usuarios", json=_payload())

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"]["header"] == "X-Op-Id"


def test_create_list_get_y_baja_usuario_sistema(client, db_session):
    payload = _payload("CRUD")

    create_response = client.post(
        "/api/v1/administrativo/usuarios",
        json=payload,
        headers=_headers(),
    )

    assert create_response.status_code == 201
    created = create_response.json()["data"]
    assert created["codigo_usuario"] == payload["codigo_usuario"]
    assert created["login"] == payload["login"]
    assert created["estado_usuario"] == "ACTIVO"
    assert created["fecha_baja"] is None
    assert created["version_registro"] == 1

    id_usuario = created["id_usuario"]

    list_response = client.get("/api/v1/administrativo/usuarios")
    assert list_response.status_code == 200
    assert any(item["id_usuario"] == id_usuario for item in list_response.json()["data"])

    detail_response = client.get(f"/api/v1/administrativo/usuarios/{id_usuario}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id_usuario"] == id_usuario

    baja_response = client.patch(
        f"/api/v1/administrativo/usuarios/{id_usuario}/baja",
        headers=_headers(version=created["version_registro"]),
    )
    assert baja_response.status_code == 200
    baja_data = baja_response.json()["data"]
    assert baja_data["estado_usuario"] == "INACTIVO"
    assert baja_data["fecha_baja"] is not None
    assert baja_data["version_registro"] == created["version_registro"] + 1

    list_active_response = client.get("/api/v1/administrativo/usuarios")
    assert all(item["id_usuario"] != id_usuario for item in list_active_response.json()["data"])

    list_all_response = client.get("/api/v1/administrativo/usuarios?incluir_bajas=true")
    assert any(item["id_usuario"] == id_usuario for item in list_all_response.json()["data"])

    row = db_session.execute(
        text(
            """
            SELECT estado_usuario, fecha_baja, deleted_at, version_registro,
                   id_instalacion_origen, id_instalacion_ultima_modificacion,
                   op_id_alta, op_id_ultima_modificacion
            FROM usuario
            WHERE id_usuario = :id
            """
        ),
        {"id": id_usuario},
    ).mappings().one()
    assert row["estado_usuario"] == "INACTIVO"
    assert row["fecha_baja"] is not None
    assert row["deleted_at"] is not None
    assert row["version_registro"] == 2
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert row["op_id_alta"] is not None
    assert row["op_id_ultima_modificacion"] is not None


def test_post_retry_mismo_op_id_devuelve_mismo_resultado(client):
    op_id = str(uuid4())
    payload = _payload("RETRY")

    first = client.post("/api/v1/administrativo/usuarios", json=payload, headers=_headers(op_id))
    retry = client.post("/api/v1/administrativo/usuarios", json=payload, headers=_headers(op_id))

    assert first.status_code == 201
    assert retry.status_code == 201
    assert retry.json()["data"] == first.json()["data"]


def test_post_retry_mismo_op_id_payload_distinto_devuelve_409(client, db_session):
    op_id = str(uuid4())
    payload = _payload("RETRY-DIFF")
    changed = {**payload, "login": "usr.adm.retry.diff.changed"}

    first = client.post("/api/v1/administrativo/usuarios", json=payload, headers=_headers(op_id))
    retry = client.post("/api/v1/administrativo/usuarios", json=changed, headers=_headers(op_id))

    assert first.status_code == 201
    assert retry.status_code == 409
    assert retry.json()["error_code"] == "IDEMPOTENT_DUPLICATE"

    count = db_session.execute(
        text("SELECT COUNT(*) FROM usuario WHERE op_id_alta = :op_id"),
        {"op_id": op_id},
    ).scalar_one()
    assert count == 1


def test_baja_usuario_sistema_requiere_headers_core_ef(client):
    response = client.patch("/api/v1/administrativo/usuarios/999999/baja")

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "VALIDATION_ERROR"


def test_baja_sin_if_match_version_devuelve_validation_error(client):
    created = _crear_usuario(client, "NO-IFMATCH")

    response = client.patch(
        f"/api/v1/administrativo/usuarios/{created['id_usuario']}/baja",
        headers=_headers(),
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert response.json()["details"]["header"] == "If-Match-Version"


def test_baja_if_match_desactualizado_devuelve_concurrency_error(client):
    created = _crear_usuario(client, "STALE")

    response = client.patch(
        f"/api/v1/administrativo/usuarios/{created['id_usuario']}/baja",
        headers=_headers(version=created["version_registro"] + 10),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_retry_mismo_op_id_no_incrementa_dos_veces_version(client):
    created = _crear_usuario(client, "BAJA-RETRY")
    op_id = str(uuid4())

    first = client.patch(
        f"/api/v1/administrativo/usuarios/{created['id_usuario']}/baja",
        headers=_headers(op_id, version=created["version_registro"]),
    )
    retry = client.patch(
        f"/api/v1/administrativo/usuarios/{created['id_usuario']}/baja",
        headers=_headers(op_id, version=created["version_registro"]),
    )

    assert first.status_code == 200
    assert retry.status_code == 200
    assert first.json()["data"]["version_registro"] == created["version_registro"] + 1
    assert retry.json()["data"]["version_registro"] == first.json()["data"]["version_registro"]
