from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    GeneratePlanPagoVentaV2PorBloquesCommand,
    PlanPagoVentaBloqueInput,
)
from app.application.comercial.services.build_plan_pago_venta_v2_por_bloques_preview_service import (
    BuildPlanPagoVentaV2PorBloquesPreviewService,
)
from app.application.common.commands import CommandContext

URL = "/api/v1/ventas/{id_venta}/plan-pago-v2/preview"


def _command(
    *,
    monto_total_plan: Decimal = Decimal("10000000.00"),
    bloques: list[PlanPagoVentaBloqueInput] | None = None,
) -> GeneratePlanPagoVentaV2PorBloquesCommand:
    return GeneratePlanPagoVentaV2PorBloquesCommand(
        context=CommandContext(),
        id_venta=1,
        tipo_pago="FINANCIADO",
        monto_total_plan=monto_total_plan,
        moneda="ARS",
        bloques=(
            bloques
            if bloques is not None
            else [
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                )
            ]
        ),
    )


def _count(db_session, table: str) -> int:
    return db_session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


def _payload_tramo_por_capital_total() -> dict:
    return {
        "tipo_pago": "FINANCIADO",
        "monto_total_plan": 10000000.00,
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "importe_total_bloque": 10000000.00,
                "cantidad_cuotas": 6,
                "fecha_primer_vencimiento": "2026-06-10",
                "periodicidad": "MENSUAL",
            }
        ],
    }


def test_preview_tramo_por_capital_total_ajusta_ultima_cuota_y_suma_exacta() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(_command())

    assert result.success, result.errors
    obligaciones = result.data["obligaciones"]
    importes = [obligacion.importe_total for obligacion in obligaciones]
    assert len(importes) == 6
    assert importes[:5] == [Decimal("1666666.67")] * 5
    assert importes[-1] == Decimal("1666666.65")
    assert sum(importes, Decimal("0.00")) == Decimal("10000000.00")
    assert result.data["total_calculado"] == Decimal("10000000.00")
    assert result.data["diferencia"] == Decimal("0.00")


def test_preview_no_persiste_plan_bloques_ni_obligaciones(db_session) -> None:
    before = {
        "plan_pago_venta": _count(db_session, "plan_pago_venta"),
        "plan_pago_venta_bloque": _count(db_session, "plan_pago_venta_bloque"),
        "obligacion_financiera": _count(db_session, "obligacion_financiera"),
    }

    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(_command())

    assert result.success, result.errors
    after = {
        "plan_pago_venta": _count(db_session, "plan_pago_venta"),
        "plan_pago_venta_bloque": _count(db_session, "plan_pago_venta_bloque"),
        "obligacion_financiera": _count(db_session, "obligacion_financiera"),
    }
    assert after == before


def test_preview_contrato_legacy_por_importe_cuota_sigue_funcionando() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            monto_total_plan=Decimal("3000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_cuota=Decimal("500000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                )
            ],
        )
    )

    assert result.success, result.errors
    obligaciones = result.data["obligaciones"]
    assert [obligacion.importe_total for obligacion in obligaciones] == [
        Decimal("500000.00")
    ] * 6
    assert result.data["total_calculado"] == Decimal("3000000.00")


def test_preview_tramo_prioriza_importe_total_bloque_si_importe_cuota_viene_presente() -> (
    None
):
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            monto_total_plan=Decimal("10000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    importe_cuota=Decimal("1.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                )
            ],
        )
    )

    assert result.success, result.errors
    bloque = result.data["bloques"][0]
    obligaciones = result.data["obligaciones"]
    assert bloque.importe_total_bloque == Decimal("10000000.00")
    assert bloque.importe_cuota == Decimal("1666666.67")
    assert [obligacion.importe_total for obligacion in obligaciones[:5]] == [
        Decimal("1666666.67")
    ] * 5
    assert obligaciones[-1].importe_total == Decimal("1666666.65")
    assert sum(
        (obligacion.importe_total for obligacion in obligaciones), Decimal("0.00")
    ) == Decimal("10000000.00")


def test_preview_valida_suma_general_con_tramo_por_capital_total() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(monto_total_plan=Decimal("10000000.01"))
    )

    assert not result.success
    assert result.errors == ["SUMA_BLOQUES_INVALIDA"]


