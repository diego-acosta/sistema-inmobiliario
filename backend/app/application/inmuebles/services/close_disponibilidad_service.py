from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.common.results import AppResult
from app.application.inmuebles.commands.close_disponibilidad import (
    CloseDisponibilidadCommand,
)


@dataclass(slots=True)
class DisponibilidadClosePayload:
    id_disponibilidad: int
    fecha_hasta: datetime
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

    def close_disponibilidad(
        self, payload: DisponibilidadClosePayload
    ) -> dict[str, Any] | None:
        ...


class CloseDisponibilidadService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(
        self, command: CloseDisponibilidadCommand
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

        if disponibilidad["fecha_hasta"] is not None:
            return AppResult.fail("DISPONIBILIDAD_ALREADY_CLOSED")

        if command.fecha_hasta < disponibilidad["fecha_desde"]:
            return AppResult.fail("INVALID_DATE_RANGE")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = DisponibilidadClosePayload(
            id_disponibilidad=command.id_disponibilidad,
            fecha_hasta=command.fecha_hasta,
            version_registro_actual=disponibilidad["version_registro"],
            version_registro_nueva=disponibilidad["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        try:
            updated = self.repository.close_disponibilidad(payload)
        except (IntegrityError, DBAPIError) as exc:
            error_message = str(getattr(exc, "orig", exc))
            if "chk_disponibilidad_vigencia" in error_message:
                return AppResult.fail("INVALID_DATE_RANGE")
            if "Solapamiento de vigencia en disponibilidad" in error_message:
                return AppResult.fail("DISPONIBILIDAD_OVERLAP")
            if "chk_disponibilidad_xor" in error_message:
                return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")
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
