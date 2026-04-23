from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.common.results import AppResult
from app.application.inmuebles.commands.update_ocupacion import (
    UpdateOcupacionCommand,
)


@dataclass(slots=True)
class OcupacionUpdatePayload:
    id_ocupacion: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    tipo_ocupacion: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    descripcion: str | None
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def get_ocupacion_for_update(self, id_ocupacion: int) -> dict[str, Any] | None:
        ...

    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def update_ocupacion(
        self, payload: OcupacionUpdatePayload
    ) -> dict[str, Any] | None:
        ...


class UpdateOcupacionService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdateOcupacionCommand) -> AppResult[dict[str, Any]]:
        ocupacion = self.repository.get_ocupacion_for_update(command.id_ocupacion)
        if ocupacion is None:
            return AppResult.fail("NOT_FOUND_OCUPACION")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != ocupacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        if (command.id_inmueble is None) == (command.id_unidad_funcional is None):
            return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")

        if ocupacion["fecha_hasta"] is not None:
            return AppResult.fail("OCUPACION_ALREADY_CLOSED")

        if command.fecha_hasta is not None and command.fecha_hasta < command.fecha_desde:
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

        payload = OcupacionUpdatePayload(
            id_ocupacion=command.id_ocupacion,
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            tipo_ocupacion=command.tipo_ocupacion,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            descripcion=command.descripcion,
            observaciones=command.observaciones,
            version_registro_actual=ocupacion["version_registro"],
            version_registro_nueva=ocupacion["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        try:
            updated = self.repository.update_ocupacion(payload)
        except (IntegrityError, DBAPIError) as exc:
            error_message = str(getattr(exc, "orig", exc))
            if "chk_ocupacion_vigencia" in error_message:
                return AppResult.fail("INVALID_DATE_RANGE")
            if "chk_ocupacion_xor" in error_message:
                return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")
            if "Solapamiento de vigencia en ocupacion" in error_message:
                return AppResult.fail("OCUPACION_OVERLAP")
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
