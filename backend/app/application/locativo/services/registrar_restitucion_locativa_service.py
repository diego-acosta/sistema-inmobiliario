from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, date
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.outbox import OutboxEventPayload
from app.application.common.results import AppResult
from app.application.locativo.commands.registrar_restitucion_locativa import (
    RegistrarRestitucionLocativaCommand,
)


ESTADOS_PERMITIDOS = {"activo", "finalizado"}
EVENT_TYPE = "restitucion_locativa_registrada"
AGGREGATE_TYPE = "contrato_alquiler"


@dataclass(slots=True)
class RestitucionLocativaCreatePayload:
    id_contrato_alquiler: int
    fecha_restitucion: date
    estado_inmueble: str | None
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

    def has_ocupacion_activa_for_contrato(self, id_contrato_alquiler: int) -> bool: ...

    def has_restitucion_for_contrato(self, id_contrato_alquiler: int) -> bool: ...

    def create_restitucion_locativa_sin_commit(
        self,
        payload: RestitucionLocativaCreatePayload,
        outbox_event: OutboxEventPayload,
    ) -> dict[str, Any]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class RegistrarRestitucionLocativaService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: RegistrarRestitucionLocativaCommand
    ) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler(command.id_contrato_alquiler)
        if contrato is None or contrato["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_CONTRATO_ALQUILER")

        estado = (contrato["estado_contrato"] or "").strip().lower()
        if estado not in ESTADOS_PERMITIDOS:
            return AppResult.fail("CONTRATO_ESTADO_INVALIDO")

        if not self.repository.has_entrega_for_contrato(command.id_contrato_alquiler):
            return AppResult.fail("CONTRATO_SIN_ENTREGA")

        if not self.repository.has_ocupacion_activa_for_contrato(command.id_contrato_alquiler):
            return AppResult.fail("CONTRATO_SIN_OCUPACION_ACTIVA")

        if self.repository.has_restitucion_for_contrato(command.id_contrato_alquiler):
            return AppResult.fail("CONTRATO_YA_TIENE_RESTITUCION")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)
        uid_restitucion = str(self.uuid_generator())

        payload = RestitucionLocativaCreatePayload(
            id_contrato_alquiler=command.id_contrato_alquiler,
            fecha_restitucion=command.fecha_restitucion,
            estado_inmueble=command.estado_inmueble,
            observaciones=command.observaciones,
            uid_global=uid_restitucion,
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        objetos = contrato.get("objetos", [])
        outbox_event = OutboxEventPayload(
            event_type=EVENT_TYPE,
            aggregate_type=AGGREGATE_TYPE,
            aggregate_id=command.id_contrato_alquiler,
            payload={
                "uid_restitucion_locativa": uid_restitucion,
                "id_contrato_alquiler": command.id_contrato_alquiler,
                "fecha_restitucion": command.fecha_restitucion.isoformat(),
                "objetos": [
                    {
                        "id_inmueble": o["id_inmueble"],
                        "id_unidad_funcional": o["id_unidad_funcional"],
                    }
                    for o in objetos
                ],
            },
            occurred_at=now,
        )

        try:
            created = self.repository.create_restitucion_locativa_sin_commit(
                payload, outbox_event
            )
            self.repository.commit()
            return AppResult.ok(created)
        except Exception:
            self.repository.rollback()
            raise
