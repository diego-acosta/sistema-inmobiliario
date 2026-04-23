from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_unidad_funcional_servicios(
        self, id_unidad_funcional: int
    ) -> list[dict[str, Any]]:
        ...


class GetUnidadFuncionalServiciosService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_unidad_funcional: int) -> AppResult[list[dict[str, Any]]]:
        servicios = self.repository.get_unidad_funcional_servicios(id_unidad_funcional)
        return AppResult.ok(servicios)
