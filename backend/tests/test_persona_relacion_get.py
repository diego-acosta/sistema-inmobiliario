from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_persona_relaciones_devuelve_solo_no_eliminadas(client, db_session) -> None:
    persona_origen_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Alan",
            "apellido": "Turing",
            "razon_social": None,
            "fecha_nacimiento": "1912-06-23",
            "estado_persona": "ACTIVA",
            "observaciones": "persona origen para test get relaciones",
        },
    )

    assert persona_origen_response.status_code == 201

    persona_destino_visible_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Joan",
            "apellido": "Clarke",
            "razon_social": None,
            "fecha_nacimiento": "1917-06-24",
            "estado_persona": "ACTIVA",
            "observaciones": "persona destino visible",
        },
    )

    assert persona_destino_visible_response.status_code == 201

    persona_destino_oculta_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Max",
            "apellido": "Newman",
            "razon_social": None,
            "fecha_nacimiento": "1897-02-07",
            "estado_persona": "ACTIVA",
            "observaciones": "persona destino oculta",
        },
    )

    assert persona_destino_oculta_response.status_code == 201

    id_persona_origen = persona_origen_response.json()["data"]["id_persona"]
    id_persona_destino_visible = persona_destino_visible_response.json()["data"][
        "id_persona"
    ]
    id_persona_destino_oculta = persona_destino_oculta_response.json()["data"][
        "id_persona"
    ]

    relacion_response = client.post(
        f"/api/v1/personas/{id_persona_origen}/relaciones",
        headers=HEADERS,
        json={
            "id_persona_destino": id_persona_destino_visible,
            "tipo_relacion": "PAREJA",
            "fecha_desde": "2024-01-01T00:00:00",
            "fecha_hasta": None,
            "observaciones": "relacion visible",
        },
    )

    assert relacion_response.status_code == 201

    id_persona_relacion_visible = relacion_response.json()["data"]["id_persona_relacion"]

    relacion_oculta = db_session.execute(
        text(
            """
            INSERT INTO persona_relacion (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                deleted_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona_origen,
                id_persona_destino,
                tipo_relacion,
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
                :id_persona_origen,
                :id_persona_destino,
                'LABORAL',
                CURRENT_TIMESTAMP,
                NULL,
                'relacion eliminada'
            )
            RETURNING id_persona_relacion
            """
        ),
        {
            "id_persona_origen": id_persona_origen,
            "id_persona_destino": id_persona_destino_oculta,
        },
    ).scalar_one()

    response = client.get(f"/api/v1/personas/{id_persona_origen}/relaciones")

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    assert body["data"][0] == {
        "id_persona_relacion": id_persona_relacion_visible,
        "id_persona_origen": id_persona_origen,
        "id_persona_destino": id_persona_destino_visible,
        "tipo_relacion": "PAREJA",
        "fecha_desde": "2024-01-01T00:00:00",
        "fecha_hasta": None,
    }

    visible_row = db_session.execute(
        text(
            """
            SELECT id_persona_relacion, deleted_at
            FROM persona_relacion
            WHERE id_persona_relacion = :id_persona_relacion
            """
        ),
        {"id_persona_relacion": id_persona_relacion_visible},
    ).mappings().one()

    deleted_row = db_session.execute(
        text(
            """
            SELECT id_persona_relacion, deleted_at
            FROM persona_relacion
            WHERE id_persona_relacion = :id_persona_relacion
            """
        ),
        {"id_persona_relacion": relacion_oculta},
    ).mappings().one()

    assert visible_row["deleted_at"] is None
    assert deleted_row["deleted_at"] is not None
