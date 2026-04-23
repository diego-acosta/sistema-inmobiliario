from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_representaciones_poder_devuelve_solo_no_eliminadas(
    client, db_session
) -> None:
    persona_representado_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Alan",
            "apellido": "Turing",
            "razon_social": None,
            "fecha_nacimiento": "1912-06-23",
            "estado_persona": "ACTIVA",
            "observaciones": "persona representada para test get",
        },
    )
    assert persona_representado_response.status_code == 201

    persona_representante_visible_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Joan",
            "apellido": "Clarke",
            "razon_social": None,
            "fecha_nacimiento": "1917-06-24",
            "estado_persona": "ACTIVA",
            "observaciones": "representante visible",
        },
    )
    assert persona_representante_visible_response.status_code == 201

    persona_representante_oculta_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Max",
            "apellido": "Newman",
            "razon_social": None,
            "fecha_nacimiento": "1897-02-07",
            "estado_persona": "ACTIVA",
            "observaciones": "representante oculto",
        },
    )
    assert persona_representante_oculta_response.status_code == 201

    id_persona_representado = persona_representado_response.json()["data"]["id_persona"]
    id_persona_representante_visible = persona_representante_visible_response.json()[
        "data"
    ]["id_persona"]
    id_persona_representante_oculta = persona_representante_oculta_response.json()[
        "data"
    ]["id_persona"]

    representacion_response = client.post(
        f"/api/v1/personas/{id_persona_representado}/representaciones-poder",
        headers=HEADERS,
        json={
            "id_persona_representante": id_persona_representante_visible,
            "tipo_poder": "GENERAL",
            "estado_representacion": "ACTIVA",
            "fecha_desde": "2024-01-01T00:00:00",
            "fecha_hasta": None,
            "descripcion": "representacion visible",
        },
    )
    assert representacion_response.status_code == 201

    id_representacion_visible = representacion_response.json()["data"][
        "id_representacion_poder"
    ]

    representacion_oculta = db_session.execute(
        text(
            """
            INSERT INTO representacion_poder (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                deleted_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona_representado,
                id_persona_representante,
                tipo_poder,
                estado_representacion,
                fecha_desde,
                fecha_hasta,
                descripcion
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
                :id_persona_representado,
                :id_persona_representante,
                'ESPECIAL',
                'REVOCADA',
                CURRENT_TIMESTAMP,
                NULL,
                'representacion eliminada'
            )
            RETURNING id_representacion_poder
            """
        ),
        {
            "id_persona_representado": id_persona_representado,
            "id_persona_representante": id_persona_representante_oculta,
        },
    ).scalar_one()

    response = client.get(
        f"/api/v1/personas/{id_persona_representado}/representaciones-poder"
    )

    assert response.status_code == 200

    body = response.json()
    assert body["ok"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    assert body["data"][0] == {
        "id_representacion_poder": id_representacion_visible,
        "id_persona_representado": id_persona_representado,
        "id_persona_representante": id_persona_representante_visible,
        "tipo_poder": "GENERAL",
        "estado_representacion": "ACTIVA",
        "fecha_desde": "2024-01-01T00:00:00",
        "fecha_hasta": None,
    }

    visible_row = db_session.execute(
        text(
            """
            SELECT id_representacion_poder, deleted_at
            FROM representacion_poder
            WHERE id_representacion_poder = :id_representacion_poder
            """
        ),
        {"id_representacion_poder": id_representacion_visible},
    ).mappings().one()

    deleted_row = db_session.execute(
        text(
            """
            SELECT id_representacion_poder, deleted_at
            FROM representacion_poder
            WHERE id_representacion_poder = :id_representacion_poder
            """
        ),
        {"id_representacion_poder": representacion_oculta},
    ).mappings().one()

    assert visible_row["deleted_at"] is None
    assert deleted_row["deleted_at"] is not None
