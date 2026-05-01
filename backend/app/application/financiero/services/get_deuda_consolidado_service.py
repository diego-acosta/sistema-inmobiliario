from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def get_deuda_consolidado(
        self,
        *,
        tipo_origen: str | None,
        fecha_corte: date,
    ) -> dict[str, Any]: ...


class GetDeudaConsolidadoService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        tipo_origen: str | None,
        fecha_corte: date | None,
    ) -> AppResult[dict[str, Any]]:
        corte = fecha_corte if fecha_corte is not None else date.today()
        return AppResult.ok(
            self.repository.get_deuda_consolidado(
                tipo_origen=tipo_origen,
                fecha_corte=corte,
            )
        )
