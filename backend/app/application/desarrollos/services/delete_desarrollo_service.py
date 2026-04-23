from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.desarrollos.commands.delete_desarrollo import (
    DeleteDesarrolloCommand,
)


@dataclass(slots=True)
class DesarrolloDeletePayload:
    id_desarrollo: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class DesarrolloRepository(Protocol):
    def get_desarrollo_for_update(self, id_desarrollo: int) -> dict[str, Any] | None:
        ...

    def delete_desarrollo(self, payload: DesarrolloDeletePayload) -> Any | None:
        ...


class DeleteDesarrolloService:
    def __init__(self, repository: DesarrolloRepository) -> None:
        self.repository = repository

    def execute(self, command: DeleteDesarrolloCommand) -> AppResult[dict[str, Any]]:
        desarrollo = self.repository.get_desarrollo_for_update(command.id_desarrollo)
        if desarrollo is None:
            return AppResult.fail("NOT_FOUND_DESARROLLO")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != desarrollo["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = DesarrolloDeletePayload(
            id_desarrollo=command.id_desarrollo,
            version_registro_actual=desarrollo["version_registro"],
            version_registro_nueva=desarrollo["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_desarrollo(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_desarrollo = (
            deleted["id_desarrollo"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_desarrollo")
        )

        return AppResult.ok(
            {
                "id_desarrollo": id_desarrollo,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
