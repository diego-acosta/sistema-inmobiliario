from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_create_inmueble_inserta_en_postgresql(client, db_session) -> None:
    desarrollo_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-INM-001",
            "nombre_desarrollo": "Desarrollo Base",
            "descripcion": "desarrollo para inmueble",
            "estado_desarrollo": "ACTIVO",
            "observaciones": "obs desarrollo",
        },
    )
    assert desarrollo_response.status_code == 201
    id_desarrollo = desarrollo_response.json()["data"]["id_desarrollo"]

    response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": id_desarrollo,
            "codigo_inmueble": "INM-TEST-001",
            "nombre_inmueble": "Lote 1",
            "superficie": "125.50",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "alta desde test automatizado",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_inmueble"], int)
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["codigo_inmueble"] == "INM-TEST-001"
    assert body["data"]["estado_administrativo"] == "ACTIVO"
    assert body["data"]["estado_juridico"] == "REGULAR"

    row = db_session.execute(
        text(
            """
            SELECT
                id_inmueble,
                id_desarrollo,
                uid_global,
                version_registro,
                codigo_inmueble,
                nombre_inmueble,
                superficie,
                estado_administrativo,
                estado_juridico,
                observaciones
            FROM inmueble
            WHERE id_inmueble = :id_inmueble
            """
        ),
        {"id_inmueble": body["data"]["id_inmueble"]},
    ).mappings().one()

    assert row["id_inmueble"] == body["data"]["id_inmueble"]
    assert row["id_desarrollo"] == id_desarrollo
    assert row["uid_global"] is not None
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["codigo_inmueble"] == "INM-TEST-001"
    assert row["nombre_inmueble"] == "Lote 1"
    assert str(row["superficie"]) == "125.50"
    assert row["estado_administrativo"] == "ACTIVO"
    assert row["estado_juridico"] == "REGULAR"
    assert row["observaciones"] == "alta desde test automatizado"
