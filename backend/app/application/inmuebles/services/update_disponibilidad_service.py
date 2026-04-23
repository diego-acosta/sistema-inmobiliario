from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.common.results import AppResult
from app.application.inmuebles.commands.update_disponibilidad import (
    UpdateDisponibilidadCommand,
)


@dataclass(slots=True)
class DisponibilidadUpdatePayload:
    id_disponibilidad: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    motivo: str | None
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def get_disponibilidad_for_update(
        self, id_disponibilidad: int
    ) -> dict[str, Any] | None:
        ...

    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def update_disponibilidad(
        self, payload: DisponibilidadUpdatePayload
    ) -> dict[str, Any] | None:
        ...


class UpdateDisponibilidadService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(
        self, command: UpdateDisponibilidadCommand
    ) -> AppResult[dict[str, Any]]:
        disponibilidad = self.repository.get_disponibilidad_for_update(
            command.id_disponibilidad
        )
        if disponibilidad is None:
            return AppResult.fail("NOT_FOUND_DISPONIBILIDAD")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != disponibilidad["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        if (command.id_inmueble is None) == (command.id_unidad_funcional is None):
            return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")

        if disponibilidad["fecha_hasta"] is not None:
            return AppResult.fail("DISPONIBILIDAD_ALREADY_CLOSED")

        if (
            command.fecha_hasta is not None
            and command.fecha_hasta < command.fecha_desde
        ):
            return AppResult.fail("INVALID_DATE_RANGE")

        if command.fecha_hasta is not None:
            return AppResult.fail("USE_CLOSE_ENDPOINT")

        if (
            command.id_inmueble is not None
            and not self.repository.inmueble_exists(command.id_inmueble)
        ):
            return AppResult.fail("NOT_FOUND_INMUEBLE")

        if (
            command.id_unidad_funcional is not None
            and not self.repository.unidad_funcional_exists(
                command.id_unidad_funcional
            )
        ):
            return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = DisponibilidadUpdatePayload(
            id_disponibilidad=command.id_disponibilidad,
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            estado_disponibilidad=command.estado_disponibilidad,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            motivo=command.motivo,
            observaciones=command.observaciones,
            version_registro_actual=disponibilidad["version_registro"],
            version_registro_nueva=disponibilidad["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        try:
            updated = self.repository.update_disponibilidad(payload)
        except (IntegrityError, DBAPIError) as exc:
            error_message = str(getattr(exc, "orig", exc))
            if "chk_disponibilidad_vigencia" in error_message:
                return AppResult.fail("INVALID_DATE_RANGE")
            if "chk_disponibilidad_xor" in error_message:
                return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")
            if "Solapamiento de vigencia en disponibilidad" in error_message:
                return AppResult.fail("DISPONIBILIDAD_OVERLAP")
            raise

        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        return AppResult.ok(
            {
                "id_disponibilidad": updated["id_disponibilidad"],
                "version_registro": updated["version_registro"],
                "id_inmueble": updated["id_inmueble"],
                "id_unidad_funcional": updated["id_unidad_funcional"],
                "estado_disponibilidad": updated["estado_disponibilidad"],
                "fecha_desde": updated["fecha_desde"],
                "fecha_hasta": updated["fecha_hasta"],
                "motivo": updated["motivo"],
                "observaciones": updated["observaciones"],
            }
        )
