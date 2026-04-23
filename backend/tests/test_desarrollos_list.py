from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_desarrollos_devuelve_solo_no_borrados(client, db_session) -> None:
    response_1 = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-LIST-001",
            "nombre_desarrollo": "Desarrollo Uno",
            "descripcion": "primer desarrollo",
            "estado_desarrollo": "ACTIVO",
            "observaciones": "obs uno",
        },
    )
    assert response_1.status_code == 201
    id_desarrollo_1 = response_1.json()["data"]["id_desarrollo"]

    response_2 = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-LIST-002",
            "nombre_desarrollo": "Desarrollo Dos",
            "descripcion": "segundo desarrollo",
            "estado_desarrollo": "INACTIVO",
            "observaciones": "obs dos",
        },
    )
    assert response_2.status_code == 201
    id_desarrollo_2 = response_2.json()["data"]["id_desarrollo"]

    db_session.execute(
        text(
            """
            UPDATE desarrollo
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_desarrollo = :id_desarrollo
            """
        ),
        {"id_desarrollo": id_desarrollo_2},
    )

    response = client.get("/api/v1/desarrollos")

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    ids = [item["id_desarrollo"] for item in body["data"]]
    assert id_desarrollo_1 in ids
    assert id_desarrollo_2 not in ids

    item = next(
        item for item in body["data"] if item["id_desarrollo"] == id_desarrollo_1
    )
    assert item == {
        "id_desarrollo": id_desarrollo_1,
        "codigo_desarrollo": "DESA-LIST-001",
        "nombre_desarrollo": "Desarrollo Uno",
        "descripcion": "primer desarrollo",
        "estado_desarrollo": "ACTIVO",
        "observaciones": "obs uno",
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
                observaciones,
                deleted_at
            FROM desarrollo
            WHERE id_desarrollo = :id_desarrollo
            """
        ),
        {"id_desarrollo": id_desarrollo_1},
    ).mappings().one()

    assert row["id_desarrollo"] == id_desarrollo_1
    assert row["codigo_desarrollo"] == "DESA-LIST-001"
    assert row["nombre_desarrollo"] == "Desarrollo Uno"
    assert row["descripcion"] == "primer desarrollo"
    assert row["estado_desarrollo"] == "ACTIVO"
    assert row["observaciones"] == "obs uno"
    assert row["deleted_at"] is None


def test_get_desarrollos_devuelve_lista_vacia_si_no_hay_registros_activos(
    client, db_session
) -> None:
    db_session.execute(text("UPDATE desarrollo SET deleted_at = CURRENT_TIMESTAMP"))

    response = client.get("/api/v1/desarrollos")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": [],
    }
