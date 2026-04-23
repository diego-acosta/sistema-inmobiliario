from sqlalchemy import text

from tests.test_ocupaciones_create import HEADERS


def test_baja_ocupacion_actualiza_deleted_at_en_postgresql(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-BAJA-001",
            "nombre_inmueble": "Inmueble Baja Ocupacion",
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
            "descripcion": "Alta inicial",
            "observaciones": "baja logica",
        },
    )
    assert create_response.status_code == 201
    ocupacion = create_response.json()["data"]

    response = client.patch(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}/baja",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_ocupacion": ocupacion["id_ocupacion"],
            "version_registro": 2,
            "deleted": True,
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_ocupacion,
                version_registro,
                deleted_at,
                updated_at,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion
            FROM ocupacion
            WHERE id_ocupacion = :id_ocupacion
            """
        ),
        {"id_ocupacion": ocupacion["id_ocupacion"]},
    ).mappings().one()

    assert row["id_ocupacion"] == ocupacion["id_ocupacion"]
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_baja_ocupacion_devuelve_409_si_hay_error_de_concurrencia(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-BAJA-002",
            "nombre_inmueble": "Inmueble Concurrencia Baja Ocupacion",
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
            "descripcion": None,
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
    ocupacion = create_response.json()["data"]

    response = client.patch(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}/baja",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_ocupacion_devuelve_404_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/ocupaciones/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_ocupacion_devuelve_404_si_ya_tiene_deleted_at(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-BAJA-003",
            "nombre_inmueble": "Inmueble Ocupacion Ya Eliminada",
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
            "descripcion": None,
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
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

    response = client.patch(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}/baja",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
