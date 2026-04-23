from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.update_persona_relacion import (
    UpdatePersonaRelacionCommand,
)


@dataclass(slots=True)
class PersonaRelacionUpdatePayload:
    id_persona_relacion: int
    id_persona_destino: int
    tipo_relacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_persona(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def get_persona_relacion_for_update(
        self, id_persona_relacion: int
    ) -> dict[str, Any] | None:
        ...

    def update_persona_relacion(
        self, payload: PersonaRelacionUpdatePayload
    ) -> Any | None:
        ...


class UpdatePersonaRelacionService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: UpdatePersonaRelacionCommand
    ) -> AppResult[dict[str, Any]]:
        persona_origen = self.repository.get_persona(command.id_persona_origen)
        if persona_origen is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        relacion = self.repository.get_persona_relacion_for_update(
            command.id_persona_relacion
        )
        if relacion is None:
            return AppResult.fail("NOT_FOUND_RELACION")

        if relacion["id_persona_origen"] != command.id_persona_origen:
            return AppResult.fail("NOT_FOUND_RELACION")

        persona_destino = self.repository.get_persona(command.id_persona_destino)
        if persona_destino is None:
            return AppResult.fail("NOT_FOUND_PERSONA_DESTINO")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != relacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

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

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaRelacionUpdatePayload(
            id_persona_relacion=command.id_persona_relacion,
            id_persona_destino=command.id_persona_destino,
            tipo_relacion=command.tipo_relacion,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            observaciones=command.observaciones,
            version_registro_actual=relacion["version_registro"],
            version_registro_nueva=relacion["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_persona_relacion(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_persona_relacion = (
            updated["id_persona_relacion"]
            if isinstance(updated, dict)
            else getattr(updated, "id_persona_relacion")
        )

        return AppResult.ok(
            {
                "id_persona_relacion": id_persona_relacion,
                "id_persona_origen": command.id_persona_origen,
                "id_persona_destino": payload.id_persona_destino,
                "version_registro": payload.version_registro_nueva,
                "tipo_relacion": payload.tipo_relacion,
                "fecha_desde": payload.fecha_desde,
                "fecha_hasta": payload.fecha_hasta,
            }
        )
