from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.application.common.results import AppResult


EVENT_TYPE_ESCRITURACION_REGISTRADA = "escrituracion_registrada"
ESTADO_DISPONIBILIDAD_ESPERADO = "RESERVADA"
ESTADO_DISPONIBILIDAD_DESTINO = "NO_DISPONIBLE"
TERMINAL_OUTBOX_STATUS = "REJECTED"
PROCESSOR_NAME = "inmobiliario.consume_escrituracion_registrada"
TERMINAL_CONSUMER_ERRORS = {
    "INVALID_EVENT_PAYLOAD",
    "INVALID_EVENT_DATE",
    "INVALID_EVENT_OBJECTS",
    "NO_OPEN_DISPONIBILIDAD",
    "MULTIPLE_OPEN_DISPONIBILIDAD",
    "CURRENT_NOT_RESERVADA",
    "INVALID_REPLACEMENT_DATE",
}


@dataclass(slots=True)
class EscrituracionRegistradaReplacePayload:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    motivo: str | None
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
    def replace_disponibilidad_vigente_por_escrituracion(
        self,
        payload: EscrituracionRegistradaReplacePayload,
        *,
        expected_current_state: str,
        already_applied_state: str,
    ) -> dict[str, Any]:
        ...


class OutboxRepository(Protocol):
    def get_pending_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        ...

    def mark_as_published(
        self,
        event_id: int,
        *,
        published_at: datetime | None = None,
        processing_reason: dict[str, Any] | None = None,
        processing_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        ...

    def mark_as_terminal(
        self,
        event_id: int,
        *,
        terminal_status: str = "REJECTED",
        processing_reason: dict[str, Any] | None = None,
        processing_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        ...


class ConsumeEscrituracionRegistradaService:
    def __init__(
        self,
        db: Session,
        inmueble_repository: InmuebleRepository,
        outbox_repository: OutboxRepository,
        uuid_generator=None,
    ) -> None:
        self.db = db
        self.inmueble_repository = inmueble_repository
        self.outbox_repository = outbox_repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, *, limit: int = 100) -> AppResult[dict[str, Any]]:
        pending_events = self.outbox_repository.get_pending_events(limit=limit)
        escrituracion_events = [
            event
            for event in pending_events
            if event["event_type"] == EVENT_TYPE_ESCRITURACION_REGISTRADA
        ]

        processed_events: list[dict[str, Any]] = []
        for event in escrituracion_events:
            result = self._consume_single_event(event)
            if not result.success:
                return result
            processed_events.append(result.data or {})

        return AppResult.ok(
            {
                "processed_events": len(processed_events),
                "events": processed_events,
            }
        )

    def _consume_single_event(self, event: dict[str, Any]) -> AppResult[dict[str, Any]]:
        try:
            payload = event["payload"]
            if not isinstance(payload, dict):
                return self._reject_event(event["id"], "INVALID_EVENT_PAYLOAD")

            id_venta = payload.get("id_venta")
            if not isinstance(id_venta, int):
                return self._reject_event(event["id"], "INVALID_EVENT_PAYLOAD")

            fecha_escrituracion_raw = payload.get("fecha_escrituracion")
            if not isinstance(fecha_escrituracion_raw, str):
                return self._reject_event(event["id"], "INVALID_EVENT_DATE")

            try:
                fecha_escrituracion = datetime.fromisoformat(fecha_escrituracion_raw)
            except ValueError:
                return self._reject_event(event["id"], "INVALID_EVENT_DATE")

            objetos = payload.get("objetos")
            if not isinstance(objetos, list) or not objetos:
                return self._reject_event(event["id"], "INVALID_EVENT_OBJECTS")

            seen_objects: set[tuple[str, int]] = set()
            now = datetime.now(UTC)
            consumer_op_id = self.uuid_generator()

            object_results: list[dict[str, Any]] = []
            for objeto in objetos:
                if not isinstance(objeto, dict):
                    return self._reject_event(event["id"], "INVALID_EVENT_OBJECTS")

                id_inmueble = objeto.get("id_inmueble")
                id_unidad_funcional = objeto.get("id_unidad_funcional")
                if (id_inmueble is None) == (id_unidad_funcional is None):
                    return self._reject_event(event["id"], "INVALID_EVENT_OBJECTS")

                object_key = (
                    ("inmueble", id_inmueble)
                    if id_inmueble is not None
                    else ("unidad_funcional", id_unidad_funcional)
                )
                if object_key in seen_objects:
                    return self._reject_event(event["id"], "INVALID_EVENT_OBJECTS")
                seen_objects.add(object_key)

                replace_result = self.inmueble_repository.replace_disponibilidad_vigente_por_escrituracion(
                    EscrituracionRegistradaReplacePayload(
                        id_inmueble=id_inmueble,
                        id_unidad_funcional=id_unidad_funcional,
                        estado_disponibilidad=ESTADO_DISPONIBILIDAD_DESTINO,
                        fecha_desde=fecha_escrituracion,
                        motivo=EVENT_TYPE_ESCRITURACION_REGISTRADA,
                        observaciones=None,
                        uid_global=str(self.uuid_generator()),
                        version_registro=1,
                        created_at=now,
                        updated_at=now,
                        id_instalacion_origen=None,
                        id_instalacion_ultima_modificacion=None,
                        op_id_alta=consumer_op_id,
                        op_id_ultima_modificacion=consumer_op_id,
                    ),
                    expected_current_state=ESTADO_DISPONIBILIDAD_ESPERADO,
                    already_applied_state=ESTADO_DISPONIBILIDAD_DESTINO,
                )
                status = replace_result.get("status")
                if status not in {"OK", "ALREADY_APPLIED"}:
                    error_code = status or "UNKNOWN_CONSUMER_ERROR"
                    if error_code in TERMINAL_CONSUMER_ERRORS:
                        return self._reject_event(event["id"], error_code)
                    self.db.rollback()
                    return AppResult.fail(error_code)

                object_results.append(
                    {
                        "id_inmueble": id_inmueble,
                        "id_unidad_funcional": id_unidad_funcional,
                        "status": status,
                    }
                )

            published = self.outbox_repository.mark_as_published(
                event["id"],
                published_at=now,
                processing_reason=self._build_success_reason(object_results),
                processing_metadata=self._build_processing_metadata(
                    processed_at=now,
                    object_results=object_results,
                ),
            )
            if published is None:
                self.db.rollback()
                return AppResult.fail("OUTBOX_EVENT_NOT_PENDING")

            self.db.commit()
            return AppResult.ok(
                {
                    "event_id": event["id"],
                    "id_venta": id_venta,
                    "event_type": event["event_type"],
                    "objects": object_results,
                }
            )
        except Exception:
            self.db.rollback()
            raise

    def _reject_event(self, event_id: int, error_code: str) -> AppResult[dict[str, Any]]:
        self.db.rollback()
        rejected = self.outbox_repository.mark_as_terminal(
            event_id,
            terminal_status=TERMINAL_OUTBOX_STATUS,
            processing_reason={
                "code": error_code,
                "category": "CONSUMER_REJECTION",
                "detail": "escrituracion_registrada_rejected_due_to_permanent_inconsistency",
            },
            processing_metadata=self._build_processing_metadata(
                processed_at=datetime.now(UTC),
                object_results=None,
            ),
        )
        if rejected is None:
            self.db.rollback()
            return AppResult.fail("OUTBOX_EVENT_NOT_PENDING", error_code)
        self.db.commit()
        return AppResult.fail(error_code)

    def _build_success_reason(
        self, object_results: list[dict[str, Any]]
    ) -> dict[str, str]:
        statuses = {result["status"] for result in object_results}
        if statuses == {"OK"}:
            code = "CONSUMED_APPLIED"
            detail = "escrituracion_registrada_applied_operationally"
        elif statuses == {"ALREADY_APPLIED"}:
            code = "CONSUMED_ALREADY_APPLIED"
            detail = "escrituracion_registrada_was_already_applied"
        else:
            code = "CONSUMED_APPLIED_IDEMPOTENT"
            detail = "escrituracion_registrada_mixed_apply_and_already_applied"
        return {
            "code": code,
            "category": "CONSUMER_RESULT",
            "detail": detail,
        }

    def _build_processing_metadata(
        self,
        *,
        processed_at: datetime,
        object_results: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return {
            "processor": PROCESSOR_NAME,
            "mode": "consumer",
            "processed_at": processed_at.isoformat(),
            "object_count": 0 if object_results is None else len(object_results),
        }
