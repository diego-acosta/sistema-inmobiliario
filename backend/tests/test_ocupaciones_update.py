from sqlalchemy import text

from tests.test_ocupaciones_create import HEADERS


def test_update_ocupacion_actualiza_registro_abierto_en_postgresql(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-UPD-001",
            "nombre_inmueble": "Inmueble Update Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": "antes del update",
            "observaciones": "observacion inicial",
        },
    )
    assert create_response.status_code == 201
    ocupacion = create_response.json()["data"]

    response = client.put(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "TERCEROS",
            "fecha_desde": "2026-04-22T10:00:00",
            "fecha_hasta": None,
            "descripcion": "despues del update",
            "observaciones": "observacion final",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_ocupacion"] == ocupacion["id_ocupacion"]
    assert body["data"]["version_registro"] == 2
    assert body["data"]["id_inmueble"] == id_inmueble
    assert body["data"]["id_unidad_funcional"] is None
    assert body["data"]["tipo_ocupacion"] == "TERCEROS"
    assert body["data"]["fecha_desde"] == "2026-04-22T10:00:00"
    assert body["data"]["fecha_hasta"] is None
    assert body["data"]["descripcion"] == "despues del update"
    assert body["data"]["observaciones"] == "observacion final"

    row = db_session.execute(
        text(
            """
            SELECT
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
                observaciones,
                deleted_at
            FROM ocupacion
            WHERE id_ocupacion = :id_ocupacion
            """
        ),
        {"id_ocupacion": ocupacion["id_ocupacion"]},
    ).mappings().one()

    assert row["version_registro"] == 2
    assert row["id_inmueble"] == id_inmueble
    assert row["id_unidad_funcional"] is None
    assert row["tipo_ocupacion"] == "TERCEROS"
    assert row["fecha_desde"].isoformat() == "2026-04-22T10:00:00"
    assert row["fecha_hasta"] is None
    assert row["descripcion"] == "despues del update"
    assert row["observaciones"] == "observacion final"
    assert row["deleted_at"] is None


def test_update_ocupacion_devuelve_error_si_vienen_ambos_parents(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-UPD-002",
            "nombre_inmueble": "Inmueble Ambos Parents Ocupacion",
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
            "codigo_unidad": "UF-OC-UPD-002",
            "nombre_unidad": "Unidad Ambos Parents Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert uf_response.status_code == 201
    id_unidad_funcional = uf_response.json()["data"]["id_unidad_funcional"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    ocupacion = create_response.json()["data"]

    response = client.put(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"


def test_update_ocupacion_devuelve_error_si_no_viene_ningun_parent(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-UPD-003",
            "nombre_inmueble": "Inmueble Sin Parent Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    ocupacion = create_response.json()["data"]

    response = client.put(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={
            "id_inmueble": None,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"


def test_update_ocupacion_devuelve_error_si_fecha_hasta_es_menor(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-UPD-004",
            "nombre_inmueble": "Inmueble Fecha Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    ocupacion = create_response.json()["data"]

    response = client.put(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-20T10:00:00",
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"
    assert response.json()["error_message"] == "fecha_hasta no puede ser menor que fecha_desde."


def test_update_ocupacion_devuelve_error_de_concurrencia(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-UPD-005",
            "nombre_inmueble": "Inmueble Concurrencia Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    ocupacion = create_response.json()["data"]

    response = client.put(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}",
        headers={**HEADERS, "If-Match-Version": "999"},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_ocupacion_devuelve_error_si_no_existe(client) -> None:
    response = client.put(
        "/api/v1/ocupaciones/999999",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_inmueble": 1,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_ocupacion_devuelve_error_si_tiene_deleted_at(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-UPD-006",
            "nombre_inmueble": "Inmueble Eliminado Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    ocupacion = create_response.json()["data"]

    db_session.execute(
        text(
            """
            UPDATE ocupacion
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_ocupacion = :id_ocupacion
            """
        ),
        {"id_ocupacion": ocupacion["id_ocupacion"]},
    )

    response = client.put(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_ocupacion_devuelve_error_si_el_registro_ya_esta_cerrado(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-UPD-007",
            "nombre_inmueble": "Inmueble Cerrado Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-22T10:00:00",
            "descripcion": None,
            "observaciones": None,
        },
    )
    ocupacion = create_response.json()["data"]

    response = client.put(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "TERCEROS",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-22T10:00:00",
            "descripcion": "no debe editar",
            "observaciones": "cerrada",
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"
    assert (
        response.json()["error_message"]
        == "La ocupacion ya se encuentra cerrada y no puede editarse."
    )


def test_update_ocupacion_devuelve_error_si_intenta_cerrar_via_put(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-UPD-008",
            "nombre_inmueble": "Inmueble Cierre Encubierto Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    ocupacion = create_response.json()["data"]

    response = client.put(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-22T10:00:00",
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"
    assert (
        response.json()["error_message"]
        == "Para cerrar una ocupacion vigente debe usarse PATCH /api/v1/ocupaciones/{id_ocupacion}/cerrar."
    )
