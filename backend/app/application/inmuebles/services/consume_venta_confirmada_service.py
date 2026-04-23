from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.application.common.results import AppResult


EVENT_TYPE_VENTA_CONFIRMADA = "venta_confirmada"
ESTADO_VENTA_CONFIRMADA = "confirmada"
NO_OP_OBJECT_STATUS = "NO_OP"
TERMINAL_OUTBOX_STATUS = "REJECTED"
PROCESSOR_NAME = "inmobiliario.consume_venta_confirmada"
TERMINAL_CONSUMER_ERRORS = {
    "INVALID_EVENT_PAYLOAD",
    "INVALID_EVENT_STATE",
    "INVALID_EVENT_OBJECTS",
    "NOT_FOUND_INMUEBLE",
    "NOT_FOUND_UNIDAD_FUNCIONAL",
}


@dataclass(frozen=True, slots=True)
class VentaConfirmadaObjectRef:
    id_inmueble: int | None
    id_unidad_funcional: int | None


class InmuebleRepository(Protocol):
    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
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


class ConsumeVentaConfirmadaService:
    def __init__(
        self,
        db: Session,
        inmueble_repository: InmuebleRepository,
        outbox_repository: OutboxRepository,
    ) -> None:
        self.db = db
        self.inmueble_repository = inmueble_repository
        self.outbox_repository = outbox_repository

    def execute(self, *, limit: int = 100) -> AppResult[dict[str, Any]]:
        pending_events = self.outbox_repository.get_pending_events(limit=limit)
        venta_confirmada_events = [
            event
            for event in pending_events
            if event["event_type"] == EVENT_TYPE_VENTA_CONFIRMADA
        ]

        processed_events: list[dict[str, Any]] = []
        for event in venta_confirmada_events:
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

            estado_venta = payload.get("estado_venta")
            if (
                not isinstance(estado_venta, str)
                or estado_venta.strip().lower() != ESTADO_VENTA_CONFIRMADA
            ):
                return self._reject_event(event["id"], "INVALID_EVENT_STATE")

            objetos = payload.get("objetos")
            object_refs = self._parse_object_refs(objetos)
            if object_refs is None:
                return self._reject_event(event["id"], "INVALID_EVENT_OBJECTS")

            object_results: list[dict[str, Any]] = []
            for object_ref in object_refs:
                if object_ref.id_inmueble is not None:
                    if not self.inmueble_repository.inmueble_exists(object_ref.id_inmueble):
                        return self._reject_event(event["id"], "NOT_FOUND_INMUEBLE")
                elif object_ref.id_unidad_funcional is not None:
                    if not self.inmueble_repository.unidad_funcional_exists(
                        object_ref.id_unidad_funcional
                    ):
                        return self._reject_event(
                            event["id"], "NOT_FOUND_UNIDAD_FUNCIONAL"
                        )

                object_results.append(
                    {
                        "id_inmueble": object_ref.id_inmueble,
                        "id_unidad_funcional": object_ref.id_unidad_funcional,
                        "status": NO_OP_OBJECT_STATUS,
                    }
                )

            now = datetime.now(UTC)
            published = self.outbox_repository.mark_as_published(
                event["id"],
                published_at=now,
                processing_reason={
                    "code": "CONSUMED_NO_OP",
                    "category": "CONSUMER_RESULT",
                    "detail": "venta_confirmada_no_mutates_operational_state",
                },
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
                    "effect": NO_OP_OBJECT_STATUS,
                }
            )
        except Exception:
            self.db.rollback()
            raise

    def _parse_object_refs(
        self, objetos: Any
    ) -> list[VentaConfirmadaObjectRef] | None:
        if not isinstance(objetos, list) or not objetos:
            return None

        seen_objects: set[tuple[str, int]] = set()
        object_refs: list[VentaConfirmadaObjectRef] = []
        for objeto in objetos:
            if not isinstance(objeto, dict):
                return None

            id_inmueble = objeto.get("id_inmueble")
            id_unidad_funcional = objeto.get("id_unidad_funcional")
            if (id_inmueble is None) == (id_unidad_funcional is None):
                return None
            if id_inmueble is not None and not isinstance(id_inmueble, int):
                return None
            if id_unidad_funcional is not None and not isinstance(id_unidad_funcional, int):
                return None

            object_key = (
                ("inmueble", id_inmueble)
                if id_inmueble is not None
                else ("unidad_funcional", id_unidad_funcional)
            )
            if object_key in seen_objects:
                return None
            seen_objects.add(object_key)

            object_refs.append(
                VentaConfirmadaObjectRef(
                    id_inmueble=id_inmueble,
                    id_unidad_funcional=id_unidad_funcional,
                )
            )

        return object_refs

    def _reject_event(self, event_id: int, error_code: str) -> AppResult[dict[str, Any]]:
        self.db.rollback()
        rejected = self.outbox_repository.mark_as_terminal(
            event_id,
            terminal_status=TERMINAL_OUTBOX_STATUS,
            processing_reason={
                "code": error_code,
                "category": "CONSUMER_REJECTION",
                "detail": "venta_confirmada_rejected_due_to_permanent_inconsistency",
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
        if error_code in TERMINAL_CONSUMER_ERRORS:
            return AppResult.fail(error_code)
        return AppResult.fail("UNKNOWN_CONSUMER_ERROR", error_code)

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
