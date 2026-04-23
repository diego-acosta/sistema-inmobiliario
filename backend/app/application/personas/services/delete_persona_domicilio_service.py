from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.delete_persona_domicilio import (
    DeletePersonaDomicilioCommand,
)


@dataclass(slots=True)
class PersonaDomicilioDeletePayload:
    id_persona_domicilio: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_persona(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def get_persona_domicilio_for_update(
        self, id_persona_domicilio: int
    ) -> dict[str, Any] | None:
        ...

    def delete_persona_domicilio(
        self, payload: PersonaDomicilioDeletePayload
    ) -> Any | None:
        ...


class DeletePersonaDomicilioService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: DeletePersonaDomicilioCommand
    ) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona(command.id_persona)
        if persona is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        domicilio = self.repository.get_persona_domicilio_for_update(
            command.id_persona_domicilio
        )
        if domicilio is None:
            return AppResult.fail("NOT_FOUND_DOMICILIO")

        if domicilio["id_persona"] != command.id_persona:
            return AppResult.fail("NOT_FOUND_DOMICILIO")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != domicilio["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaDomicilioDeletePayload(
            id_persona_domicilio=command.id_persona_domicilio,
            version_registro_actual=domicilio["version_registro"],
            version_registro_nueva=domicilio["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_persona_domicilio(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_persona_domicilio = (
            deleted["id_persona_domicilio"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_persona_domicilio")
        )

        return AppResult.ok(
            {
                "id_persona_domicilio": id_persona_domicilio,
                "id_persona": command.id_persona,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
