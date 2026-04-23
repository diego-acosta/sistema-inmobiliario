from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.servicios.commands.create_servicio import CreateServicioCommand


@dataclass(slots=True)
class ServicioCreatePayload:
    codigo_servicio: str
    nombre_servicio: str
    descripcion: str | None
    estado_servicio: str
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class ServicioRepository(Protocol):
    def create_servicio(self, payload: ServicioCreatePayload) -> Any:
        ...


class CreateServicioService:
    def __init__(self, repository: ServicioRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: CreateServicioCommand) -> AppResult[dict[str, Any]]:
        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = ServicioCreatePayload(
            codigo_servicio=command.codigo_servicio,
            nombre_servicio=command.nombre_servicio,
            descripcion=command.descripcion,
            estado_servicio=command.estado_servicio,
            uid_global=uid_global,
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        created = self.repository.create_servicio(payload)

        id_servicio = (
            created["id_servicio"]
            if isinstance(created, dict)
            else getattr(created, "id_servicio")
        )

        return AppResult.ok(
            {
                "id_servicio": id_servicio,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "codigo_servicio": payload.codigo_servicio,
                "nombre_servicio": payload.nombre_servicio,
                "estado_servicio": payload.estado_servicio,
            }
        )
