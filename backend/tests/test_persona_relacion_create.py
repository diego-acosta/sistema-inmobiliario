from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_create_persona_relacion_inserta_en_postgresql(client, db_session) -> None:
    persona_origen_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Grace",
            "apellido": "Hopper",
            "razon_social": None,
            "fecha_nacimiento": "1906-12-09",
            "estado_persona": "ACTIVA",
            "observaciones": "persona origen para test de relacion",
        },
    )

    assert persona_origen_response.status_code == 201

    persona_destino_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Katherine",
            "apellido": "Johnson",
            "razon_social": None,
            "fecha_nacimiento": "1918-08-26",
            "estado_persona": "ACTIVA",
            "observaciones": "persona destino para test de relacion",
        },
    )

    assert persona_destino_response.status_code == 201

    id_persona_origen = persona_origen_response.json()["data"]["id_persona"]
    id_persona_destino = persona_destino_response.json()["data"]["id_persona"]

    response = client.post(
        f"/api/v1/personas/{id_persona_origen}/relaciones",
        headers=HEADERS,
        json={
            "id_persona_destino": id_persona_destino,
            "tipo_relacion": "FAMILIAR",
            "fecha_desde": "2024-01-01T00:00:00Z",
            "fecha_hasta": None,
            "observaciones": "relacion creada desde test",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_persona_relacion"], int)
    assert body["data"]["id_persona_origen"] == id_persona_origen
    assert body["data"]["id_persona_destino"] == id_persona_destino
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["tipo_relacion"] == "FAMILIAR"

    row = db_session.execute(
        text(
            """
            SELECT
                id_persona_relacion,
                id_persona_origen,
                id_persona_destino,
                uid_global,
                version_registro,
                tipo_relacion
            FROM persona_relacion
            WHERE id_persona_relacion = :id_persona_relacion
            """
        ),
        {"id_persona_relacion": body["data"]["id_persona_relacion"]},
    ).mappings().one()

    assert row["id_persona_relacion"] == body["data"]["id_persona_relacion"]
    assert row["id_persona_origen"] == id_persona_origen
    assert row["id_persona_destino"] == id_persona_destino
    assert row["uid_global"] is not None
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["tipo_relacion"] == "FAMILIAR"
