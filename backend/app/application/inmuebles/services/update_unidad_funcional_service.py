from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.inmuebles.commands.update_unidad_funcional import (
    UpdateUnidadFuncionalCommand,
)


@dataclass(slots=True)
class UnidadFuncionalUpdatePayload:
    id_unidad_funcional: int
    id_inmueble: int | None
    codigo_unidad: str
    nombre_unidad: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_operativo: str
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def get_unidad_funcional_for_update(
        self, id_unidad_funcional: int
    ) -> dict[str, Any] | None:
        ...

    def update_unidad_funcional(self, payload: UnidadFuncionalUpdatePayload) -> Any | None:
        ...


class UpdateUnidadFuncionalService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(
        self, command: UpdateUnidadFuncionalCommand
    ) -> AppResult[dict[str, Any]]:
        unidad = self.repository.get_unidad_funcional_for_update(
            command.id_unidad_funcional
        )
        if unidad is None:
            return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != unidad["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        if (
            command.codigo_unidad is None
            or command.estado_administrativo is None
            or command.estado_operativo is None
        ):
            return AppResult.fail("INVALID_REQUIRED_FIELDS")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = UnidadFuncionalUpdatePayload(
            id_unidad_funcional=command.id_unidad_funcional,
            id_inmueble=unidad["id_inmueble"],
            codigo_unidad=command.codigo_unidad,
            nombre_unidad=command.nombre_unidad,
            superficie=command.superficie,
            estado_administrativo=command.estado_administrativo,
            estado_operativo=command.estado_operativo,
            observaciones=command.observaciones,
            version_registro_actual=unidad["version_registro"],
            version_registro_nueva=unidad["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_unidad_funcional(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_unidad_funcional = (
            updated["id_unidad_funcional"]
            if isinstance(updated, dict)
            else getattr(updated, "id_unidad_funcional")
        )

        return AppResult.ok(
            {
                "id_unidad_funcional": id_unidad_funcional,
                "id_inmueble": payload.id_inmueble,
                "version_registro": payload.version_registro_nueva,
                "codigo_unidad": payload.codigo_unidad,
                "nombre_unidad": payload.nombre_unidad,
                "superficie": payload.superficie,
                "estado_administrativo": payload.estado_administrativo,
                "estado_operativo": payload.estado_operativo,
                "observaciones": payload.observaciones,
            }
        )
