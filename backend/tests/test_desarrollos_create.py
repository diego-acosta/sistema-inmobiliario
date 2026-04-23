from sqlalchemy import text


def test_create_desarrollo_inserta_en_postgresql(client, db_session) -> None:
    response = client.post(
        "/api/v1/desarrollos",
        headers={
            "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
            "X-Usuario-Id": "1",
            "X-Sucursal-Id": "1",
            "X-Instalacion-Id": "1",
        },
        json={
            "codigo_desarrollo": "DESA-TEST-001",
            "nombre_desarrollo": "Desarrollo Norte",
            "descripcion": "alta desde test automatizado",
            "estado_desarrollo": "ACTIVO",
            "observaciones": "observacion de alta",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_desarrollo"], int)
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["estado_desarrollo"] == "ACTIVO"

    row = db_session.execute(
        text(
            """
            SELECT
                id_desarrollo,
                uid_global,
                version_registro,
                codigo_desarrollo,
                nombre_desarrollo,
                descripcion,
                estado_desarrollo,
                observaciones
            FROM desarrollo
            WHERE id_desarrollo = :id_desarrollo
            """
        ),
        {"id_desarrollo": body["data"]["id_desarrollo"]},
    ).mappings().one()

    assert row["id_desarrollo"] == body["data"]["id_desarrollo"]
    assert row["uid_global"] is not None
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["codigo_desarrollo"] == "DESA-TEST-001"
    assert row["nombre_desarrollo"] == "Desarrollo Norte"
    assert row["descripcion"] == "alta desde test automatizado"
    assert row["estado_desarrollo"] == "ACTIVO"
    assert row["observaciones"] == "observacion de alta"
