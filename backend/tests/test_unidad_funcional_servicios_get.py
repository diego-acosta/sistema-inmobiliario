from sqlalchemy import text

from tests.test_unidad_funcional_servicios_create import HEADERS


def test_get_unidad_funcional_servicios_devuelve_solo_no_borrados(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UFS-LIST-001",
            "nombre_inmueble": "Inmueble Lista UFS",
            "superficie": "101.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    unidad_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-LIST-SERV-001",
            "nombre_unidad": "Unidad Lista Servicios",
            "superficie": "48.50",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": "unidad para listar servicios",
        },
    )
    assert unidad_response.status_code == 201
    id_unidad_funcional = unidad_response.json()["data"]["id_unidad_funcional"]

    servicio_1_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-UFS-LIST-001",
            "nombre_servicio": "Agua UF",
            "descripcion": "servicio uno",
            "estado_servicio": "ACTIVO",
        },
    )
    assert servicio_1_response.status_code == 201
    id_servicio_1 = servicio_1_response.json()["data"]["id_servicio"]

    servicio_2_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-UFS-LIST-002",
            "nombre_servicio": "Luz UF",
            "descripcion": "servicio dos",
            "estado_servicio": "ACTIVO",
        },
    )
    assert servicio_2_response.status_code == 201
    id_servicio_2 = servicio_2_response.json()["data"]["id_servicio"]

    asociacion_1_response = client.post(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio_1, "estado": "ACTIVO"},
    )
    assert asociacion_1_response.status_code == 201
    id_unidad_funcional_servicio_1 = asociacion_1_response.json()["data"][
        "id_unidad_funcional_servicio"
    ]

    asociacion_2_response = client.post(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio_2, "estado": "INACTIVO"},
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

    response = client.get(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios"
    )

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
    assert item["id_unidad_funcional"] == id_unidad_funcional
    assert item["id_servicio"] == id_servicio_1
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
    assert row["id_unidad_funcional"] == id_unidad_funcional
    assert row["id_servicio"] == id_servicio_1
    assert row["estado"] == "ACTIVO"
    assert row["fecha_alta"] is not None
    assert row["deleted_at"] is None


def test_get_unidad_funcional_servicios_devuelve_lista_vacia_si_no_hay_registros_activos(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UFS-EMPTY-001",
            "nombre_inmueble": "Inmueble Vacio UFS",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    unidad_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-EMPTY-SERV-001",
            "nombre_unidad": "Unidad Vacia",
            "superficie": "30.00",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert unidad_response.status_code == 201
    id_unidad_funcional = unidad_response.json()["data"]["id_unidad_funcional"]

    response = client.get(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios"
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}


def test_get_unidad_funcional_servicios_devuelve_lista_vacia_si_unidad_no_existe(
    client,
) -> None:
    response = client.get("/api/v1/unidades-funcionales/999999/servicios")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}
