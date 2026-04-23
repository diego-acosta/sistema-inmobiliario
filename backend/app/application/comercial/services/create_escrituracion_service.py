from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.comercial.commands.create_escrituracion import (
    CreateEscrituracionCommand,
)
from app.application.common.outbox import OutboxEventPayload
from app.application.common.results import AppResult


ESTADO_VENTA_ESCRITURABLE = "confirmada"


@dataclass(slots=True)
class EscrituracionCreatePayload:
    id_venta: int
    fecha_escrituracion: datetime
    numero_escritura: str | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def get_venta(self, id_venta: int) -> dict[str, Any] | None:
        ...

    def escrituracion_exists_for_venta(self, id_venta: int) -> bool:
        ...

    def rescision_exists_for_venta(self, id_venta: int) -> bool:
        ...

    def create_escrituracion(
        self,
        payload: EscrituracionCreatePayload,
        *,
        outbox_event: OutboxEventPayload | None = None,
    ) -> dict[str, Any]:
        ...


class CreateEscrituracionService:
    def __init__(self, repository: ComercialRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateEscrituracionCommand
    ) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta(command.id_venta)
        if venta is None or venta["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_VENTA")

        estado_venta = (venta["estado_venta"] or "").strip().lower()
        if estado_venta != ESTADO_VENTA_ESCRITURABLE:
            return AppResult.fail("INVALID_VENTA_STATE")

        objetos = venta["objetos"]
        if not objetos:
            return AppResult.fail("VENTA_WITHOUT_OBJECTS")

        seen_objects: set[tuple[str, int]] = set()
        for objeto in objetos:
            id_inmueble = objeto["id_inmueble"]
            id_unidad_funcional = objeto["id_unidad_funcional"]

            if (id_inmueble is None) == (id_unidad_funcional is None):
                return AppResult.fail("INVALID_VENTA_OBJECTS")

            object_key = (
                ("inmueble", id_inmueble)
                if id_inmueble is not None
                else ("unidad_funcional", id_unidad_funcional)
            )
            if object_key in seen_objects:
                return AppResult.fail("INVALID_VENTA_OBJECTS")
            seen_objects.add(object_key)

        if self.repository.rescision_exists_for_venta(command.id_venta):
            return AppResult.fail("CONFLICTING_RESCISION")

        if self.repository.escrituracion_exists_for_venta(command.id_venta):
            return AppResult.fail("CONFLICTING_ESCRITURACION")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)
        payload = EscrituracionCreatePayload(
            id_venta=command.id_venta,
            fecha_escrituracion=command.fecha_escrituracion,
            numero_escritura=command.numero_escritura,
            observaciones=command.observaciones,
            uid_global=str(self.uuid_generator()),
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        outbox_event = OutboxEventPayload(
            event_type="escrituracion_registrada",
            aggregate_type="venta",
            aggregate_id=command.id_venta,
            payload={
                "id_venta": command.id_venta,
                "fecha_escrituracion": command.fecha_escrituracion.isoformat(),
                "numero_escritura": command.numero_escritura,
                "objetos": [
                    {
                        "id_inmueble": objeto["id_inmueble"],
                        "id_unidad_funcional": objeto["id_unidad_funcional"],
                    }
                    for objeto in objetos
                ],
            },
            occurred_at=now,
        )

        return AppResult.ok(
            self.repository.create_escrituracion(payload, outbox_event=outbox_event)["data"]
        )
