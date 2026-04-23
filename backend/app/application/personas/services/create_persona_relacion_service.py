from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.personas.commands.create_persona_relacion import (
    CreatePersonaRelacionCommand,
)


@dataclass(slots=True)
class PersonaRelacionCreatePayload:
    id_persona_origen: int
    id_persona_destino: int
    tipo_relacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None
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

    def create_persona_relacion(self, payload: PersonaRelacionCreatePayload) -> Any:
        ...


class CreatePersonaRelacionService:
    def __init__(self, repository: PersonaRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreatePersonaRelacionCommand
    ) -> AppResult[dict[str, Any]]:
        if not self.repository.persona_exists(command.id_persona_origen):
            return AppResult.fail("La persona origen indicada no existe.")

        if not self.repository.persona_exists(command.id_persona_destino):
            return AppResult.fail("La persona destino indicada no existe.")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        if not command.tipo_relacion.strip():
            return AppResult.fail("tipo_relacion es requerido.")

        if command.fecha_desde and command.fecha_hasta:
            if command.fecha_hasta < command.fecha_desde:
                return AppResult.fail(
                    "fecha_hasta no puede ser anterior a fecha_desde."
                )

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaRelacionCreatePayload(
            id_persona_origen=command.id_persona_origen,
            id_persona_destino=command.id_persona_destino,
            tipo_relacion=command.tipo_relacion,
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

        created = self.repository.create_persona_relacion(payload)

        id_persona_relacion = (
            created["id_persona_relacion"]
            if isinstance(created, dict)
            else getattr(created, "id_persona_relacion")
        )

        return AppResult.ok(
            {
                "id_persona_relacion": id_persona_relacion,
                "id_persona_origen": payload.id_persona_origen,
                "id_persona_destino": payload.id_persona_destino,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "tipo_relacion": payload.tipo_relacion,
            }
        )
