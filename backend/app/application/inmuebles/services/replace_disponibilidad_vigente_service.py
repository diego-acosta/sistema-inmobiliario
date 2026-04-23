from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.common.results import AppResult
from app.application.inmuebles.commands.replace_disponibilidad_vigente import (
    ReplaceDisponibilidadVigenteCommand,
)


@dataclass(slots=True)
class DisponibilidadReplaceVigentePayload:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    motivo: str | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def replace_disponibilidad_vigente(
        self, payload: DisponibilidadReplaceVigentePayload
    ) -> dict[str, Any]:
        ...


class ReplaceDisponibilidadVigenteService:
    def __init__(self, repository: InmuebleRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: ReplaceDisponibilidadVigenteCommand
    ) -> AppResult[dict[str, Any]]:
        if (command.id_inmueble is None) == (command.id_unidad_funcional is None):
            return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")

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

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = DisponibilidadReplaceVigentePayload(
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            estado_disponibilidad=command.estado_disponibilidad,
            fecha_desde=command.fecha_desde,
            motivo=command.motivo,
            observaciones=command.observaciones,
            uid_global=uid_global,
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        try:
            result = self.repository.replace_disponibilidad_vigente(payload)
        except (IntegrityError, DBAPIError) as exc:
            error_message = str(getattr(exc, "orig", exc))
            if "chk_disponibilidad_vigencia" in error_message:
                return AppResult.fail("INVALID_REPLACEMENT_DATE")
            if "Solapamiento de vigencia en disponibilidad" in error_message:
                return AppResult.fail("DISPONIBILIDAD_OVERLAP")
            if "chk_disponibilidad_xor" in error_message:
                return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")
            raise

        status = result.get("status")
        if status == "NO_OPEN":
            return AppResult.fail("NO_OPEN_DISPONIBILIDAD")
        if status == "MULTIPLE_OPEN":
            return AppResult.fail("MULTIPLE_OPEN_DISPONIBILIDAD")
        if status == "INVALID_REPLACEMENT_DATE":
            return AppResult.fail("INVALID_REPLACEMENT_DATE")

        created = result["data"]

        return AppResult.ok(
            {
                "id_disponibilidad": created["id_disponibilidad"],
                "uid_global": created["uid_global"],
                "version_registro": created["version_registro"],
                "id_inmueble": created["id_inmueble"],
                "id_unidad_funcional": created["id_unidad_funcional"],
                "estado_disponibilidad": created["estado_disponibilidad"],
                "fecha_desde": created["fecha_desde"],
                "fecha_hasta": created["fecha_hasta"],
                "motivo": created["motivo"],
                "observaciones": created["observaciones"],
            }
        )
