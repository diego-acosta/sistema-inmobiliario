from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.delete_persona_relacion import (
    DeletePersonaRelacionCommand,
)


@dataclass(slots=True)
class PersonaRelacionDeletePayload:
    id_persona_relacion: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_persona(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def get_persona_relacion_for_update(
        self, id_persona_relacion: int
    ) -> dict[str, Any] | None:
        ...

    def delete_persona_relacion(
        self, payload: PersonaRelacionDeletePayload
    ) -> Any | None:
        ...


class DeletePersonaRelacionService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: DeletePersonaRelacionCommand
    ) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona(command.id_persona_origen)
        if persona is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        relacion = self.repository.get_persona_relacion_for_update(
            command.id_persona_relacion
        )
        if relacion is None:
            return AppResult.fail("NOT_FOUND_RELACION")

        if relacion["id_persona_origen"] != command.id_persona_origen:
            return AppResult.fail("NOT_FOUND_RELACION")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != relacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaRelacionDeletePayload(
            id_persona_relacion=command.id_persona_relacion,
            version_registro_actual=relacion["version_registro"],
            version_registro_nueva=relacion["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_persona_relacion(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_persona_relacion = (
            deleted["id_persona_relacion"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_persona_relacion")
        )

        return AppResult.ok(
            {
                "id_persona_relacion": id_persona_relacion,
                "id_persona_origen": command.id_persona_origen,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
