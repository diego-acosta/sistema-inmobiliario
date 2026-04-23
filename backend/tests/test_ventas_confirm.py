from sqlalchemy import text

from tests.sql_failpoints import install_statement_failpoint_once
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
    _crear_disponibilidad,
    _payload_base,
)
from tests.test_ventas_definir_condiciones_comerciales import (
    _insertar_venta_para_condiciones,
)


def _payload_generar_venta(*, codigo_venta: str) -> dict[str, object]:
    return {
        "codigo_venta": codigo_venta,
        "fecha_venta": "2026-04-22T11:00:00",
        "monto_total": None,
        "observaciones": "Venta generada desde reserva",
    }


def _payload_condiciones(
    *,
    monto_total: float,
    id_inmueble: int,
    precio_asignado: float,
) -> dict[str, object]:
    return {
        "monto_total": monto_total,
        "objetos": [
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": precio_asignado,
            }
        ],
    }


def _payload_confirmar_venta(
    observaciones: str = "Venta confirmada comercialmente",
) -> dict[str, object]:
    return {"observaciones": observaciones}


def _crear_trigger_falla_confirmacion_venta(db_session, *, id_venta: int) -> None:
    install_statement_failpoint_once(
        db_session,
        statement_prefix="UPDATE venta",
        parameter_name="id_venta",
        parameter_value=id_venta,
        error_message="forced failure on venta confirm",
    )


def _crear_venta_desde_reserva_publica(client, db_session) -> dict[str, int]:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Margaret", apellido="Hamilton")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9301)
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-CONF-001")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )

    create_response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-VTA-CONF-001",
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto principal",
                }
            ],
            id_persona=id_persona,
            id_rol=9301,
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

    confirm_response = client.post(
        f"/api/v1/reservas-venta/{reserva_activa['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva_activa["version_registro"])},
    )
    assert confirm_response.status_code == 200
    reserva_confirmada = confirm_response.json()["data"]

    generate_response = client.post(
        f"/api/v1/reservas-venta/{reserva_confirmada['id_reserva_venta']}/generar-venta",
        headers={
            **HEADERS,
            "If-Match-Version": str(reserva_confirmada["version_registro"]),
        },
        json=_payload_generar_venta(codigo_venta="V-CONF-001"),
    )
    assert generate_response.status_code == 201
    venta_generada = generate_response.json()["data"]

    condiciones_response = client.post(
        f"/api/v1/ventas/{venta_generada['id_venta']}/definir-condiciones-comerciales",
        headers={
            **HEADERS,
            "If-Match-Version": str(venta_generada["version_registro"]),
        },
        json=_payload_condiciones(
            monto_total=150000.00,
            id_inmueble=id_inmueble,
            precio_asignado=150000.00,
        ),
    )
    assert condiciones_response.status_code == 200
    venta_definida = condiciones_response.json()["data"]

    return {
        "id_inmueble": id_inmueble,
        "id_reserva_venta": reserva["id_reserva_venta"],
        "id_venta": venta_definida["id_venta"],
        "version_registro": venta_definida["version_registro"],
    }


def test_confirm_venta_exitosa_desde_flujo_publico_reserva(client, db_session) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)

    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_venta"] == venta["id_venta"]
    assert body["data"]["estado_venta"] == "confirmada"
    assert body["data"]["observaciones"] == "Venta confirmada comercialmente"

    venta_row = db_session.execute(
        text(
            """
            SELECT estado_venta, version_registro, observaciones
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert venta_row["estado_venta"] == "confirmada"
    assert venta_row["version_registro"] == venta["version_registro"] + 1
    assert venta_row["observaciones"] == "Venta confirmada comercialmente"

    reserva_row = db_session.execute(
        text(
            """
            SELECT estado_reserva
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": venta["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["estado_reserva"] == "finalizada"

    disponibilidades = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad, fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().all()
    assert len(disponibilidades) == 2
    assert disponibilidades[0]["estado_disponibilidad"] == "DISPONIBLE"
    assert disponibilidades[0]["fecha_hasta"] is not None
    assert disponibilidades[1]["estado_disponibilidad"] == "RESERVADA"
    assert disponibilidades[1]["fecha_hasta"] is None

    ocupaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM ocupacion")
    ).mappings().one()
    assert ocupaciones["total"] == 0

    obligaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM obligacion_financiera")
    ).mappings().one()
    assert obligaciones["total"] == 0


def test_confirm_venta_devuelve_error_si_estado_es_invalido(client, db_session) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-CONF-002")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-CONF-002",
        estado_venta="confirmada",
        monto_total=150000,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": 150000,
            }
        ],
    )

    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una venta en estado borrador o activa puede confirmarse."
    )


def test_confirm_venta_devuelve_error_si_faltan_condiciones_comerciales(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-CONF-003")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-CONF-003",
        estado_venta="borrador",
        monto_total=None,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": None,
            }
        ],
    )

    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "La venta debe tener condiciones comerciales completas antes de confirmarse."
    )

    venta_row = db_session.execute(
        text(
            """
            SELECT estado_venta, version_registro
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert venta_row["estado_venta"] == "borrador"
    assert venta_row["version_registro"] == 1


def test_confirm_venta_devuelve_error_si_la_venta_es_inconsistente(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-CONF-004")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-CONF-004",
        estado_venta="borrador",
        monto_total=300000,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": 150000,
            },
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": 150000,
            }
        ],
    )

    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "La venta presenta un detalle multiobjeto inconsistente."
    )


def test_confirm_venta_devuelve_error_de_concurrencia(client, db_session) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-CONF-005")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-CONF-005",
        estado_venta="borrador",
        monto_total=150000,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": 150000,
            }
        ],
    )

    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": "999"},
        json=_payload_confirmar_venta(),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_confirm_venta_hace_rollback_completo_si_falla_la_persistencia(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-CONF-006")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-CONF-006",
        estado_venta="borrador",
        monto_total=150000,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": 150000,
            }
        ],
    )
    _crear_trigger_falla_confirmacion_venta(db_session, id_venta=venta["id_venta"])
    db_session.commit()

    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"

    venta_row = db_session.execute(
        text(
            """
            SELECT estado_venta, version_registro, observaciones
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert venta_row["estado_venta"] == "borrador"
    assert venta_row["version_registro"] == 1
    assert venta_row["observaciones"] == "Venta para condiciones comerciales"
