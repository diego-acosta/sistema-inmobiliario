from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_create_disponibilidad_inserta_en_postgresql_para_inmueble(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-001",
            "nombre_inmueble": "Inmueble Disponibilidad",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-30T10:00:00",
            "motivo": "Alta inicial",
            "observaciones": "disponibilidad por inmueble",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_disponibilidad"], int)
    assert body["data"]["id_inmueble"] == id_inmueble
    assert body["data"]["id_unidad_funcional"] is None
    assert body["data"]["estado_disponibilidad"] == "DISPONIBLE"
    assert body["data"]["fecha_desde"] == "2026-04-21T10:00:00"
    assert body["data"]["fecha_hasta"] == "2026-04-30T10:00:00"
    assert body["data"]["motivo"] == "Alta inicial"
    assert body["data"]["observaciones"] == "disponibilidad por inmueble"
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1

    row = db_session.execute(
        text(
            """
            SELECT
                id_disponibilidad,
                uid_global,
                version_registro,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones
            FROM disponibilidad
            WHERE id_disponibilidad = :id_disponibilidad
            """
        ),
        {"id_disponibilidad": body["data"]["id_disponibilidad"]},
    ).mappings().one()

    assert row["id_disponibilidad"] == body["data"]["id_disponibilidad"]
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_alta"]) == HEADERS["X-Op-Id"]
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]
    assert row["id_inmueble"] == id_inmueble
    assert row["id_unidad_funcional"] is None
    assert row["estado_disponibilidad"] == "DISPONIBLE"
    assert row["motivo"] == "Alta inicial"
    assert row["observaciones"] == "disponibilidad por inmueble"


def test_create_disponibilidad_inserta_en_postgresql_para_unidad_funcional(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UF-001",
            "nombre_inmueble": "Inmueble Base UF",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    uf_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-DISP-001",
            "nombre_unidad": "Unidad con Disponibilidad",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert uf_response.status_code == 201
    id_unidad_funcional = uf_response.json()["data"]["id_unidad_funcional"]

    response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": None,
            "id_unidad_funcional": id_unidad_funcional,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-22T09:30:00",
            "fecha_hasta": None,
            "motivo": "Reserva comercial",
            "observaciones": "disponibilidad por unidad",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["id_inmueble"] is None
    assert body["data"]["id_unidad_funcional"] == id_unidad_funcional
    assert body["data"]["estado_disponibilidad"] == "RESERVADA"
    assert body["data"]["fecha_desde"] == "2026-04-22T09:30:00"
    assert body["data"]["fecha_hasta"] is None


def test_create_disponibilidad_devuelve_error_si_vienen_ambos_padres(client) -> None:
    response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": 1,
            "id_unidad_funcional": 1,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional."
    )


def test_create_disponibilidad_devuelve_error_si_no_viene_ningun_padre(
    client,
) -> None:
    response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": None,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional."
    )


def test_create_disponibilidad_devuelve_error_si_fecha_hasta_es_menor(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-FECHA-001",
            "nombre_inmueble": "Inmueble Fecha",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-20T10:00:00",
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["error_message"] == "fecha_hasta no puede ser menor que fecha_desde."
