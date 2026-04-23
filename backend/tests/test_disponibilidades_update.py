from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS


def test_update_disponibilidad_actualiza_registro_abierto_en_postgresql(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UPD-001",
            "nombre_inmueble": "Inmueble Update Disponibilidad",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": "Alta inicial",
            "observaciones": "antes del update",
        },
    )
    assert create_response.status_code == 201
    disponibilidad = create_response.json()["data"]

    response = client.put(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}",
        headers={**HEADERS, "If-Match-Version": str(disponibilidad["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-22T10:00:00",
            "fecha_hasta": None,
            "motivo": "Actualizacion operativa",
            "observaciones": "despues del update",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_disponibilidad"] == disponibilidad["id_disponibilidad"]
    assert body["data"]["version_registro"] == 2
    assert body["data"]["id_inmueble"] == id_inmueble
    assert body["data"]["id_unidad_funcional"] is None
    assert body["data"]["estado_disponibilidad"] == "RESERVADA"
    assert body["data"]["fecha_desde"] == "2026-04-22T10:00:00"
    assert body["data"]["fecha_hasta"] is None
    assert body["data"]["motivo"] == "Actualizacion operativa"
    assert body["data"]["observaciones"] == "despues del update"

    row = db_session.execute(
        text(
            """
            SELECT
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones,
                deleted_at
            FROM disponibilidad
            WHERE id_disponibilidad = :id_disponibilidad
            """
        ),
        {"id_disponibilidad": disponibilidad["id_disponibilidad"]},
    ).mappings().one()

    assert row["version_registro"] == 2
    assert row["id_inmueble"] == id_inmueble
    assert row["id_unidad_funcional"] is None
    assert row["estado_disponibilidad"] == "RESERVADA"
    assert row["fecha_desde"].isoformat() == "2026-04-22T10:00:00"
    assert row["fecha_hasta"] is None
    assert row["motivo"] == "Actualizacion operativa"
    assert row["observaciones"] == "despues del update"
    assert row["deleted_at"] is None


def test_update_disponibilidad_devuelve_error_si_vienen_ambos_parents(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UPD-008",
            "nombre_inmueble": "Inmueble Ambos Parents",
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
            "codigo_unidad": "UF-DISP-UPD-008",
            "nombre_unidad": "Unidad Ambos Parents",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert uf_response.status_code == 201
    id_unidad_funcional = uf_response.json()["data"]["id_unidad_funcional"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )
    disponibilidad = create_response.json()["data"]

    response = client.put(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}",
        headers={**HEADERS, "If-Match-Version": str(disponibilidad["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"


def test_update_disponibilidad_devuelve_error_si_no_viene_ningun_parent(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UPD-002",
            "nombre_inmueble": "Inmueble Parent",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )
    disponibilidad = create_response.json()["data"]

    response = client.put(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}",
        headers={**HEADERS, "If-Match-Version": str(disponibilidad["version_registro"])},
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
    assert response.json()["error_code"] == "APPLICATION_ERROR"


def test_update_disponibilidad_devuelve_error_si_fecha_hasta_es_menor(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UPD-003",
            "nombre_inmueble": "Inmueble Fecha",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )
    disponibilidad = create_response.json()["data"]

    response = client.put(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}",
        headers={**HEADERS, "If-Match-Version": str(disponibilidad["version_registro"])},
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
    assert response.json()["error_code"] == "APPLICATION_ERROR"
    assert response.json()["error_message"] == "fecha_hasta no puede ser menor que fecha_desde."


def test_update_disponibilidad_devuelve_error_de_concurrencia(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UPD-004",
            "nombre_inmueble": "Inmueble Concurrencia",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )
    disponibilidad = create_response.json()["data"]

    response = client.put(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}",
        headers={**HEADERS, "If-Match-Version": "999"},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_disponibilidad_devuelve_error_si_no_existe(client) -> None:
    response = client.put(
        "/api/v1/disponibilidades/999999",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_inmueble": 1,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_disponibilidad_devuelve_error_si_tiene_deleted_at(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UPD-005",
            "nombre_inmueble": "Inmueble Eliminado",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )
    disponibilidad = create_response.json()["data"]

    db_session.execute(
        text(
            """
            UPDATE disponibilidad
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_disponibilidad = :id_disponibilidad
            """
        ),
        {"id_disponibilidad": disponibilidad["id_disponibilidad"]},
    )

    response = client.put(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}",
        headers={**HEADERS, "If-Match-Version": str(disponibilidad["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_disponibilidad_devuelve_error_si_el_registro_ya_esta_cerrado(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UPD-006",
            "nombre_inmueble": "Inmueble Cerrado",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-22T10:00:00",
            "motivo": None,
            "observaciones": None,
        },
    )
    disponibilidad = create_response.json()["data"]

    response = client.put(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}",
        headers={**HEADERS, "If-Match-Version": str(disponibilidad["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-22T10:00:00",
            "motivo": "no debe editar",
            "observaciones": "cerrada",
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"
    assert (
        response.json()["error_message"]
        == "La disponibilidad ya se encuentra cerrada y no puede editarse."
    )


def test_update_disponibilidad_devuelve_error_si_intenta_cerrar_via_put(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UPD-007",
            "nombre_inmueble": "Inmueble Cierre Encubierto",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": None,
            "observaciones": None,
        },
    )
    disponibilidad = create_response.json()["data"]

    response = client.put(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}",
        headers={**HEADERS, "If-Match-Version": str(disponibilidad["version_registro"])},
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-22T10:00:00",
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"
    assert (
        response.json()["error_message"]
        == "Para cerrar una disponibilidad vigente debe usarse PATCH /api/v1/disponibilidades/{id_disponibilidad}/cerrar."
    )
