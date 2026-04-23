from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.inmuebles.commands.delete_inmueble import DeleteInmuebleCommand


@dataclass(slots=True)
class InmuebleDeletePayload:
    id_inmueble: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def get_inmueble_for_update(self, id_inmueble: int) -> dict[str, Any] | None:
        ...

    def delete_inmueble(self, payload: InmuebleDeletePayload) -> Any | None:
        ...


class DeleteInmuebleService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, command: DeleteInmuebleCommand) -> AppResult[dict[str, Any]]:
        inmueble = self.repository.get_inmueble_for_update(command.id_inmueble)
        if inmueble is None:
            return AppResult.fail("NOT_FOUND_INMUEBLE")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != inmueble["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = InmuebleDeletePayload(
            id_inmueble=command.id_inmueble,
            version_registro_actual=inmueble["version_registro"],
            version_registro_nueva=inmueble["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_inmueble(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_inmueble = (
            deleted["id_inmueble"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_inmueble")
        )

        return AppResult.ok(
            {
                "id_inmueble": id_inmueble,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
