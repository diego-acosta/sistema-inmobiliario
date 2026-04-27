from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.application.common.results import AppResult


EVENT_TYPE = "restitucion_locativa_registrada"
TIPO_OCUPACION = "ALQUILER"
ESTADO_DISPONIBILIDAD_ESPERADO = "NO_DISPONIBLE"
ESTADO_DISPONIBILIDAD_DESTINO = "DISPONIBLE"
TERMINAL_OUTBOX_STATUS = "REJECTED"
PROCESSOR_NAME = "inmobiliario.restitucion_locativa"

TERMINAL_CONSUMER_ERRORS = {
    "INVALID_EVENT_PAYLOAD",
    "INVALID_EVENT_DATE",
    "INVALID_EVENT_OBJECTS",
    "NO_OPEN_OCUPACION_ALQUILER",
    "MULTIPLE_OPEN_OCUPACION_ALQUILER",
    "NO_OPEN_DISPONIBILIDAD",
    "MULTIPLE_OPEN_DISPONIBILIDAD",
    "CURRENT_NOT_RESERVADA",
    "INVALID_REPLACEMENT_DATE",
}


@dataclass(slots=True)
class EntregaRestitucionPayload:
    id_contrato_alquiler: int
    fecha_entrega: date
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


@dataclass(slots=True)
class CloseOcupacionPayload:
    id_ocupacion: int
    fecha_hasta: datetime
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class DisponibilidadReplacePayload:
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
    def get_open_ocupacion_alquiler_sin_commit(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
    ) -> dict[str, Any]: ...

    def close_ocupacion_sin_commit(self, payload: CloseOcupacionPayload) -> dict[str, Any]: ...

    def replace_disponibilidad_vigente_por_escrituracion(
        self,
        payload: DisponibilidadReplacePayload,
        *,
        expected_current_state: str,
        already_applied_state: str,
    ) -> dict[str, Any]: ...

    def create_entrega_restitucion_inmueble_sin_commit(
        self, payload: EntregaRestitucionPayload
    ) -> dict[str, Any]: ...


