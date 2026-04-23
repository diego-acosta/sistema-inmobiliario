from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_edificacion_devuelve_edificacion_activa(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-GET-001",
            "nombre_inmueble": "Inmueble Edificacion Get",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Edificacion para consulta",
            "tipo_edificacion": "CASA",
            "superficie": "210.75",
            "observaciones": "detalle edificacion",
        },
    )
    assert create_response.status_code == 201
    id_edificacion = create_response.json()["data"]["id_edificacion"]

    response = client.get(f"/api/v1/edificaciones/{id_edificacion}")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_edificacion": id_edificacion,
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Edificacion para consulta",
            "tipo_edificacion": "CASA",
            "superficie": "210.75",
            "observaciones": "detalle edificacion",
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_edificacion,
                id_inmueble,
                id_unidad_funcional,
                descripcion,
                tipo_edificacion,
                superficie,
                observaciones
            FROM edificacion
            WHERE id_edificacion = :id_edificacion
            """
        ),
        {"id_edificacion": id_edificacion},
    ).mappings().one()

    assert row["id_edificacion"] == id_edificacion
    assert row["id_inmueble"] == id_inmueble
    assert row["id_unidad_funcional"] is None
    assert row["descripcion"] == "Edificacion para consulta"
    assert row["tipo_edificacion"] == "CASA"
    assert str(row["superficie"]) == "210.75"
    assert row["observaciones"] == "detalle edificacion"


def test_get_edificacion_inexistente_devuelve_404(client) -> None:
    response = client.get("/api/v1/edificaciones/999999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "La edificacion indicada no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }


def test_get_edificacion_filtra_soft_delete(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-DEL-001",
            "nombre_inmueble": "Inmueble Edificacion Delete",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "No debe leerse",
            "tipo_edificacion": "GALPON",
            "superficie": None,
            "observaciones": "soft deleted",
        },
    )
    assert create_response.status_code == 201
    id_edificacion = create_response.json()["data"]["id_edificacion"]

    db_session.execute(
        text(
            """
            UPDATE edificacion
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_edificacion = :id_edificacion
            """
        ),
        {"id_edificacion": id_edificacion},
    )

    response = client.get(f"/api/v1/edificaciones/{id_edificacion}")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "La edificacion indicada no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }
