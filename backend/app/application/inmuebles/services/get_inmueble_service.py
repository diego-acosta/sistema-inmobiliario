from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_inmueble(self, id_inmueble: int) -> dict[str, Any] | None:
        ...


class GetInmuebleService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, id_inmueble: int) -> AppResult[dict[str, Any]]:
        inmueble = self.repository.get_inmueble(id_inmueble)
        if inmueble is None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(inmueble)
