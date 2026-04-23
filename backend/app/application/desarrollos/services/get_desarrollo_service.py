from typing import Any, Protocol

from app.application.common.results import AppResult


class DesarrolloRepository(Protocol):
    def get_desarrollo(self, id_desarrollo: int) -> dict[str, Any] | None:
        ...


class GetDesarrolloService:
    def __init__(self, repository: DesarrolloRepository) -> None:
        self.repository = repository

    def execute(self, id_desarrollo: int) -> AppResult[dict[str, Any]]:
        desarrollo = self.repository.get_desarrollo(id_desarrollo)
        if desarrollo is None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(desarrollo)
