from decimal import Decimal

from sqlalchemy import text

from app.application.financiero.services.handle_venta_confirmada_event_service import (
    HandleVentaConfirmadaEventService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from tests.test_cesiones_create import _payload_cesion
from tests.test_disponibilidades_create import HEADERS
from tests.test_escrituraciones_create import _payload_escrituracion
from tests.test_instrumentos_compraventa_create import _payload_instrumento
from tests.test_ventas_confirm import (
    _crear_venta_desde_reserva_publica,
    _payload_confirmar_venta,
)
from tests.test_reservas_venta_confirmar_venta_completa import (
    _usar_plan_refuerzo_interno,
)
from tests.test_ventas_directa_confirmar_venta_completa import (
    _crear_base_directa,
    _obligaciones_items_by_venta,
    _payload,
    _venta_by_codigo,
)


def _detalle(client, id_venta: int):
    return client.get(f"/api/v1/ventas/{id_venta}/detalle-integral")


def _contadores_efectos(db_session) -> dict:
    return dict(
        db_session.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM relacion_generadora) AS relaciones,
                    (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones,
                    (SELECT COUNT(*) FROM movimiento_financiero) AS movimientos,
                    (SELECT COUNT(*) FROM aplicacion_financiera) AS aplicaciones,
                    (SELECT COUNT(*) FROM movimiento_tesoreria) AS movimientos_tesoreria,
                    (SELECT COUNT(*) FROM outbox_event) AS outbox_events,
                    (SELECT COUNT(*) FROM inbox_event) AS inbox_events,
                    (SELECT COUNT(*) FROM liquidacion_punitorio) AS punitorios
                """
            )
        ).mappings().one()
    )


def _confirmar_venta(client, db_session) -> dict:
    venta = _crear_venta_desde_reserva_publica(client, db_session)
    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    return {
        "id_venta": data["id_venta"],
        "version_registro": data["version_registro"],
        "id_inmueble": venta["id_inmueble"],
        "id_reserva_venta": venta["id_reserva_venta"],
    }


def _procesar_evento_financiero_venta(db_session, *, id_venta: int) -> dict:
    event = dict(
        db_session.execute(
            text(
                """
                SELECT id, event_type, aggregate_type, aggregate_id, payload
                FROM outbox_event
                WHERE event_type = 'venta_confirmada'
                  AND aggregate_type = 'venta'
                  AND aggregate_id = :id_venta
                """
            ),
            {"id_venta": id_venta},
        ).mappings().one()
    )
    result = HandleVentaConfirmadaEventService(
        repository=FinancieroRepository(db_session),
    ).execute(event)
    assert result.success is True
    assert result.data is not None
    return result.data


def _id_persona_parte_venta(db_session, *, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT id_persona
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'venta'
              AND id_relacion = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_relacion_persona_rol
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()["id_persona"]


def _payload_plan_pago_v2_bloques() -> dict:
    return {
        "tipo_pago": "FINANCIADO",
        "monto_total_plan": 12700000.00,
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "ANTICIPO",
                "etiqueta_bloque": "Anticipo",
                "importe_total_bloque": 2000000.00,
                "fecha_vencimiento": "2026-05-10",
            },
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "etiqueta_bloque": "Primer tramo",
                "cantidad_cuotas": 6,
                "importe_cuota": 500000.00,
                "fecha_primer_vencimiento": "2026-06-10",
                "periodicidad": "MENSUAL",
            },
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "etiqueta_bloque": "Segundo tramo",
                "cantidad_cuotas": 6,
                "importe_cuota": 700000.00,
                "fecha_primer_vencimiento": "2026-12-10",
                "periodicidad": "MENSUAL",
            },
            {
                "tipo_bloque": "REFUERZO",
                "etiqueta_bloque": "Refuerzo diciembre",
                "importe_total_bloque": 1500000.00,
                "fecha_vencimiento": "2026-12-20",
            },
            {
                "tipo_bloque": "SALDO",
                "etiqueta_bloque": "Saldo contra escritura",
                "importe_total_bloque": 2000000.00,
                "fecha_vencimiento": "2027-03-10",
            },
        ],
    }


def test_detalle_integral_venta_sin_financiero_devuelve_relacion_null_y_obligaciones_vacias(
    client, db_session
) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id_venta"] == venta["id_venta"]
    assert data["estado_venta"] == "borrador"
    assert data["relacion_financiera"] is None
    assert data["obligaciones_financieras"] == []
    assert data["plan_pago_v2"] is None
    assert data["resumen_financiero"] == {
        "cantidad_obligaciones": 0,
        "saldo_total": "0",
        "saldo_pendiente": "0",
        "importe_cancelado": "0",
        "cantidad_vencidas": 0,
        "cantidad_canceladas": 0,
        "cantidad_anuladas": 0,
    }


def test_detalle_integral_venta_confirmada_devuelve_relacion_y_capital_venta(
    client, db_session
) -> None:
    venta = _confirmar_venta(client, db_session)
    fin = _procesar_evento_financiero_venta(db_session, id_venta=venta["id_venta"])

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["relacion_financiera"]["tipo_origen"].lower() == "venta"
    assert data["relacion_financiera"]["id_origen"] == venta["id_venta"]
    assert data["relacion_financiera"]["id_relacion_generadora"] == (
        fin["id_relacion_generadora"]
    )
    assert len(data["obligaciones_financieras"]) == 1
    obligacion = data["obligaciones_financieras"][0]
    assert obligacion["id_obligacion_financiera"] == fin["id_obligacion_financiera"]
    assert obligacion["estado_obligacion"] == "PROYECTADA"
    assert obligacion["composiciones"][0]["codigo_concepto_financiero"] == "CAPITAL_VENTA"
    assert float(obligacion["composiciones"][0]["saldo_componente"]) == 150000.00
    assert data["resumen_financiero"]["cantidad_obligaciones"] == 1
    assert float(data["resumen_financiero"]["saldo_pendiente"]) == 150000.00


def test_detalle_integral_incluye_objetos_condiciones_partes_y_recursos_comerciales(
    client, db_session
) -> None:
    venta = _confirmar_venta(client, db_session)

    instrumento = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            objetos=[
                {
                    "id_inmueble": venta["id_inmueble"],
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto alcanzado",
                }
            ]
        ),
    )
    assert instrumento.status_code == 201
    cesion = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(),
    )
    assert cesion.status_code == 201
    escrituracion = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(numero_escritura="ESC-DET-INT-001"),
    )
    assert escrituracion.status_code == 201

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["reserva_origen"]["id_reserva_venta"] == venta["id_reserva_venta"]
    assert len(data["objetos"]) == 1
    assert data["objetos"][0]["id_inmueble"] == venta["id_inmueble"]
    assert float(data["condiciones_comerciales"]["monto_total"]) == 150000.00
    assert data["condiciones_comerciales"]["tipo_plan_financiero"] == "CONTADO"
    assert data["condiciones_comerciales"]["moneda"] == "ARS"
    assert float(data["condiciones_comerciales"]["objetos"][0]["precio_asignado"]) == 150000.00
    assert len(data["partes"]) == 1
    assert data["partes"][0]["codigo_rol"] == "COMPRADOR"
    assert len(data["instrumentos_compraventa"]) == 1
    assert len(data["cesiones"]) == 1
    assert len(data["escrituraciones"]) == 1
    assert len(data["integracion_inmobiliaria"]["eventos"]) == 2


def test_detalle_integral_incluye_obligados_si_existen(client, db_session) -> None:
    venta = _confirmar_venta(client, db_session)
    _procesar_evento_financiero_venta(db_session, id_venta=venta["id_venta"])
    id_persona = _id_persona_parte_venta(db_session, id_venta=venta["id_venta"])

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    obligados = response.json()["data"]["obligaciones_financieras"][0]["obligados"]
    assert len(obligados) == 1
    assert obligados[0]["id_persona"] == id_persona
    assert obligados[0]["rol_obligado"] == "COMPRADOR"


def test_detalle_integral_anticipo_y_saldo_muestra_plan_y_dos_obligaciones(
    client, db_session
) -> None:
    venta_base = _crear_venta_desde_reserva_publica(client, db_session)
    db_session.execute(
        text(
            """
            UPDATE venta
            SET tipo_plan_financiero = 'ANTICIPO_Y_SALDO',
                moneda = 'ARS',
                importe_anticipo = 50000.00,
                fecha_vencimiento_anticipo = DATE '2026-05-10',
                importe_saldo = 100000.00,
                fecha_vencimiento_saldo = DATE '2026-06-10'
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta_base["id_venta"]},
    )
    response_confirm = client.patch(
        f"/api/v1/ventas/{venta_base['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta_base["version_registro"])},
        json=_payload_confirmar_venta(),
    )
    assert response_confirm.status_code == 200
    _procesar_evento_financiero_venta(db_session, id_venta=venta_base["id_venta"])

    response = _detalle(client, venta_base["id_venta"])

    assert response.status_code == 200
    data = response.json()["data"]
    condiciones = data["condiciones_comerciales"]
    assert condiciones["tipo_plan_financiero"] == "ANTICIPO_Y_SALDO"
    assert condiciones["moneda"] == "ARS"
    assert float(condiciones["importe_anticipo"]) == 50000.00
    assert condiciones["fecha_vencimiento_anticipo"] == "2026-05-10"
    assert float(condiciones["importe_saldo"]) == 100000.00
    assert condiciones["fecha_vencimiento_saldo"] == "2026-06-10"

    obligaciones = data["obligaciones_financieras"]
    assert len(obligaciones) == 2
    assert data["plan_pago_v2"] is None
    conceptos = [
        obligacion["composiciones"][0]["codigo_concepto_financiero"]
        for obligacion in obligaciones
    ]
    assert conceptos == ["ANTICIPO_VENTA", "CAPITAL_VENTA"]
    assert data["resumen_financiero"]["cantidad_obligaciones"] == 2
    assert float(data["resumen_financiero"]["saldo_pendiente"]) == 150000.00


