from typing import Any, Protocol

from app.application.common.results import AppResult


class PersonaRepository(Protocol):
    def get_persona_detalle_integral(self, id_persona: int) -> dict[str, Any] | None:
        ...


class GetPersonaDetalleIntegralService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(self, id_persona: int) -> AppResult[dict[str, Any]]:
        detalle = self.repository.get_persona_detalle_integral(id_persona)
        if detalle is None:
            return AppResult.fail("NOT_FOUND")
        return AppResult.ok(detalle)
