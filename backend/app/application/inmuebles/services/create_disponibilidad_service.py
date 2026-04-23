from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.inmuebles.commands.create_disponibilidad import (
    CreateDisponibilidadCommand,
)


@dataclass(slots=True)
class DisponibilidadCreatePayload:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    motivo: str | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def create_disponibilidad(self, payload: DisponibilidadCreatePayload) -> Any:
        ...


class CreateDisponibilidadService:
    def __init__(self, repository: InmuebleRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateDisponibilidadCommand
    ) -> AppResult[dict[str, Any]]:
        if (command.id_inmueble is None) == (command.id_unidad_funcional is None):
            return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")

        if (
            command.fecha_hasta is not None
            and command.fecha_hasta < command.fecha_desde
        ):
            return AppResult.fail("INVALID_DATE_RANGE")

        if (
            command.id_inmueble is not None
            and not self.repository.inmueble_exists(command.id_inmueble)
        ):
            return AppResult.fail("NOT_FOUND_INMUEBLE")

        if (
            command.id_unidad_funcional is not None
            and not self.repository.unidad_funcional_exists(
                command.id_unidad_funcional
            )
        ):
            return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = DisponibilidadCreatePayload(
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            estado_disponibilidad=command.estado_disponibilidad,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            motivo=command.motivo,
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

        created = self.repository.create_disponibilidad(payload)

        id_disponibilidad = (
            created["id_disponibilidad"]
            if isinstance(created, dict)
            else getattr(created, "id_disponibilidad")
        )

        return AppResult.ok(
            {
                "id_disponibilidad": id_disponibilidad,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "id_inmueble": payload.id_inmueble,
                "id_unidad_funcional": payload.id_unidad_funcional,
                "estado_disponibilidad": payload.estado_disponibilidad,
                "fecha_desde": payload.fecha_desde,
                "fecha_hasta": payload.fecha_hasta,
                "motivo": payload.motivo,
                "observaciones": payload.observaciones,
            }
        )
