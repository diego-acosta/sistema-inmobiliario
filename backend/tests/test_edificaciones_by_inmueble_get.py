from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_edificaciones_by_inmueble_devuelve_solo_no_borradas(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-LIST-001",
            "nombre_inmueble": "Inmueble Lista Edif",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response_1 = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Edificacion Uno",
            "tipo_edificacion": "CASA",
            "superficie": "120.10",
            "observaciones": "obs uno",
        },
    )
    assert response_1.status_code == 201
    id_edificacion_1 = response_1.json()["data"]["id_edificacion"]

    response_2 = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Edificacion Dos",
            "tipo_edificacion": "LOCAL",
            "superficie": "95.00",
            "observaciones": "obs dos",
        },
    )
    assert response_2.status_code == 201
    id_edificacion_2 = response_2.json()["data"]["id_edificacion"]

    db_session.execute(
        text(
            """
            UPDATE edificacion
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_edificacion = :id_edificacion
            """
        ),
        {"id_edificacion": id_edificacion_2},
    )

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}/edificaciones")

    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    ids = [item["id_edificacion"] for item in body["data"]]
    assert id_edificacion_1 in ids
    assert id_edificacion_2 not in ids

    item = next(item for item in body["data"] if item["id_edificacion"] == id_edificacion_1)
    assert item == {
        "id_edificacion": id_edificacion_1,
        "id_inmueble": id_inmueble,
        "id_unidad_funcional": None,
        "descripcion": "Edificacion Uno",
        "tipo_edificacion": "CASA",
        "superficie": "120.10",
        "observaciones": "obs uno",
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
                observaciones,
                deleted_at
            FROM edificacion
            WHERE id_edificacion = :id_edificacion
            """
        ),
        {"id_edificacion": id_edificacion_1},
    ).mappings().one()

    assert row["id_edificacion"] == id_edificacion_1
    assert row["id_inmueble"] == id_inmueble
    assert row["id_unidad_funcional"] is None
    assert row["descripcion"] == "Edificacion Uno"
    assert row["tipo_edificacion"] == "CASA"
    assert str(row["superficie"]) == "120.10"
    assert row["observaciones"] == "obs uno"
    assert row["deleted_at"] is None


def test_get_edificaciones_by_inmueble_devuelve_lista_vacia_si_no_hay_registros_activos(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-EMPTY-001",
            "nombre_inmueble": "Inmueble Vacio Edif",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}/edificaciones")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": [],
    }


def test_get_edificaciones_by_inmueble_devuelve_lista_vacia_si_inmueble_no_existe(
    client,
) -> None:
    response = client.get("/api/v1/inmuebles/999999/edificaciones")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": [],
    }
