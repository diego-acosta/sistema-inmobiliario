from typing import Any, Protocol

from app.application.common.results import AppResult


class FacturaServicioRepository(Protocol):
    def get_facturas_servicio(self) -> list[dict[str, Any]]:
        ...


class GetFacturasServicioService:
    def __init__(self, repository: FacturaServicioRepository) -> None:
        self.repository = repository

    def execute(self) -> AppResult[list[dict[str, Any]]]:
        return AppResult.ok(self.repository.get_facturas_servicio())
