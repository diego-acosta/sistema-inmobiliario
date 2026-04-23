from typing import Any, Protocol

from app.application.common.results import AppResult


class ServicioRepository(Protocol):
    def get_servicio_inmuebles(self, id_servicio: int) -> list[dict[str, Any]]:
        ...


class GetServicioInmueblesService:
    def __init__(self, repository: ServicioRepository) -> None:
        self.repository = repository

    def execute(self, id_servicio: int) -> AppResult[list[dict[str, Any]]]:
        inmuebles = self.repository.get_servicio_inmuebles(id_servicio)
        return AppResult.ok(inmuebles)
