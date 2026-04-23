from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.common.results import AppResult
from app.application.inmuebles.commands.delete_ocupacion import (
    DeleteOcupacionCommand,
)


@dataclass(slots=True)
class OcupacionDeletePayload:
    id_ocupacion: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def get_ocupacion_for_update(self, id_ocupacion: int) -> dict[str, Any] | None:
        ...

    def delete_ocupacion(self, payload: OcupacionDeletePayload) -> Any | None:
        ...


class DeleteOcupacionService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, command: DeleteOcupacionCommand) -> AppResult[dict[str, Any]]:
        ocupacion = self.repository.get_ocupacion_for_update(command.id_ocupacion)
        if ocupacion is None:
            return AppResult.fail("NOT_FOUND_OCUPACION")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != ocupacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = OcupacionDeletePayload(
            id_ocupacion=command.id_ocupacion,
            version_registro_actual=ocupacion["version_registro"],
            version_registro_nueva=ocupacion["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        try:
            deleted = self.repository.delete_ocupacion(payload)
        except (IntegrityError, DBAPIError) as exc:
            error_message = str(getattr(exc, "orig", exc))
            if "chk_ocupacion_vigencia" in error_message:
                return AppResult.fail("INVALID_OCUPACION_STATE")
            if "chk_ocupacion_xor" in error_message:
                return AppResult.fail("INVALID_OCUPACION_STATE")
            raise

        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_ocupacion = (
            deleted["id_ocupacion"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_ocupacion")
        )

        return AppResult.ok(
            {
                "id_ocupacion": id_ocupacion,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
