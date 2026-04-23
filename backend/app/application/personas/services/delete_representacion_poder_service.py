from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.delete_representacion_poder import (
    DeleteRepresentacionPoderCommand,
)


@dataclass(slots=True)
class RepresentacionPoderDeletePayload:
    id_representacion_poder: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_persona(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def get_representacion_poder_for_update(
        self, id_representacion_poder: int
    ) -> dict[str, Any] | None:
        ...

    def delete_representacion_poder(
        self, payload: RepresentacionPoderDeletePayload
    ) -> Any | None:
        ...


class DeleteRepresentacionPoderService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: DeleteRepresentacionPoderCommand
    ) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona(command.id_persona_representado)
        if persona is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        representacion = self.repository.get_representacion_poder_for_update(
            command.id_representacion_poder
        )
        if representacion is None:
            return AppResult.fail("NOT_FOUND_REPRESENTACION_PODER")

        if representacion["id_persona_representado"] != command.id_persona_representado:
            return AppResult.fail("NOT_FOUND_REPRESENTACION_PODER")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != representacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = RepresentacionPoderDeletePayload(
            id_representacion_poder=command.id_representacion_poder,
            version_registro_actual=representacion["version_registro"],
            version_registro_nueva=representacion["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_representacion_poder(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_representacion_poder = (
            deleted["id_representacion_poder"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_representacion_poder")
        )

        return AppResult.ok(
            {
                "id_representacion_poder": id_representacion_poder,
                "id_persona_representado": command.id_persona_representado,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
