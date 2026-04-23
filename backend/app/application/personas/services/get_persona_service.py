from typing import Any, Protocol

from app.application.common.results import AppResult


class PersonaRepository(Protocol):
    def get_persona(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def get_persona_documentos(self, id_persona: int) -> list[dict[str, Any]]:
        ...

    def get_persona_domicilios(self, id_persona: int) -> list[dict[str, Any]]:
        ...

    def get_persona_contactos(self, id_persona: int) -> list[dict[str, Any]]:
        ...

    def get_persona_relaciones(self, id_persona_origen: int) -> list[dict[str, Any]]:
        ...

    def get_representaciones_poder(
        self, id_persona_representado: int
    ) -> list[dict[str, Any]]:
        ...


class GetPersonaService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(self, id_persona: int) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona(id_persona)
        if persona is None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(
            {
                **persona,
                "documentos": self.repository.get_persona_documentos(id_persona),
                "domicilios": self.repository.get_persona_domicilios(id_persona),
                "contactos": self.repository.get_persona_contactos(id_persona),
                "relaciones": self.repository.get_persona_relaciones(id_persona),
                "representaciones_poder": self.repository.get_representaciones_poder(
                    id_persona
                ),
            }
        )
