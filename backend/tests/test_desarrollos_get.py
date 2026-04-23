from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_desarrollo_devuelve_desarrollo_activo(client, db_session) -> None:
    create_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-GET-001",
            "nombre_desarrollo": "Desarrollo Centro",
            "descripcion": "desarrollo para consulta",
            "estado_desarrollo": "ACTIVO",
            "observaciones": "observacion get",
        },
    )

    assert create_response.status_code == 201
    id_desarrollo = create_response.json()["data"]["id_desarrollo"]

    response = client.get(f"/api/v1/desarrollos/{id_desarrollo}")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_desarrollo": id_desarrollo,
            "codigo_desarrollo": "DESA-GET-001",
            "nombre_desarrollo": "Desarrollo Centro",
            "descripcion": "desarrollo para consulta",
            "estado_desarrollo": "ACTIVO",
            "observaciones": "observacion get",
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_desarrollo,
                codigo_desarrollo,
                nombre_desarrollo,
                descripcion,
                estado_desarrollo,
                observaciones
            FROM desarrollo
            WHERE id_desarrollo = :id_desarrollo
            """
        ),
        {"id_desarrollo": id_desarrollo},
    ).mappings().one()

    assert row["id_desarrollo"] == id_desarrollo
    assert row["codigo_desarrollo"] == "DESA-GET-001"
    assert row["nombre_desarrollo"] == "Desarrollo Centro"
    assert row["descripcion"] == "desarrollo para consulta"
    assert row["estado_desarrollo"] == "ACTIVO"
    assert row["observaciones"] == "observacion get"


def test_get_desarrollo_inexistente_devuelve_404(client) -> None:
    response = client.get("/api/v1/desarrollos/999999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "El desarrollo indicado no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }


def test_get_desarrollo_filtra_soft_delete(client, db_session) -> None:
    create_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-DEL-001",
            "nombre_desarrollo": "Desarrollo Baja",
            "descripcion": "desarrollo soft deleted",
            "estado_desarrollo": "ACTIVO",
            "observaciones": "no debe leerse",
        },
    )

    assert create_response.status_code == 201
    id_desarrollo = create_response.json()["data"]["id_desarrollo"]

    db_session.execute(
        text(
            """
            UPDATE desarrollo
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_desarrollo = :id_desarrollo
            """
        ),
        {"id_desarrollo": id_desarrollo},
    )

    response = client.get(f"/api/v1/desarrollos/{id_desarrollo}")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "El desarrollo indicado no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }
