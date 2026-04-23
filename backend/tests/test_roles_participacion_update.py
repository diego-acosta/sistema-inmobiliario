import pytest
from sqlalchemy import text

from app.infrastructure.persistence.repositories.persona_repository import PersonaRepository


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_persona(client, nombre: str) -> int:
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


def _payload(id_persona: int, id_rol: int, id_relacion: int, **overrides) -> dict:
    base = {
        "id_persona": id_persona,
        "id_rol_participacion": id_rol,
        "tipo_relacion": "reserva_venta",
        "id_relacion": id_relacion,
        "fecha_desde": "2024-01-01",
        "fecha_hasta": None,
        "observaciones": None,
    }
    base.update(overrides)
    return base


def test_update_relacion_persona_rol_actualiza_en_postgresql(client, db_session) -> None:
    id_persona = _crear_persona(client, "Grace")
    _crear_rol(db_session, id_rol=1301)
    _crear_reserva_venta(db_session, id_reserva=2301)
    _crear_reserva_venta(db_session, id_reserva=2302)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1301, id_reserva=2301
    )

    response = client.put(
        f"/api/v1/roles-participacion/{id_relacion}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json=_payload(
            id_persona,
            1301,
            2302,
            fecha_desde="2024-02-01",
            observaciones="relacion actualizada",
        ),
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id_relacion_persona_rol": id_relacion,
        "id_persona": id_persona,
        "id_rol_participacion": 1301,
        "tipo_relacion": "reserva_venta",
        "id_relacion": 2302,
        "version_registro": 2,
        "fecha_desde": "2024-02-01",
        "fecha_hasta": None,
    }

    row = db_session.execute(
        text(
            """
            SELECT version_registro, id_relacion, observaciones, id_instalacion_ultima_modificacion,
                   op_id_ultima_modificacion, updated_at
            FROM relacion_persona_rol
            WHERE id_relacion_persona_rol = :id
            """
        ),
        {"id": id_relacion},
    ).mappings().one()
    assert row["version_registro"] == 2
    assert row["id_relacion"] == 2302
    assert row["observaciones"] == "relacion actualizada"
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]
    assert row["updated_at"] is not None


@pytest.mark.parametrize(
    ("case", "mutator"),
    [
        ("relacion_inexistente", None),
        ("relacion_soft_deleted", "relacion"),
        ("persona_inexistente", "persona_inexistente"),
        ("persona_soft_deleted", "persona_deleted"),
        ("rol_inexistente", "rol_inexistente"),
        ("rol_soft_deleted", "rol_deleted"),
    ],
)
def test_update_relacion_persona_rol_devuelve_404_segun_caso(
    client, db_session, case, mutator
) -> None:
    id_persona = _crear_persona(client, case)
    _crear_rol(db_session, id_rol=1302)
    _crear_reserva_venta(db_session, id_reserva=2303)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1302, id_reserva=2303
    )
    payload = _payload(id_persona, 1302, 2303)
    target_id = id_relacion

    if mutator == "relacion":
        db_session.execute(
            text(
                "UPDATE relacion_persona_rol SET deleted_at = created_at + INTERVAL '1 second' WHERE id_relacion_persona_rol = :id"
            ),
            {"id": id_relacion},
        )
    elif mutator == "persona_inexistente":
        payload["id_persona"] = 999999
    elif mutator == "persona_deleted":
        db_session.execute(
            text(
                "UPDATE persona SET deleted_at = created_at + INTERVAL '1 second' WHERE id_persona = :id"
            ),
            {"id": id_persona},
        )
    elif mutator == "rol_inexistente":
        payload["id_rol_participacion"] = 999999
    elif mutator == "rol_deleted":
        db_session.execute(
            text(
                "UPDATE rol_participacion SET deleted_at = created_at + INTERVAL '1 second' WHERE id_rol_participacion = 1302"
            )
        )
    elif case == "relacion_inexistente":
        target_id = 999999

    response = client.put(
        f"/api/v1/roles-participacion/{target_id}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json=payload,
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
    if mutator == "persona_deleted":
        assert PersonaRepository(db_session).persona_exists(id_persona) is False


@pytest.mark.parametrize(
    ("payload_overrides", "setup", "expected_status"),
    [
        ({"id_rol_participacion": 1304}, "rol_inactivo", 400),
        ({"tipo_relacion": "OPERACION"}, None, 400),
        ({"id_relacion": 0}, None, 400),
        ({"id_relacion": 999999}, None, 400),
        ({}, "missing_if_match", 409),
        ({}, "invalid_if_match", 409),
    ],
)
def test_update_relacion_persona_rol_validaciones_y_concurrencia(
    client, db_session, payload_overrides, setup, expected_status
) -> None:
    id_persona = _crear_persona(client, "Validacion")
    _crear_rol(db_session, id_rol=1303)
    _crear_reserva_venta(db_session, id_reserva=2304)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1303, id_reserva=2304
    )

    headers = {**HEADERS, "If-Match-Version": "1"}
    if setup == "rol_inactivo":
        _crear_rol(db_session, id_rol=1304, estado="INACTIVO")
    elif setup == "missing_if_match":
        headers = HEADERS.copy()
    elif setup == "invalid_if_match":
        headers = {**HEADERS, "If-Match-Version": "abc"}

    response = client.put(
        f"/api/v1/roles-participacion/{id_relacion}",
        headers=headers,
        json=_payload(
            id_persona,
            payload_overrides.get("id_rol_participacion", 1303),
            payload_overrides.get("id_relacion", 2304),
            **{
                key: value
                for key, value in payload_overrides.items()
                if key not in {"id_rol_participacion", "id_relacion"}
            },
        ),
    )

    assert response.status_code == expected_status
    assert response.json()["error_code"] == (
        "CONCURRENCY_ERROR" if expected_status == 409 else "APPLICATION_ERROR"
    )


def test_update_relacion_persona_rol_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    id_persona = _crear_persona(client, "Concurrency")
    _crear_rol(db_session, id_rol=1305)
    _crear_reserva_venta(db_session, id_reserva=2305)
    id_relacion = _crear_relacion(
        db_session, id_persona=id_persona, id_rol=1305, id_reserva=2305
    )

    original_get = PersonaRepository.get_relacion_persona_rol_for_update
    db_session.execute(
        text(
            "UPDATE relacion_persona_rol SET version_registro = 2 WHERE id_relacion_persona_rol = :id"
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

    response = client.put(
        f"/api/v1/roles-participacion/{id_relacion}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json=_payload(id_persona, 1305, 2305),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
