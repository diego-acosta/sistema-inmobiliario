from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.update_representacion_poder import (
    UpdateRepresentacionPoderCommand,
)


@dataclass(slots=True)
class RepresentacionPoderUpdatePayload:
    id_representacion_poder: int
    id_persona_representante: int
    tipo_poder: str
    estado_representacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None
    descripcion: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_persona(self, id_persona: int) -> dict[str, Any] | None:
        ...

    def get_representacion_poder_for_update(
        self, id_representacion_poder: int
    ) -> dict[str, Any] | None:
        ...

    def update_representacion_poder(
        self, payload: RepresentacionPoderUpdatePayload
    ) -> Any | None:
        ...


class UpdateRepresentacionPoderService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: UpdateRepresentacionPoderCommand
    ) -> AppResult[dict[str, Any]]:
        persona_representado = self.repository.get_persona(command.id_persona_representado)
        if persona_representado is None:
            return AppResult.fail("NOT_FOUND_PERSONA")

        representacion = self.repository.get_representacion_poder_for_update(
            command.id_representacion_poder
        )
        if representacion is None:
            return AppResult.fail("NOT_FOUND_REPRESENTACION_PODER")

        if representacion["id_persona_representado"] != command.id_persona_representado:
            return AppResult.fail("NOT_FOUND_REPRESENTACION_PODER")

        persona_representante = self.repository.get_persona(
            command.id_persona_representante
        )
        if persona_representante is None:
            return AppResult.fail("NOT_FOUND_PERSONA_REPRESENTANTE")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != representacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

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

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = RepresentacionPoderUpdatePayload(
            id_representacion_poder=command.id_representacion_poder,
            id_persona_representante=command.id_persona_representante,
            tipo_poder=command.tipo_poder,
            estado_representacion=command.estado_representacion,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            descripcion=command.descripcion,
            version_registro_actual=representacion["version_registro"],
            version_registro_nueva=representacion["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_representacion_poder(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_representacion_poder = (
            updated["id_representacion_poder"]
            if isinstance(updated, dict)
            else getattr(updated, "id_representacion_poder")
        )

        return AppResult.ok(
            {
                "id_representacion_poder": id_representacion_poder,
                "id_persona_representado": command.id_persona_representado,
                "id_persona_representante": payload.id_persona_representante,
                "version_registro": payload.version_registro_nueva,
                "tipo_poder": payload.tipo_poder,
                "estado_representacion": payload.estado_representacion,
                "fecha_desde": payload.fecha_desde,
                "fecha_hasta": payload.fecha_hasta,
            }
        )
