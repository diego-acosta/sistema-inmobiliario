from uuid import uuid4

from sqlalchemy import text


CORE_HEADERS = {
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def headers(op_id: str | None = None) -> dict[str, str]:
    return {**CORE_HEADERS, "X-Op-Id": op_id or str(uuid4())}


def payload(codigo: str = "SUC-OPE-250") -> dict[str, object]:
    return {
        "codigo_sucursal": codigo,
        "nombre_sucursal": f"Sucursal {codigo}",
        "descripcion_sucursal": "Sucursal operativa de test",
        "estado_sucursal": "ACTIVA",
        "es_casa_central": False,
        "permite_operacion": True,
        "observaciones": "Creada por tests #250",
    }


def test_crear_sucursal_ok_incluye_version_y_metadata_core_ef(client, db_session):
    op_id = str(uuid4())
    response = client.post(
        "/api/v1/operativo/sucursales",
        json=payload("SUC-OPE-OK"),
        headers=headers(op_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["version_registro"] == 1
    assert data["deleted_at"] is None
    assert data["id_instalacion_origen"] == 1
    assert data["id_instalacion_ultima_modificacion"] == 1
    assert data["op_id_alta"] == op_id
    assert data["op_id_ultima_modificacion"] == op_id

    row = db_session.execute(
        text(
            """
            SELECT version_registro, id_instalacion_origen,
                   id_instalacion_ultima_modificacion, op_id_alta::text AS op_id_alta,
                   deleted_at
            FROM sucursal
            WHERE id_sucursal = :id_sucursal
            """
        ),
        {"id_sucursal": data["id_sucursal"]},
    ).mappings().one()
    assert row["version_registro"] == 1
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert row["op_id_alta"] == op_id
    assert row["deleted_at"] is None

    outbox = db_session.execute(
        text(
            """
            SELECT event_type, aggregate_type, aggregate_id
            FROM outbox_event
            WHERE event_type = 'sucursal_creada'
              AND aggregate_id = :id_sucursal
            """
        ),
        {"id_sucursal": data["id_sucursal"]},
    ).mappings().one()
    assert outbox["aggregate_type"] == "sucursal"


def test_alta_idempotente_mismo_op_id_payload_compatible_no_duplica(client, db_session):
    op_id = str(uuid4())
    body = payload("SUC-OPE-IDEMP")

    first = client.post("/api/v1/operativo/sucursales", json=body, headers=headers(op_id))
    second = client.post("/api/v1/operativo/sucursales", json=body, headers=headers(op_id))

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["id_sucursal"] == first.json()["data"]["id_sucursal"]
    count = db_session.execute(
        text("SELECT COUNT(*) FROM sucursal WHERE op_id_alta = :op_id"),
        {"op_id": op_id},
    ).scalar()
    assert count == 1


def test_alta_mismo_op_id_payload_incompatible_devuelve_409(client):
    op_id = str(uuid4())
    first_payload = payload("SUC-OPE-CONFLICT")
    second_payload = {**first_payload, "nombre_sucursal": "Otro nombre"}

    assert client.post(
        "/api/v1/operativo/sucursales", json=first_payload, headers=headers(op_id)
    ).status_code == 200
    response = client.post(
        "/api/v1/operativo/sucursales", json=second_payload, headers=headers(op_id)
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENT_DUPLICATE"


def test_duplicado_activo_codigo_sucursal_devuelve_409(client):
    first_payload = payload("SUC-OPE-DUP")
    second_payload = {**first_payload, "nombre_sucursal": "Nombre distinto"}

    assert client.post(
        "/api/v1/operativo/sucursales", json=first_payload, headers=headers()
    ).status_code == 200
    response = client.post(
        "/api/v1/operativo/sucursales", json=second_payload, headers=headers()
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TECHNICAL_INCONSISTENCY"


def test_listar_sucursales_excluye_bajas(client, db_session):
    active = client.post(
        "/api/v1/operativo/sucursales", json=payload("SUC-OPE-LIST-A"), headers=headers()
    ).json()["data"]
    deleted = client.post(
        "/api/v1/operativo/sucursales", json=payload("SUC-OPE-LIST-D"), headers=headers()
    ).json()["data"]
    db_session.execute(
        text("UPDATE sucursal SET deleted_at = CURRENT_TIMESTAMP WHERE id_sucursal = :id"),
        {"id": deleted["id_sucursal"]},
    )
    db_session.flush()

    response = client.get("/api/v1/operativo/sucursales")

    assert response.status_code == 200
    ids = {item["id_sucursal"] for item in response.json()["data"]}
    assert active["id_sucursal"] in ids
    assert deleted["id_sucursal"] not in ids


def test_obtener_ficha_ok(client):
    created = client.post(
        "/api/v1/operativo/sucursales", json=payload("SUC-OPE-GET"), headers=headers()
    ).json()["data"]

    response = client.get(f"/api/v1/operativo/sucursales/{created['id_sucursal']}")

    assert response.status_code == 200
    assert response.json()["data"]["id_sucursal"] == created["id_sucursal"]


def test_obtener_ficha_inexistente_devuelve_404(client):
    response = client.get("/api/v1/operativo/sucursales/999999999")

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_falta_headers_core_ef_en_post_devuelve_400(client):
    response = client.post("/api/v1/operativo/sucursales", json=payload("SUC-OPE-NO-H"))

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"]["header"] == "X-Op-Id"
