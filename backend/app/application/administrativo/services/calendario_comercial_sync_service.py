from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import date
from itertools import pairwise
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.administrativo.parametro_entero import parse_parametro_entero
from app.application.common.idempotency import canonical_payload_hash
from app.application.common.synchronization_policy import validate_sync_event
from app.application.integration.inbox_retry import (
    InboxOutcome,
    InboxOutcomeKind,
    InboxRetryProcessor,
)
from app.infrastructure.persistence.repositories.calendario_comercial_command_repository import (
    CODIGOS,
)
from app.infrastructure.persistence.repositories.calendario_comercial_sync_repository import (
    CalendarioComercialSyncCasLost,
    CalendarioComercialSyncRepository,
)
from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)

CALENDARIO_SYNC_CONSUMER = "administrativo.calendario_comercial"
CALENDARIO_SYNC_EVENTS = frozenset(
    {"calendario_comercial_creado", "calendario_comercial_programado"}
)
_RECONCILIABLE_CONSTRAINTS = frozenset(
    {
        "uq_configuracion_calendario_comercial_uid",
        "ux_configuracion_calendario_comercial_activa",
        "ux_configuracion_calendario_comercial_op_id_alta",
        "uq_valor_parametro_uid_global",
        "ux_valor_parametro_op_id_alta",
    }
)

_METADATA_FIELDS = frozenset({"uid_instalacion_origen", "payload_hash"})
_WRAPPER_FIELDS = frozenset({"metadata", "data"})
_VALUE_FIELDS = frozenset({"uid_global", "version_registro"})
_CREATED_FIELDS = frozenset(
    {
        "uid_global",
        "version_agregada",
        "vigente_desde",
        "fecha_hasta",
        "dia_cierre_comercial",
        "dia_vencimiento_predeterminado_cuotas",
        "valor_dia_cierre_comercial",
        "valor_dia_vencimiento_predeterminado_cuotas",
        "op_id",
    }
)
_PROGRAMMED_FIELDS = frozenset(
    {
        "uid_global",
        "version_agregada",
        "version_agregada_anterior",
        "vigente_desde",
        "fecha_desde_vigencia_anterior",
        "fecha_hasta_vigencia_anterior",
        "dia_cierre_comercial",
        "dia_vencimiento_predeterminado_cuotas",
        "valor_dia_cierre_comercial",
        "valor_dia_vencimiento_predeterminado_cuotas",
        "valor_anterior_dia_cierre_comercial",
        "valor_anterior_dia_vencimiento_predeterminado_cuotas",
        "op_id",
    }
)


class CalendarioComercialSyncPayloadError(ValueError):
    code = "SYNC_PAYLOAD_INVALID"


class CalendarioComercialSyncConcurrentApplyRetry(RuntimeError):
    """La historia cambió durante el CAS y debe reprocesarse desde #512."""


def _is_reconciliable_integrity_error(exc: IntegrityError) -> bool:
    """Sólo carreras UNIQUE conocidas pueden releerse como convergencia/conflicto."""
    original = getattr(exc, "orig", None)
    diagnostic = getattr(original, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", None)
    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    return sqlstate == "23505" and constraint in _RECONCILIABLE_CONSTRAINTS


def _invalid() -> None:
    raise CalendarioComercialSyncPayloadError(CalendarioComercialSyncPayloadError.code)


def _uuid(value: Any) -> tuple[str, UUID]:
    if not isinstance(value, str):
        _invalid()
    try:
        parsed = UUID(value)
    except (AttributeError, TypeError, ValueError):
        _invalid()
    if str(parsed) != value:
        _invalid()
    return value, parsed


def _positive_version(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        _invalid()
    return value


def _day(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 31:
        _invalid()
    return value


def _date(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 10 or not value.isascii():
        _invalid()
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _invalid()
    if parsed.isoformat() != value:
        _invalid()
    return value


def _portable_value(value: Any, *, expected_version: int | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _VALUE_FIELDS:
        _invalid()
    uid, _ = _uuid(value["uid_global"])
    version = _positive_version(value["version_registro"])
    if expected_version is not None and version != expected_version:
        _invalid()
    return {"uid_global": uid, "version_registro": version}


def _parse_data(event_type: str, value: Any) -> dict[str, Any]:
    expected = (
        _CREATED_FIELDS
        if event_type == "calendario_comercial_creado"
        else _PROGRAMMED_FIELDS
    )
    if not isinstance(value, dict) or set(value) != expected:
        _invalid()
    root_uid, _ = _uuid(value["uid_global"])
    op_id, op_id_uuid = _uuid(value["op_id"])
    version = _positive_version(value["version_agregada"])
    start = _date(value["vigente_desde"])
    values = {
        CODIGOS[0]: {
            **_portable_value(
                value["valor_dia_cierre_comercial"], expected_version=1
            ),
            "value": _day(value["dia_cierre_comercial"]),
        },
        CODIGOS[1]: {
            **_portable_value(
                value["valor_dia_vencimiento_predeterminado_cuotas"],
                expected_version=1,
            ),
            "value": _day(value["dia_vencimiento_predeterminado_cuotas"]),
        },
    }
    if len({item["uid_global"] for item in values.values()}) != 2:
        _invalid()
    parsed = {
        "event_type": event_type,
        "aggregate_uid": root_uid,
        "version_agregada": version,
        "version_registro": version,
        "vigente_desde": start,
        "op_id": op_id,
        "op_id_uuid": op_id_uuid,
        "values": values,
    }
    if event_type == "calendario_comercial_creado":
        if version != 1 or value["fecha_hasta"] is not None:
            _invalid()
        parsed["previous_values"] = None
        return parsed

    previous_version = _positive_version(value["version_agregada_anterior"])
    previous_start = _date(value["fecha_desde_vigencia_anterior"])
    previous_end = _date(value["fecha_hasta_vigencia_anterior"])
    if (
        version != previous_version + 1
        or previous_end != start
        or previous_start >= start
    ):
        _invalid()
    previous_values = {
        CODIGOS[0]: _portable_value(
            value["valor_anterior_dia_cierre_comercial"], expected_version=2
        ),
        CODIGOS[1]: _portable_value(
            value["valor_anterior_dia_vencimiento_predeterminado_cuotas"],
            expected_version=2,
        ),
    }
    all_uids = {item["uid_global"] for item in values.values()} | {
        item["uid_global"] for item in previous_values.values()
    }
    if len(all_uids) != 4:
        _invalid()
    parsed.update(
        {
            "version_agregada_anterior": previous_version,
            "fecha_desde_vigencia_anterior": previous_start,
            "fecha_hasta_vigencia_anterior": previous_end,
            "previous_values": previous_values,
        }
    )
    return parsed


def parse_calendario_outbox_envelope(
    *, event_type: str, aggregate_type: str, value: Any
) -> dict[str, Any]:
    if event_type not in CALENDARIO_SYNC_EVENTS or aggregate_type != "calendario_comercial":
        _invalid()
    if not isinstance(value, dict) or set(value) != _WRAPPER_FIELDS:
        _invalid()
    metadata = value["metadata"]
    if not isinstance(metadata, dict) or set(metadata) != _METADATA_FIELDS:
        _invalid()
    installation_uid, _ = _uuid(metadata["uid_instalacion_origen"])
    payload_hash = metadata["payload_hash"]
    if (
        not isinstance(payload_hash, str)
        or len(payload_hash) != 64
        or any(character not in "0123456789abcdef" for character in payload_hash)
    ):
        _invalid()
    data = value["data"]
    expected_hash = canonical_payload_hash(
        {"metadata": {"uid_instalacion_origen": installation_uid}, "data": data}
    )
    if payload_hash != expected_hash:
        _invalid()
    parsed = _parse_data(event_type, data)
    validate_sync_event(event_type, aggregate_type, value)
    return {
        **parsed,
        "payload": data,
        "provenance": {
            "installation_uid": installation_uid,
            "producer_payload_hash": payload_hash,
        },
    }


def register_calendario_outbox_delivery(
    session: Session, *, outbox_event: dict[str, Any]
) -> bool:
    event_id, _ = _uuid(str(outbox_event.get("event_id")))
    envelope = parse_calendario_outbox_envelope(
        event_type=outbox_event.get("event_type"),
        aggregate_type=outbox_event.get("aggregate_type"),
        value=outbox_event.get("payload"),
    )
    return InboxRepository(session).claim(
        event_id=event_id,
        event_type=envelope["event_type"],
        aggregate_type="calendario_comercial",
        aggregate_id=0,
        consumer=CALENDARIO_SYNC_CONSUMER,
        op_id=envelope["op_id"],
        payload=envelope["payload"],
        provenance=envelope["provenance"],
        aggregate_uid=envelope["aggregate_uid"],
        version_registro=envelope["version_agregada"],
    )


def _parse_retained_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = event.get("event_type")
    if (
        event_type not in CALENDARIO_SYNC_EVENTS
        or event.get("aggregate_type") != "calendario_comercial"
    ):
        _invalid()
    provenance = event.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) != {
        "installation_uid",
        "producer_payload_hash",
    }:
        _invalid()
    installation_uid, _ = _uuid(provenance["installation_uid"])
    producer_hash = provenance["producer_payload_hash"]
    data = event.get("payload")
    if producer_hash != canonical_payload_hash(
        {"metadata": {"uid_instalacion_origen": installation_uid}, "data": data}
    ):
        _invalid()
    parsed = _parse_data(event_type, data)
    if (
        parsed["aggregate_uid"] != event.get("aggregate_uid")
        or parsed["version_agregada"] != event.get("version_registro")
        or parsed["op_id"] != event.get("op_id")
    ):
        _invalid()
    return parsed


class CalendarioComercialSyncApplicator:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = CalendarioComercialSyncRepository(session)

    @staticmethod
    def _processed() -> InboxOutcome:
        return InboxOutcome(InboxOutcomeKind.PROCESSED)

    @staticmethod
    def _pending() -> InboxOutcome:
        return InboxOutcome(
            InboxOutcomeKind.PENDING_DEPENDENCY, "SYNC_DEPENDENCY_UNAVAILABLE"
        )

    @staticmethod
    def _conflict() -> InboxOutcome:
        return InboxOutcome(InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT")

    @staticmethod
    def _history_pairs(history: list[dict[str, Any]]) -> list[dict[str, dict[str, Any]]] | None:
        intervals: dict[tuple[Any, Any], dict[str, dict[str, Any]]] = {}
        for row in history:
            if row["deleted_at"] is not None:
                return None
            try:
                parsed = parse_parametro_entero(row["valor_parametro"])
            except ValueError:
                return None
            if not 1 <= parsed <= 31:
                return None
            start, end = row["fecha_desde"], row["fecha_hasta"]
            if start is None or (end is not None and start >= end):
                return None
            if row["es_valor_vigente"] is not (end is None):
                return None
            pair = intervals.setdefault((start, end), {})
            if row["codigo_parametro"] in pair:
                return None
            pair[row["codigo_parametro"]] = {**row, "parsed_value": parsed}
        ordered = sorted(intervals, key=lambda key: key[0])
        if not ordered or any(set(intervals[key]) != set(CODIGOS) for key in ordered):
            return None
        if any(left[1] != right[0] for left, right in pairwise(ordered)):
            return None
        if ordered[-1][1] is not None or sum(end is None for _, end in ordered) != 1:
            return None
        return [intervals[key] for key in ordered]

    @staticmethod
    def _pair_matches(
        pair: dict[str, dict[str, Any]],
        values: dict[str, dict[str, Any]],
        *,
        start: str,
        end: str | None,
    ) -> bool:
        for code in CODIGOS:
            row, expected = pair[code], values[code]
            if (
                str(row["uid_global"]) != expected["uid_global"]
                or row["version_registro"] != expected["version_registro"]
                or row["parsed_value"] != expected.get("value", row["parsed_value"])
                or row["fecha_desde"].date().isoformat() != start
                or (
                    row["fecha_hasta"].date().isoformat()
                    if row["fecha_hasta"] is not None
                    else None
                )
                != end
            ):
                return False
        return True

    def _equivalent(
        self, envelope: dict[str, Any], roots: list[dict[str, Any]], history: list[dict[str, Any]]
    ) -> bool:
        active = [row for row in roots if row["deleted_at"] is None]
        if (
            len(roots) != 1
            or len(active) != 1
            or str(active[0]["uid_global"]) != envelope["aggregate_uid"]
        ):
            return False
        if active[0]["version_registro"] != envelope["version_agregada"]:
            return False
        pairs = self._history_pairs(history)
        if pairs is None or len(pairs) != envelope["version_agregada"]:
            return False
        current = pairs[-1]
        if not self._pair_matches(
            current,
            envelope["values"],
            start=envelope["vigente_desde"],
            end=None,
        ):
            return False
        if envelope["event_type"] == "calendario_comercial_creado":
            return len(pairs) == 1
        if len(pairs) < 2:
            return False
        return self._pair_matches(
            pairs[-2],
            envelope["previous_values"],
            start=envelope["fecha_desde_vigencia_anterior"],
            end=envelope["fecha_hasta_vigencia_anterior"],
        )

    def _apply_created(
        self,
        envelope: dict[str, Any],
        definitions: dict[str, int],
        roots: list[dict[str, Any]],
        history: list[dict[str, Any]],
    ) -> InboxOutcome:
        if roots or history:
            return (
                self._processed()
                if self._equivalent(envelope, roots, history)
                else self._conflict()
            )
        incoming_uids = {value["uid_global"] for value in envelope["values"].values()}
        if self.repository.child_uid_owners(incoming_uids):
            return self._conflict()
        nested = self.session.begin_nested()
        try:
            self.repository.create_remote(definitions=definitions, envelope=envelope)
            nested.commit()
            return self._processed()
        except IntegrityError as exc:
            nested.rollback()
            if not _is_reconciliable_integrity_error(exc):
                raise
        roots = self.repository.lock_roots()
        history = self.repository.lock_history()
        return self._processed() if self._equivalent(envelope, roots, history) else self._conflict()

    def _apply_programmed(
        self,
        envelope: dict[str, Any],
        definitions: dict[str, int],
        roots: list[dict[str, Any]],
        history: list[dict[str, Any]],
    ) -> InboxOutcome:
        active = [row for row in roots if row["deleted_at"] is None]
        if not active:
            return self._pending() if not roots and not history else self._conflict()
        if (
            len(roots) != 1
            or len(active) != 1
            or str(active[0]["uid_global"]) != envelope["aggregate_uid"]
        ):
            return self._conflict()
        local_version = active[0]["version_registro"]
        incoming_version = envelope["version_agregada"]
        pairs = self._history_pairs(history)
        if pairs is None or len(pairs) != local_version:
            return self._conflict()
        if incoming_version < local_version:
            return self._processed()
        if incoming_version == local_version:
            return (
                self._processed()
                if self._equivalent(envelope, roots, history)
                else self._conflict()
            )
        if incoming_version > local_version + 1:
            return self._pending()
        if envelope["version_agregada_anterior"] != local_version:
            return self._conflict()
        current = pairs[-1]
        if not self._pair_matches(
            current,
            {
                code: {
                    "uid_global": envelope["previous_values"][code]["uid_global"],
                    "version_registro": envelope["previous_values"][code]["version_registro"] - 1,
                }
                for code in CODIGOS
            },
            start=envelope["fecha_desde_vigencia_anterior"],
            end=None,
        ):
            return self._conflict()
        new_uids = {value["uid_global"] for value in envelope["values"].values()}
        if self.repository.child_uid_owners(new_uids):
            return self._conflict()
        nested = self.session.begin_nested()
        try:
            root_version = self.repository.apply_programming(
                root_id=active[0]["id_configuracion_calendario_comercial"],
                definitions=definitions,
                previous_by_code=current,
                envelope=envelope,
            )
            if root_version != incoming_version:
                raise CalendarioComercialSyncCasLost("CALENDARIO_SYNC_CAS_LOST")
            nested.commit()
            return self._processed()
        except IntegrityError as exc:
            nested.rollback()
            if not _is_reconciliable_integrity_error(exc):
                raise
        except CalendarioComercialSyncCasLost as exc:
            nested.rollback()
            raise CalendarioComercialSyncConcurrentApplyRetry(
                "SYNC_CONCURRENT_APPLY_RETRY"
            ) from exc
        roots = self.repository.lock_roots()
        history = self.repository.lock_history()
        return self._processed() if self._equivalent(envelope, roots, history) else self._conflict()

    def apply(self, event: dict[str, Any]) -> InboxOutcome:
        try:
            envelope = _parse_retained_event(event)
        except CalendarioComercialSyncPayloadError:
            return InboxOutcome(
                InboxOutcomeKind.REJECTED, CalendarioComercialSyncPayloadError.code
            )
        # Todos los writers comparten el mismo orden: advisory del agregado,
        # raíz total, definiciones y finalmente historia ordenada por código/fecha/id.
        self.repository.lock_global()
        roots = self.repository.lock_roots()
        definition_status, definitions = self.repository.lock_definitions()
        if definition_status == "MISSING":
            return self._pending()
        if definition_status != "READY":
            return self._conflict()
        history = self.repository.lock_history()
        if envelope["event_type"] == "calendario_comercial_creado":
            return self._apply_created(envelope, definitions, roots, history)
        return self._apply_programmed(envelope, definitions, roots, history)


def run_calendario_inbox_once(
    session: Session,
    *,
    worker_id: str,
    event_id: str | None = None,
    manual: bool = False,
    lifecycle_session_factory: Callable[[], AbstractContextManager[Session]]
    | None = None,
) -> InboxOutcome | None:
    processor = InboxRetryProcessor(
        session,
        consumer=CALENDARIO_SYNC_CONSUMER,
        lifecycle_session_factory=lifecycle_session_factory,
    )
    return processor.run_once(
        CalendarioComercialSyncApplicator(session).apply,
        worker_id=worker_id,
        event_id=event_id,
        manual=manual,
    )


def transport_calendario_outbox_once(
    source_session: Session,
    destination_session: Session,
    *,
    limit: int = 100,
) -> tuple[int, int]:
    """Entrega at-least-once entre bases; no intenta un commit distribuido.

    Cada delivery se confirma primero en destino y recién después se acredita en
    origen. Si falla el ack de origen, la reentrega queda protegida por
    ``(event_id, consumer)`` en #512.
    """
    if source_session is destination_session:
        raise ValueError("CALENDARIO_SYNC_SOURCE_DESTINATION_MUST_DIFFER")
    repository = OutboxRepository(source_session)
    events = repository.get_pending_events(
        limit=limit, event_types=CALENDARIO_SYNC_EVENTS
    )
    registered = 0
    for event in events:
        try:
            created = register_calendario_outbox_delivery(
                destination_session, outbox_event=event
            )
            destination_session.commit()
        except Exception:
            destination_session.rollback()
            source_session.rollback()
            raise
        try:
            repository.mark_as_published(event["id"])
            source_session.commit()
        except Exception:
            source_session.rollback()
            raise
        registered += int(created)
    return len(events), registered
