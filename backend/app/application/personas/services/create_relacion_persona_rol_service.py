from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.personas.commands.create_relacion_persona_rol import (
    CreateRelacionPersonaRolCommand,
)


@dataclass(slots=True)
class RelacionPersonaRolCreatePayload:
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    fecha_desde: date
    fecha_hasta: date | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def persona_exists(self, id_persona: int) -> bool:
        ...

    def rol_participacion_exists(self, id_rol_participacion: int) -> bool:
        ...

    def relacion_objetivo_exists(self, tipo_relacion: str, id_relacion: int) -> bool:
        ...

    def create_relacion_persona_rol(
        self, payload: RelacionPersonaRolCreatePayload
    ) -> Any:
        ...


class CreateRelacionPersonaRolService:
    TIPOS_RELACION_PERMITIDOS = {
        "venta",
        "contrato_alquiler",
        "cesion",
        "escrituracion",
        "reserva_venta",
        "reserva_locativa",
    }

    def __init__(self, repository: PersonaRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateRelacionPersonaRolCommand
    ) -> AppResult[dict[str, Any]]:
        if not self.repository.persona_exists(command.id_persona):
            return AppResult.fail("NOT_FOUND_PERSONA")

        if not self.repository.rol_participacion_exists(command.id_rol_participacion):
            return AppResult.fail("NOT_FOUND_ROL_PARTICIPACION")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        if not command.tipo_relacion.strip():
            return AppResult.fail("tipo_relacion es requerido.")

        if command.tipo_relacion not in self.TIPOS_RELACION_PERMITIDOS:
            return AppResult.fail("tipo_relacion no permitido.")

        if command.id_relacion <= 0:
            return AppResult.fail("id_relacion debe ser mayor a 0.")

        if not self.repository.relacion_objetivo_exists(
            command.tipo_relacion, command.id_relacion
        ):
            return AppResult.fail("La relacion indicada no existe.")

        if command.fecha_hasta and command.fecha_hasta < command.fecha_desde:
            return AppResult.fail("fecha_hasta no puede ser anterior a fecha_desde.")

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = RelacionPersonaRolCreatePayload(
            id_persona=command.id_persona,
            id_rol_participacion=command.id_rol_participacion,
            tipo_relacion=command.tipo_relacion,
            id_relacion=command.id_relacion,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
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

        created = self.repository.create_relacion_persona_rol(payload)

        id_relacion_persona_rol = (
            created["id_relacion_persona_rol"]
            if isinstance(created, dict)
            else getattr(created, "id_relacion_persona_rol")
        )

        return AppResult.ok(
            {
                "id_relacion_persona_rol": id_relacion_persona_rol,
                "id_persona": payload.id_persona,
                "id_rol_participacion": payload.id_rol_participacion,
                "tipo_relacion": payload.tipo_relacion,
                "id_relacion": payload.id_relacion,
                "version_registro": payload.version_registro,
                "fecha_desde": payload.fecha_desde,
                "fecha_hasta": payload.fecha_hasta,
            }
        )
