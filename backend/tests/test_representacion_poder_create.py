from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_create_representacion_poder_inserta_en_postgresql(client, db_session) -> None:
    persona_representado_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Grace",
            "apellido": "Hopper",
            "razon_social": None,
            "fecha_nacimiento": "1906-12-09",
            "estado_persona": "ACTIVA",
            "observaciones": "persona representada para test",
        },
    )
    assert persona_representado_response.status_code == 201

    persona_representante_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Katherine",
            "apellido": "Johnson",
            "razon_social": None,
            "fecha_nacimiento": "1918-08-26",
            "estado_persona": "ACTIVA",
            "observaciones": "persona representante para test",
        },
    )
    assert persona_representante_response.status_code == 201

    id_persona_representado = persona_representado_response.json()["data"]["id_persona"]
    id_persona_representante = persona_representante_response.json()["data"][
        "id_persona"
    ]

    response = client.post(
        f"/api/v1/personas/{id_persona_representado}/representaciones-poder",
        headers=HEADERS,
        json={
            "id_persona_representante": id_persona_representante,
            "tipo_poder": "GENERAL",
            "estado_representacion": "ACTIVA",
            "fecha_desde": "2024-01-01T00:00:00",
            "fecha_hasta": None,
            "descripcion": "poder creado desde test",
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["ok"] is True
    assert isinstance(body["data"]["id_representacion_poder"], int)
    assert body["data"]["id_persona_representado"] == id_persona_representado
    assert body["data"]["id_persona_representante"] == id_persona_representante
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["tipo_poder"] == "GENERAL"
    assert body["data"]["estado_representacion"] == "ACTIVA"

    row = db_session.execute(
        text(
            """
            SELECT
                id_representacion_poder,
                id_persona_representado,
                id_persona_representante,
                uid_global,
                version_registro,
                tipo_poder,
                estado_representacion
            FROM representacion_poder
            WHERE id_representacion_poder = :id_representacion_poder
            """
        ),
        {"id_representacion_poder": body["data"]["id_representacion_poder"]},
    ).mappings().one()

    assert row["id_representacion_poder"] == body["data"]["id_representacion_poder"]
    assert row["id_persona_representado"] == id_persona_representado
    assert row["id_persona_representante"] == id_persona_representante
    assert row["uid_global"] is not None
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["tipo_poder"] == "GENERAL"
    assert row["estado_representacion"] == "ACTIVA"
