from __future__ import annotations

from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def get_liquidacion_recupero_detalle(
        self, id_liquidacion_recupero: int
    ) -> dict[str, Any] | None: ...


class GetLiquidacionRecuperoService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(self, id_liquidacion_recupero: int) -> AppResult[dict[str, Any]]:
        liquidacion = self.repository.get_liquidacion_recupero_detalle(
            id_liquidacion_recupero
        )
        if liquidacion is None:
            return AppResult.fail("LIQUIDACION_RECUPERO_NOT_FOUND")
        return AppResult.ok(liquidacion)
