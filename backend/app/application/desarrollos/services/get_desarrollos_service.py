from typing import Any, Protocol

from app.application.common.results import AppResult


class DesarrolloRepository(Protocol):
    def get_desarrollos(self) -> list[dict[str, Any]]:
        ...


class GetDesarrollosService:
    def __init__(self, repository: DesarrolloRepository) -> None:
        self.repository = repository

    def execute(self) -> AppResult[list[dict[str, Any]]]:
        desarrollos = self.repository.get_desarrollos()
        return AppResult.ok(desarrollos)
