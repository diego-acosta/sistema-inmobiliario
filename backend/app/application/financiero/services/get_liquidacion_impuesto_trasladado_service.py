from __future__ import annotations

from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def get_liquidacion_impuesto_trasladado_detalle(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> dict[str, Any] | None: ...


class GetLiquidacionImpuestoTrasladadoService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> AppResult[dict[str, Any]]:
        liquidacion = self.repository.get_liquidacion_impuesto_trasladado_detalle(
            id_liquidacion_impuesto_trasladado
        )
        if liquidacion is None:
            return AppResult.fail("LIQUIDACION_IMPUESTO_TRASLADADO_NOT_FOUND")
        return AppResult.ok(liquidacion)
