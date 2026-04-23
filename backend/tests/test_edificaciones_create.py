from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_create_edificacion_inserta_en_postgresql_para_inmueble(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-001",
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
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Edificacion sobre inmueble",
            "tipo_edificacion": "CASA",
            "superficie": "110.25",
            "observaciones": "alta desde test automatizado",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_edificacion"], int)
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["id_inmueble"] == id_inmueble
    assert body["data"]["id_unidad_funcional"] is None
    assert body["data"]["tipo_edificacion"] == "CASA"

    row = db_session.execute(
        text(
            """
            SELECT
                id_edificacion,
                id_inmueble,
                id_unidad_funcional,
                uid_global,
                version_registro,
                descripcion,
                tipo_edificacion,
                superficie,
                observaciones
            FROM edificacion
            WHERE id_edificacion = :id_edificacion
            """
        ),
        {"id_edificacion": body["data"]["id_edificacion"]},
    ).mappings().one()

    assert row["id_edificacion"] == body["data"]["id_edificacion"]
    assert row["id_inmueble"] == id_inmueble
    assert row["id_unidad_funcional"] is None
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["descripcion"] == "Edificacion sobre inmueble"
    assert row["tipo_edificacion"] == "CASA"
    assert str(row["superficie"]) == "110.25"
    assert row["observaciones"] == "alta desde test automatizado"


def test_create_edificacion_inserta_en_postgresql_para_unidad_funcional(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-UF-001",
            "nombre_inmueble": "Inmueble Base UF",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    uf_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-EDIF-001",
            "nombre_unidad": "Unidad Base",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert uf_response.status_code == 201
    id_unidad_funcional = uf_response.json()["data"]["id_unidad_funcional"]

    response = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": None,
            "id_unidad_funcional": id_unidad_funcional,
            "descripcion": "Edificacion sobre UF",
            "tipo_edificacion": "DEPTO",
            "superficie": "55.50",
            "observaciones": "alta uf",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["data"]["id_inmueble"] is None
    assert body["data"]["id_unidad_funcional"] == id_unidad_funcional
    assert body["data"]["tipo_edificacion"] == "DEPTO"


def test_create_edificacion_devuelve_400_si_no_hay_padre_o_hay_dos(client) -> None:
    response_sin_padre = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": None,
            "id_unidad_funcional": None,
            "descripcion": None,
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )
    assert response_sin_padre.status_code == 400
    assert response_sin_padre.json()["error_code"] == "APPLICATION_ERROR"

    response_con_dos = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": 1,
            "id_unidad_funcional": 1,
            "descripcion": None,
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )
    assert response_con_dos.status_code == 400
    assert response_con_dos.json()["error_code"] == "APPLICATION_ERROR"
