from sqlalchemy import text

from tests.test_unidad_funcional_servicios_create import HEADERS


def test_get_servicio_unidades_funcionales_devuelve_solo_no_borrados(
    client, db_session
) -> None:
    servicio_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-UF-LIST-001",
            "nombre_servicio": "Servicio con UF",
            "descripcion": "servicio para listar UF",
            "estado_servicio": "ACTIVO",
        },
    )
    assert servicio_response.status_code == 201
    id_servicio = servicio_response.json()["data"]["id_servicio"]

    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-SERV-UF-001",
            "nombre_inmueble": "Inmueble Servicio UF",
            "superficie": "84.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    unidad_1_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-SERV-BY-001",
            "nombre_unidad": "Unidad Uno",
            "superficie": "40.10",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert unidad_1_response.status_code == 201
    id_unidad_funcional_1 = unidad_1_response.json()["data"]["id_unidad_funcional"]

    unidad_2_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-SERV-BY-002",
            "nombre_unidad": "Unidad Dos",
            "superficie": "42.20",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert unidad_2_response.status_code == 201
    id_unidad_funcional_2 = unidad_2_response.json()["data"]["id_unidad_funcional"]

    asociacion_1_response = client.post(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional_1}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio, "estado": "ACTIVO"},
    )
    assert asociacion_1_response.status_code == 201
    id_unidad_funcional_servicio_1 = asociacion_1_response.json()["data"][
        "id_unidad_funcional_servicio"
    ]

    asociacion_2_response = client.post(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional_2}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio, "estado": "INACTIVO"},
    )
    assert asociacion_2_response.status_code == 201
    id_unidad_funcional_servicio_2 = asociacion_2_response.json()["data"][
        "id_unidad_funcional_servicio"
    ]

    db_session.execute(
        text(
            """
            UPDATE unidad_funcional_servicio
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_unidad_funcional_servicio = :id_unidad_funcional_servicio
            """
        ),
        {"id_unidad_funcional_servicio": id_unidad_funcional_servicio_2},
    )

    response = client.get(f"/api/v1/servicios/{id_servicio}/unidades-funcionales")

    assert response.status_code == 200
    body = response.json()

    assert body["ok"] is True
    ids = [item["id_unidad_funcional_servicio"] for item in body["data"]]
    assert id_unidad_funcional_servicio_1 in ids
    assert id_unidad_funcional_servicio_2 not in ids

    item = next(
        item
        for item in body["data"]
        if item["id_unidad_funcional_servicio"] == id_unidad_funcional_servicio_1
    )
    assert item["id_unidad_funcional_servicio"] == id_unidad_funcional_servicio_1
    assert item["id_unidad_funcional"] == id_unidad_funcional_1
    assert item["id_servicio"] == id_servicio
    assert item["estado"] == "ACTIVO"
    assert item["fecha_alta"] is not None

    row = db_session.execute(
        text(
            """
            SELECT
                id_unidad_funcional_servicio,
                id_unidad_funcional,
                id_servicio,
                estado,
                fecha_alta,
                deleted_at
            FROM unidad_funcional_servicio
            WHERE id_unidad_funcional_servicio = :id_unidad_funcional_servicio
            """
        ),
        {"id_unidad_funcional_servicio": id_unidad_funcional_servicio_1},
    ).mappings().one()

    assert row["id_unidad_funcional_servicio"] == id_unidad_funcional_servicio_1
    assert row["id_unidad_funcional"] == id_unidad_funcional_1
    assert row["id_servicio"] == id_servicio
    assert row["estado"] == "ACTIVO"
    assert row["fecha_alta"] is not None
    assert row["deleted_at"] is None


def test_get_servicio_unidades_funcionales_devuelve_lista_vacia_si_no_hay_registros_activos(
    client,
) -> None:
    servicio_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-UF-EMPTY-001",
            "nombre_servicio": "Servicio Vacio UF",
            "descripcion": None,
            "estado_servicio": "ACTIVO",
        },
    )
    assert servicio_response.status_code == 201
    id_servicio = servicio_response.json()["data"]["id_servicio"]

    response = client.get(f"/api/v1/servicios/{id_servicio}/unidades-funcionales")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}


def test_get_servicio_unidades_funcionales_devuelve_lista_vacia_si_servicio_no_existe(
    client,
) -> None:
    response = client.get("/api/v1/servicios/999999/unidades-funcionales")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}
