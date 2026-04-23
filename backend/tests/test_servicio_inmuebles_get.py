from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_servicio_inmuebles_devuelve_solo_no_borrados(client, db_session) -> None:
    servicio_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-INM-LIST-001",
            "nombre_servicio": "Servicio con Inmuebles",
            "descripcion": "servicio para listar inmuebles",
            "estado_servicio": "ACTIVO",
        },
    )
    assert servicio_response.status_code == 201
    id_servicio = servicio_response.json()["data"]["id_servicio"]

    inmueble_1_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-SERV-BY-001",
            "nombre_inmueble": "Inmueble Uno",
            "superficie": "88.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_1_response.status_code == 201
    id_inmueble_1 = inmueble_1_response.json()["data"]["id_inmueble"]

    inmueble_2_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-SERV-BY-002",
            "nombre_inmueble": "Inmueble Dos",
            "superficie": "92.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_2_response.status_code == 201
    id_inmueble_2 = inmueble_2_response.json()["data"]["id_inmueble"]

    asociacion_1_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble_1}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio, "estado": "ACTIVO"},
    )
    assert asociacion_1_response.status_code == 201
    id_inmueble_servicio_1 = asociacion_1_response.json()["data"]["id_inmueble_servicio"]

    asociacion_2_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble_2}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio, "estado": "INACTIVO"},
    )
    assert asociacion_2_response.status_code == 201
    id_inmueble_servicio_2 = asociacion_2_response.json()["data"]["id_inmueble_servicio"]

    db_session.execute(
        text(
            """
            UPDATE inmueble_servicio
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_inmueble_servicio = :id_inmueble_servicio
            """
        ),
        {"id_inmueble_servicio": id_inmueble_servicio_2},
    )

    response = client.get(f"/api/v1/servicios/{id_servicio}/inmuebles")

    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    ids = [item["id_inmueble_servicio"] for item in body["data"]]
    assert id_inmueble_servicio_1 in ids
    assert id_inmueble_servicio_2 not in ids

    item = next(
        item
        for item in body["data"]
        if item["id_inmueble_servicio"] == id_inmueble_servicio_1
    )
    assert item["id_inmueble_servicio"] == id_inmueble_servicio_1
    assert item["id_inmueble"] == id_inmueble_1
    assert item["id_servicio"] == id_servicio
    assert item["estado"] == "ACTIVO"
    assert item["fecha_alta"] is not None

    row = db_session.execute(
        text(
            """
            SELECT
                id_inmueble_servicio,
                id_inmueble,
                id_servicio,
                estado,
                fecha_alta,
                deleted_at
            FROM inmueble_servicio
            WHERE id_inmueble_servicio = :id_inmueble_servicio
            """
        ),
        {"id_inmueble_servicio": id_inmueble_servicio_1},
    ).mappings().one()

    assert row["id_inmueble_servicio"] == id_inmueble_servicio_1
    assert row["id_inmueble"] == id_inmueble_1
    assert row["id_servicio"] == id_servicio
    assert row["estado"] == "ACTIVO"
    assert row["fecha_alta"] is not None
    assert row["deleted_at"] is None


def test_get_servicio_inmuebles_devuelve_lista_vacia_si_no_hay_registros_activos(
    client,
) -> None:
    servicio_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-INM-EMPTY-001",
            "nombre_servicio": "Servicio Vacio",
            "descripcion": None,
            "estado_servicio": "ACTIVO",
        },
    )
    assert servicio_response.status_code == 201
    id_servicio = servicio_response.json()["data"]["id_servicio"]

    response = client.get(f"/api/v1/servicios/{id_servicio}/inmuebles")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}


def test_get_servicio_inmuebles_devuelve_lista_vacia_si_servicio_no_existe(
    client,
) -> None:
    response = client.get("/api/v1/servicios/999999/inmuebles")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}
