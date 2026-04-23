from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.personas.commands.update_relacion_persona_rol import (
    UpdateRelacionPersonaRolCommand,
)


@dataclass(slots=True)
class RelacionPersonaRolUpdatePayload:
    id_relacion_persona_rol: int
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    fecha_desde: date
    fecha_hasta: date | None
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class PersonaRepository(Protocol):
    def get_relacion_persona_rol_for_update(
        self, id_relacion_persona_rol: int
    ) -> dict[str, Any] | None:
        ...

    def persona_exists(self, id_persona: int) -> bool:
        ...

    def get_rol_participacion(
        self, id_rol_participacion: int
    ) -> dict[str, Any] | None:
        ...

    def relacion_objetivo_exists(self, tipo_relacion: str, id_relacion: int) -> bool:
        ...

    def update_relacion_persona_rol(
        self, payload: RelacionPersonaRolUpdatePayload
    ) -> Any | None:
        ...


class UpdateRelacionPersonaRolService:
    TIPOS_RELACION_PERMITIDOS = {
        "venta",
        "contrato_alquiler",
        "cesion",
        "escrituracion",
        "reserva_venta",
        "reserva_locativa",
    }

    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self, command: UpdateRelacionPersonaRolCommand
    ) -> AppResult[dict[str, Any]]:
        relacion = self.repository.get_relacion_persona_rol_for_update(
            command.id_relacion_persona_rol
        )
        if relacion is None:
            return AppResult.fail("NOT_FOUND_RELACION_PERSONA_ROL")

        if not self.repository.persona_exists(command.id_persona):
            return AppResult.fail("NOT_FOUND_PERSONA")

        rol = self.repository.get_rol_participacion(command.id_rol_participacion)
        if rol is None:
            return AppResult.fail("NOT_FOUND_ROL_PARTICIPACION")

        if rol["estado_rol"] != "ACTIVO":
            return AppResult.fail("ROL_PARTICIPACION_INACTIVO")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != relacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        if not command.tipo_relacion.strip():
            return AppResult.fail("tipo_relacion es requerido.")

        if command.tipo_relacion not in self.TIPOS_RELACION_PERMITIDOS:
            return AppResult.fail("tipo_relacion no permitido.")

        if command.id_relacion <= 0:
            return AppResult.fail("id_relacion debe ser mayor a 0.")

        if not self.repository.relacion_objetivo_exists(
            command.tipo_relacion, command.id_relacion
        ):
            return AppResult.fail("La relacion indicada no existe.")

        if command.fecha_hasta and command.fecha_hasta < command.fecha_desde:
            return AppResult.fail("fecha_hasta no puede ser anterior a fecha_desde.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = RelacionPersonaRolUpdatePayload(
            id_relacion_persona_rol=command.id_relacion_persona_rol,
            id_persona=command.id_persona,
            id_rol_participacion=command.id_rol_participacion,
            tipo_relacion=command.tipo_relacion,
            id_relacion=command.id_relacion,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            observaciones=command.observaciones,
            version_registro_actual=relacion["version_registro"],
            version_registro_nueva=relacion["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_relacion_persona_rol(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_relacion_persona_rol = (
            updated["id_relacion_persona_rol"]
            if isinstance(updated, dict)
            else getattr(updated, "id_relacion_persona_rol")
        )

        return AppResult.ok(
            {
                "id_relacion_persona_rol": id_relacion_persona_rol,
                "id_persona": payload.id_persona,
                "id_rol_participacion": payload.id_rol_participacion,
                "tipo_relacion": payload.tipo_relacion,
                "id_relacion": payload.id_relacion,
                "version_registro": payload.version_registro_nueva,
                "fecha_desde": payload.fecha_desde,
                "fecha_hasta": payload.fecha_hasta,
            }
        )
