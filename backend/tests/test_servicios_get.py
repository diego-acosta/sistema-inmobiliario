from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_servicio_devuelve_servicio_activo(client, db_session) -> None:
    create_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-GET-001",
            "nombre_servicio": "Electricidad",
            "descripcion": "servicio para consulta",
            "estado_servicio": "ACTIVO",
        },
    )

    assert create_response.status_code == 201
    id_servicio = create_response.json()["data"]["id_servicio"]

    response = client.get(f"/api/v1/servicios/{id_servicio}")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_servicio": id_servicio,
            "codigo_servicio": "SERV-GET-001",
            "nombre_servicio": "Electricidad",
            "descripcion": "servicio para consulta",
            "estado_servicio": "ACTIVO",
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_servicio,
                codigo_servicio,
                nombre_servicio,
                descripcion,
                estado_servicio
            FROM servicio
            WHERE id_servicio = :id_servicio
            """
        ),
        {"id_servicio": id_servicio},
    ).mappings().one()

    assert row["id_servicio"] == id_servicio
    assert row["codigo_servicio"] == "SERV-GET-001"
    assert row["nombre_servicio"] == "Electricidad"
    assert row["descripcion"] == "servicio para consulta"
    assert row["estado_servicio"] == "ACTIVO"


def test_get_servicio_inexistente_devuelve_404(client) -> None:
    response = client.get("/api/v1/servicios/999999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "El servicio indicado no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }


def test_get_servicio_filtra_soft_delete(client, db_session) -> None:
    create_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-DEL-001",
            "nombre_servicio": "Gas",
            "descripcion": "no debe leerse",
            "estado_servicio": "ACTIVO",
        },
    )

    assert create_response.status_code == 201
    id_servicio = create_response.json()["data"]["id_servicio"]

    db_session.execute(
        text(
            """
            UPDATE servicio
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_servicio = :id_servicio
            """
        ),
        {"id_servicio": id_servicio},
    )

    response = client.get(f"/api/v1/servicios/{id_servicio}")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "El servicio indicado no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }
