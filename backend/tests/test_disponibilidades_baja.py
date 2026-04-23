from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS


def test_baja_disponibilidad_actualiza_deleted_at_en_postgresql(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-BAJA-001",
            "nombre_inmueble": "Inmueble Baja Disponibilidad",
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
            "observaciones": "baja logica",
        },
    )
    assert create_response.status_code == 201
    disponibilidad = create_response.json()["data"]

    response = client.patch(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}/baja",
        headers={**HEADERS, "If-Match-Version": str(disponibilidad["version_registro"])},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_disponibilidad": disponibilidad["id_disponibilidad"],
            "version_registro": 2,
            "deleted": True,
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_disponibilidad,
                version_registro,
                deleted_at,
                updated_at,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion
            FROM disponibilidad
            WHERE id_disponibilidad = :id_disponibilidad
            """
        ),
        {"id_disponibilidad": disponibilidad["id_disponibilidad"]},
    ).mappings().one()

    assert row["id_disponibilidad"] == disponibilidad["id_disponibilidad"]
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_baja_disponibilidad_devuelve_409_si_hay_error_de_concurrencia(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-BAJA-002",
            "nombre_inmueble": "Inmueble Concurrencia Baja",
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
            "motivo": None,
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
    disponibilidad = create_response.json()["data"]

    response = client.patch(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}/baja",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_disponibilidad_devuelve_404_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/disponibilidades/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_disponibilidad_devuelve_404_si_ya_tiene_deleted_at(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-BAJA-003",
            "nombre_inmueble": "Inmueble Ya Eliminado",
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
            "motivo": None,
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
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

    response = client.patch(
        f"/api/v1/disponibilidades/{disponibilidad['id_disponibilidad']}/baja",
        headers={**HEADERS, "If-Match-Version": str(disponibilidad["version_registro"])},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
