from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.update_persona_documento import (
    UpdatePersonaDocumentoCommand,
)


@dataclass(slots=True)
class PersonaDocumentoUpdatePayload:
    id_persona_documento: int
    tipo_documento: str
    numero_documento: str
    pais_emision: str | None
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

    def get_persona_documento_for_update(
        self, id_persona_documento: int
    ) -> dict[str, Any] | None:
        ...

    def update_persona_documento(
        self, payload: PersonaDocumentoUpdatePayload
    ) -> Any | None:
        ...


class UpdatePersonaDocumentoService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: UpdatePersonaDocumentoCommand
    ) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona(command.id_persona)
        if persona is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        documento = self.repository.get_persona_documento_for_update(
            command.id_persona_documento
        )
        if documento is None:
            return AppResult.fail("NOT_FOUND_DOCUMENTO")

        if documento["id_persona"] != command.id_persona:
            return AppResult.fail("NOT_FOUND_DOCUMENTO")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != documento["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        if not command.numero_documento.strip():
            return AppResult.fail("numero_documento es requerido.")

        if command.fecha_desde and command.fecha_hasta:
            if command.fecha_hasta < command.fecha_desde:
                return AppResult.fail(
                    "fecha_hasta no puede ser anterior a fecha_desde."
                )

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaDocumentoUpdatePayload(
            id_persona_documento=command.id_persona_documento,
            tipo_documento=command.tipo_documento,
            numero_documento=command.numero_documento,
            pais_emision=command.pais_emision,
            es_principal=command.es_principal,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            observaciones=command.observaciones,
            version_registro_actual=documento["version_registro"],
            version_registro_nueva=documento["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_persona_documento(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_persona_documento = (
            updated["id_persona_documento"]
            if isinstance(updated, dict)
            else getattr(updated, "id_persona_documento")
        )

        return AppResult.ok(
            {
                "id_persona_documento": id_persona_documento,
                "id_persona": command.id_persona,
                "version_registro": payload.version_registro_nueva,
                "tipo_documento": payload.tipo_documento,
                "numero_documento": payload.numero_documento,
                "pais_emision": payload.pais_emision,
                "es_principal": payload.es_principal,
            }
        )
