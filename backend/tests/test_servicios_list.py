from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_servicios_devuelve_solo_no_borrados(client, db_session) -> None:
    response_1 = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-LIST-001",
            "nombre_servicio": "Agua",
            "descripcion": "obs uno",
            "estado_servicio": "ACTIVO",
        },
    )
    assert response_1.status_code == 201
    id_servicio_1 = response_1.json()["data"]["id_servicio"]

    response_2 = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-LIST-002",
            "nombre_servicio": "Gas",
            "descripcion": "obs dos",
            "estado_servicio": "INACTIVO",
        },
    )
    assert response_2.status_code == 201
    id_servicio_2 = response_2.json()["data"]["id_servicio"]

    db_session.execute(
        text(
            """
            UPDATE servicio
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_servicio = :id_servicio
            """
        ),
        {"id_servicio": id_servicio_2},
    )

    response = client.get("/api/v1/servicios")

    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    ids = [item["id_servicio"] for item in body["data"]]
    assert id_servicio_1 in ids
    assert id_servicio_2 not in ids

    item = next(item for item in body["data"] if item["id_servicio"] == id_servicio_1)
    assert item == {
        "id_servicio": id_servicio_1,
        "codigo_servicio": "SERV-LIST-001",
        "nombre_servicio": "Agua",
        "descripcion": "obs uno",
        "estado_servicio": "ACTIVO",
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_servicio,
                codigo_servicio,
                nombre_servicio,
                descripcion,
                estado_servicio,
                deleted_at
            FROM servicio
            WHERE id_servicio = :id_servicio
            """
        ),
        {"id_servicio": id_servicio_1},
    ).mappings().one()

    assert row["id_servicio"] == id_servicio_1
    assert row["codigo_servicio"] == "SERV-LIST-001"
    assert row["nombre_servicio"] == "Agua"
    assert row["descripcion"] == "obs uno"
    assert row["estado_servicio"] == "ACTIVO"
    assert row["deleted_at"] is None


def test_get_servicios_devuelve_lista_vacia_si_no_hay_registros_activos(
    client,
) -> None:
    response = client.get("/api/v1/servicios")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": [],
    }