def test_endpoint_preview_tramo_por_capital_total_devuelve_ultima_cuota_ajustada(
    client,
) -> None:
    response = client.post(URL.format(id_venta=1), json=_payload_tramo_por_capital_total())

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["metodo_plan_pago"] == "PLAN_POR_BLOQUES"
    assert data["total_calculado"] == "10000000.00"
    assert data["diferencia"] == "0.00"
    assert len(data["bloques"]) == 1
    assert data["bloques"][0]["importe_total_bloque"] == "10000000.00"
    assert data["bloques"][0]["importe_cuota"] == "1666666.67"

    importes = [obligacion["importe_total"] for obligacion in data["obligaciones"]]
    assert len(importes) == 6
    assert importes[:5] == ["1666666.67"] * 5
    assert importes[-1] == "1666666.65"


def test_endpoint_preview_no_persiste_filas(db_session, client) -> None:
    tables = [
        "plan_pago_venta",
        "plan_pago_venta_bloque",
        "generacion_cronograma_financiero",
        "obligacion_financiera",
        "composicion_obligacion",
        "obligacion_obligado",
    ]
    before = {table: _count(db_session, table) for table in tables}

    response = client.post(URL.format(id_venta=1), json=_payload_tramo_por_capital_total())

    assert response.status_code == 200, response.text
    after = {table: _count(db_session, table) for table in tables}
    assert after == before


def test_endpoint_preview_legacy_por_importe_cuota_sigue_funcionando(client) -> None:
    payload = {
        "tipo_pago": "FINANCIADO",
        "monto_total_plan": 3000000.00,
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "importe_cuota": 500000.00,
                "cantidad_cuotas": 6,
                "fecha_primer_vencimiento": "2026-06-10",
                "periodicidad": "MENSUAL",
            }
        ],
    }

    response = client.post(URL.format(id_venta=1), json=payload)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total_calculado"] == "3000000.00"
    assert [obligacion["importe_total"] for obligacion in data["obligaciones"]] == [
        "500000.00"
    ] * 6


def test_endpoint_preview_rechaza_campos_extra_internos(client) -> None:
    payload = _payload_tramo_por_capital_total()
    payload["id_plan_pago_venta"] = 1
    payload["bloques"][0]["id_plan_pago_venta_bloque"] = 1
    payload["bloques"][0]["clave_bloque"] = "CLIENTE:NO:DEBE:ENVIAR"

    response = client.post(URL.format(id_venta=1), json=payload)

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    locations = {tuple(error["loc"]) for error in errors}
    assert ("body", "id_plan_pago_venta") in locations
    assert ("body", "bloques", 0, "id_plan_pago_venta_bloque") in locations
    assert ("body", "bloques", 0, "clave_bloque") in locations

def test_preview_interes_directo_requiere_tres_parametros() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                    metodo_liquidacion="INTERES_DIRECTO",
                )
            ]
        )
    )
    assert not result.success
    assert result.errors == ["VALIDATION_ERROR"]


def test_endpoint_preview_interes_directo_devuelve_campos_nuevos(client) -> None:
    payload = _payload_tramo_por_capital_total()
    payload["bloques"][0].update(
        {
            "metodo_liquidacion": "INTERES_DIRECTO",
            "tasa_interes_directo_periodica": 0.02,
            "cantidad_periodos": 6,
            "base_calculo_interes": "capital_inicial_bloque",
        }
    )
    response = client.post(URL.format(id_venta=1), json=payload)
    assert response.status_code == 200, response.text
    bloque = response.json()["data"]["bloques"][0]
    assert bloque["metodo_liquidacion"] == "INTERES_DIRECTO"
    assert bloque["tasa_interes_directo_periodica"] == "0.02"
    assert bloque["cantidad_periodos"] == 6
    assert bloque["base_calculo_interes"] == "CAPITAL_INICIAL_BLOQUE"


def test_preview_interes_directo_base_calculo_invalida_devuelve_validation_error() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                    metodo_liquidacion="INTERES_DIRECTO",
                    tasa_interes_directo_periodica=Decimal("0.02"),
                    cantidad_periodos=6,
                    base_calculo_interes="SALDO",
                )
            ]
        )
    )
    assert not result.success
    assert result.errors == ["VALIDATION_ERROR"]
