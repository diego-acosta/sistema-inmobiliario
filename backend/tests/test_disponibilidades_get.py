from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS


def test_get_inmueble_disponibilidades_devuelve_registros_por_inmueble(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-LIST-001",
            "nombre_inmueble": "Inmueble Lista Disponibilidad",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": "Alta",
            "observaciones": "lista inmueble",
        },
    )
    assert create_response.status_code == 201
    id_disponibilidad = create_response.json()["data"]["id_disponibilidad"]

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}/disponibilidades")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]) == 1
    item = body["data"][0]
    assert item["id_disponibilidad"] == id_disponibilidad
    assert item["id_inmueble"] == id_inmueble
    assert item["id_unidad_funcional"] is None
    assert item["estado_disponibilidad"] == "DISPONIBLE"
    assert item["motivo"] == "Alta"
    assert item["observaciones"] == "lista inmueble"


def test_get_unidad_funcional_disponibilidades_devuelve_registros_por_unidad(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-UF-LIST-001",
            "nombre_inmueble": "Inmueble Lista UF",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    uf_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-DISP-LIST-001",
            "nombre_unidad": "Unidad Lista Disponibilidad",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert uf_response.status_code == 201
    id_unidad_funcional = uf_response.json()["data"]["id_unidad_funcional"]

    create_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": None,
            "id_unidad_funcional": id_unidad_funcional,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-21T11:00:00",
            "fecha_hasta": None,
            "motivo": "Reserva",
            "observaciones": "lista unidad",
        },
    )
    assert create_response.status_code == 201
    id_disponibilidad = create_response.json()["data"]["id_disponibilidad"]

    response = client.get(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/disponibilidades"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]) == 1
    item = body["data"][0]
    assert item["id_disponibilidad"] == id_disponibilidad
    assert item["id_inmueble"] is None
    assert item["id_unidad_funcional"] == id_unidad_funcional
    assert item["estado_disponibilidad"] == "RESERVADA"


def test_get_disponibilidades_excluye_deleted_at_en_lecturas(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DISP-DEL-001",
            "nombre_inmueble": "Inmueble Deleted At",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    activa_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "motivo": "Activa",
            "observaciones": None,
        },
    )
    assert activa_response.status_code == 201
    id_activa = activa_response.json()["data"]["id_disponibilidad"]

    borrada_response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-21T11:00:00",
            "fecha_hasta": None,
            "motivo": "Borrada",
            "observaciones": None,
        },
    )
    assert borrada_response.status_code == 201
    id_borrada = borrada_response.json()["data"]["id_disponibilidad"]

    db_session.execute(
        text(
            """
            UPDATE disponibilidad
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_disponibilidad = :id_disponibilidad
            """
        ),
        {"id_disponibilidad": id_borrada},
    )

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}/disponibilidades")

    assert response.status_code == 200
    body = response.json()
    ids = [item["id_disponibilidad"] for item in body["data"]]
    assert id_activa in ids
    assert id_borrada not in ids
