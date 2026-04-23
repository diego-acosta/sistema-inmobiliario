from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.delete_relacion_persona_rol import (
    DeleteRelacionPersonaRolCommand,
)


@dataclass(slots=True)
class RelacionPersonaRolDeletePayload:
    id_relacion_persona_rol: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_relacion_persona_rol_for_update(
        self, id_relacion_persona_rol: int
    ) -> dict[str, Any] | None:
        ...

    def delete_relacion_persona_rol(
        self, payload: RelacionPersonaRolDeletePayload
    ) -> Any | None:
        ...


class DeleteRelacionPersonaRolService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: DeleteRelacionPersonaRolCommand
    ) -> AppResult[dict[str, Any]]:
        relacion = self.repository.get_relacion_persona_rol_for_update(
            command.id_relacion_persona_rol
        )
        if relacion is None:
            return AppResult.fail("NOT_FOUND_RELACION_PERSONA_ROL")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != relacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = RelacionPersonaRolDeletePayload(
            id_relacion_persona_rol=command.id_relacion_persona_rol,
            version_registro_actual=relacion["version_registro"],
            version_registro_nueva=relacion["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_relacion_persona_rol(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_relacion_persona_rol = (
            deleted["id_relacion_persona_rol"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_relacion_persona_rol")
        )

        return AppResult.ok(
            {
                "id_relacion_persona_rol": id_relacion_persona_rol,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
