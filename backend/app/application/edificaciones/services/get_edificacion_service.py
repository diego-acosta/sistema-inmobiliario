from typing import Any, Protocol

from app.application.common.results import AppResult


class EdificacionRepository(Protocol):
    def get_edificacion(self, id_edificacion: int) -> dict[str, Any] | None:
        ...


class GetEdificacionService:
    def __init__(self, repository: EdificacionRepository) -> None:
        self.repository = repository

    def execute(self, id_edificacion: int) -> AppResult[dict[str, Any]]:
        edificacion = self.repository.get_edificacion(id_edificacion)
        if edificacion is None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(edificacion)
