from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_unidad_funcional_integracion_trazabilidad(
        self, id_unidad_funcional: int
    ) -> list[dict[str, Any]]:
        ...


class GetUnidadFuncionalIntegracionTrazabilidadService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_unidad_funcional: int) -> AppResult[list[dict[str, Any]]]:
        trazabilidad = self.repository.get_unidad_funcional_integracion_trazabilidad(
            id_unidad_funcional
        )
        return AppResult.ok(trazabilidad)
