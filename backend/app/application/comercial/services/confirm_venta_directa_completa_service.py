from typing import Any

from app.application.comercial.commands.confirm_venta_directa_completa import (
    ConfirmVentaDirectaCompletaCommand,
)
from app.application.common.results import AppResult


class ConfirmVentaDirectaCompletaService:
    def execute(
        self, command: ConfirmVentaDirectaCompletaCommand
    ) -> AppResult[dict[str, Any]]:
        return AppResult.fail("NOT_IMPLEMENTED")
