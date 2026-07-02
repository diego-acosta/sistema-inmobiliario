from uuid import uuid4

from sqlalchemy import text

CORE_HEADERS = {
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def headers(op_id: str | None = None) -> dict[str, str]:
    return {**CORE_HEADERS, "X-Op-Id": op_id or str(uuid4())}


def payload(codigo: str = "INST-OPE-251", id_sucursal: int = 1) -> dict[str, object]:
    return {
        "id_sucursal": id_sucursal,
        "codigo_instalacion": codigo,
        "nombre_instalacion": f"Instalación {codigo}",
        "descripcion_instalacion": "Instalación operativa de test",
        "estado_instalacion": "ACTIVA",
        "es_principal": False,
        "permite_sincronizacion": True,
        "identificador_tecnico": f"tech-{codigo}",
        "direccion_local": "Calle Test 123",
        "observaciones": "Creada por tests #251",
    }


def test_existe_indice_unico_instalacion_op_id_alta(db_session):
    index_exists = db_session.execute(
        text("SELECT to_regclass('public.ux_instalacion_op_id_alta')")
    ).scalar()

    assert index_exists == "ux_instalacion_op_id_alta"


def test_crear_instalacion_ok_incluye_version_metadata_y_outbox(client, db_session):
    op_id = str(uuid4())
    response = client.post(
        "/api/v1/operativo/instalaciones",
        json=payload("INST-OPE-OK"),
        headers=headers(op_id),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["version_registro"] == 1
    assert data["id_instalacion_origen"] == 1
    assert data["id_instalacion_ultima_modificacion"] == 1
    assert data["op_id_alta"] == op_id
    assert data["op_id_ultima_modificacion"] == op_id

    row = (
        db_session.execute(
            text("""
            SELECT version_registro, id_instalacion_origen,
                   id_instalacion_ultima_modificacion, op_id_alta::text AS op_id_alta,
                   deleted_at
            FROM instalacion
            WHERE id_instalacion = :id_instalacion
            """),
            {"id_instalacion": data["id_instalacion"]},
        )
        .mappings()
        .one()
    )
    assert row["version_registro"] == 1
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert row["op_id_alta"] == op_id
    assert row["deleted_at"] is None

    outbox_count = db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM outbox_event
            WHERE event_type = 'instalacion_creada'
              AND aggregate_id = :id_instalacion
            """),
        {"id_instalacion": data["id_instalacion"]},
    ).scalar()
    assert outbox_count == 1


def test_alta_idempotente_mismo_op_id_payload_compatible_no_duplica(client, db_session):
    op_id = str(uuid4())
    body = payload("INST-OPE-IDEMP")

    first = client.post(
        "/api/v1/operativo/instalaciones", json=body, headers=headers(op_id)
    )
    second = client.post(
        "/api/v1/operativo/instalaciones", json=body, headers=headers(op_id)
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert (
        second.json()["data"]["id_instalacion"]
        == first.json()["data"]["id_instalacion"]
    )
    count = db_session.execute(
        text("SELECT COUNT(*) FROM instalacion WHERE op_id_alta = :op_id"),
        {"op_id": op_id},
    ).scalar()
    assert count == 1
    outbox_count = db_session.execute(
        text("""
            SELECT COUNT(*) FROM outbox_event
            WHERE event_type = 'instalacion_creada' AND aggregate_id = :id_instalacion
            """),
        {"id_instalacion": first.json()["data"]["id_instalacion"]},
    ).scalar()
    assert outbox_count == 1


def test_alta_mismo_op_id_payload_incompatible_devuelve_409(client):
    op_id = str(uuid4())
    first_payload = payload("INST-OPE-CONFLICT")
    second_payload = {**first_payload, "nombre_instalacion": "Otro nombre"}

    assert (
        client.post(
            "/api/v1/operativo/instalaciones",
            json=first_payload,
            headers=headers(op_id),
        ).status_code
        == 201
    )
    response = client.post(
        "/api/v1/operativo/instalaciones", json=second_payload, headers=headers(op_id)
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENT_DUPLICATE"


def test_mismo_op_id_distinto_codigo_no_crea_dos_filas(client, db_session):
    op_id = str(uuid4())
    assert (
        client.post(
            "/api/v1/operativo/instalaciones",
            json=payload("INST-OPE-SAME-A"),
            headers=headers(op_id),
        ).status_code
        == 201
    )
    response = client.post(
        "/api/v1/operativo/instalaciones",
        json=payload("INST-OPE-SAME-B"),
        headers=headers(op_id),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    count = db_session.execute(
        text("SELECT COUNT(*) FROM instalacion WHERE op_id_alta = :op_id"),
        {"op_id": op_id},
    ).scalar()
    assert count == 1


def test_duplicado_activo_codigo_instalacion_devuelve_409(client):
    first_payload = payload("INST-OPE-DUP")
    second_payload = {**first_payload, "nombre_instalacion": "Nombre distinto"}

    assert (
        client.post(
            "/api/v1/operativo/instalaciones", json=first_payload, headers=headers()
        ).status_code
        == 201
    )
    response = client.post(
        "/api/v1/operativo/instalaciones", json=second_payload, headers=headers()
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TECHNICAL_INCONSISTENCY"


def test_sucursal_inexistente_devuelve_404(client):
    response = client.post(
        "/api/v1/operativo/instalaciones",
        json=payload("INST-OPE-NO-SUC", 999999999),
        headers=headers(),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_estado_instalacion_invalido_devuelve_422(client):
    response = client.post(
        "/api/v1/operativo/instalaciones",
        json={**payload("INST-OPE-EST-INV"), "estado_instalacion": "SUSPENDIDA"},
        headers=headers(),
    )

    assert response.status_code == 422


def test_listar_instalaciones_excluye_bajas_y_filtra_por_sucursal(client, db_session):
    active = client.post(
        "/api/v1/operativo/instalaciones",
        json=payload("INST-OPE-LIST-A"),
        headers=headers(),
    ).json()["data"]
    other_sucursal = client.post(
        "/api/v1/operativo/sucursales",
        json={
            "codigo_sucursal": "SUC-OPE-INST-FILTER",
            "nombre_sucursal": "Sucursal filtro instalación",
            "estado_sucursal": "ACTIVA",
        },
        headers=headers(),
    ).json()["data"]
    other = client.post(
        "/api/v1/operativo/instalaciones",
        json=payload("INST-OPE-LIST-OTHER", other_sucursal["id_sucursal"]),
        headers=headers(),
    ).json()["data"]
    deleted = client.post(
        "/api/v1/operativo/instalaciones",
        json=payload("INST-OPE-LIST-D"),
        headers=headers(),
    ).json()["data"]
    db_session.execute(
        text(
            "UPDATE instalacion SET deleted_at = CURRENT_TIMESTAMP WHERE id_instalacion = :id"
        ),
        {"id": deleted["id_instalacion"]},
    )
    db_session.flush()

    response = client.get("/api/v1/operativo/instalaciones", params={"id_sucursal": 1})

    assert response.status_code == 200
    ids = {item["id_instalacion"] for item in response.json()["data"]}
    assert active["id_instalacion"] in ids
    assert deleted["id_instalacion"] not in ids
    assert other["id_instalacion"] not in ids


def test_listar_filtra_por_estado_instalacion(client):
    active = client.post(
        "/api/v1/operativo/instalaciones",
        json=payload("INST-OPE-EST-A"),
        headers=headers(),
    ).json()["data"]
    inactive = client.post(
        "/api/v1/operativo/instalaciones",
        json={**payload("INST-OPE-EST-I"), "estado_instalacion": "INACTIVA"},
        headers=headers(),
    ).json()["data"]

    response = client.get(
        "/api/v1/operativo/instalaciones", params={"estado_instalacion": "INACTIVA"}
    )

    assert response.status_code == 200
    ids = {item["id_instalacion"] for item in response.json()["data"]}
    assert inactive["id_instalacion"] in ids
    assert active["id_instalacion"] not in ids


def test_obtener_ficha_ok(client):
    created = client.post(
        "/api/v1/operativo/instalaciones",
        json=payload("INST-OPE-GET"),
        headers=headers(),
    ).json()["data"]

    response = client.get(
        f"/api/v1/operativo/instalaciones/{created['id_instalacion']}"
    )

    assert response.status_code == 200
    assert response.json()["data"]["id_instalacion"] == created["id_instalacion"]


def test_obtener_ficha_inexistente_devuelve_404(client):
    response = client.get("/api/v1/operativo/instalaciones/999999999")

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_falta_headers_core_ef_en_post_devuelve_400(client):
    response = client.post(
        "/api/v1/operativo/instalaciones", json=payload("INST-OPE-NO-H")
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"]["header"] == "X-Op-Id"
