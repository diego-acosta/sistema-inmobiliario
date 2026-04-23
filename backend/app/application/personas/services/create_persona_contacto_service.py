from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.personas.commands.create_persona_contacto import (
    CreatePersonaContactoCommand,
)


@dataclass(slots=True)
class PersonaContactoCreatePayload:
    id_persona: int
    tipo_contacto: str | None
    valor_contacto: str
    es_principal: bool
    fecha_desde: date | None
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

    def create_persona_contacto(self, payload: PersonaContactoCreatePayload) -> Any:
        ...


class CreatePersonaContactoService:
    def __init__(self, repository: PersonaRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreatePersonaContactoCommand
    ) -> AppResult[dict[str, Any]]:
        if not self.repository.persona_exists(command.id_persona):
            return AppResult.fail("La persona indicada no existe.")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        if not command.valor_contacto.strip():
            return AppResult.fail("valor_contacto es requerido.")

        if command.fecha_desde and command.fecha_hasta:
            if command.fecha_hasta < command.fecha_desde:
                return AppResult.fail(
                    "fecha_hasta no puede ser anterior a fecha_desde."
                )

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaContactoCreatePayload(
            id_persona=command.id_persona,
            tipo_contacto=command.tipo_contacto,
            valor_contacto=command.valor_contacto,
            es_principal=command.es_principal,
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

        created = self.repository.create_persona_contacto(payload)

        id_persona_contacto = (
            created["id_persona_contacto"]
            if isinstance(created, dict)
            else getattr(created, "id_persona_contacto")
        )

        return AppResult.ok(
            {
                "id_persona_contacto": id_persona_contacto,
                "id_persona": payload.id_persona,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "tipo_contacto": payload.tipo_contacto,
                "valor_contacto": payload.valor_contacto,
                "es_principal": payload.es_principal,
            }
        )
