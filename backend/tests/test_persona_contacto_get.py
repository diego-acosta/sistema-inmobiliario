from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_persona_contactos_devuelve_solo_no_eliminados(client, db_session) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Alan",
            "apellido": "Turing",
            "razon_social": None,
            "fecha_nacimiento": "1912-06-23",
            "estado_persona": "ACTIVA",
            "observaciones": "persona creada para test get contactos",
        },
    )

    assert persona_response.status_code == 201

    id_persona = persona_response.json()["data"]["id_persona"]

    contacto_response = client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "alan@example.com",
            "es_principal": True,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": "contacto visible",
        },
    )

    assert contacto_response.status_code == 201

    id_persona_contacto_visible = contacto_response.json()["data"]["id_persona_contacto"]

    contacto_oculto = db_session.execute(
        text(
            """
            INSERT INTO persona_contacto (
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
                tipo_contacto,
                valor_contacto,
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
                'TELEFONO',
                '123456789',
                false,
                NULL,
                NULL,
                'contacto eliminado'
            )
            RETURNING id_persona_contacto
            """
        ),
        {"id_persona": id_persona},
    ).scalar_one()

    response = client.get(f"/api/v1/personas/{id_persona}/contactos")

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    assert body["data"][0] == {
        "id_persona_contacto": id_persona_contacto_visible,
        "tipo_contacto": "EMAIL",
        "valor_contacto": "alan@example.com",
        "es_principal": True,
    }

    visible_row = db_session.execute(
        text(
            """
            SELECT id_persona_contacto, deleted_at
            FROM persona_contacto
            WHERE id_persona_contacto = :id_persona_contacto
            """
        ),
        {"id_persona_contacto": id_persona_contacto_visible},
    ).mappings().one()

    deleted_row = db_session.execute(
        text(
            """
            SELECT id_persona_contacto, deleted_at
            FROM persona_contacto
            WHERE id_persona_contacto = :id_persona_contacto
            """
        ),
        {"id_persona_contacto": contacto_oculto},
    ).mappings().one()

    assert visible_row["deleted_at"] is None
    assert deleted_row["deleted_at"] is not None
