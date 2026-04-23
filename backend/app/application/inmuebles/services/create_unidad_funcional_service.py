from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.inmuebles.commands.create_unidad_funcional import (
    CreateUnidadFuncionalCommand,
)


@dataclass(slots=True)
class UnidadFuncionalCreatePayload:
    id_inmueble: int
    codigo_unidad: str
    nombre_unidad: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_operativo: str
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

    def create_unidad_funcional(self, payload: UnidadFuncionalCreatePayload) -> Any:
        ...


class CreateUnidadFuncionalService:
    def __init__(self, repository: InmuebleRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateUnidadFuncionalCommand
    ) -> AppResult[dict[str, Any]]:
        if not self.repository.inmueble_exists(command.id_inmueble):
            return AppResult.fail("NOT_FOUND_INMUEBLE")

        if (
            command.codigo_unidad is None
            or command.estado_administrativo is None
            or command.estado_operativo is None
        ):
            return AppResult.fail("INVALID_REQUIRED_FIELDS")

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = UnidadFuncionalCreatePayload(
            id_inmueble=command.id_inmueble,
            codigo_unidad=command.codigo_unidad,
            nombre_unidad=command.nombre_unidad,
            superficie=command.superficie,
            estado_administrativo=command.estado_administrativo,
            estado_operativo=command.estado_operativo,
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

        created = self.repository.create_unidad_funcional(payload)

        id_unidad_funcional = (
            created["id_unidad_funcional"]
            if isinstance(created, dict)
            else getattr(created, "id_unidad_funcional")
        )

        return AppResult.ok(
            {
                "id_unidad_funcional": id_unidad_funcional,
                "id_inmueble": payload.id_inmueble,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "codigo_unidad": payload.codigo_unidad,
                "estado_administrativo": payload.estado_administrativo,
                "estado_operativo": payload.estado_operativo,
            }
        )
