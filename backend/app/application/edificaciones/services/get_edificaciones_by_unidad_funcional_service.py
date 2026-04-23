from typing import Any, Protocol

from app.application.common.results import AppResult


class EdificacionRepository(Protocol):
    def get_edificaciones_by_unidad_funcional(
        self, id_unidad_funcional: int
    ) -> list[dict[str, Any]]:
        ...


class GetEdificacionesByUnidadFuncionalService:
    def __init__(self, repository: EdificacionRepository) -> None:
        self.repository = repository

    def execute(self, id_unidad_funcional: int) -> AppResult[list[dict[str, Any]]]:
        edificaciones = self.repository.get_edificaciones_by_unidad_funcional(
            id_unidad_funcional
        )
        return AppResult.ok(edificaciones)
