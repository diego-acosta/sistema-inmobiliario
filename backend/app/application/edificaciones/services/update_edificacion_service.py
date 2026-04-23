from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.edificaciones.commands.update_edificacion import (
    UpdateEdificacionCommand,
)


@dataclass(slots=True)
class EdificacionUpdatePayload:
    id_edificacion: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    descripcion: str | None
    tipo_edificacion: str | None
    superficie: Decimal | None
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class EdificacionRepository(Protocol):
    def get_edificacion_for_update(self, id_edificacion: int) -> dict[str, Any] | None:
        ...

    def update_edificacion(self, payload: EdificacionUpdatePayload) -> Any | None:
        ...


class UpdateEdificacionService:
    def __init__(self, repository: EdificacionRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdateEdificacionCommand) -> AppResult[dict[str, Any]]:
        edificacion = self.repository.get_edificacion_for_update(command.id_edificacion)
        if edificacion is None:
            return AppResult.fail("NOT_FOUND_EDIFICACION")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != edificacion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = EdificacionUpdatePayload(
            id_edificacion=command.id_edificacion,
            id_inmueble=edificacion["id_inmueble"],
            id_unidad_funcional=edificacion["id_unidad_funcional"],
            descripcion=command.descripcion,
            tipo_edificacion=command.tipo_edificacion,
            superficie=command.superficie,
            observaciones=command.observaciones,
            version_registro_actual=edificacion["version_registro"],
            version_registro_nueva=edificacion["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_edificacion(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_edificacion = (
            updated["id_edificacion"]
            if isinstance(updated, dict)
            else getattr(updated, "id_edificacion")
        )

        return AppResult.ok(
            {
                "id_edificacion": id_edificacion,
                "id_inmueble": payload.id_inmueble,
                "id_unidad_funcional": payload.id_unidad_funcional,
                "version_registro": payload.version_registro_nueva,
                "descripcion": payload.descripcion,
                "tipo_edificacion": payload.tipo_edificacion,
                "superficie": payload.superficie,
                "observaciones": payload.observaciones,
            }
        )
