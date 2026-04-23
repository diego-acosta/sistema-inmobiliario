from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_confirm import _insertar_reserva_para_confirmar
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
    _insertar_reserva_conflictiva,
    _insertar_venta_conflictiva,
    _payload_base,
)


def test_activate_reserva_venta_pasa_de_borrador_a_activa_sin_mutar_disponibilidad(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Ana", apellido="Activa")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9401)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-ACT-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")

    create_response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-ACT-001",
            objetos=[{"id_inmueble": id_inmueble, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9401,
        ),
    )
    assert create_response.status_code == 201
    reserva = create_response.json()["data"]
    assert reserva["estado_reserva"] == "borrador"

    activate_response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert activate_response.status_code == 200
    body = activate_response.json()
    assert body["ok"] is True
    assert body["data"]["id_reserva_venta"] == reserva["id_reserva_venta"]
    assert body["data"]["estado_reserva"] == "activa"
    assert body["data"]["version_registro"] == 2

    reserva_row = db_session.execute(
        text(
            """
            SELECT estado_reserva, version_registro
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["estado_reserva"] == "activa"
    assert reserva_row["version_registro"] == 2

    disponibilidad_rows = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad, fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().all()
    assert len(disponibilidad_rows) == 1
    assert disponibilidad_rows[0]["estado_disponibilidad"] == "DISPONIBLE"
    assert disponibilidad_rows[0]["fecha_hasta"] is None

    ocupaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM ocupacion
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().one()
    assert ocupaciones["total"] == 0


def test_flujo_publico_reserva_venta_create_activate_confirm(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Bruno", apellido="Flujo")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9402)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-ACT-001B")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")

    create_response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-ACT-001B",
            objetos=[{"id_inmueble": id_inmueble, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9402,
        ),
    )
    assert create_response.status_code == 201
    reserva = create_response.json()["data"]

    activate_response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )
    assert activate_response.status_code == 200
    reserva_activa = activate_response.json()["data"]
    assert reserva_activa["estado_reserva"] == "activa"

    confirm_response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva_activa["version_registro"])},
    )
    assert confirm_response.status_code == 200
    reserva_confirmada = confirm_response.json()["data"]
    assert reserva_confirmada["estado_reserva"] == "confirmada"

    disponibilidad_rows = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad, fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().all()
    assert len(disponibilidad_rows) == 2
    assert any(
        row["estado_disponibilidad"] == "DISPONIBLE" and row["fecha_hasta"] is not None
        for row in disponibilidad_rows
    )
    assert any(
        row["estado_disponibilidad"] == "RESERVADA" and row["fecha_hasta"] is None
        for row in disponibilidad_rows
    )


def test_activate_reserva_venta_devuelve_404_si_no_existe(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)

    response = client.post(
        "/api/v1/reservas-venta/999999/activar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "NOT_FOUND"


def test_activate_reserva_venta_devuelve_404_si_esta_eliminada(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-ACT-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-ACT-002",
        estado_reserva="borrador",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )
    db_session.execute(
        text(
            """
            UPDATE reserva_venta
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_activate_reserva_venta_devuelve_error_si_estado_es_invalido(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-ACT-003")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-ACT-003",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["error_message"] == "Solo una reserva en estado borrador puede activarse."


def test_activate_reserva_venta_devuelve_error_de_concurrencia(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-ACT-004")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-ACT-004",
        estado_reserva="borrador",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_activate_reserva_venta_devuelve_error_si_un_objeto_no_es_elegible(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-ACT-005")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="NO_DISPONIBLE")
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-ACT-005",
        estado_reserva="borrador",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "El objeto inmobiliario indicado no esta disponible para activar la reserva."
    )


def test_activate_reserva_venta_devuelve_error_si_hay_conflicto_con_venta_activa(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-ACT-006")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _insertar_venta_conflictiva(
        db_session,
        id_inmueble=id_inmueble,
        codigo_venta="V-ACT-006",
    )
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-ACT-006",
        estado_reserva="borrador",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    assert response.json()["error_message"] == (
        "El objeto inmobiliario indicado ya participa en una venta activa incompatible."
    )


def test_activate_reserva_venta_devuelve_error_si_hay_conflicto_con_reserva_activa(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-ACT-007")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _insertar_reserva_conflictiva(
        db_session,
        id_inmueble=id_inmueble,
        codigo_reserva="RV-CONFLICTO-ACT-007",
    )
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-ACT-007",
        estado_reserva="borrador",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    assert response.json()["error_message"] == (
        "El objeto inmobiliario indicado ya participa en una reserva vigente incompatible."
    )
