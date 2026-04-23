from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.common.results import AppResult
from app.application.inmuebles.commands.close_ocupacion import (
    CloseOcupacionCommand,
)


@dataclass(slots=True)
class OcupacionClosePayload:
    id_ocupacion: int
    fecha_hasta: datetime
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def get_ocupacion_for_update(
        self, id_ocupacion: int
    ) -> dict[str, Any] | None:
        ...

    def close_ocupacion(
        self, payload: OcupacionClosePayload
    ) -> dict[str, Any] | None:
        ...


class CloseOcupacionService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, command: CloseOcupacionCommand) -> AppResult[dict[str, Any]]:
        ocupacion = self.repository.get_ocupacion_for_update(command.id_ocupacion)
        if ocupacion is None:
            return AppResult.fail("NOT_FOUND_OCUPACION")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != ocupacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        if ocupacion["fecha_hasta"] is not None:
            return AppResult.fail("OCUPACION_ALREADY_CLOSED")

        if command.fecha_hasta < ocupacion["fecha_desde"]:
            return AppResult.fail("INVALID_DATE_RANGE")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = OcupacionClosePayload(
            id_ocupacion=command.id_ocupacion,
            fecha_hasta=command.fecha_hasta,
            version_registro_actual=ocupacion["version_registro"],
            version_registro_nueva=ocupacion["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        try:
            updated = self.repository.close_ocupacion(payload)
        except (IntegrityError, DBAPIError) as exc:
            error_message = str(getattr(exc, "orig", exc))
            if "chk_ocupacion_vigencia" in error_message:
                return AppResult.fail("INVALID_DATE_RANGE")
            if "Solapamiento de vigencia en ocupacion" in error_message:
                return AppResult.fail("OCUPACION_OVERLAP")
            if "chk_ocupacion_xor" in error_message:
                return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")
            raise

        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        return AppResult.ok(
            {
                "id_ocupacion": updated["id_ocupacion"],
                "version_registro": updated["version_registro"],
                "id_inmueble": updated["id_inmueble"],
                "id_unidad_funcional": updated["id_unidad_funcional"],
                "tipo_ocupacion": updated["tipo_ocupacion"],
                "fecha_desde": updated["fecha_desde"],
                "fecha_hasta": updated["fecha_hasta"],
                "descripcion": updated["descripcion"],
                "observaciones": updated["observaciones"],
            }
        )
