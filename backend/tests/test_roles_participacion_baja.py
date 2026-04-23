from sqlalchemy import text

from app.infrastructure.persistence.repositories.persona_repository import PersonaRepository


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_persona(client) -> int:
    response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Grace",
            "apellido": "Hopper",
            "razon_social": None,
            "fecha_nacimiento": "1906-12-09",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    return response.json()["data"]["id_persona"]


def _crear_rol(db_session, *, id_rol: int) -> None:
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
                1, 1, :op_id, :op_id, :codigo, :nombre, NULL, 'ACTIVO'
            )
            """
        ),
        {
            "id_rol": id_rol,
            "op_id": HEADERS["X-Op-Id"],
            "codigo": f"ROL_{id_rol}",
            "nombre": f"Rol {id_rol}",
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
                'reserva_venta', :id_reserva, DATE '2024-01-01', NULL, 'relacion inicial'
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


def test_baja_relacion_persona_rol_actualiza_en_postgresql(client, db_session) -> None:
    id_persona = _crear_persona(client)
    _crear_rol(db_session, id_rol=1401)
    _crear_reserva_venta(db_session, id_reserva=2401)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1401, id_reserva=2401
    )

    response = client.patch(
        f"/api/v1/roles-participacion/{id_relacion}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id_relacion_persona_rol": id_relacion,
        "version_registro": 2,
        "deleted": True,
    }

    row = db_session.execute(
        text(
            """
            SELECT version_registro, deleted_at, updated_at,
                   id_instalacion_ultima_modificacion, op_id_ultima_modificacion
            FROM relacion_persona_rol
            WHERE id_relacion_persona_rol = :id
            """
        ),
        {"id": id_relacion},
    ).mappings().one()
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_baja_relacion_persona_rol_devuelve_404_si_relacion_inexistente(client) -> None:
    response = client.patch(
        "/api/v1/roles-participacion/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_relacion_persona_rol_devuelve_404_si_relacion_ya_esta_eliminada(
    client, db_session
) -> None:
    id_persona = _crear_persona(client)
    _crear_rol(db_session, id_rol=1402)
    _crear_reserva_venta(db_session, id_reserva=2402)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1402, id_reserva=2402
    )
    db_session.execute(
        text(
            """
            UPDATE relacion_persona_rol
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_relacion_persona_rol = :id
            """
        ),
        {"id": id_relacion},
    )

    response = client.patch(
        f"/api/v1/roles-participacion/{id_relacion}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_relacion_persona_rol_devuelve_409_si_falta_if_match_version(
    client, db_session
) -> None:
    id_persona = _crear_persona(client)
    _crear_rol(db_session, id_rol=1403)
    _crear_reserva_venta(db_session, id_reserva=2403)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1403, id_reserva=2403
    )

    response = client.patch(
        f"/api/v1/roles-participacion/{id_relacion}/baja",
        headers=HEADERS,
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_relacion_persona_rol_devuelve_409_si_if_match_version_es_invalido(
    client, db_session
) -> None:
    id_persona = _crear_persona(client)
    _crear_rol(db_session, id_rol=1404)
    _crear_reserva_venta(db_session, id_reserva=2404)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1404, id_reserva=2404
    )

    response = client.patch(
        f"/api/v1/roles-participacion/{id_relacion}/baja",
        headers={**HEADERS, "If-Match-Version": "abc"},
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_relacion_persona_rol_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    id_persona = _crear_persona(client)
    _crear_rol(db_session, id_rol=1405)
    _crear_reserva_venta(db_session, id_reserva=2405)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1405, id_reserva=2405
    )

    original_get = PersonaRepository.get_relacion_persona_rol_for_update
    db_session.execute(
        text(
            """
            UPDATE relacion_persona_rol
            SET version_registro = 2
            WHERE id_relacion_persona_rol = :id
            """
        ),
        {"id": id_relacion},
    )

    def stale_get(self, rel_id: int):
        data = original_get(self, rel_id)
        if data is None:
            return None
        return {**data, "version_registro": 1}

    monkeypatch.setattr(
        PersonaRepository, "get_relacion_persona_rol_for_update", stale_get
    )

    response = client.patch(
        f"/api/v1/roles-participacion/{id_relacion}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
