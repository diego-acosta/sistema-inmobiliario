from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.desarrollos.commands.update_desarrollo import (
    UpdateDesarrolloCommand,
)


@dataclass(slots=True)
class DesarrolloUpdatePayload:
    id_desarrollo: int
    codigo_desarrollo: str
    nombre_desarrollo: str
    descripcion: str | None
    estado_desarrollo: str
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class DesarrolloRepository(Protocol):
    def get_desarrollo_for_update(self, id_desarrollo: int) -> dict[str, Any] | None:
        ...

    def update_desarrollo(self, payload: DesarrolloUpdatePayload) -> Any | None:
        ...


class UpdateDesarrolloService:
    def __init__(self, repository: DesarrolloRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdateDesarrolloCommand) -> AppResult[dict[str, Any]]:
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

        payload = DesarrolloUpdatePayload(
            id_desarrollo=command.id_desarrollo,
            codigo_desarrollo=command.codigo_desarrollo,
            nombre_desarrollo=command.nombre_desarrollo,
            descripcion=command.descripcion,
            estado_desarrollo=command.estado_desarrollo,
            observaciones=command.observaciones,
            version_registro_actual=desarrollo["version_registro"],
            version_registro_nueva=desarrollo["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_desarrollo(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_desarrollo = (
            updated["id_desarrollo"]
            if isinstance(updated, dict)
            else getattr(updated, "id_desarrollo")
        )

        return AppResult.ok(
            {
                "id_desarrollo": id_desarrollo,
                "version_registro": payload.version_registro_nueva,
                "codigo_desarrollo": payload.codigo_desarrollo,
                "nombre_desarrollo": payload.nombre_desarrollo,
                "descripcion": payload.descripcion,
                "estado_desarrollo": payload.estado_desarrollo,
                "observaciones": payload.observaciones,
            }
        )
