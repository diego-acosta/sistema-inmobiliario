from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_inmuebles(self) -> list[dict[str, Any]]:
        ...


class GetInmueblesService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self) -> AppResult[list[dict[str, Any]]]:
        inmuebles = self.repository.get_inmuebles()
        return AppResult.ok(inmuebles)
