from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.inmuebles.commands.create_unidad_funcional_servicio import (
    CreateUnidadFuncionalServicioCommand,
)


@dataclass(slots=True)
class UnidadFuncionalServicioCreatePayload:
    id_unidad_funcional: int
    id_servicio: int
    estado: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def servicio_exists(self, id_servicio: int) -> bool:
        ...

    def unidad_funcional_servicio_exists(
        self, id_unidad_funcional: int, id_servicio: int
    ) -> bool:
        ...

    def create_unidad_funcional_servicio(
        self, payload: UnidadFuncionalServicioCreatePayload
    ) -> Any:
        ...


class CreateUnidadFuncionalServicioService:
    def __init__(self, repository: InmuebleRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateUnidadFuncionalServicioCommand
    ) -> AppResult[dict[str, Any]]:
        if not self.repository.unidad_funcional_exists(command.id_unidad_funcional):
            return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

        if not self.repository.servicio_exists(command.id_servicio):
            return AppResult.fail("NOT_FOUND_SERVICIO")

        if self.repository.unidad_funcional_servicio_exists(
            command.id_unidad_funcional, command.id_servicio
        ):
            return AppResult.fail("DUPLICATE_UNIDAD_FUNCIONAL_SERVICIO")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = UnidadFuncionalServicioCreatePayload(
            id_unidad_funcional=command.id_unidad_funcional,
            id_servicio=command.id_servicio,
            estado=command.estado,
            uid_global=uid_global,
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        created = self.repository.create_unidad_funcional_servicio(payload)

        id_unidad_funcional_servicio = (
            created["id_unidad_funcional_servicio"]
            if isinstance(created, dict)
            else getattr(created, "id_unidad_funcional_servicio")
        )

        return AppResult.ok(
            {
                "id_unidad_funcional_servicio": id_unidad_funcional_servicio,
                "id_unidad_funcional": payload.id_unidad_funcional,
                "id_servicio": payload.id_servicio,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "estado": payload.estado,
            }
        )
