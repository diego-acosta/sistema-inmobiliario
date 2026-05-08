from typing import Any, Protocol

from app.application.common.results import AppResult


class ComercialRepository(Protocol):
    def get_venta_detalle_integral(self, id_venta: int) -> dict[str, Any] | None: ...


class GetVentaDetalleIntegralService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(self, id_venta: int) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta_detalle_integral(id_venta)
        if venta is None or venta["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND")
        return AppResult.ok(venta)
