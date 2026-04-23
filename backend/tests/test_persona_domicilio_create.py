from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_create_persona_domicilio_inserta_en_postgresql(client, db_session) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Elena",
            "apellido": "Gilbert",
            "razon_social": None,
            "fecha_nacimiento": "1990-05-15",
            "estado_persona": "ACTIVA",
            "observaciones": "persona creada para test de domicilio",
        },
    )

    assert persona_response.status_code == 201

    id_persona = persona_response.json()["data"]["id_persona"]

    response = client.post(
        f"/api/v1/personas/{id_persona}/domicilios",
        headers=HEADERS,
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Av. Siempre Viva 742",
            "localidad": "Springfield",
            "provincia": "Buenos Aires",
            "pais": "AR",
            "codigo_postal": "1000",
            "es_principal": True,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": "domicilio principal desde test",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_persona_domicilio"], int)
    assert body["data"]["id_persona"] == id_persona
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["tipo_domicilio"] == "REAL"
    assert body["data"]["direccion"] == "Av. Siempre Viva 742"
    assert body["data"]["es_principal"] is True

    row = db_session.execute(
        text(
            """
            SELECT
                id_persona_domicilio,
                id_persona,
                uid_global,
                version_registro,
                tipo_domicilio,
                direccion,
                es_principal
            FROM persona_domicilio
            WHERE id_persona_domicilio = :id_persona_domicilio
            """
        ),
        {"id_persona_domicilio": body["data"]["id_persona_domicilio"]},
    ).mappings().one()

    assert row["id_persona_domicilio"] == body["data"]["id_persona_domicilio"]
    assert row["id_persona"] == id_persona
    assert row["uid_global"] is not None
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["tipo_domicilio"] == "REAL"
    assert row["direccion"] == "Av. Siempre Viva 742"
    assert row["es_principal"] is True
