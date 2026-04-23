from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_unidad_funcional(self, id_unidad_funcional: int) -> dict[str, Any] | None:
        ...


class GetUnidadFuncionalService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_unidad_funcional: int) -> AppResult[dict[str, Any]]:
        unidad = self.repository.get_unidad_funcional(id_unidad_funcional)
        if unidad is None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(unidad)
