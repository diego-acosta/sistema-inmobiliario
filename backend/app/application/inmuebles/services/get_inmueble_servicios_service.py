from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_inmueble_servicios(self, id_inmueble: int) -> list[dict[str, Any]]:
        ...


class GetInmuebleServiciosService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_inmueble: int) -> AppResult[list[dict[str, Any]]]:
        servicios = self.repository.get_inmueble_servicios(id_inmueble)
        return AppResult.ok(servicios)
