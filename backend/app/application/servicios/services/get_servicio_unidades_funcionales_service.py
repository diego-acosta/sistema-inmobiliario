from typing import Any, Protocol

from app.application.common.results import AppResult


class ServicioRepository(Protocol):
    def get_servicio_unidades_funcionales(
        self, id_servicio: int
    ) -> list[dict[str, Any]]:
        ...


class GetServicioUnidadesFuncionalesService:
    def __init__(self, repository: ServicioRepository) -> None:
        self.repository = repository

    def execute(self, id_servicio: int) -> AppResult[list[dict[str, Any]]]:
        unidades_funcionales = self.repository.get_servicio_unidades_funcionales(
            id_servicio
        )
        return AppResult.ok(unidades_funcionales)
