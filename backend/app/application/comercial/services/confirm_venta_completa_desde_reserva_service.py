from typing import Any

from app.application.comercial.commands.confirm_venta_completa_desde_reserva import (
    ConfirmVentaCompletaDesdeReservaCommand,
)
from app.application.common.results import AppResult


class ConfirmVentaCompletaDesdeReservaService:
    def execute(
        self, command: ConfirmVentaCompletaDesdeReservaCommand
    ) -> AppResult[dict[str, Any]]:
        if command.if_match_version_reserva is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if (
            command.condiciones_comerciales.monto_total
            != command.plan_pago_v2.monto_total_plan
        ):
            return AppResult.fail("MONTO_TOTAL_PLAN_MISMATCH")

        return AppResult.fail("NOT_IMPLEMENTED")
