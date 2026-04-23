from typing import Any, Protocol

from app.application.common.results import AppResult


class PersonaRepository(Protocol):
    def persona_exists(self, id_persona: int) -> bool:
        ...

    def get_persona_documentos(self, id_persona: int) -> list[dict[str, Any]]:
        ...


class GetPersonaDocumentosService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(self, id_persona: int) -> AppResult[list[dict[str, Any]]]:
        if not self.repository.persona_exists(id_persona):
            return AppResult.fail("La persona indicada no existe.")

        documentos = self.repository.get_persona_documentos(id_persona)
        return AppResult.ok(documentos)
