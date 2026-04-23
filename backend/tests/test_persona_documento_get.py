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


def test_get_persona_documentos_devuelve_solo_no_eliminados(client, db_session) -> None:
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
            "observaciones": "persona creada para test get documentos",
        },
    )

    assert persona_response.status_code == 201

    id_persona = persona_response.json()["data"]["id_persona"]

    documento_response = client.post(
        f"/api/v1/personas/{id_persona}/documentos",
        headers=HEADERS,
        json={
            "tipo_documento": "DNI",
            "numero_documento": numero_documento,
            "pais_emision": "Argentina",
            "es_principal": True,
            "fecha_desde": "2020-01-01",
            "fecha_hasta": None,
            "observaciones": "documento visible",
        },
    )

    assert documento_response.status_code == 201

    id_persona_documento_visible = documento_response.json()["data"]["id_persona_documento"]

    documento_oculto = db_session.execute(
        text(
            """
            INSERT INTO persona_documento (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                deleted_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona,
                tipo_documento_persona,
                numero_documento,
                pais_emision,
                es_principal,
                fecha_desde,
                fecha_hasta,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                '550e8400-e29b-41d4-a716-446655440000',
                '550e8400-e29b-41d4-a716-446655440000',
                :id_persona,
                'PASAPORTE',
                'AA000001',
                'Argentina',
                false,
                NULL,
                NULL,
                'documento eliminado'
            )
            RETURNING id_persona_documento
            """
        ),
        {"id_persona": id_persona},
    ).scalar_one()

    response = client.get(f"/api/v1/personas/{id_persona}/documentos")

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    assert body["data"][0] == {
        "id_persona_documento": id_persona_documento_visible,
        "tipo_documento": "DNI",
        "numero_documento": numero_documento,
        "pais_emision": "Argentina",
        "es_principal": True,
    }

    visible_row = db_session.execute(
        text(
            """
            SELECT id_persona_documento, deleted_at
            FROM persona_documento
            WHERE id_persona_documento = :id_persona_documento
            """
        ),
        {"id_persona_documento": id_persona_documento_visible},
    ).mappings().one()

    deleted_row = db_session.execute(
        text(
            """
            SELECT id_persona_documento, deleted_at
            FROM persona_documento
            WHERE id_persona_documento = :id_persona_documento
            """
        ),
        {"id_persona_documento": documento_oculto},
    ).mappings().one()

    assert visible_row["deleted_at"] is None
    assert deleted_row["deleted_at"] is not None
