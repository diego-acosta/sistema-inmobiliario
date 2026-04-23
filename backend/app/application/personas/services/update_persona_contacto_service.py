from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.update_persona_contacto import (
    UpdatePersonaContactoCommand,
)


@dataclass(slots=True)
class PersonaContactoUpdatePayload:
    id_persona_contacto: int
    tipo_contacto: str | None
    valor_contacto: str
    es_principal: bool
    fecha_desde: date | None
    fecha_hasta: date | None
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_persona(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def get_persona_contacto_for_update(
        self, id_persona_contacto: int
    ) -> dict[str, Any] | None:
        ...

    def update_persona_contacto(
        self, payload: PersonaContactoUpdatePayload
    ) -> Any | None:
        ...


class UpdatePersonaContactoService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: UpdatePersonaContactoCommand
    ) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona(command.id_persona)
        if persona is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        contacto = self.repository.get_persona_contacto_for_update(
            command.id_persona_contacto
        )
        if contacto is None:
            return AppResult.fail("NOT_FOUND_CONTACTO")

        if contacto["id_persona"] != command.id_persona:
            return AppResult.fail("NOT_FOUND_CONTACTO")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != contacto["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

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

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaContactoUpdatePayload(
            id_persona_contacto=command.id_persona_contacto,
            tipo_contacto=command.tipo_contacto,
            valor_contacto=command.valor_contacto,
            es_principal=command.es_principal,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            observaciones=command.observaciones,
            version_registro_actual=contacto["version_registro"],
            version_registro_nueva=contacto["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_persona_contacto(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_persona_contacto = (
            updated["id_persona_contacto"]
            if isinstance(updated, dict)
            else getattr(updated, "id_persona_contacto")
        )

        return AppResult.ok(
            {
                "id_persona_contacto": id_persona_contacto,
                "id_persona": command.id_persona,
                "version_registro": payload.version_registro_nueva,
                "tipo_contacto": payload.tipo_contacto,
                "valor_contacto": payload.valor_contacto,
                "es_principal": payload.es_principal,
            }
        )
