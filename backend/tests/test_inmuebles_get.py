from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_inmueble_devuelve_inmueble_activo(client, db_session) -> None:
    desarrollo_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-GET-INM-001",
            "nombre_desarrollo": "Desarrollo GET Inmueble",
            "descripcion": "desarrollo para consulta inmueble",
            "estado_desarrollo": "ACTIVO",
            "observaciones": "obs desarrollo",
        },
    )
    assert desarrollo_response.status_code == 201
    id_desarrollo = desarrollo_response.json()["data"]["id_desarrollo"]

    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": id_desarrollo,
            "codigo_inmueble": "INM-GET-001",
            "nombre_inmueble": "Unidad 1",
            "superficie": "98.75",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "inmueble para consulta",
        },
    )
    assert create_response.status_code == 201
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_inmueble": id_inmueble,
            "id_desarrollo": id_desarrollo,
            "codigo_inmueble": "INM-GET-001",
            "nombre_inmueble": "Unidad 1",
            "superficie": "98.75",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "inmueble para consulta",
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_inmueble,
                id_desarrollo,
                codigo_inmueble,
                nombre_inmueble,
                superficie,
                estado_administrativo,
                estado_juridico,
                observaciones
            FROM inmueble
            WHERE id_inmueble = :id_inmueble
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().one()

    assert row["id_inmueble"] == id_inmueble
    assert row["id_desarrollo"] == id_desarrollo
    assert row["codigo_inmueble"] == "INM-GET-001"
    assert row["nombre_inmueble"] == "Unidad 1"
    assert str(row["superficie"]) == "98.75"
    assert row["estado_administrativo"] == "ACTIVO"
    assert row["estado_juridico"] == "REGULAR"
    assert row["observaciones"] == "inmueble para consulta"


def test_get_inmueble_inexistente_devuelve_404(client) -> None:
    response = client.get("/api/v1/inmuebles/999999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "El inmueble indicado no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }


def test_get_inmueble_filtra_soft_delete(client, db_session) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DEL-001",
            "nombre_inmueble": "Unidad Eliminada",
            "superficie": "80.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "no debe leerse",
        },
    )
    assert create_response.status_code == 201
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    db_session.execute(
        text(
            """
            UPDATE inmueble
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_inmueble = :id_inmueble
            """
        ),
        {"id_inmueble": id_inmueble},
    )

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "El inmueble indicado no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }
