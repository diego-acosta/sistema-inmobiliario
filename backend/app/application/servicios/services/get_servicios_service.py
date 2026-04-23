from typing import Any, Protocol

from app.application.common.results import AppResult


class ServicioRepository(Protocol):
    def get_servicios(self) -> list[dict[str, Any]]:
        ...


class GetServiciosService:
    def __init__(self, repository: ServicioRepository) -> None:
        self.repository = repository

    def execute(self) -> AppResult[list[dict[str, Any]]]:
        servicios = self.repository.get_servicios()
        return AppResult.ok(servicios)
