from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.personas.commands.create_persona_documento import (
    CreatePersonaDocumentoCommand,
)


@dataclass(slots=True)
class PersonaDocumentoCreatePayload:
    id_persona: int
    tipo_documento: str
    numero_documento: str
    pais_emision: str | None
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

    def create_persona_documento(self, payload: PersonaDocumentoCreatePayload) -> Any:
        ...


class CreatePersonaDocumentoService:
    def __init__(self, repository: PersonaRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreatePersonaDocumentoCommand
    ) -> AppResult[dict[str, Any]]:
        if not self.repository.persona_exists(command.id_persona):
            return AppResult.fail("La persona indicada no existe.")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaDocumentoCreatePayload(
            id_persona=command.id_persona,
            tipo_documento=command.tipo_documento,
            numero_documento=command.numero_documento,
            pais_emision=command.pais_emision,
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

        created = self.repository.create_persona_documento(payload)

        id_persona_documento = (
            created["id_persona_documento"]
            if isinstance(created, dict)
            else getattr(created, "id_persona_documento")
        )

        return AppResult.ok(
            {
                "id_persona_documento": id_persona_documento,
                "id_persona": payload.id_persona,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "tipo_documento": payload.tipo_documento,
                "numero_documento": payload.numero_documento,
                "es_principal": payload.es_principal,
            }
        )
