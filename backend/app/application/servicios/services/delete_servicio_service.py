from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.servicios.commands.delete_servicio import DeleteServicioCommand


@dataclass(slots=True)
class ServicioDeletePayload:
    id_servicio: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class ServicioRepository(Protocol):
    def get_servicio_for_update(self, id_servicio: int) -> dict[str, Any] | None:
        ...

    def delete_servicio(self, payload: ServicioDeletePayload) -> Any | None:
        ...


class DeleteServicioService:
    def __init__(self, repository: ServicioRepository) -> None:
        self.repository = repository

    def execute(self, command: DeleteServicioCommand) -> AppResult[dict[str, Any]]:
        servicio = self.repository.get_servicio_for_update(command.id_servicio)
        if servicio is None:
            return AppResult.fail("NOT_FOUND_SERVICIO")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != servicio["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = ServicioDeletePayload(
            id_servicio=command.id_servicio,
            version_registro_actual=servicio["version_registro"],
            version_registro_nueva=servicio["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        deleted = self.repository.delete_servicio(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_servicio = (
            deleted["id_servicio"]
            if isinstance(deleted, dict)
            else getattr(deleted, "id_servicio")
        )

        return AppResult.ok(
            {
                "id_servicio": id_servicio,
                "version_registro": payload.version_registro_nueva,
                "deleted": True,
            }
        )
