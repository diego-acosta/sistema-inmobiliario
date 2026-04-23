from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.edificaciones.commands.delete_edificacion import (
    DeleteEdificacionCommand,
)


@dataclass(slots=True)
class EdificacionDeletePayload:
    id_edificacion: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class EdificacionRepository(Protocol):
    def get_edificacion_for_update(self, id_edificacion: int) -> dict[str, Any] | None:
        ...

    def delete_edificacion(self, payload: EdificacionDeletePayload) -> Any | None:
        ...


class DeleteEdificacionService:
    def __init__(self, repository: EdificacionRepository) -> None:
        self.repository = repository

    def execute(self, command: DeleteEdificacionCommand) -> AppResult[dict[str, Any]]:
        edificacion = self.repository.get_edificacion_for_update(command.id_edificacion)
        if edificacion is None:
            return AppResult.fail("NOT_FOUND_EDIFICACION")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != edificacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = EdificacionDeletePayload(
            id_edificacion=command.id_edificacion,
            version_registro_actual=edificacion["version_registro"],
            version_registro_nueva=edificacion["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_edificacion(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_edificacion = (
            deleted["id_edificacion"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_edificacion")
        )

        return AppResult.ok(
            {
                "id_edificacion": id_edificacion,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
