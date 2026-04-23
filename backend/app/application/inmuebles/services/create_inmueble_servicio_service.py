from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.application.common.results import AppResult
from app.application.inmuebles.commands.create_inmueble_servicio import (
    CreateInmuebleServicioCommand,
)

ACTIVE_DUPLICATE_CONSTRAINT = "ux_inmueble_servicio_activo"


@dataclass(slots=True)
class InmuebleServicioCreatePayload:
    id_inmueble: int
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
    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def servicio_exists(self, id_servicio: int) -> bool:
        ...

    def inmueble_servicio_exists(
        self, id_inmueble: int, id_servicio: int
    ) -> bool:
        ...

    def create_inmueble_servicio(self, payload: InmuebleServicioCreatePayload) -> Any:
        ...


class CreateInmuebleServicioService:
    def __init__(self, repository: InmuebleRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateInmuebleServicioCommand
    ) -> AppResult[dict[str, Any]]:
        if not self.repository.inmueble_exists(command.id_inmueble):
            return AppResult.fail("NOT_FOUND_INMUEBLE")

        if not self.repository.servicio_exists(command.id_servicio):
            return AppResult.fail("NOT_FOUND_SERVICIO")

        if self.repository.inmueble_servicio_exists(
            command.id_inmueble, command.id_servicio
        ):
            return AppResult.fail("DUPLICATE_INMUEBLE_SERVICIO")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = InmuebleServicioCreatePayload(
            id_inmueble=command.id_inmueble,
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

        try:
            created = self.repository.create_inmueble_servicio(payload)
        except IntegrityError as exc:
            if self._is_active_duplicate_violation(exc):
                return AppResult.fail("DUPLICATE_INMUEBLE_SERVICIO")
            raise

        id_inmueble_servicio = (
            created["id_inmueble_servicio"]
            if isinstance(created, dict)
            else getattr(created, "id_inmueble_servicio")
        )

        return AppResult.ok(
            {
                "id_inmueble_servicio": id_inmueble_servicio,
                "id_inmueble": payload.id_inmueble,
                "id_servicio": payload.id_servicio,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "estado": payload.estado,
            }
        )

    @staticmethod
    def _is_active_duplicate_violation(exc: IntegrityError) -> bool:
        diag = getattr(getattr(exc, "orig", None), "diag", None)
        return getattr(diag, "constraint_name", None) == ACTIVE_DUPLICATE_CONSTRAINT
