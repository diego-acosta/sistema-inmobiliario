from typing import Any, Protocol

from app.application.common.results import AppResult


class EdificacionRepository(Protocol):
    def get_edificaciones(self) -> list[dict[str, Any]]:
        ...


class GetEdificacionesService:
    def __init__(self, repository: EdificacionRepository) -> None:
        self.repository = repository

    def execute(self) -> AppResult[list[dict[str, Any]]]:
        edificaciones = self.repository.get_edificaciones()
        return AppResult.ok(edificaciones)
