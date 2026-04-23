from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.delete_persona_documento import (
    DeletePersonaDocumentoCommand,
)


@dataclass(slots=True)
class PersonaDocumentoDeletePayload:
    id_persona_documento: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_persona(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def get_persona_documento_for_update(
        self, id_persona_documento: int
    ) -> dict[str, Any] | None:
        ...

    def delete_persona_documento(
        self, payload: PersonaDocumentoDeletePayload
    ) -> Any | None:
        ...


class DeletePersonaDocumentoService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: DeletePersonaDocumentoCommand
    ) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona(command.id_persona)
        if persona is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        documento = self.repository.get_persona_documento_for_update(
            command.id_persona_documento
        )
        if documento is None:
            return AppResult.fail("NOT_FOUND_DOCUMENTO")

        if documento["id_persona"] != command.id_persona:
            return AppResult.fail("NOT_FOUND_DOCUMENTO")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != documento["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaDocumentoDeletePayload(
            id_persona_documento=command.id_persona_documento,
            version_registro_actual=documento["version_registro"],
            version_registro_nueva=documento["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_persona_documento(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_persona_documento = (
            deleted["id_persona_documento"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_persona_documento")
        )

        return AppResult.ok(
            {
                "id_persona_documento": id_persona_documento,
                "id_persona": command.id_persona,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
