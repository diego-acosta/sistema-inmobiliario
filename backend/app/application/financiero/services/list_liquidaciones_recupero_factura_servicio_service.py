from __future__ import annotations

from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def factura_servicio_exists(self, id_factura_servicio: int) -> bool: ...

    def list_liquidaciones_recupero_by_factura_servicio(
        self, id_factura_servicio: int
    ) -> list[dict[str, Any]]: ...


class ListLiquidacionesRecuperoFacturaServicioService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(self, id_factura_servicio: int) -> AppResult[list[dict[str, Any]]]:
        if not self.repository.factura_servicio_exists(id_factura_servicio):
            return AppResult.fail("FACTURA_SERVICIO_NOT_FOUND")
        liquidaciones = self.repository.list_liquidaciones_recupero_by_factura_servicio(
            id_factura_servicio
        )
        return AppResult.ok(liquidaciones)
