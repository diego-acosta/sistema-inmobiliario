from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.delete_persona import DeletePersonaCommand


@dataclass(slots=True)
class PersonaDeletePayload:
    id_persona: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_persona_for_update(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def delete_persona(self, payload: PersonaDeletePayload) -> Any | None:
        ...


class DeletePersonaService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(self, command: DeletePersonaCommand) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona_for_update(command.id_persona)
        if persona is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != persona["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaDeletePayload(
            id_persona=command.id_persona,
            version_registro_actual=persona["version_registro"],
            version_registro_nueva=persona["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_persona(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_persona = (
            deleted["id_persona"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_persona")
        )

        return AppResult.ok(
            {
                "id_persona": id_persona,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
