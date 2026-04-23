from typing import Any, Protocol

from app.application.common.results import AppResult


class EdificacionRepository(Protocol):
    def get_edificaciones_by_inmueble(self, id_inmueble: int) -> list[dict[str, Any]]:
        ...


class GetEdificacionesByInmuebleService:
    def __init__(self, repository: EdificacionRepository) -> None:
        self.repository = repository

    def execute(self, id_inmueble: int) -> AppResult[list[dict[str, Any]]]:
        edificaciones = self.repository.get_edificaciones_by_inmueble(id_inmueble)
        return AppResult.ok(edificaciones)
