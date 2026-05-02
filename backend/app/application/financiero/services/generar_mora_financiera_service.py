from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.application.common.results import AppResult
from app.application.financiero.commands.generar_mora_financiera import (
    GenerarMoraFinancieraCommand,
)
from app.domain.financiero.parametros_mora import TASA_DIARIA_MORA_DEFAULT


class FinancieroRepository(Protocol):
    def buscar_obligaciones_elegibles_mora(
        self, fecha_proceso: date
    ) -> list[dict[str, Any]]: ...

    def marcar_obligaciones_vencidas(self, fecha_proceso: date) -> int: ...


class GenerarMoraFinancieraService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self, command: GenerarMoraFinancieraCommand
    ) -> AppResult[dict[str, Any]]:
        fecha_proceso = command.fecha_proceso or date.today()

        obligaciones = self.repository.buscar_obligaciones_elegibles_mora(
            fecha_proceso
        )
        marcadas = self.repository.marcar_obligaciones_vencidas(fecha_proceso)

        return AppResult.ok(
            {
                "fecha_proceso": fecha_proceso,
                "procesadas": len(obligaciones),
                "marcadas": marcadas,
                "generadas": 0,
                "tasa_diaria": str(TASA_DIARIA_MORA_DEFAULT),
            }
        )
