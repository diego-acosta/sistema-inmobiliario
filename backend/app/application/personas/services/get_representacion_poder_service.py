from typing import Any, Protocol

from app.application.common.results import AppResult


class PersonaRepository(Protocol):
    def persona_exists(self, id_persona: int) -> bool:
        ...

    def get_representaciones_poder(
        self, id_persona_representado: int
    ) -> list[dict[str, Any]]:
        ...


class GetRepresentacionPoderService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(self, id_persona: int) -> AppResult[list[dict[str, Any]]]:
        if not self.repository.persona_exists(id_persona):
            return AppResult.fail("La persona indicada no existe.")

        representaciones = self.repository.get_representaciones_poder(id_persona)
        return AppResult.ok(representaciones)
