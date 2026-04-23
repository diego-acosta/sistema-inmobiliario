from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_unidades_funcionales_global(self) -> list[dict[str, Any]]:
        ...


class GetUnidadesFuncionalesGlobalService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self) -> AppResult[list[dict[str, Any]]]:
        unidades = self.repository.get_unidades_funcionales_global()
        return AppResult.ok(unidades)
