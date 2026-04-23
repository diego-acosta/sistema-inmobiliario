from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.inmuebles.commands.create_inmueble import CreateInmuebleCommand


@dataclass(slots=True)
class InmuebleCreatePayload:
    id_desarrollo: int | None
    codigo_inmueble: str
    nombre_inmueble: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_juridico: str
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
    def desarrollo_exists(self, id_desarrollo: int) -> bool:
        ...

    def create_inmueble(self, payload: InmuebleCreatePayload) -> Any:
        ...


class CreateInmuebleService:
    def __init__(self, repository: InmuebleRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: CreateInmuebleCommand) -> AppResult[dict[str, Any]]:
        if (
            command.id_desarrollo is not None
            and not self.repository.desarrollo_exists(command.id_desarrollo)
        ):
            return AppResult.fail("NOT_FOUND_DESARROLLO")

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = InmuebleCreatePayload(
            id_desarrollo=command.id_desarrollo,
            codigo_inmueble=command.codigo_inmueble,
            nombre_inmueble=command.nombre_inmueble,
            superficie=command.superficie,
            estado_administrativo=command.estado_administrativo,
            estado_juridico=command.estado_juridico,
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

        created = self.repository.create_inmueble(payload)

        id_inmueble = (
            created["id_inmueble"]
            if isinstance(created, dict)
            else getattr(created, "id_inmueble")
        )

        return AppResult.ok(
            {
                "id_inmueble": id_inmueble,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "codigo_inmueble": payload.codigo_inmueble,
                "estado_administrativo": payload.estado_administrativo,
                "estado_juridico": payload.estado_juridico,
            }
        )
