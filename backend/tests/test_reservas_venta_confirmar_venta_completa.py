from sqlalchemy import text

from tests.sql_failpoints import install_statement_failpoint_once
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
)
from tests.test_reservas_venta_generate_venta import (
    _insertar_reserva_para_generar_venta,
)


def _crear_reserva_confirmada(client, db_session, *, codigo: str) -> dict[str, int]:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre=f"Comprador {codigo}", apellido="Test")
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9600 + abs(hash(codigo)) % 300,
        codigo_rol="COMPRADOR",
    )
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo}")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva=codigo,
        estado_reserva="confirmada",
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "observaciones": "Objeto reservado",
            }
        ],
        participaciones=[
            {
                "id_persona": id_persona,
                "id_rol_participacion": id_rol,
                "fecha_desde": "2026-04-21",
                "observaciones": "Comprador",
            }
        ],
    )
    return {
        **reserva,
        "id_inmueble": id_inmueble,
    }


def _payload(
    *,
    codigo_venta: str,
    id_inmueble: int,
    confirmacion_observaciones: str = "Venta confirmada completa",
) -> dict[str, object]:
    return {
        "generar_venta": {
            "codigo_venta": codigo_venta,
            "fecha_venta": "2026-04-22T11:00:00",
            "monto_total": "150000.00",
            "observaciones": "Venta completa desde reserva",
        },
        "condiciones_comerciales": {
            "monto_total": "150000.00",
            "tipo_plan_financiero": "ANTICIPO_Y_SALDO",
            "moneda": "ARS",
            "importe_anticipo": "50000.00",
            "fecha_vencimiento_anticipo": "2026-04-30",
            "importe_saldo": "100000.00",
            "fecha_vencimiento_saldo": "2026-05-30",
            "cuotas": [],
            "objetos": [
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "precio_asignado": "150000.00",
                }
            ],
        },
        "plan_pago_v2": {
            "tipo_pago": "FINANCIADO",
            "monto_total_plan": "150000.00",
            "moneda": "ARS",
            "bloques": [
                {
                    "tipo_bloque": "ANTICIPO",
                    "etiqueta_bloque": "Anticipo",
                    "importe_total_bloque": "50000.00",
                    "fecha_vencimiento": "2026-04-30",
                },
                {
                    "tipo_bloque": "SALDO",
                    "etiqueta_bloque": "Saldo",
                    "importe_total_bloque": "100000.00",
                    "fecha_vencimiento": "2026-05-30",
                },
            ],
            "observaciones": "Plan por bloques",
        },
        "confirmacion": {
            "observaciones": confirmacion_observaciones,
        },
    }


def _venta_by_codigo(db_session, codigo_venta: str):
    return db_session.execute(
        text(
            """
            SELECT id_venta, estado_venta, version_registro
            FROM venta
            WHERE codigo_venta = :codigo_venta
              AND deleted_at IS NULL
            """
        ),
        {"codigo_venta": codigo_venta},
    ).mappings().one_or_none()


def _estado_reserva(db_session, id_reserva_venta: int) -> str:
    return db_session.execute(
        text(
            """
            SELECT estado_reserva
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": id_reserva_venta},
    ).scalar_one()


def _count_obligaciones(db_session) -> int:
    return db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera WHERE deleted_at IS NULL")
    ).scalar_one()


def test_confirmar_venta_completa_desde_reserva_exito(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-OK")

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload(codigo_venta="V-COMP-OK", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["reserva_venta"]["estado_reserva"] == "finalizada"
    assert body["data"]["venta"]["estado_venta"] == "confirmada"
    assert body["data"]["obligaciones"]["cantidad"] == 2

    venta = _venta_by_codigo(db_session, "V-COMP-OK")
    assert venta is not None
    assert venta["estado_venta"] == "confirmada"


def test_confirmar_venta_completa_falla_condiciones_hace_rollback(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-COND")
    payload = _payload(codigo_venta="V-COMP-COND", id_inmueble=reserva["id_inmueble"])
    payload["condiciones_comerciales"]["objetos"] = []

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 400
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"
    assert _venta_by_codigo(db_session, "V-COMP-COND") is None


def test_confirmar_venta_completa_falla_plan_pago_hace_rollback(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-PLAN")
    before_obligaciones = _count_obligaciones(db_session)
    payload = _payload(codigo_venta="V-COMP-PLAN", id_inmueble=reserva["id_inmueble"])
    payload["plan_pago_v2"]["tipo_pago"] = "INVALIDO"

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=payload,
    )

    assert response.status_code == 400
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"
    assert _venta_by_codigo(db_session, "V-COMP-PLAN") is None
    assert _count_obligaciones(db_session) == before_obligaciones


def test_confirmar_venta_completa_falla_confirmacion_hace_rollback(
    client, db_session
) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-CONF")
    before_obligaciones = _count_obligaciones(db_session)
    install_statement_failpoint_once(
        db_session,
        statement_prefix="UPDATE venta",
        parameter_name="observaciones",
        parameter_value="FORCE_CONFIRM_FAIL",
        error_message="forced failure on complete confirm",
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload(
            codigo_venta="V-COMP-CONF",
            id_inmueble=reserva["id_inmueble"],
            confirmacion_observaciones="FORCE_CONFIRM_FAIL",
        ),
    )

    assert response.status_code == 500
    assert _estado_reserva(db_session, reserva["id_reserva_venta"]) == "confirmada"
    assert _venta_by_codigo(db_session, "V-COMP-CONF") is None
    assert _count_obligaciones(db_session) == before_obligaciones


def test_confirmar_venta_completa_reserva_inexistente(client) -> None:
    response = client.post(
        "/api/v1/reservas-venta/999999/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": "1"},
        json=_payload(codigo_venta="V-COMP-NF", id_inmueble=1),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND_RESERVA_VENTA"


def test_confirmar_venta_completa_reserva_estado_invalido(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-STATE")
    db_session.execute(
        text(
            """
            UPDATE reserva_venta
            SET estado_reserva = 'borrador'
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload(codigo_venta="V-COMP-STATE", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_RESERVA_STATE"]


def test_confirmar_venta_completa_if_match_invalido(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-IFMATCH")

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": "999"},
        json=_payload(codigo_venta="V-COMP-IFMATCH", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_confirmar_venta_completa_x_op_id_faltante_devuelve_400(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-HDR-MISS")

    headers = {**HEADERS, "If-Match-Version": str(reserva["version_registro"])}
    headers.pop("X-Op-Id", None)

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers=headers,
        json=_payload(codigo_venta="V-COMP-HDR-MISS", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": "X-Op-Id"}


def test_confirmar_venta_completa_if_match_faltante_devuelve_400(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-IFMISS")

    headers = dict(HEADERS)

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers=headers,
        json=_payload(codigo_venta="V-COMP-IFMISS", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": "If-Match-Version"}


def test_confirmar_venta_completa_if_match_invalido_formato_devuelve_400(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(client, db_session, codigo="RV-COMP-IFBAD")

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar-venta-completa",
        headers={**HEADERS, "If-Match-Version": "abc"},
        json=_payload(codigo_venta="V-COMP-IFBAD", id_inmueble=reserva["id_inmueble"]),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": "If-Match-Version"}
