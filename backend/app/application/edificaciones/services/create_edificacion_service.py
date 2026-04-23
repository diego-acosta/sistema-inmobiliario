from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.edificaciones.commands.create_edificacion import (
    CreateEdificacionCommand,
)


@dataclass(slots=True)
class EdificacionCreatePayload:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    descripcion: str | None
    tipo_edificacion: str | None
    superficie: Decimal | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class EdificacionRepository(Protocol):
    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def create_edificacion(self, payload: EdificacionCreatePayload) -> Any:
        ...


class CreateEdificacionService:
    def __init__(self, repository: EdificacionRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: CreateEdificacionCommand) -> AppResult[dict[str, Any]]:
        if (command.id_inmueble is None) == (command.id_unidad_funcional is None):
            return AppResult.fail(
                "EXACTLY_ONE_PARENT_REQUIRED"
            )

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

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = EdificacionCreatePayload(
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            descripcion=command.descripcion,
            tipo_edificacion=command.tipo_edificacion,
            superficie=command.superficie,
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

        created = self.repository.create_edificacion(payload)

        id_edificacion = (
            created["id_edificacion"]
            if isinstance(created, dict)
            else getattr(created, "id_edificacion")
        )

        return AppResult.ok(
            {
                "id_edificacion": id_edificacion,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "id_inmueble": payload.id_inmueble,
                "id_unidad_funcional": payload.id_unidad_funcional,
                "tipo_edificacion": payload.tipo_edificacion,
            }
        )
