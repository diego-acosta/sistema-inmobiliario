from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.common.results import AppResult
from app.application.inmuebles.commands.delete_disponibilidad import (
    DeleteDisponibilidadCommand,
)


@dataclass(slots=True)
class DisponibilidadDeletePayload:
    id_disponibilidad: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def get_disponibilidad_for_update(
        self, id_disponibilidad: int
    ) -> dict[str, Any] | None:
        ...

    def delete_disponibilidad(
        self, payload: DisponibilidadDeletePayload
    ) -> Any | None:
        ...


class DeleteDisponibilidadService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(
        self, command: DeleteDisponibilidadCommand
    ) -> AppResult[dict[str, Any]]:
        disponibilidad = self.repository.get_disponibilidad_for_update(
            command.id_disponibilidad
        )
        if disponibilidad is None:
            return AppResult.fail("NOT_FOUND_DISPONIBILIDAD")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != disponibilidad["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = DisponibilidadDeletePayload(
            id_disponibilidad=command.id_disponibilidad,
            version_registro_actual=disponibilidad["version_registro"],
            version_registro_nueva=disponibilidad["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        try:
            deleted = self.repository.delete_disponibilidad(payload)
        except (IntegrityError, DBAPIError) as exc:
            error_message = str(getattr(exc, "orig", exc))
            if "chk_disponibilidad_vigencia" in error_message:
                return AppResult.fail("INVALID_DISPONIBILIDAD_STATE")
            if "chk_disponibilidad_xor" in error_message:
                return AppResult.fail("INVALID_DISPONIBILIDAD_STATE")
            raise

        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_disponibilidad = (
            deleted["id_disponibilidad"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_disponibilidad")
        )

        return AppResult.ok(
            {
                "id_disponibilidad": id_disponibilidad,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