def test_detalle_integral_cuotas_fijas_muestra_cuotas_y_obligaciones(
    client, db_session
) -> None:
    venta_base = _crear_venta_desde_reserva_publica(client, db_session)
    db_session.execute(
        text(
            """
            UPDATE venta
            SET tipo_plan_financiero = 'CUOTAS_FIJAS',
                moneda = 'ARS',
                importe_anticipo = NULL,
                fecha_vencimiento_anticipo = NULL,
                importe_saldo = NULL,
                fecha_vencimiento_saldo = NULL
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta_base["id_venta"]},
    )
    db_session.execute(
        text(
            """
            INSERT INTO venta_plan_cuota (
                id_venta,
                numero_cuota,
                importe_cuota,
                fecha_vencimiento,
                moneda
            )
            VALUES
                (:id_venta, 1, 50000.00, DATE '2026-05-10', 'ARS'),
                (:id_venta, 2, 100000.00, DATE '2026-06-10', 'ARS')
            """
        ),
        {"id_venta": venta_base["id_venta"]},
    )
    response_confirm = client.patch(
        f"/api/v1/ventas/{venta_base['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta_base["version_registro"])},
        json=_payload_confirmar_venta(),
    )
    assert response_confirm.status_code == 200
    _procesar_evento_financiero_venta(db_session, id_venta=venta_base["id_venta"])

    response = _detalle(client, venta_base["id_venta"])

    assert response.status_code == 200
    data = response.json()["data"]
    condiciones = data["condiciones_comerciales"]
    assert condiciones["tipo_plan_financiero"] == "CUOTAS_FIJAS"
    assert [cuota["numero_cuota"] for cuota in condiciones["cuotas"]] == [1, 2]
    assert [float(cuota["importe_cuota"]) for cuota in condiciones["cuotas"]] == [
        50000.00,
        100000.00,
    ]

    obligaciones = data["obligaciones_financieras"]
    assert len(obligaciones) == 2
    assert data["plan_pago_v2"] is None
    assert [
        obligacion["composiciones"][0]["codigo_concepto_financiero"]
        for obligacion in obligaciones
    ] == ["CAPITAL_VENTA", "CAPITAL_VENTA"]
    assert [obligacion["fecha_vencimiento"] for obligacion in obligaciones] == [
        "2026-05-10",
        "2026-06-10",
    ]
    assert data["resumen_financiero"]["cantidad_obligaciones"] == 2
    assert float(data["resumen_financiero"]["saldo_pendiente"]) == 150000.00


def test_detalle_integral_plan_pago_v2_por_bloques_agrupa_bloques_obligaciones_y_composiciones(
    client, db_session
) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)
    response_plan = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/plan-pago-v2/generar",
        headers=HEADERS,
        json=_payload_plan_pago_v2_bloques(),
    )
    assert response_plan.status_code == 200, response_plan.text

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    plan = data["plan_pago_v2"]
    assert plan["id_plan_pago_venta"] == response_plan.json()["data"]["plan_pago_venta"][
        "id_plan_pago_venta"
    ]
    assert plan["metodo_plan_pago"] == "PLAN_POR_BLOQUES"
    assert plan["estado_plan_pago"] == "GENERADO"
    assert plan["monto_total_plan"] == "12700000.00"
    assert plan["moneda"] == "ARS"
    assert [bloque["tipo_bloque"] for bloque in plan["bloques"]] == [
        "ANTICIPO",
        "TRAMO_CUOTAS",
        "TRAMO_CUOTAS",
        "REFUERZO",
        "SALDO",
    ]
    assert [bloque["numero_bloque"] for bloque in plan["bloques"]] == [1, 2, 3, 4, 5]
    assert [len(bloque["obligaciones"]) for bloque in plan["bloques"]] == [
        1,
        6,
        6,
        1,
        1,
    ]

    obligaciones_agrupadas = [
        obligacion
        for bloque in plan["bloques"]
        for obligacion in bloque["obligaciones"]
    ]
    assert len(obligaciones_agrupadas) == 15
    assert len({ob["id_obligacion_financiera"] for ob in obligaciones_agrupadas}) == 15
    assert [ob["numero_obligacion"] for ob in obligaciones_agrupadas] == list(
        range(1, 16)
    )
    assert [ob["tipo_item_cronograma"] for ob in obligaciones_agrupadas] == [
        "ANTICIPO",
        *["CUOTA"] * 6,
        *["CUOTA"] * 6,
        "REFUERZO",
        "SALDO",
    ]
    assert all(ob["composiciones"] for ob in obligaciones_agrupadas)
    assert obligaciones_agrupadas[0]["composiciones"][0][
        "codigo_concepto_financiero"
    ] == "ANTICIPO_VENTA"
    assert {
        composicion["codigo_concepto_financiero"]
        for ob in obligaciones_agrupadas[1:]
        for composicion in ob["composiciones"]
    } == {"CAPITAL_VENTA"}
    assert len(data["obligaciones_financieras"]) == 15
    assert {ob["id_obligacion_financiera"] for ob in data["obligaciones_financieras"]} == {
        ob["id_obligacion_financiera"] for ob in obligaciones_agrupadas
    }
    assert data["resumen_financiero"]["cantidad_obligaciones"] == 15


def test_detalle_integral_no_crea_efectos_ni_ejecuta_mora(client, db_session) -> None:
    venta = _confirmar_venta(client, db_session)
    fin = _procesar_evento_financiero_venta(db_session, id_venta=venta["id_venta"])
    db_session.execute(
        text(
            """
            UPDATE obligacion_financiera
            SET fecha_emision = DATE '2026-01-01',
                fecha_vencimiento = DATE '2026-01-02',
                estado_obligacion = 'EMITIDA'
            WHERE id_obligacion_financiera = :id_obligacion_financiera
            """
        ),
        {"id_obligacion_financiera": fin["id_obligacion_financiera"]},
    )
    before = _contadores_efectos(db_session)

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    assert _contadores_efectos(db_session) == before
    obligacion = response.json()["data"]["obligaciones_financieras"][0]
    assert obligacion["fecha_vencimiento"] == "2026-01-02"
    assert obligacion["estado_obligacion"] == "EMITIDA"
    assert response.json()["data"]["resumen_financiero"]["cantidad_vencidas"] == 0


def test_detalle_integral_404_si_venta_no_existe(client) -> None:
    response = _detalle(client, 999999)

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_detalle_integral_404_si_venta_dada_de_baja(client, db_session) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)
    db_session.execute(
        text(
            """
            UPDATE venta
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    )

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_detalle_integral_venta_directa_confirmada_incluye_contrato_enriquecido(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="DET-INT")
    payload = _payload(codigo_venta="VD-DET-INT", **base)

    confirm = client.post(
        "/api/v1/ventas/directa/confirmar-venta-completa",
        headers=HEADERS,
        json=payload,
    )

    assert confirm.status_code == 200, confirm.text
    id_venta = confirm.json()["data"]["venta"]["id_venta"]

    response = _detalle(client, id_venta)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["venta"]["id_venta"] == id_venta
    assert data["venta"]["estado_venta"] == "confirmada"
    assert data["objetos_vendidos"][0]["id_inmueble"] == base["id_inmueble"]
    assert data["objetos_vendidos"][0]["precio_asignado"] == "150000.00"
    assert data["compradores"][0]["persona"]["id_persona"] == base["id_persona"]
    assert data["compradores"][0]["rol_participacion"]["codigo_rol"] == "COMPRADOR"
    assert data["compradores"][0]["porcentaje_responsabilidad"] == "100.00"
    assert data["impacto_activo"]["objetos"][0]["id_inmueble"] == base["id_inmueble"]

    plan = data["plan_pago_v2"]
    assert plan["cabecera"]["id_plan_pago_venta"] == plan["id_plan_pago_venta"]
    obligaciones_plan = [
        obligacion
        for bloque in plan["bloques"]
        for obligacion in bloque["obligaciones"]
    ]
    assert len(obligaciones_plan) == confirm.json()["data"]["obligaciones"]["cantidad"]
    assert len(data["obligaciones_financieras"]) == len(obligaciones_plan)
    assert sum(Decimal(ob["importe_total"]) for ob in obligaciones_plan) == Decimal(
        plan["monto_total_plan"]
    )
    assert sum(
        Decimal(ob["importe_total"]) for ob in data["obligaciones_financieras"]
    ) == Decimal(data["resumen_financiero"]["saldo_total"])
    assert plan["resumen_financiero"]["cantidad_obligaciones"] == len(
        obligaciones_plan
    )
    assert all(ob["composiciones"] for ob in obligaciones_plan)
    assert all(ob["obligados"] for ob in obligaciones_plan)


def test_detalle_integral_refuerzos_integrados_son_cuotas_de_mayor_importe(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="DET-REF")
    payload = _payload(codigo_venta="VD-DET-REF", **base)
    _usar_plan_refuerzo_interno(payload)

    confirm = client.post(
        "/api/v1/ventas/directa/confirmar-venta-completa",
        headers=HEADERS,
        json=payload,
    )

    assert confirm.status_code == 200, confirm.text
    id_venta = _venta_by_codigo(db_session, "VD-DET-REF")["id_venta"]
    persisted = _obligaciones_items_by_venta(db_session, id_venta)
    assert [ob["importe_total"] for ob in persisted] == [
        Decimal("37500.00"),
        Decimal("75000.00"),
        Decimal("37500.00"),
    ]

    response = _detalle(client, id_venta)

    assert response.status_code == 200, response.text
    plan = response.json()["data"]["plan_pago_v2"]
    obligaciones = [
        obligacion
        for bloque in plan["bloques"]
        for obligacion in bloque["obligaciones"]
    ]
    assert len(obligaciones) == 3
    assert {ob["tipo_item_cronograma"] for ob in obligaciones} == {"CUOTA"}
    assert [Decimal(ob["importe_total"]) for ob in obligaciones] == [
        Decimal("37500.00"),
        Decimal("75000.00"),
        Decimal("37500.00"),
    ]
    assert sum(Decimal(ob["importe_total"]) for ob in obligaciones) == Decimal(
        "150000.00"
    )
