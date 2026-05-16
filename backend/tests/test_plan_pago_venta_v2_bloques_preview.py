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
        bloques=bloques
        if bloques is not None
        else [
            PlanPagoVentaBloqueInput(
                tipo_bloque="TRAMO_CUOTAS",
                importe_total_bloque=Decimal("10000000.00"),
                cantidad_cuotas=6,
                fecha_primer_vencimiento=date(2026, 6, 10),
                periodicidad="MENSUAL",
            )
        ],
    )


def _count(db_session, table: str) -> int:
    return db_session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


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


def test_preview_valida_suma_general_con_tramo_por_capital_total() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(monto_total_plan=Decimal("10000000.01"))
    )

    assert not result.success
    assert result.errors == ["SUMA_BLOQUES_INVALIDA"]
