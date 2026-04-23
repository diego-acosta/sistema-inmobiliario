from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_unidades_funcionales_devuelve_solo_no_borradas(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-LIST-001",
            "nombre_inmueble": "Inmueble Lista UF",
            "superficie": "150.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "inmueble para listar UF",
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response_1 = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-LIST-001",
            "nombre_unidad": "Unidad Uno",
            "superficie": "70.10",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": "obs uno",
        },
    )
    assert response_1.status_code == 201
    id_unidad_1 = response_1.json()["data"]["id_unidad_funcional"]

    response_2 = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-LIST-002",
            "nombre_unidad": "Unidad Dos",
            "superficie": "85.20",
            "estado_administrativo": "INACTIVA",
            "estado_operativo": "RESERVADA",
            "observaciones": "obs dos",
        },
    )
    assert response_2.status_code == 201
    id_unidad_2 = response_2.json()["data"]["id_unidad_funcional"]

    db_session.execute(
        text(
            """
            UPDATE unidad_funcional
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_unidad_funcional = :id_unidad_funcional
            """
        ),
        {"id_unidad_funcional": id_unidad_2},
    )

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales")

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    ids = [item["id_unidad_funcional"] for item in body["data"]]
    assert id_unidad_1 in ids
    assert id_unidad_2 not in ids

    item = next(
        item for item in body["data"] if item["id_unidad_funcional"] == id_unidad_1
    )
    assert item == {
        "id_unidad_funcional": id_unidad_1,
        "id_inmueble": id_inmueble,
        "codigo_unidad": "UF-LIST-001",
        "nombre_unidad": "Unidad Uno",
        "superficie": "70.10",
        "estado_administrativo": "ACTIVA",
        "estado_operativo": "DISPONIBLE",
        "observaciones": "obs uno",
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_unidad_funcional,
                id_inmueble,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                observaciones,
                deleted_at
            FROM unidad_funcional
            WHERE id_unidad_funcional = :id_unidad_funcional
            """
        ),
        {"id_unidad_funcional": id_unidad_1},
    ).mappings().one()

    assert row["id_unidad_funcional"] == id_unidad_1
    assert row["id_inmueble"] == id_inmueble
    assert row["codigo_unidad"] == "UF-LIST-001"
    assert row["nombre_unidad"] == "Unidad Uno"
    assert str(row["superficie"]) == "70.10"
    assert row["estado_administrativo"] == "ACTIVA"
    assert row["estado_operativo"] == "DISPONIBLE"
    assert row["observaciones"] == "obs uno"
    assert row["deleted_at"] is None


def test_get_unidades_funcionales_devuelve_lista_vacia_si_no_hay_registros_activos(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-EMPTY-001",
            "nombre_inmueble": "Inmueble Vacio",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": [],
    }


def test_get_unidades_funcionales_devuelve_lista_vacia_si_inmueble_no_existe(
    client,
) -> None:
    response = client.get("/api/v1/inmuebles/999999/unidades-funcionales")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": [],
    }
