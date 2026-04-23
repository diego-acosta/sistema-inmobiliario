from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_inmueble_integracion_trazabilidad(
        self, id_inmueble: int
    ) -> list[dict[str, Any]]:
        ...


class GetInmuebleIntegracionTrazabilidadService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_inmueble: int) -> AppResult[list[dict[str, Any]]]:
        trazabilidad = self.repository.get_inmueble_integracion_trazabilidad(
            id_inmueble
        )
        return AppResult.ok(trazabilidad)
