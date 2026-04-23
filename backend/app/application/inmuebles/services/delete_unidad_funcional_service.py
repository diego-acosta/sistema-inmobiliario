from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.inmuebles.commands.delete_unidad_funcional import (
    DeleteUnidadFuncionalCommand,
)


@dataclass(slots=True)
class UnidadFuncionalDeletePayload:
    id_unidad_funcional: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def get_unidad_funcional_for_update(
        self, id_unidad_funcional: int
    ) -> dict[str, Any] | None:
        ...

    def delete_unidad_funcional(self, payload: UnidadFuncionalDeletePayload) -> Any | None:
        ...


class DeleteUnidadFuncionalService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(
        self, command: DeleteUnidadFuncionalCommand
    ) -> AppResult[dict[str, Any]]:
        unidad = self.repository.get_unidad_funcional_for_update(
            command.id_unidad_funcional
        )
        if unidad is None:
            return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != unidad["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = UnidadFuncionalDeletePayload(
            id_unidad_funcional=command.id_unidad_funcional,
            version_registro_actual=unidad["version_registro"],
            version_registro_nueva=unidad["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_unidad_funcional(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_unidad_funcional = (
            deleted["id_unidad_funcional"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_unidad_funcional")
        )

        return AppResult.ok(
            {
                "id_unidad_funcional": id_unidad_funcional,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
