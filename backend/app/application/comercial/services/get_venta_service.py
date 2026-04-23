from typing import Any, Protocol

from app.application.common.results import AppResult


class ComercialRepository(Protocol):
    def get_venta_detail(self, id_venta: int) -> dict[str, Any] | None:
        ...


class GetVentaService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(self, id_venta: int) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta_detail(id_venta)
        if venta is None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(venta)
