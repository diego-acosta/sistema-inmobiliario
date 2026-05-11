from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_unidad_funcional_detalle_integral(
        self, id_unidad_funcional: int
    ) -> dict[str, Any] | None:
        ...


class GetUnidadFuncionalDetalleIntegralService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_unidad_funcional: int) -> AppResult[dict[str, Any]]:
        detalle = self.repository.get_unidad_funcional_detalle_integral(
            id_unidad_funcional
        )
        if detalle is None:
            return AppResult.fail("NOT_FOUND")
        return AppResult.ok(detalle)
