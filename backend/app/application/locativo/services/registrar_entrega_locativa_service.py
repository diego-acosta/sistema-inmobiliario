from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, date
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.outbox import OutboxEventPayload
from app.application.common.results import AppResult
from app.application.locativo.commands.registrar_entrega_locativa import (
    RegistrarEntregaLocativaCommand,
)


ESTADO_ACTIVO = "activo"
EVENT_TYPE = "entrega_locativa_registrada"
AGGREGATE_TYPE = "contrato_alquiler"


@dataclass(slots=True)
class EntregaLocativaCreatePayload:
    id_contrato_alquiler: int
    fecha_entrega: date
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class LocativoRepository(Protocol):
    def get_contrato_alquiler(self, id_contrato_alquiler: int) -> dict[str, Any] | None: ...

    def has_entrega_for_contrato(self, id_contrato_alquiler: int) -> bool: ...

    def create_entrega_locativa_sin_commit(
        self,
        payload: EntregaLocativaCreatePayload,
        outbox_event: OutboxEventPayload,
    ) -> dict[str, Any]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class RegistrarEntregaLocativaService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: RegistrarEntregaLocativaCommand
    ) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler(command.id_contrato_alquiler)
        if contrato is None or contrato["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_CONTRATO_ALQUILER")

        estado = (contrato["estado_contrato"] or "").strip().lower()
        if estado != ESTADO_ACTIVO:
            return AppResult.fail("CONTRATO_NOT_ACTIVO")

        if self.repository.has_entrega_for_contrato(command.id_contrato_alquiler):
            return AppResult.fail("CONTRATO_YA_TIENE_ENTREGA")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = EntregaLocativaCreatePayload(
            id_contrato_alquiler=command.id_contrato_alquiler,
            fecha_entrega=command.fecha_entrega,
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
            event_type=EVENT_TYPE,
            aggregate_type=AGGREGATE_TYPE,
            aggregate_id=command.id_contrato_alquiler,
            payload={
                "id_contrato_alquiler": command.id_contrato_alquiler,
                "fecha_entrega": command.fecha_entrega.isoformat(),
                "objetos": [
                    {
                        "id_inmueble": o["id_inmueble"],
                        "id_unidad_funcional": o["id_unidad_funcional"],
                    }
                    for o in contrato["objetos"]
                ],
            },
            occurred_at=now,
        )

        try:
            created = self.repository.create_entrega_locativa_sin_commit(
                payload, outbox_event
            )
            self.repository.commit()
            return AppResult.ok(created)
        except Exception:
            self.repository.rollback()
            raise
