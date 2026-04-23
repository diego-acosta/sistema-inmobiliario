from uuid import uuid4

from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _numero_documento_unico() -> str:
    return str((uuid4().int % 90_000_000) + 10_000_000)


def test_create_persona_documento_inserta_en_postgresql(client, db_session) -> None:
    numero_documento = _numero_documento_unico()

    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Grace",
            "apellido": "Hopper",
            "razon_social": None,
            "fecha_nacimiento": "1906-12-09",
            "estado_persona": "ACTIVA",
            "observaciones": "persona creada para test de documento",
        },
    )

    assert persona_response.status_code == 201

    id_persona = persona_response.json()["data"]["id_persona"]

    response = client.post(
        f"/api/v1/personas/{id_persona}/documentos",
        headers=HEADERS,
        json={
            "tipo_documento": "DNI",
            "numero_documento": numero_documento,
            "pais_emision": "AR",
            "es_principal": True,
            "fecha_desde": "2020-01-01",
            "fecha_hasta": None,
            "observaciones": "documento principal desde test",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_persona_documento"], int)
    assert body["data"]["id_persona"] == id_persona
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["tipo_documento"] == "DNI"
    assert body["data"]["numero_documento"] == numero_documento
    assert body["data"]["es_principal"] is True

    row = db_session.execute(
        text(
            """
            SELECT
                id_persona_documento,
                id_persona,
                uid_global,
                version_registro,
                tipo_documento_persona,
                numero_documento,
                es_principal
            FROM persona_documento
            WHERE id_persona_documento = :id_persona_documento
            """
        ),
        {"id_persona_documento": body["data"]["id_persona_documento"]},
    ).mappings().one()

    assert row["id_persona_documento"] == body["data"]["id_persona_documento"]
    assert row["id_persona"] == id_persona
    assert row["uid_global"] is not None
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["tipo_documento_persona"] == "DNI"
    assert row["numero_documento"] == numero_documento
    assert row["es_principal"] is True
