from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_inmuebles_devuelve_solo_no_borrados(client, db_session) -> None:
    response_1 = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-LIST-001",
            "nombre_inmueble": "Unidad Uno",
            "superficie": "55.25",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "obs uno",
        },
    )
    assert response_1.status_code == 201
    id_inmueble_1 = response_1.json()["data"]["id_inmueble"]

    response_2 = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-LIST-002",
            "nombre_inmueble": "Unidad Dos",
            "superficie": "75.50",
            "estado_administrativo": "INACTIVO",
            "estado_juridico": "OBSERVADO",
            "observaciones": "obs dos",
        },
    )
    assert response_2.status_code == 201
    id_inmueble_2 = response_2.json()["data"]["id_inmueble"]

    db_session.execute(
        text(
            """
            UPDATE inmueble
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_inmueble = :id_inmueble
            """
        ),
        {"id_inmueble": id_inmueble_2},
    )

    response = client.get("/api/v1/inmuebles")

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    ids = [item["id_inmueble"] for item in body["data"]]
    assert id_inmueble_1 in ids
    assert id_inmueble_2 not in ids

    item = next(item for item in body["data"] if item["id_inmueble"] == id_inmueble_1)
    assert {
        key: item[key]
        for key in (
            "id_inmueble",
            "id_desarrollo",
            "codigo_inmueble",
            "nombre_inmueble",
            "superficie",
            "estado_administrativo",
            "estado_juridico",
            "observaciones",
        )
    } == {
        "id_inmueble": id_inmueble_1,
        "id_desarrollo": None,
        "codigo_inmueble": "INM-LIST-001",
        "nombre_inmueble": "Unidad Uno",
        "superficie": "55.25",
        "estado_administrativo": "ACTIVO",
        "estado_juridico": "REGULAR",
        "observaciones": "obs uno",
    }
    assert item["nombre"] == "Unidad Uno"
    assert item["descripcion"] == "obs uno"
    assert item["disponibilidad_actual"] is None
    assert item["disponibilidad_ambigua"] is False
    assert item["ocupacion_actual"] is None
    assert item["ocupacion_ambigua"] is False
    assert item["cantidad_unidades_funcionales"] == 0
    assert body["items"] == body["data"]
    assert body["total"] >= 1
    assert body["limit"] == 100
    assert body["offset"] == 0

    row = db_session.execute(
        text(
            """
            SELECT
                id_inmueble,
                codigo_inmueble,
                nombre_inmueble,
                superficie,
                estado_administrativo,
                estado_juridico,
                observaciones,
                deleted_at
            FROM inmueble
            WHERE id_inmueble = :id_inmueble
            """
        ),
        {"id_inmueble": id_inmueble_1},
    ).mappings().one()

    assert row["id_inmueble"] == id_inmueble_1
    assert row["codigo_inmueble"] == "INM-LIST-001"
    assert row["nombre_inmueble"] == "Unidad Uno"
    assert str(row["superficie"]) == "55.25"
    assert row["estado_administrativo"] == "ACTIVO"
    assert row["estado_juridico"] == "REGULAR"
    assert row["observaciones"] == "obs uno"
    assert row["deleted_at"] is None


def test_get_inmuebles_devuelve_lista_vacia_si_no_hay_registros_activos(
    client, db_session
) -> None:
    db_session.execute(text("UPDATE inmueble SET deleted_at = CURRENT_TIMESTAMP"))

    response = client.get("/api/v1/inmuebles")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": [],
        "items": [],
        "total": 0,
        "limit": 100,
        "offset": 0,
    }
