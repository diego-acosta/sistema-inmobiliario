from sqlalchemy import text

from tests.sql_failpoints import install_statement_failpoint_once
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
    _insertar_reserva_conflictiva,
    _insertar_venta_conflictiva,
)


ENDPOINT = "/api/v1/ventas/directa/confirmar-venta-completa"


def _crear_base_directa(client, db_session, *, codigo: str) -> dict[str, int]:
    id_persona = _crear_persona(client, nombre=f"Comprador {codigo}", apellido="Directo")
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9900 + abs(hash(codigo)) % 200,
        codigo_rol="COMPRADOR",
    )
    id_inmueble = _crear_inmueble(client, codigo=f"INM-VD-COMP-{codigo}")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    return {
        "id_inmueble": id_inmueble,
        "id_persona": id_persona,
        "id_rol": id_rol,
    }


def _payload(
    *,
    codigo_venta: str,
    id_inmueble: int,
    id_persona: int,
    id_rol: int,
    confirmacion_observaciones: str = "Venta directa confirmada",
) -> dict[str, object]:
    return {
        "generar_venta": {
            "codigo_venta": codigo_venta,
            "fecha_venta": "2026-05-22T10:00:00",
            "monto_total": "150000.00",
            "observaciones": "Venta directa completa",
        },
        "objetos": [
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": "150000.00",
                "observaciones": "Objeto venta directa",
            }
        ],
        "compradores": [
            {
                "id_persona": id_persona,
                "id_rol_participacion": id_rol,
                "fecha_desde": "2026-05-22",
                "fecha_hasta": None,
                "observaciones": "Comprador principal",
            }
        ],
        "condiciones_comerciales": {
            "monto_total": "150000.00",
            "tipo_plan_financiero": "ANTICIPO_Y_SALDO",
            "moneda": "ARS",
            "importe_anticipo": "50000.00",
            "fecha_vencimiento_anticipo": "2026-05-30",
            "importe_saldo": "100000.00",
            "fecha_vencimiento_saldo": "2026-06-30",
            "cuotas": [],
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
                    "fecha_vencimiento": "2026-05-30",
                },
                {
                    "tipo_bloque": "SALDO",
                    "etiqueta_bloque": "Saldo",
                    "importe_total_bloque": "100000.00",
                    "fecha_vencimiento": "2026-06-30",
                },
            ],
            "observaciones": "Plan venta directa",
        },
        "confirmacion": {
            "observaciones": confirmacion_observaciones,
        },
    }


def _venta_by_codigo(db_session, codigo_venta: str):
    return db_session.execute(
        text(
            """
            SELECT id_venta, id_reserva_venta, estado_venta, version_registro
            FROM venta
            WHERE codigo_venta = :codigo_venta
              AND deleted_at IS NULL
            """
        ),
        {"codigo_venta": codigo_venta},
    ).mappings().one_or_none()


def _count_obligaciones(db_session) -> int:
    return db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera WHERE deleted_at IS NULL")
    ).scalar_one()


def _count_venta_objetos(db_session, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).scalar_one()


def _count_compradores(db_session, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'venta'
              AND id_relacion = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).scalar_one()


def test_confirmar_venta_directa_completa_exito(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="OK")

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-OK", **base),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["venta"]["estado_venta"] == "confirmada"
    assert body["data"]["obligaciones"]["cantidad"] == 2

    venta = _venta_by_codigo(db_session, "VD-COMP-OK")
    assert venta is not None
    assert venta["id_reserva_venta"] is None
    assert venta["estado_venta"] == "confirmada"
    assert _count_venta_objetos(db_session, venta["id_venta"]) == 1
    assert _count_compradores(db_session, venta["id_venta"]) == 1


def test_confirmar_venta_directa_falla_condiciones_hace_rollback(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="COND")
    payload = _payload(codigo_venta="VD-COMP-COND", **base)
    payload["condiciones_comerciales"]["monto_total"] = "140000.00"
    payload["plan_pago_v2"]["monto_total_plan"] = "140000.00"

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_MONTO_TOTAL"]
    assert _venta_by_codigo(db_session, "VD-COMP-COND") is None


def test_confirmar_venta_directa_falla_plan_pago_hace_rollback(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="PLAN")
    before_obligaciones = _count_obligaciones(db_session)
    payload = _payload(codigo_venta="VD-COMP-PLAN", **base)
    payload["plan_pago_v2"]["tipo_pago"] = "INVALIDO"

    response = client.post(ENDPOINT, headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert _venta_by_codigo(db_session, "VD-COMP-PLAN") is None
    assert _count_obligaciones(db_session) == before_obligaciones


def test_confirmar_venta_directa_falla_confirmacion_hace_rollback(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="CONF")
    before_obligaciones = _count_obligaciones(db_session)
    install_statement_failpoint_once(
        db_session,
        statement_prefix="UPDATE venta",
        parameter_name="observaciones",
        parameter_value="FORCE_CONFIRM_FAIL",
        error_message="forced failure on direct complete confirm",
    )

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(
            codigo_venta="VD-COMP-CONF",
            confirmacion_observaciones="FORCE_CONFIRM_FAIL",
            **base,
        ),
    )

    assert response.status_code == 500
    assert _venta_by_codigo(db_session, "VD-COMP-CONF") is None
    assert _count_obligaciones(db_session) == before_obligaciones


def test_confirmar_venta_directa_objeto_no_disponible(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="NO-DISP")
    db_session.execute(
        text(
            """
            UPDATE disponibilidad
            SET estado_disponibilidad = 'RESERVADA'
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": base["id_inmueble"]},
    )

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-NO-DISP", **base),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_DISPONIBILIDAD_STATE"]
    assert _venta_by_codigo(db_session, "VD-COMP-NO-DISP") is None


def test_confirmar_venta_directa_objeto_con_reserva_vigente(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="RESERVA")
    _insertar_reserva_conflictiva(
        db_session,
        id_inmueble=base["id_inmueble"],
        codigo_reserva="RV-VD-COMP-CONFLICTO",
    )

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-RESERVA", **base),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["CONFLICTING_RESERVA"]
    assert _venta_by_codigo(db_session, "VD-COMP-RESERVA") is None


def test_confirmar_venta_directa_comprador_invalido(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="ROL")
    id_rol_no_comprador = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9950,
        codigo_rol="VENDEDOR-VD-COMP",
    )
    base["id_rol"] = id_rol_no_comprador

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-ROL", **base),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_ROL_COMPRADOR"]
    assert _venta_by_codigo(db_session, "VD-COMP-ROL") is None


def test_confirmar_venta_directa_codigo_duplicado(client, db_session) -> None:
    base = _crear_base_directa(client, db_session, codigo="DUP")
    _insertar_venta_conflictiva(
        db_session,
        id_inmueble=base["id_inmueble"],
        codigo_venta="VD-COMP-DUP",
    )

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload(codigo_venta="VD-COMP-DUP", **base),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["DUPLICATE_CODIGO_VENTA"]