class OutboxRepository(Protocol):
    def get_pending_events(self, *, limit: int = 100) -> list[dict[str, Any]]: ...

    def mark_as_published(
        self,
        event_id: int,
        *,
        published_at: datetime | None = None,
        processing_reason: dict[str, Any] | None = None,
        processing_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None: ...

    def mark_as_terminal(
        self,
        event_id: int,
        *,
        terminal_status: str = "REJECTED",
        processing_reason: dict[str, Any] | None = None,
        processing_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None: ...

    def mark_as_failed(self, event_id: int, *, error: str) -> dict[str, Any] | None: ...


class InboxRepository(Protocol):
    def claim(
        self,
        *,
        event_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: int,
        consumer: str,
    ) -> bool: ...

    def mark_as_processed(self, *, event_id: str, consumer: str) -> None: ...

    def mark_as_rejected(
        self, *, event_id: str, consumer: str, error_detail: str
    ) -> None: ...


class ConsumeRestitucionLocativaService:
    def __init__(
        self,
        db: Session,
        inmueble_repository: InmuebleRepository,
        outbox_repository: OutboxRepository,
        inbox_repository: InboxRepository,
        uuid_generator=None,
    ) -> None:
        self.db = db
        self.inmueble_repository = inmueble_repository
        self.outbox_repository = outbox_repository
        self.inbox_repository = inbox_repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, *, limit: int = 100) -> AppResult[dict[str, Any]]:
        pending_events = self.outbox_repository.get_pending_events(limit=limit)
        restitucion_events = [e for e in pending_events if e["event_type"] == EVENT_TYPE]

        processed: list[dict[str, Any]] = []
        for event in restitucion_events:
            result = self._consume_single_event(event)
            if not result.success:
                return result
            processed.append(result.data or {})

        return AppResult.ok({"processed_events": len(processed), "events": processed})

    def _consume_single_event(self, event: dict[str, Any]) -> AppResult[dict[str, Any]]:
        event_uuid: str = event["event_id"]
        now = datetime.now(UTC)
        consumer_op_id = self.uuid_generator()

        try:
            # ── validación de payload ──────────────────────────────────────────
            payload = event["payload"]
            if not isinstance(payload, dict):
                return self._reject_business(event, event_uuid, "INVALID_EVENT_PAYLOAD")

            id_contrato_alquiler = payload.get("id_contrato_alquiler")
            if not isinstance(id_contrato_alquiler, int):
                return self._reject_business(event, event_uuid, "INVALID_EVENT_PAYLOAD")

            fecha_restitucion_raw = payload.get("fecha_restitucion")
            if not isinstance(fecha_restitucion_raw, str):
                return self._reject_business(event, event_uuid, "INVALID_EVENT_DATE")
            try:
                fecha_restitucion_date = date.fromisoformat(fecha_restitucion_raw)
                fecha_restitucion_dt = datetime(
                    fecha_restitucion_date.year,
                    fecha_restitucion_date.month,
                    fecha_restitucion_date.day,
                )
            except ValueError:
                return self._reject_business(event, event_uuid, "INVALID_EVENT_DATE")

            objetos = payload.get("objetos")
            if not isinstance(objetos, list) or not objetos:
                return self._reject_business(event, event_uuid, "INVALID_EVENT_OBJECTS")

            seen: set[tuple[str, int]] = set()
            for obj in objetos:
                if not isinstance(obj, dict):
                    return self._reject_business(event, event_uuid, "INVALID_EVENT_OBJECTS")
                id_inm = obj.get("id_inmueble")
                id_uf = obj.get("id_unidad_funcional")
                if (id_inm is None) == (id_uf is None):
                    return self._reject_business(event, event_uuid, "INVALID_EVENT_OBJECTS")
                key = ("inmueble", id_inm) if id_inm is not None else ("uf", id_uf)
                if key in seen:
                    return self._reject_business(event, event_uuid, "INVALID_EVENT_OBJECTS")
                seen.add(key)

            # ── claim inbox para idempotencia ──────────────────────────────────
            claimed = self.inbox_repository.claim(
                event_id=event_uuid,
                event_type=event["event_type"],
                aggregate_type=event["aggregate_type"],
                aggregate_id=event["aggregate_id"],
                consumer=PROCESSOR_NAME,
            )

            if not claimed:
                published = self.outbox_repository.mark_as_published(
                    event["id"],
                    published_at=now,
                    processing_reason={
                        "code": "CONSUMED_ALREADY_CLAIMED",
                        "category": "CONSUMER_RESULT",
                        "detail": "event_already_claimed_by_consumer",
                    },
                    processing_metadata=self._build_metadata(now, object_results=None),
                )
                if published is None:
                    self.db.rollback()
                    return AppResult.fail("OUTBOX_EVENT_NOT_PENDING")
                self.db.commit()
                return AppResult.ok(
                    {
                        "event_id": event["id"],
                        "id_contrato_alquiler": id_contrato_alquiler,
                        "status": "ALREADY_CLAIMED",
                    }
                )

            # ── procesar objetos: cerrar ocupación + liberar disponibilidad ────
            object_results: list[dict[str, Any]] = []
            for obj in objetos:
                id_inm = obj.get("id_inmueble")
                id_uf = obj.get("id_unidad_funcional")

                ocp_result = self.inmueble_repository.get_open_ocupacion_alquiler_sin_commit(
                    id_inmueble=id_inm,
                    id_unidad_funcional=id_uf,
                )
                ocp_status = ocp_result["status"]
                if ocp_status in TERMINAL_CONSUMER_ERRORS:
                    return self._reject_business(event, event_uuid, ocp_status)
                if ocp_status != "OK":
                    self.db.rollback()
                    return AppResult.fail(ocp_status)

                ocupacion = ocp_result["data"]
                close_result = self.inmueble_repository.close_ocupacion_sin_commit(
                    CloseOcupacionPayload(
                        id_ocupacion=ocupacion["id_ocupacion"],
                        fecha_hasta=fecha_restitucion_dt,
                        version_registro_actual=ocupacion["version_registro"],
                        version_registro_nueva=ocupacion["version_registro"] + 1,
                        updated_at=now,
                        id_instalacion_ultima_modificacion=None,
                        op_id_ultima_modificacion=consumer_op_id,
                    )
                )
                if close_result.get("status") != "OK":
                    self.db.rollback()
                    return AppResult.fail(close_result.get("status") or "UNKNOWN_CONSUMER_ERROR")

                disp_result = self.inmueble_repository.replace_disponibilidad_vigente_por_escrituracion(
                    DisponibilidadReplacePayload(
                        id_inmueble=id_inm,
                        id_unidad_funcional=id_uf,
                        estado_disponibilidad=ESTADO_DISPONIBILIDAD_DESTINO,
                        fecha_desde=fecha_restitucion_dt,
                        motivo=EVENT_TYPE,
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

                status = disp_result.get("status")
                if status not in {"OK", "ALREADY_APPLIED"}:
                    error_code = status or "UNKNOWN_CONSUMER_ERROR"
                    if error_code in TERMINAL_CONSUMER_ERRORS:
                        return self._reject_business(event, event_uuid, error_code)
                    self.db.rollback()
                    return AppResult.fail(error_code)

                object_results.append(
                    {
                        "id_inmueble": id_inm,
                        "id_unidad_funcional": id_uf,
                        "status": status,
                    }
                )

            # ── crear entrega_restitucion_inmueble ─────────────────────────────
            self.inmueble_repository.create_entrega_restitucion_inmueble_sin_commit(
                EntregaRestitucionPayload(
                    id_contrato_alquiler=id_contrato_alquiler,
                    fecha_entrega=fecha_restitucion_date,
                    estado_inmueble=None,
                    observaciones=None,
                    uid_global=str(self.uuid_generator()),
                    version_registro=1,
                    created_at=now,
                    updated_at=now,
                    id_instalacion_origen=None,
                    id_instalacion_ultima_modificacion=None,
                    op_id_alta=consumer_op_id,
                    op_id_ultima_modificacion=consumer_op_id,
                )
            )

            # ── commit único: inbox + outbox + todo el DML ────────────────────
            self.inbox_repository.mark_as_processed(
                event_id=event_uuid, consumer=PROCESSOR_NAME
            )
            published = self.outbox_repository.mark_as_published(
                event["id"],
                published_at=now,
                processing_reason=self._build_success_reason(object_results),
                processing_metadata=self._build_metadata(now, object_results=object_results),
            )
            if published is None:
                self.db.rollback()
                return AppResult.fail("OUTBOX_EVENT_NOT_PENDING")

            self.db.commit()
            return AppResult.ok(
                {
                    "event_id": event["id"],
                    "id_contrato_alquiler": id_contrato_alquiler,
                    "event_type": event["event_type"],
                    "objects": object_results,
                }
            )

        except Exception as exc:
            self.db.rollback()
            self.outbox_repository.mark_as_failed(event["id"], error=str(exc))
            self.db.commit()
            raise

    def _reject_business(
        self, event: dict[str, Any], event_uuid: str, error_code: str
    ) -> AppResult[dict[str, Any]]:
        now = datetime.now(UTC)
        self.db.rollback()
        self.outbox_repository.mark_as_terminal(
            event["id"],
            terminal_status=TERMINAL_OUTBOX_STATUS,
            processing_reason={
                "code": error_code,
                "category": "CONSUMER_REJECTION",
                "detail": f"{EVENT_TYPE}_rejected_due_to_permanent_inconsistency",
            },
            processing_metadata=self._build_metadata(now, object_results=None),
        )
        self.db.commit()
        return AppResult.fail(error_code)

    def _build_success_reason(self, object_results: list[dict[str, Any]]) -> dict[str, str]:
        statuses = {r["status"] for r in object_results}
        if statuses == {"OK"}:
            code, detail = "CONSUMED_APPLIED", f"{EVENT_TYPE}_applied_operationally"
        elif statuses == {"ALREADY_APPLIED"}:
            code, detail = "CONSUMED_ALREADY_APPLIED", f"{EVENT_TYPE}_was_already_applied"
        else:
            code, detail = "CONSUMED_APPLIED_IDEMPOTENT", f"{EVENT_TYPE}_mixed_apply_and_already_applied"
        return {"code": code, "category": "CONSUMER_RESULT", "detail": detail}

    def _build_metadata(
        self,
        processed_at: datetime,
        *,
        object_results: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return {
            "processor": PROCESSOR_NAME,
            "mode": "consumer",
            "processed_at": processed_at.isoformat(),
            "object_count": 0 if object_results is None else len(object_results),
        }
