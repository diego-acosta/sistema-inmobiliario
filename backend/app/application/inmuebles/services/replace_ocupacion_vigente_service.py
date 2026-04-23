from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.common.results import AppResult
from app.application.inmuebles.commands.replace_ocupacion_vigente import (
    ReplaceOcupacionVigenteCommand,
)


@dataclass(slots=True)
class OcupacionReplaceVigentePayload:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    tipo_ocupacion: str
    fecha_desde: datetime
    descripcion: str | None
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

    def replace_ocupacion_vigente(
        self, payload: OcupacionReplaceVigentePayload
    ) -> dict[str, Any]:
        ...


class ReplaceOcupacionVigenteService:
    def __init__(self, repository: InmuebleRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: ReplaceOcupacionVigenteCommand
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

        payload = OcupacionReplaceVigentePayload(
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            tipo_ocupacion=command.tipo_ocupacion,
            fecha_desde=command.fecha_desde,
            descripcion=command.descripcion,
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
            result = self.repository.replace_ocupacion_vigente(payload)
        except (IntegrityError, DBAPIError) as exc:
            error_message = str(getattr(exc, "orig", exc))
            if "chk_ocupacion_vigencia" in error_message:
                return AppResult.fail("INVALID_REPLACEMENT_DATE")
            if "Solapamiento de vigencia en ocupacion" in error_message:
                return AppResult.fail("OCUPACION_OVERLAP")
            if "chk_ocupacion_xor" in error_message:
                return AppResult.fail("EXACTLY_ONE_PARENT_REQUIRED")
            raise

        status = result.get("status")
        if status == "NO_OPEN":
            return AppResult.fail("NO_OPEN_OCUPACION")
        if status == "MULTIPLE_OPEN":
            return AppResult.fail("MULTIPLE_OPEN_OCUPACION")
        if status == "INVALID_REPLACEMENT_DATE":
            return AppResult.fail("INVALID_REPLACEMENT_DATE")

        created = result["data"]

        return AppResult.ok(
            {
                "id_ocupacion": created["id_ocupacion"],
                "uid_global": created["uid_global"],
                "version_registro": created["version_registro"],
                "id_inmueble": created["id_inmueble"],
                "id_unidad_funcional": created["id_unidad_funcional"],
                "tipo_ocupacion": created["tipo_ocupacion"],
                "fecha_desde": created["fecha_desde"],
                "fecha_hasta": created["fecha_hasta"],
                "descripcion": created["descripcion"],
                "observaciones": created["observaciones"],
            }
        )
