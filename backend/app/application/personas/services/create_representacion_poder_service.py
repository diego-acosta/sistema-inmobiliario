from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.personas.commands.create_representacion_poder import (
    CreateRepresentacionPoderCommand,
)


@dataclass(slots=True)
class RepresentacionPoderCreatePayload:
    id_persona_representado: int
    id_persona_representante: int
    tipo_poder: str
    estado_representacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None
    descripcion: str | None
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

    def create_representacion_poder(
        self, payload: RepresentacionPoderCreatePayload
    ) -> Any:
        ...


class CreateRepresentacionPoderService:
    def __init__(self, repository: PersonaRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateRepresentacionPoderCommand
    ) -> AppResult[dict[str, Any]]:
        if not self.repository.persona_exists(command.id_persona_representado):
            return AppResult.fail("La persona representada indicada no existe.")

        if not self.repository.persona_exists(command.id_persona_representante):
            return AppResult.fail("La persona representante indicada no existe.")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        if not command.tipo_poder.strip():
            return AppResult.fail("tipo_poder es requerido.")

        if not command.estado_representacion.strip():
            return AppResult.fail("estado_representacion es requerido.")

        if command.fecha_desde and command.fecha_hasta:
            if command.fecha_hasta < command.fecha_desde:
                return AppResult.fail(
                    "fecha_hasta no puede ser anterior a fecha_desde."
                )

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = RepresentacionPoderCreatePayload(
            id_persona_representado=command.id_persona_representado,
            id_persona_representante=command.id_persona_representante,
            tipo_poder=command.tipo_poder,
            estado_representacion=command.estado_representacion,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            descripcion=command.descripcion,
            uid_global=uid_global,
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        created = self.repository.create_representacion_poder(payload)

        id_representacion_poder = (
            created["id_representacion_poder"]
            if isinstance(created, dict)
            else getattr(created, "id_representacion_poder")
        )

        return AppResult.ok(
            {
                "id_representacion_poder": id_representacion_poder,
                "id_persona_representado": payload.id_persona_representado,
                "id_persona_representante": payload.id_persona_representante,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "tipo_poder": payload.tipo_poder,
                "estado_representacion": payload.estado_representacion,
            }
        )
