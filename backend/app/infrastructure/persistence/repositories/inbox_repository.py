from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.common.idempotency import (
    NonCanonicalizablePayload,
    canonical_payload_hash,
)
from app.application.common.synchronization_policy import (
    validate_retained_sync_envelope,
)

INBOX_STATUSES = frozenset(
    {"PENDING_DEPENDENCY", "PROCESSING", "PROCESSED", "REJECTED", "CONFLICTO"}
)


class InboxOwnershipLost(RuntimeError):
    code = "SYNC_INBOX_OWNERSHIP_LOST"


class InboxPortableTargetRequired(RuntimeError):
    code = "SYNC_PORTABLE_TARGET_REQUIRED"


class InboxOperationIdRequired(RuntimeError):
    code = "SYNC_OPERATION_ID_REQUIRED"


class InboxInvalidPortableTarget(RuntimeError):
    code = "SYNC_INVALID_PORTABLE_TARGET"


class InboxInvalidFingerprint(RuntimeError):
    code = "SYNC_INBOX_FINGERPRINT_INVALID"


class InboxInvalidVersion(RuntimeError):
    code = "SYNC_INVALID_VERSION_REGISTRO"


class OperationDecision(StrEnum):
    ACQUIRED = "ACQUIRED"
    BUSY = "BUSY"
    REPLAY_PROCESSED = "REPLAY_PROCESSED"
    REPLAY_CONFLICT = "REPLAY_CONFLICT"
    INCOMPATIBLE = "INCOMPATIBLE"


