from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_unidades_funcionales(self, id_inmueble: int) -> list[dict[str, Any]]:
        ...


class GetUnidadesFuncionalesService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_inmueble: int) -> AppResult[list[dict[str, Any]]]:
        unidades = self.repository.get_unidades_funcionales(id_inmueble)
        return AppResult.ok(unidades)
