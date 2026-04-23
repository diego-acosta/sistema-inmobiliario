from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_rol_participacion_activo(db_session, *, id_rol_participacion: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO rol_participacion (
                id_rol_participacion,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_rol,
                nombre_rol,
                descripcion,
                estado_rol
            )
            VALUES (
                :id_rol_participacion,
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                '550e8400-e29b-41d4-a716-446655440000',
                '550e8400-e29b-41d4-a716-446655440000',
                :codigo_rol,
                :nombre_rol,
                NULL,
                'ACTIVO'
            )
            """
        ),
        {
            "id_rol_participacion": id_rol_participacion,
            "codigo_rol": f"ROL_{id_rol_participacion}",
            "nombre_rol": f"Rol {id_rol_participacion}",
        },
    )


def _crear_reserva_venta(db_session, *, id_reserva_venta: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO reserva_venta (
                id_reserva_venta,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                observaciones
            )
            VALUES (
                :id_reserva_venta,
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                '550e8400-e29b-41d4-a716-446655440000',
                '550e8400-e29b-41d4-a716-446655440000',
                :codigo_reserva,
                DATE '2024-01-01',
                'ACTIVA',
                NULL
            )
            """
        ),
        {
            "id_reserva_venta": id_reserva_venta,
            "codigo_reserva": f"RES-{id_reserva_venta}",
        },
    )


def test_get_persona_participaciones_devuelve_solo_no_eliminadas(
    client, db_session
) -> None:
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
            "observaciones": "persona creada para test get participaciones",
        },
    )

    assert persona_response.status_code == 201

    id_persona = persona_response.json()["data"]["id_persona"]
    _crear_rol_participacion_activo(db_session, id_rol_participacion=1101)
    _crear_rol_participacion_activo(db_session, id_rol_participacion=1102)
    _crear_reserva_venta(db_session, id_reserva_venta=2101)
    _crear_reserva_venta(db_session, id_reserva_venta=2102)

    visible = db_session.execute(
        text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona,
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
                fecha_desde,
                fecha_hasta,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                '550e8400-e29b-41d4-a716-446655440000',
                '550e8400-e29b-41d4-a716-446655440000',
                :id_persona,
                1101,
                'reserva_venta',
                2101,
                DATE '2024-01-01',
                NULL,
                'participacion visible'
            )
            RETURNING id_relacion_persona_rol
            """
        ),
        {"id_persona": id_persona},
    ).scalar_one()

    oculta = db_session.execute(
        text(
            """
            INSERT INTO relacion_persona_rol (
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
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
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
                1102,
                'reserva_venta',
                2102,
                DATE '2024-02-01',
                NULL,
                'participacion oculta'
            )
            RETURNING id_relacion_persona_rol
            """
        ),
        {"id_persona": id_persona},
    ).scalar_one()

    response = client.get(f"/api/v1/personas/{id_persona}/participaciones")

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    assert body["data"] == [
        {
            "id_relacion_persona_rol": visible,
            "id_persona": id_persona,
            "id_rol_participacion": 1101,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 2101,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
        }
    ]

    visible_row = db_session.execute(
        text(
            """
            SELECT id_relacion_persona_rol, deleted_at
            FROM relacion_persona_rol
            WHERE id_relacion_persona_rol = :id_relacion_persona_rol
            """
        ),
        {"id_relacion_persona_rol": visible},
    ).mappings().one()

    deleted_row = db_session.execute(
        text(
            """
            SELECT id_relacion_persona_rol, deleted_at
            FROM relacion_persona_rol
            WHERE id_relacion_persona_rol = :id_relacion_persona_rol
            """
        ),
        {"id_relacion_persona_rol": oculta},
    ).mappings().one()

    assert visible_row["deleted_at"] is None
    assert deleted_row["deleted_at"] is not None


def test_get_persona_participaciones_no_trae_deleted_at(client, db_session) -> None:
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
            "observaciones": "persona creada para test hidden participaciones",
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]
    _crear_rol_participacion_activo(db_session, id_rol_participacion=1103)
    _crear_reserva_venta(db_session, id_reserva_venta=2103)

    db_session.execute(
        text(
            """
            INSERT INTO relacion_persona_rol (
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
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
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
                1103,
                'reserva_venta',
                2103,
                DATE '2024-01-01',
                NULL,
                'participacion eliminada'
            )
            """
        ),
        {"id_persona": id_persona},
    )

    response = client.get(f"/api/v1/personas/{id_persona}/participaciones")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": [],
    }


def test_get_persona_participaciones_persona_inexistente_devuelve_404(client) -> None:
    response = client.get("/api/v1/personas/999999/participaciones")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "La persona indicada no existe.",
        "details": {"errors": ["La persona indicada no existe."]},
    }


def test_get_persona_participaciones_persona_soft_deleted_devuelve_404(
    client, db_session
) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Barbara",
            "apellido": "Liskov",
            "razon_social": None,
            "fecha_nacimiento": "1939-11-07",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]

    db_session.execute(
        text(
            """
            UPDATE persona
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_persona = :id_persona
            """
        ),
        {"id_persona": id_persona},
    )

    response = client.get(f"/api/v1/personas/{id_persona}/participaciones")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "La persona indicada no existe.",
        "details": {"errors": ["La persona indicada no existe."]},
    }
