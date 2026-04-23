from sqlalchemy import text


def test_create_persona_inserta_en_postgresql(client, db_session) -> None:
    response = client.post(
        "/api/v1/personas",
        headers={
            "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
            "X-Usuario-Id": "1",
            "X-Sucursal-Id": "1",
            "X-Instalacion-Id": "1",
        },
        json={
            "tipo_persona": "FISICA",
            "nombre": "Ada",
            "apellido": "Lovelace",
            "razon_social": None,
            "fecha_nacimiento": "1815-12-10",
            "estado_persona": "ACTIVA",
            "observaciones": "alta desde test automatizado",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_persona"], int)
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["estado_persona"] == "ACTIVA"

    row = db_session.execute(
        text(
            """
            SELECT id_persona, uid_global, version_registro, nombre, apellido
            FROM persona
            WHERE id_persona = :id_persona
            """
        ),
        {"id_persona": body["data"]["id_persona"]},
    ).mappings().one()

    assert row["id_persona"] == body["data"]["id_persona"]
    assert row["uid_global"] is not None
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["nombre"] == "Ada"
    assert row["apellido"] == "Lovelace"
