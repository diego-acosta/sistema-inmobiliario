from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.locativo.commands.create_solicitud_alquiler import (
    CreateSolicitudAlquilerCommand,
)


ESTADO_INICIAL_SOLICITUD = "pendiente"


@dataclass(slots=True)
class SolicitudAlquilerCreatePayload:
    codigo_solicitud: str
    fecha_solicitud: datetime
    estado_solicitud: str
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class SolicitudAlquilerTransicionPayload:
    id_solicitud_alquiler: int
    estado_solicitud: str
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class LocativoRepository(Protocol):
    def create_solicitud_alquiler(
        self, payload: SolicitudAlquilerCreatePayload
    ) -> dict[str, Any]: ...


class CreateSolicitudAlquilerService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateSolicitudAlquilerCommand
    ) -> AppResult[dict[str, Any]]:
        if not command.codigo_solicitud.strip():
            return AppResult.fail("INVALID_REQUIRED_FIELDS")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = SolicitudAlquilerCreatePayload(
            codigo_solicitud=command.codigo_solicitud,
            fecha_solicitud=command.fecha_solicitud,
            estado_solicitud=ESTADO_INICIAL_SOLICITUD,
            observaciones=command.observaciones,
            uid_global=str(self.uuid_generator()),
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        return AppResult.ok(self.repository.create_solicitud_alquiler(payload))
