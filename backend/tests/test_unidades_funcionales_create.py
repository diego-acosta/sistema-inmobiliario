from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_create_unidad_funcional_inserta_en_postgresql(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-001",
            "nombre_inmueble": "Inmueble Base",
            "superficie": "140.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "inmueble para unidad funcional",
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-001",
            "nombre_unidad": "Unidad A",
            "superficie": "72.35",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": "alta desde test automatizado",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_unidad_funcional"], int)
    assert body["data"]["id_inmueble"] == id_inmueble
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["codigo_unidad"] == "UF-001"
    assert body["data"]["estado_administrativo"] == "ACTIVA"
    assert body["data"]["estado_operativo"] == "DISPONIBLE"

    row = db_session.execute(
        text(
            """
            SELECT
                id_unidad_funcional,
                id_inmueble,
                uid_global,
                version_registro,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                observaciones
            FROM unidad_funcional
            WHERE id_unidad_funcional = :id_unidad_funcional
            """
        ),
        {"id_unidad_funcional": body["data"]["id_unidad_funcional"]},
    ).mappings().one()

    assert row["id_unidad_funcional"] == body["data"]["id_unidad_funcional"]
    assert row["id_inmueble"] == id_inmueble
    assert row["uid_global"] is not None
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["codigo_unidad"] == "UF-001"
    assert row["nombre_unidad"] == "Unidad A"
    assert str(row["superficie"]) == "72.35"
    assert row["estado_administrativo"] == "ACTIVA"
    assert row["estado_operativo"] == "DISPONIBLE"
    assert row["observaciones"] == "alta desde test automatizado"


def test_create_unidad_funcional_devuelve_404_si_inmueble_no_existe(client) -> None:
    response = client.post(
        "/api/v1/inmuebles/999999/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-404",
            "nombre_unidad": "Unidad Fantasma",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_create_unidad_funcional_devuelve_422_si_campos_obligatorios_son_null(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-422-001",
            "nombre_inmueble": "Inmueble Base",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": None,
            "nombre_unidad": "Unidad Invalida",
            "superficie": None,
            "estado_administrativo": None,
            "estado_operativo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 422
