from dataclasses import dataclass
from datetime import UTC, datetime, date
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.update_persona import UpdatePersonaCommand


@dataclass(slots=True)
class PersonaUpdatePayload:
    id_persona: int
    tipo_persona: str
    nombre: str | None
    apellido: str | None
    razon_social: str | None
    fecha_nacimiento: date | None
    estado_persona: str
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_persona_for_update(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def update_persona(self, payload: PersonaUpdatePayload) -> Any | None:
        ...


class UpdatePersonaService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdatePersonaCommand) -> AppResult[dict[str, Any]]:
        persona = self.repository.get_persona_for_update(command.id_persona)
        if persona is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != persona["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = PersonaUpdatePayload(
            id_persona=command.id_persona,
            tipo_persona=command.tipo_persona,
            nombre=command.nombre,
            apellido=command.apellido,
            razon_social=command.razon_social,
            fecha_nacimiento=command.fecha_nacimiento,
            estado_persona=command.estado_persona,
            observaciones=command.observaciones,
            version_registro_actual=persona["version_registro"],
            version_registro_nueva=persona["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_persona(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_persona = (
            updated["id_persona"]
            if isinstance(updated, dict)
            else getattr(updated, "id_persona")
        )

        return AppResult.ok(
            {
                "id_persona": id_persona,
                "version_registro": payload.version_registro_nueva,
                "tipo_persona": payload.tipo_persona,
                "nombre": payload.nombre,
                "apellido": payload.apellido,
                "razon_social": payload.razon_social,
                "estado_persona": payload.estado_persona,
            }
        )
