from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_persona(client, nombre: str = "Alias") -> int:
    response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": nombre,
            "apellido": "Test",
            "razon_social": None,
            "fecha_nacimiento": "1990-01-01",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    return response.json()["data"]["id_persona"]


def _crear_rol(db_session, *, id_rol: int, estado: str = "ACTIVO") -> None:
    db_session.execute(
        text(
            """
            INSERT INTO rol_participacion (
                id_rol_participacion, uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, codigo_rol, nombre_rol, descripcion, estado_rol
            )
            VALUES (
                :id_rol, gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id, :codigo, :nombre, NULL, :estado
            )
            """
        ),
        {
            "id_rol": id_rol,
            "op_id": HEADERS["X-Op-Id"],
            "codigo": f"ROL_{id_rol}",
            "nombre": f"Rol {id_rol}",
            "estado": estado,
        },
    )


def _crear_reserva_venta(db_session, *, id_reserva: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO reserva_venta (
                id_reserva_venta, uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, codigo_reserva, fecha_reserva, estado_reserva, observaciones
            )
            VALUES (
                :id_reserva, gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id, :codigo, DATE '2024-01-01', 'ACTIVA', NULL
            )
            """
        ),
        {
            "id_reserva": id_reserva,
            "op_id": HEADERS["X-Op-Id"],
            "codigo": f"RES-{id_reserva}",
        },
    )


def _crear_relacion(db_session, *, id_persona: int, id_rol: int, id_reserva: int) -> int:
    return db_session.execute(
        text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, id_persona, id_rol_participacion,
                tipo_relacion, id_relacion, fecha_desde, fecha_hasta, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id, :id_persona, :id_rol,
                'reserva_venta', :id_reserva, DATE '2024-01-01', NULL, 'relacion alias'
            )
            RETURNING id_relacion_persona_rol
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_persona": id_persona,
            "id_rol": id_rol,
            "id_reserva": id_reserva,
        },
    ).scalar_one()


def test_alias_create_relacion_persona_rol(client, db_session) -> None:
    id_persona = _crear_persona(client, "CreateAlias")
    _crear_rol(db_session, id_rol=1501)
    _crear_reserva_venta(db_session, id_reserva=2501)

    response = client.post(
        "/api/v1/relaciones-persona-rol",
        headers=HEADERS,
        json={
            "id_persona": id_persona,
            "id_rol_participacion": 1501,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 2501,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": "alta por alias",
        },
    )

    assert response.status_code == 201
    assert isinstance(response.json()["data"]["id_relacion_persona_rol"], int)


def test_alias_update_relacion_persona_rol(client, db_session) -> None:
    id_persona = _crear_persona(client, "UpdateAlias")
    _crear_rol(db_session, id_rol=1502)
    _crear_reserva_venta(db_session, id_reserva=2502)
    _crear_reserva_venta(db_session, id_reserva=2503)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1502, id_reserva=2502
    )

    response = client.put(
        f"/api/v1/relaciones-persona-rol/{id_relacion}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_persona": id_persona,
            "id_rol_participacion": 1502,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 2503,
            "fecha_desde": "2024-02-01",
            "fecha_hasta": None,
            "observaciones": "update por alias",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["version_registro"] == 2


def test_alias_baja_relacion_persona_rol(client, db_session) -> None:
    id_persona = _crear_persona(client, "DeleteAlias")
    _crear_rol(db_session, id_rol=1503)
    _crear_reserva_venta(db_session, id_reserva=2504)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1503, id_reserva=2504
    )

    response = client.patch(
        f"/api/v1/relaciones-persona-rol/{id_relacion}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id_relacion_persona_rol": id_relacion,
        "version_registro": 2,
        "deleted": True,
    }
