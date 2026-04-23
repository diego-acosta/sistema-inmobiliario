from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.desarrollos.commands.create_desarrollo import (
    CreateDesarrolloCommand,
)


@dataclass(slots=True)
class DesarrolloCreatePayload:
    codigo_desarrollo: str
    nombre_desarrollo: str
    descripcion: str | None
    estado_desarrollo: str
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class DesarrolloRepository(Protocol):
    def create_desarrollo(self, payload: DesarrolloCreatePayload) -> Any:
        ...


class CreateDesarrolloService:
    def __init__(self, repository: DesarrolloRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: CreateDesarrolloCommand) -> AppResult[dict[str, Any]]:
        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = DesarrolloCreatePayload(
            codigo_desarrollo=command.codigo_desarrollo,
            nombre_desarrollo=command.nombre_desarrollo,
            descripcion=command.descripcion,
            estado_desarrollo=command.estado_desarrollo,
            observaciones=command.observaciones,
            uid_global=uid_global,
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        created = self.repository.create_desarrollo(payload)

        id_desarrollo = (
            created["id_desarrollo"]
            if isinstance(created, dict)
            else getattr(created, "id_desarrollo")
        )

        return AppResult.ok(
            {
                "id_desarrollo": id_desarrollo,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "estado_desarrollo": payload.estado_desarrollo,
            }
        )
