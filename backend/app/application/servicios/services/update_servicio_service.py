from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.servicios.commands.update_servicio import UpdateServicioCommand


@dataclass(slots=True)
class ServicioUpdatePayload:
    id_servicio: int
    codigo_servicio: str
    nombre_servicio: str
    descripcion: str | None
    estado_servicio: str
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class ServicioRepository(Protocol):
    def get_servicio_for_update(self, id_servicio: int) -> dict[str, Any] | None:
        ...

    def update_servicio(self, payload: ServicioUpdatePayload) -> Any | None:
        ...


class UpdateServicioService:
    def __init__(self, repository: ServicioRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdateServicioCommand) -> AppResult[dict[str, Any]]:
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

        payload = ServicioUpdatePayload(
            id_servicio=command.id_servicio,
            codigo_servicio=command.codigo_servicio,
            nombre_servicio=command.nombre_servicio,
            descripcion=command.descripcion,
            estado_servicio=command.estado_servicio,
            version_registro_actual=servicio["version_registro"],
            version_registro_nueva=servicio["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_servicio(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_servicio = (
            updated["id_servicio"]
            if isinstance(updated, dict)
            else getattr(updated, "id_servicio")
        )

        return AppResult.ok(
            {
                "id_servicio": id_servicio,
                "version_registro": payload.version_registro_nueva,
                "codigo_servicio": payload.codigo_servicio,
                "nombre_servicio": payload.nombre_servicio,
                "descripcion": payload.descripcion,
                "estado_servicio": payload.estado_servicio,
            }
        )
