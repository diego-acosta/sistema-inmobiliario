from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_inmueble_ocupaciones(self, id_inmueble: int) -> list[dict[str, Any]]:
        ...


class GetInmuebleOcupacionesService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_inmueble: int) -> AppResult[list[dict[str, Any]]]:
        ocupaciones = self.repository.get_inmueble_ocupaciones(id_inmueble)
        return AppResult.ok(ocupaciones)
