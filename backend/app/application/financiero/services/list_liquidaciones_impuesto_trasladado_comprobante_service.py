from __future__ import annotations

from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def get_comprobante_impuesto(
        self, id_comprobante_impuesto: int
    ) -> dict[str, Any] | None: ...

    def list_liquidaciones_impuesto_trasladado_by_comprobante(
        self, id_comprobante_impuesto: int
    ) -> list[dict[str, Any]]: ...


class ListLiquidacionesImpuestoTrasladadoComprobanteService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(self, id_comprobante_impuesto: int) -> AppResult[list[dict[str, Any]]]:
        if self.repository.get_comprobante_impuesto(id_comprobante_impuesto) is None:
            return AppResult.fail("COMPROBANTE_IMPUESTO_NOT_FOUND")
        liquidaciones = (
            self.repository.list_liquidaciones_impuesto_trasladado_by_comprobante(
                id_comprobante_impuesto
            )
        )
        return AppResult.ok(liquidaciones)
