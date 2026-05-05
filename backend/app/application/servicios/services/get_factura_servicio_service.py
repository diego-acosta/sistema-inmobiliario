from typing import Any, Protocol

from app.application.common.results import AppResult


class FacturaServicioRepository(Protocol):
    def get_factura_servicio(self, id_factura_servicio: int) -> dict[str, Any] | None:
        ...


class GetFacturaServicioService:
    def __init__(self, repository: FacturaServicioRepository) -> None:
        self.repository = repository

    def execute(self, id_factura_servicio: int) -> AppResult[dict[str, Any]]:
        factura = self.repository.get_factura_servicio(id_factura_servicio)
        if factura is None:
            return AppResult.fail("NOT_FOUND_FACTURA_SERVICIO")
        return AppResult.ok(factura)