@dataclass(frozen=True, slots=True)
class DeliveryClaim:
    """Identidad concreta e intransferible de una adquisición de delivery."""

    event: dict[str, Any]
    attempt_id: str
    worker_id: str
    fence_generation: int

    def __getitem__(self, key: str) -> Any:
        return self.event[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.event.get(key, default)


@dataclass(frozen=True, slots=True)
class OperationClaim:
    consumer: str
    op_id: str
    attempt_id: str
    fence_generation: int


@dataclass(frozen=True, slots=True)
class OperationScopeDecision:
    decision: OperationDecision
    claim: OperationClaim | None = None


def canonicalize_version_registro(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise InboxInvalidVersion(InboxInvalidVersion.code)
    if isinstance(value, int):
        canonical = value
    elif isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value):
        canonical = int(value)
    else:
        raise InboxInvalidVersion(InboxInvalidVersion.code)
    if not 1 <= canonical <= 2**31 - 1:
        raise InboxInvalidVersion(InboxInvalidVersion.code)
    return canonical


def compute_retained_envelope_fingerprint(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_uid: Any,
    version_registro: Any,
    payload: dict[str, Any] | None,
    provenance: dict[str, Any] | None,
    op_id: Any,
) -> str | None:
    if op_id is None and payload is None and provenance is None:
        return None
    try:
        canonical_uid = (
            str(UUID(str(aggregate_uid))) if aggregate_uid is not None else None
        )
    except (AttributeError, TypeError, ValueError):
        raise InboxInvalidPortableTarget(InboxInvalidPortableTarget.code) from None
    return canonical_payload_hash(
        {
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_uid": canonical_uid,
            "version_registro": canonicalize_version_registro(version_registro),
            "payload": payload,
            "provenance": provenance,
        }
    )


def has_valid_scoped_fingerprint(delivery: dict[str, Any] | DeliveryClaim) -> bool:
    if delivery.get("op_id") is None:
        return True
    stored = delivery.get("payload_fingerprint")
    if stored is None:
        return False
    try:
        expected = compute_retained_envelope_fingerprint(
            event_type=delivery["event_type"],
            aggregate_type=delivery["aggregate_type"],
            aggregate_uid=delivery.get("aggregate_uid"),
            version_registro=delivery.get("version_registro"),
            payload=delivery.get("payload"),
            provenance=delivery.get("provenance"),
            op_id=delivery.get("op_id"),
        )
    except NonCanonicalizablePayload:
        return False
    return stored == expected


class InboxRepository:
    """Lifecycle técnico del inbox; nunca decide semántica del consumer."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _map_row(row: Any) -> dict[str, Any]:
        value = dict(row)
        value["event_id"] = str(value["event_id"])
        for key in ("op_id", "aggregate_uid", "attempt_id"):
            if value.get(key) is not None:
                value[key] = str(value[key])
        return value

    def claim(
        self,
        *,
        event_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: int,
        consumer: str,
        op_id: str | None = None,
        payload: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
        aggregate_uid: str | None = None,
        version_registro: int | str | None = None,
    ) -> bool:
        """Registra una delivery; True no concede derecho funcional scoped."""
        retained_envelope = any(
            value is not None
            for value in (payload, provenance, aggregate_uid, version_registro)
        )
        if op_id is None and retained_envelope:
            raise InboxOperationIdRequired(InboxOperationIdRequired.code)
        if op_id is not None and aggregate_uid is None:
            raise InboxPortableTargetRequired(InboxPortableTargetRequired.code)
        try:
            canonical_uid = (
                str(UUID(str(aggregate_uid))) if aggregate_uid is not None else None
            )
        except (AttributeError, TypeError, ValueError):
            raise InboxInvalidPortableTarget(InboxInvalidPortableTarget.code) from None
        canonical_version = canonicalize_version_registro(version_registro)
        validate_retained_sync_envelope(
            event_type=event_type,
            aggregate_type=aggregate_type,
            payload=payload,
            provenance=provenance,
            op_id=op_id,
            aggregate_uid=canonical_uid,
            version_registro=canonical_version,
        )
        fingerprint = compute_retained_envelope_fingerprint(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_uid=canonical_uid,
            version_registro=canonical_version,
            payload=payload,
            provenance=provenance,
            op_id=op_id,
        )
        portable = op_id is not None
        result = self.db.execute(
            text("""
            INSERT INTO inbox_event (
                event_id, event_type, aggregate_type, aggregate_id, consumer,
                status, created_at, op_id, aggregate_uid, version_registro,
                payload, payload_fingerprint, provenance, next_attempt_at
            ) VALUES (
                CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
                :consumer, :status, now(), CAST(:op_id AS uuid),
                CAST(:aggregate_uid AS uuid), :version_registro,
                CAST(:payload AS jsonb), :fingerprint, CAST(:provenance AS jsonb),
                CASE WHEN CAST(:portable AS boolean)
                     THEN clock_timestamp() AT TIME ZONE 'UTC' ELSE NULL END
            ) ON CONFLICT (event_id, consumer) DO NOTHING
        """),
            {
                "event_id": event_id,
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "consumer": consumer,
                "status": "PENDING_DEPENDENCY" if portable else "PROCESSING",
                "op_id": op_id,
                "aggregate_uid": canonical_uid,
                "version_registro": canonical_version,
                "payload": json.dumps(payload) if payload is not None else None,
                "fingerprint": fingerprint,
                "provenance": json.dumps(provenance)
                if provenance is not None
                else None,
                "portable": portable,
            },
        )
        return result.rowcount == 1

    @staticmethod
    def _canonical_envelope_fingerprint(**kwargs: Any) -> str | None:
        return compute_retained_envelope_fingerprint(**kwargs)

    def list_eligible(
        self, *, limit: int, automatic_attempt_limit: int, now: datetime | None = None
    ) -> list[dict[str, Any]]:
        del now
        rows = (
            self.db.execute(
                text("""
            WITH db_clock AS (SELECT clock_timestamp() AT TIME ZONE 'UTC' AS now_utc)
            SELECT i.* FROM inbox_event i, db_clock
             WHERE status='PENDING_DEPENDENCY' AND attempt_count < :attempt_limit
               AND (next_attempt_at IS NULL OR next_attempt_at <= db_clock.now_utc)
             ORDER BY next_attempt_at NULLS FIRST, created_at, id LIMIT :limit
        """),
                {"attempt_limit": automatic_attempt_limit, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [self._map_row(row) for row in rows]

    def claim_pending(
        self,
        *,
        consumer: str,
        worker_id: str,
        lease_duration: timedelta,
        automatic_attempt_limit: int,
        now: datetime | None = None,
        event_id: str | None = None,
        manual: bool = False,
    ) -> DeliveryClaim | None:
        """Adquiere una pending elegible o hace takeover atómico de una vencida."""
        del now
        attempt_id = str(uuid4())
        row = (
            self.db.execute(
                text("""
            WITH db_clock AS (SELECT clock_timestamp() AT TIME ZONE 'UTC' AS now_utc),
            candidate AS (
                SELECT i.id FROM inbox_event i, db_clock
                 WHERE consumer=:consumer
                   AND (CAST(:event_id AS uuid) IS NULL OR event_id=CAST(:event_id AS uuid))
                   AND (
                       (
                           status='PENDING_DEPENDENCY'
                           AND op_id IS NOT NULL
                           AND aggregate_uid IS NOT NULL
                           AND payload IS NOT NULL
                           AND payload_fingerprint IS NOT NULL
                           AND attempt_id IS NULL
                           AND worker_id IS NULL
                           AND lease_expires_at IS NULL
                           AND (CAST(:manual AS boolean)
                                OR attempt_count < :attempt_limit)
                           AND (CAST(:manual AS boolean) OR next_attempt_at IS NULL
                                OR next_attempt_at <= db_clock.now_utc)
                       )
                       OR (
                           status='PROCESSING'
                           AND op_id IS NOT NULL
                           AND attempt_id IS NOT NULL
                           AND lease_expires_at IS NOT NULL
                           AND lease_expires_at <= db_clock.now_utc
                           AND (CAST(:manual AS boolean)
                                OR attempt_count < :attempt_limit)
                       )
                   )
                 ORDER BY next_attempt_at NULLS FIRST, created_at, id
                 FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE inbox_event i SET status='PROCESSING',
                attempt_id=CAST(:attempt_id AS uuid), worker_id=:worker_id,
                lease_expires_at=db_clock.now_utc + :lease_duration,
                attempt_count=i.attempt_count + 1,
                fence_generation=i.fence_generation + 1,
                last_attempt_at=db_clock.now_utc, processed_at=NULL
              FROM candidate, db_clock WHERE i.id=candidate.id RETURNING i.*
        """),
                {
                    "consumer": consumer,
                    "event_id": event_id,
                    "manual": manual,
                    "attempt_limit": automatic_attempt_limit,
                    "attempt_id": attempt_id,
                    "worker_id": worker_id,
                    "lease_duration": lease_duration,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        event = self._map_row(row)
        return DeliveryClaim(event, attempt_id, worker_id, event["fence_generation"])

    def acquire_operation_scope(
        self, *, delivery: DeliveryClaim
    ) -> OperationScopeDecision:
        """Adquiere o clasifica atómicamente la única autoridad funcional."""
        params = {
            "consumer": delivery["consumer"],
            "op_id": delivery["op_id"],
            "fingerprint": delivery["payload_fingerprint"],
            "attempt_id": delivery.attempt_id,
            "worker_id": delivery.worker_id,
            "lease_expires_at": delivery["lease_expires_at"],
        }
        generation = self.db.execute(
            text("""
            WITH db_clock AS (SELECT clock_timestamp() AT TIME ZONE 'UTC' AS now_utc)
            INSERT INTO inbox_operation_scope (
                consumer, op_id, payload_fingerprint, attempt_id, worker_id,
                lease_expires_at, fence_generation, updated_at
            ) SELECT :consumer, CAST(:op_id AS uuid), :fingerprint,
                     CAST(:attempt_id AS uuid), :worker_id, :lease_expires_at, 1, now_utc
                FROM db_clock
            ON CONFLICT (consumer, op_id) DO NOTHING
            RETURNING fence_generation
        """),
            params,
        ).scalar_one_or_none()
        if generation is None:
            generation = self.db.execute(
                text("""
                WITH db_clock AS (SELECT clock_timestamp() AT TIME ZONE 'UTC' AS now_utc)
                UPDATE inbox_operation_scope s SET
                    attempt_id=CAST(:attempt_id AS uuid), worker_id=:worker_id,
                    lease_expires_at=:lease_expires_at,
                    fence_generation=s.fence_generation + 1, updated_at=db_clock.now_utc
                  FROM db_clock
                 WHERE s.consumer=:consumer AND s.op_id=CAST(:op_id AS uuid)
                   AND s.payload_fingerprint=:fingerprint AND s.terminal_status IS NULL
                   AND (s.attempt_id IS NULL OR s.lease_expires_at <= db_clock.now_utc)
                RETURNING s.fence_generation
            """),
                params,
            ).scalar_one_or_none()
        if generation is not None:
            return OperationScopeDecision(
                OperationDecision.ACQUIRED,
                OperationClaim(
                    params["consumer"], params["op_id"], delivery.attempt_id, generation
                ),
            )
        row = (
            self.db.execute(
                text("""
            SELECT payload_fingerprint, terminal_status
              FROM inbox_operation_scope
             WHERE consumer=:consumer AND op_id=CAST(:op_id AS uuid)
        """),
                params,
            )
            .mappings()
            .one()
        )
        if row["payload_fingerprint"] != params["fingerprint"]:
            decision = OperationDecision.INCOMPATIBLE
        elif row["terminal_status"] == "PROCESSED":
            decision = OperationDecision.REPLAY_PROCESSED
        elif row["terminal_status"] == "CONFLICTO":
            decision = OperationDecision.REPLAY_CONFLICT
        else:
            decision = OperationDecision.BUSY
        return OperationScopeDecision(decision)

    def finish_operation_scope(
        self, *, claim: OperationClaim, terminal_status: str | None
    ) -> None:
        result = self.db.execute(
            text("""
            UPDATE inbox_operation_scope
               SET terminal_status=CAST(:terminal_status AS varchar),
                   attempt_id=NULL, worker_id=NULL,
                   lease_expires_at=NULL,
                   updated_at=clock_timestamp() AT TIME ZONE 'UTC'
             WHERE consumer=:consumer AND op_id=CAST(:op_id AS uuid)
               AND attempt_id=CAST(:attempt_id AS uuid)
               AND fence_generation=:fence_generation AND terminal_status IS NULL
        """),
            {
                "consumer": claim.consumer,
                "op_id": claim.op_id,
                "attempt_id": claim.attempt_id,
                "fence_generation": claim.fence_generation,
                "terminal_status": terminal_status,
            },
        )
        if result.rowcount != 1:
            raise InboxOwnershipLost(InboxOwnershipLost.code)

    def get_operation_scope(
        self, *, consumer: str, op_id: str
    ) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text("""
            SELECT * FROM inbox_operation_scope
             WHERE consumer=:consumer AND op_id=CAST(:op_id AS uuid)
        """),
                {"consumer": consumer, "op_id": op_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        value = dict(row)
        for key in ("op_id", "attempt_id"):
            if value.get(key) is not None:
                value[key] = str(value[key])
        return value

    def mark_pending_dependency(
        self,
        *,
        claim: DeliveryClaim,
        reason_code: str,
        next_attempt_at: datetime | None = None,
        retry_delay: timedelta | None = None,
        consume_attempt: bool = True,
    ) -> None:
        if next_attempt_at is not None and retry_delay is not None:
            raise ValueError("SYNC_INBOX_RETRY_SCHEDULE_INVALID")
        self._transition(
            claim,
            "PENDING_DEPENDENCY",
            reason_code,
            next_attempt_at=next_attempt_at,
            retry_delay=retry_delay,
            consume_attempt=consume_attempt,
        )

    def mark_as_processed(
        self,
        *,
        claim: DeliveryClaim | None = None,
        event_id: str | None = None,
        consumer: str | None = None,
    ) -> None:
        self._transition_compat(claim, event_id, consumer, "PROCESSED", None)

    def mark_as_rejected(
        self,
        *,
        error_detail: str,
        claim: DeliveryClaim | None = None,
        event_id: str | None = None,
        consumer: str | None = None,
    ) -> None:
        self._transition_compat(claim, event_id, consumer, "REJECTED", error_detail)

    def mark_conflict(
        self, *, claim: DeliveryClaim, reason_code: str = "SYNC_OPERATION_CONFLICT"
    ) -> None:
        self._transition(claim, "CONFLICTO", reason_code)

    def _transition_compat(
        self,
        claim: DeliveryClaim | None,
        event_id: str | None,
        consumer: str | None,
        status: str,
        reason: str | None,
    ) -> None:
        if claim is not None:
            self._transition(claim, status, reason)
            return
        if event_id is None or consumer is None:
            raise TypeError("claim or legacy event_id/consumer is required")
        result = self.db.execute(
            text("""
            UPDATE inbox_event SET status=:status, processed_at=:processed_at,
                error_detail=:reason
             WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer
               AND status='PROCESSING' AND attempt_id IS NULL
               AND lease_expires_at IS NULL
        """),
            {
                "status": status,
                "processed_at": datetime.now(UTC),
                "reason": reason,
                "event_id": event_id,
                "consumer": consumer,
            },
        )
        if result.rowcount != 1:
            leased = self.db.execute(
                text("""
                SELECT 1 FROM inbox_event
                 WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer
                   AND status='PROCESSING' AND attempt_id IS NOT NULL
            """),
                {"event_id": event_id, "consumer": consumer},
            ).scalar_one_or_none()
            if leased is not None:
                raise InboxOwnershipLost(InboxOwnershipLost.code)

    def _transition(
        self,
        claim: DeliveryClaim,
        status: str,
        reason: str | None,
        *,
        next_attempt_at: datetime | None = None,
        retry_delay: timedelta | None = None,
        consume_attempt: bool = True,
    ) -> None:
        if status not in INBOX_STATUSES:
            raise ValueError("SYNC_INBOX_TRANSITION_INVALID")
        result = self.db.execute(
            text("""
            WITH db_clock AS (SELECT clock_timestamp() AT TIME ZONE 'UTC' AS now_utc)
            UPDATE inbox_event SET status=CAST(:status AS varchar),
                processed_at=CASE
                    WHEN CAST(:status AS varchar) IN ('PROCESSED','REJECTED','CONFLICTO')
                                  THEN db_clock.now_utc ELSE NULL END,
                error_detail=:reason,
                next_attempt_at=CASE
                    WHEN CAST(:retry_delay AS interval) IS NOT NULL
                    THEN db_clock.now_utc + CAST(:retry_delay AS interval)
                    ELSE CAST(:next_attempt_at AS timestamp) END,
                attempt_count=CASE WHEN CAST(:consume_attempt AS boolean)
                                   THEN attempt_count
                                   ELSE GREATEST(attempt_count - 1, 0) END,
                attempt_id=NULL, worker_id=NULL, lease_expires_at=NULL
              FROM db_clock
             WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer
               AND status='PROCESSING' AND attempt_id=CAST(:attempt_id AS uuid)
               AND fence_generation=:fence_generation
        """),
            {
                "status": status,
                "reason": reason,
                "next_attempt_at": next_attempt_at,
                "retry_delay": retry_delay,
                "consume_attempt": consume_attempt,
                "event_id": claim["event_id"],
                "consumer": claim["consumer"],
                "attempt_id": claim.attempt_id,
                "fence_generation": claim.fence_generation,
            },
        )
        if result.rowcount != 1:
            raise InboxOwnershipLost(InboxOwnershipLost.code)

    def is_processed(self, *, event_id: str, consumer: str) -> bool:
        return (
            self.db.execute(
                text("""
            SELECT 1 FROM inbox_event
             WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer
               AND status='PROCESSED'
        """),
                {"event_id": event_id, "consumer": consumer},
            ).scalar_one_or_none()
            is not None
        )

    def get(self, *, event_id: str, consumer: str) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text("""
            SELECT * FROM inbox_event
             WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer
        """),
                {"event_id": event_id, "consumer": consumer},
            )
            .mappings()
            .one_or_none()
        )
        return self._map_row(row) if row else None
