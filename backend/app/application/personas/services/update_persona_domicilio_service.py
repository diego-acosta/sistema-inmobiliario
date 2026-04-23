from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.update_persona_domicilio import (
    UpdatePersonaDomicilioCommand,
)


@dataclass(slots=True)
class PersonaDomicilioUpdatePayload:
    id_persona_domicilio: int
    tipo_domicilio: str | None
    direccion: str | None
    localidad: str | None
    provincia: str | None
    pais: str | None
    codigo_postal: str | None
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

    def get_persona_domicilio_for_update(
        self, id_persona_domicilio: int
    ) -> dict[str, Any] | None:
        ...

    def update_persona_domicilio(
        self, payload: PersonaDomicilioUpdatePayload
    ) -> Any | None:
        ...


class UpdatePersonaDomicilioService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: UpdatePersonaDomicilioCommand
    ) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona(command.id_persona)
        if persona is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        domicilio = self.repository.get_persona_domicilio_for_update(
            command.id_persona_domicilio
        )
        if domicilio is None:
            return AppResult.fail("NOT_FOUND_DOMICILIO")

        if domicilio["id_persona"] != command.id_persona:
            return AppResult.fail("NOT_FOUND_DOMICILIO")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != domicilio["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        if command.fecha_desde and command.fecha_hasta:
            if command.fecha_hasta < command.fecha_desde:
                return AppResult.fail(
                    "fecha_hasta no puede ser anterior a fecha_desde."
                )

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaDomicilioUpdatePayload(
            id_persona_domicilio=command.id_persona_domicilio,
            tipo_domicilio=command.tipo_domicilio,
            direccion=command.direccion,
            localidad=command.localidad,
            provincia=command.provincia,
            pais=command.pais,
            codigo_postal=command.codigo_postal,
            es_principal=command.es_principal,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            observaciones=command.observaciones,
            version_registro_actual=domicilio["version_registro"],
            version_registro_nueva=domicilio["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_persona_domicilio(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_persona_domicilio = (
            updated["id_persona_domicilio"]
            if isinstance(updated, dict)
            else getattr(updated, "id_persona_domicilio")
        )

        return AppResult.ok(
            {
                "id_persona_domicilio": id_persona_domicilio,
                "id_persona": command.id_persona,
                "version_registro": payload.version_registro_nueva,
                "tipo_domicilio": payload.tipo_domicilio,
                "direccion": payload.direccion,
                "localidad": payload.localidad,
                "provincia": payload.provincia,
                "pais": payload.pais,
                "codigo_postal": payload.codigo_postal,
                "es_principal": payload.es_principal,
            }
        )
