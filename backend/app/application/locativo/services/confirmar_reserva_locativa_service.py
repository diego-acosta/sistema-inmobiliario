from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.outbox import OutboxEventPayload
from app.application.common.results import AppResult
from app.application.locativo.commands.confirmar_reserva_locativa import (
    ConfirmarReservaLocativaCommand,
)
from app.application.locativo.services.create_reserva_locativa_service import (
    ESTADOS_ACTIVOS_RESERVA_LOCATIVA,
)


ESTADO_PENDIENTE = "pendiente"
ESTADO_CONFIRMADA = "confirmada"
EVENT_TYPE_CONFIRMADA = "reserva_locativa_confirmada"
AGGREGATE_TYPE = "reserva_locativa"


@dataclass(slots=True)
class ReservaLocativaConfirmarPayload:
    id_reserva_locativa: int
    estado_reserva: str
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class LocativoRepository(Protocol):
    def get_reserva_locativa(self, id_reserva_locativa: int) -> dict[str, Any] | None: ...

    def inmueble_exists(self, id_inmueble: int) -> bool: ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool: ...

    def has_current_disponibilidad_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool: ...

    def has_current_disponibilidad_no_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool: ...

    def has_conflicting_active_reserva_locativa(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
        exclude_id_reserva_locativa: int | None = None,
    ) -> bool: ...

    def confirmar_reserva_locativa(
        self,
        payload: ReservaLocativaConfirmarPayload,
        outbox_event: OutboxEventPayload,
    ) -> dict[str, Any]: ...


class ConfirmarReservaLocativaService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(
        self, command: ConfirmarReservaLocativaCommand
    ) -> AppResult[dict[str, Any]]:
        reserva = self.repository.get_reserva_locativa(command.id_reserva_locativa)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RESERVA_LOCATIVA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != reserva["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_actual = (reserva["estado_reserva"] or "").strip().lower()
        if estado_actual != ESTADO_PENDIENTE:
            return AppResult.fail("INVALID_RESERVA_STATE")

        objetos = reserva["objetos"]
        if not objetos:
            return AppResult.fail("OBJETOS_REQUIRED")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        for objeto in objetos:
            id_inmueble = objeto["id_inmueble"]
            id_unidad_funcional = objeto["id_unidad_funcional"]

            if id_inmueble is not None and not self.repository.inmueble_exists(id_inmueble):
                return AppResult.fail("NOT_FOUND_INMUEBLE")
            if (
                id_unidad_funcional is not None
                and not self.repository.unidad_funcional_exists(id_unidad_funcional)
            ):
                return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

            if self.repository.has_current_disponibilidad_no_disponible(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                at_datetime=now,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if not self.repository.has_current_disponibilidad_disponible(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                at_datetime=now,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if self.repository.has_conflicting_active_reserva_locativa(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                conflict_states=ESTADOS_ACTIVOS_RESERVA_LOCATIVA,
                exclude_id_reserva_locativa=command.id_reserva_locativa,
            ):
                return AppResult.fail("CONFLICTING_RESERVA_LOCATIVA")

        payload = ReservaLocativaConfirmarPayload(
            id_reserva_locativa=command.id_reserva_locativa,
            estado_reserva=ESTADO_CONFIRMADA,
            version_registro_actual=reserva["version_registro"],
            version_registro_nueva=reserva["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        outbox_event = OutboxEventPayload(
            event_type=EVENT_TYPE_CONFIRMADA,
            aggregate_type=AGGREGATE_TYPE,
            aggregate_id=command.id_reserva_locativa,
            payload={
                "id_reserva_locativa": command.id_reserva_locativa,
                "codigo_reserva": reserva["codigo_reserva"],
                "estado_reserva": ESTADO_CONFIRMADA,
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

        result = self.repository.confirmar_reserva_locativa(payload, outbox_event)
        if result.get("status") == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(result["data"])
