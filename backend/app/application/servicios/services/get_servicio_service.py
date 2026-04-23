from typing import Any, Protocol

from app.application.common.results import AppResult


class ServicioRepository(Protocol):
    def get_servicio(self, id_servicio: int) -> dict[str, Any] | None:
        ...


class GetServicioService:
    def __init__(self, repository: ServicioRepository) -> None:
        self.repository = repository

    def execute(self, id_servicio: int) -> AppResult[dict[str, Any]]:
        servicio = self.repository.get_servicio(id_servicio)
        if servicio is None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(servicio)
