from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_inmueble_detalle_integral(
        self, id_inmueble: int
    ) -> dict[str, Any] | None:
        ...


class GetInmuebleDetalleIntegralService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_inmueble: int) -> AppResult[dict[str, Any]]:
        detalle = self.repository.get_inmueble_detalle_integral(id_inmueble)
        if detalle is None:
            return AppResult.fail("NOT_FOUND")
        return AppResult.ok(detalle)
