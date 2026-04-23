from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.personas.commands.create_persona import CreatePersonaCommand


@dataclass(slots=True)
class PersonaCreatePayload:
    tipo_persona: str
    nombre: str | None
    apellido: str | None
    razon_social: str | None
    fecha_nacimiento: Any
    estado_persona: str
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
    def create_persona(self, payload: PersonaCreatePayload) -> Any:
        ...


class CreatePersonaService:
    def __init__(self, repository: PersonaRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: CreatePersonaCommand) -> AppResult[dict[str, Any]]:
        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaCreatePayload(
            tipo_persona=command.tipo_persona,
            nombre=command.nombre,
            apellido=command.apellido,
            razon_social=command.razon_social,
            fecha_nacimiento=command.fecha_nacimiento,
            estado_persona=command.estado_persona,
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

        created = self.repository.create_persona(payload)

        id_persona = (
            created["id_persona"]
            if isinstance(created, dict)
            else getattr(created, "id_persona")
        )

        return AppResult.ok(
            {
                "id_persona": id_persona,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "estado_persona": payload.estado_persona,
            }
        )
