from sqlalchemy import text

HEADERS = {
    "X-Op-Id": "750e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}

PAYLOAD = {
    "id_sucursal": 1,
    "id_instalacion": 1,
    "clave_configuracion": "modo_operacion_local",
    "valor_configuracion": "LOCAL",
    "tipo_valor": "TEXTO",
    "descripcion": "Modo local",
    "estado_configuracion": "ACTIVA",
}


def _create(client, op_id=HEADERS["X-Op-Id"], payload=None):
    return client.post(
        "/api/v1/operativo/configuracion-local",
        headers={**HEADERS, "X-Op-Id": op_id},
        json=payload or PAYLOAD,
    )


def test_get_configuracion_local_sin_datos_devuelve_lista_vacia(client):
    response = client.get(
        "/api/v1/operativo/configuracion-local",
        params={"id_sucursal": 1, "id_instalacion": 1},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}


def test_crear_configuracion_local_ok_persiste_core_ef_y_outbox(client, db_session):
    response = _create(client)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["version_registro"] == 1
    assert data["uid_global"]
    assert data["id_instalacion_origen"] == 1
    assert data["id_instalacion_ultima_modificacion"] == 1
    assert data["op_id_alta"] == HEADERS["X-Op-Id"]

    row = db_session.execute(
        text(
            "SELECT COUNT(*) FROM outbox_event WHERE aggregate_type='configuracion_local' AND event_type='configuracion_local_creada'"
        )
    ).scalar()
    assert row == 1


def test_replay_idempotente_compatible_no_duplica_configuracion_ni_outbox(
    client, db_session
):
    first = _create(client)
    second = _create(client)
    assert first.status_code == 201
    assert second.status_code == 201
    assert (
        second.json()["data"]["id_configuracion_local"]
        == first.json()["data"]["id_configuracion_local"]
    )
    assert (
        db_session.execute(
            text("SELECT COUNT(*) FROM configuracion_local WHERE op_id_alta=:op"),
            {"op": HEADERS["X-Op-Id"]},
        ).scalar()
        == 1
    )
    assert (
        db_session.execute(
            text(
                "SELECT COUNT(*) FROM outbox_event WHERE aggregate_type='configuracion_local'"
            )
        ).scalar()
        == 1
    )


def test_replay_idempotente_incompatible_devuelve_409(client):
    assert _create(client).status_code == 201
    payload = {**PAYLOAD, "valor_configuracion": "OTRO"}
    response = _create(client, payload=payload)
    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENT_DUPLICATE"


def test_duplicado_activo_clave_contexto_devuelve_409(client):
    assert _create(client).status_code == 201
    response = _create(client, op_id="750e8400-e29b-41d4-a716-446655440001")
    assert response.status_code == 409


def test_actualizacion_incrementa_version_y_exige_if_match(client):
    created = _create(client).json()["data"]
    payload = {**PAYLOAD, "valor_configuracion": "CENTRAL"}
    response = client.put(
        f"/api/v1/operativo/configuracion-local/{created['id_configuracion_local']}",
        headers={
            **HEADERS,
            "X-Op-Id": "750e8400-e29b-41d4-a716-446655440002",
            "If-Match-Version": "1",
        },
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["data"]["version_registro"] == 2
    assert (
        response.json()["data"]["op_id_ultima_modificacion"]
        == "750e8400-e29b-41d4-a716-446655440002"
    )


def test_actualizacion_if_match_incorrecto_devuelve_412(client):
    created = _create(client).json()["data"]
    response = client.put(
        f"/api/v1/operativo/configuracion-local/{created['id_configuracion_local']}",
        headers={
            **HEADERS,
            "X-Op-Id": "750e8400-e29b-41d4-a716-446655440003",
            "If-Match-Version": "99",
        },
        json=PAYLOAD,
    )
    assert response.status_code == 412
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_sucursal_inexistente_e_instalacion_inexistente_devuelven_404(client):
    assert (
        client.get(
            "/api/v1/operativo/configuracion-local",
            params={"id_sucursal": 999999, "id_instalacion": 1},
        ).status_code
        == 404
    )
    response = client.get(
        "/api/v1/operativo/configuracion-local",
        params={"id_sucursal": 1, "id_instalacion": 999999},
    )
    assert response.status_code == 404


def test_instalacion_de_otra_sucursal_devuelve_error_controlado(client, db_session):
    db_session.execute(
        text(
            "INSERT INTO sucursal (id_sucursal, codigo_sucursal, nombre_sucursal, estado_sucursal) VALUES (9901, 'S9901', 'Sucursal 9901', 'ACTIVA')"
        )
    )
    response = client.get(
        "/api/v1/operativo/configuracion-local",
        params={"id_sucursal": 9901, "id_instalacion": 1},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_payload_invalido_y_headers_faltantes(client):
    response = client.post(
        "/api/v1/operativo/configuracion-local",
        headers=HEADERS,
        json={**PAYLOAD, "clave_configuracion": ""},
    )
    assert response.status_code == 422
    response = client.post(
        "/api/v1/operativo/configuracion-local",
        headers=HEADERS,
        json={**PAYLOAD, "tipo_valor": "BINARIO"},
    )
    assert response.status_code == 422
    headers = {k: v for k, v in HEADERS.items() if k != "X-Op-Id"}
    response = client.post(
        "/api/v1/operativo/configuracion-local", headers=headers, json=PAYLOAD
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_get_filtra_por_contexto_e_indices_core_ef_existen(client, db_session):
    assert _create(client).status_code == 201
    response = client.get(
        "/api/v1/operativo/configuracion-local",
        params={"id_sucursal": 1, "id_instalacion": 1},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    indexes = {
        row[0]
        for row in db_session.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE tablename='configuracion_local'"
            )
        )
    }
    assert "ux_configuracion_local_op_id_alta" in indexes
    assert "ux_configuracion_local_uid_global" in indexes
    assert "ux_configuracion_local_clave_activa" in indexes
