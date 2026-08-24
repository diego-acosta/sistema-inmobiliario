from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.common.idempotency import canonical_payload_hash

INBOX_STATUSES = frozenset(
    {"PENDING_DEPENDENCY", "PROCESSING", "PROCESSED", "REJECTED", "CONFLICTO"}
)


class InboxOwnershipLost(RuntimeError):
    code = "SYNC_INBOX_OWNERSHIP_LOST"


class InboxPortableTargetRequired(RuntimeError):
    code = "SYNC_PORTABLE_TARGET_REQUIRED"


class InboxRepository:
    """Lifecycle técnico del inbox; nunca decide semántica del consumer."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _map_row(row: Any) -> dict[str, Any]:
        value = dict(row)
        value["event_id"] = str(value["event_id"])
        if value.get("op_id") is not None:
            value["op_id"] = str(value["op_id"])
        return value

    def claim(
        self, *, event_id: str, event_type: str, aggregate_type: str,
        aggregate_id: int, consumer: str, op_id: str | None = None,
        payload: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
        aggregate_uid: str | None = None,
        version_registro: int | None = None,
    ) -> bool:
        if op_id is not None and aggregate_uid is None:
            raise InboxPortableTargetRequired(InboxPortableTargetRequired.code)
        fingerprint = self._canonical_envelope_fingerprint(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_uid=aggregate_uid,
            version_registro=version_registro,
            payload=payload,
            provenance=provenance,
            op_id=op_id,
        )
        result = self.db.execute(text("""
            INSERT INTO inbox_event (
                event_id, event_type, aggregate_type, aggregate_id, consumer,
                status, created_at, op_id, aggregate_uid, version_registro,
                payload, payload_fingerprint, provenance
            ) VALUES (
                CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
                :consumer, 'PROCESSING', now(), CAST(:op_id AS uuid),
                CAST(:aggregate_uid AS uuid), :version_registro,
                CAST(:payload AS jsonb), :fingerprint, CAST(:provenance AS jsonb)
            ) ON CONFLICT (event_id, consumer) DO NOTHING
        """), {
            "event_id": event_id, "event_type": event_type,
            "aggregate_type": aggregate_type, "aggregate_id": aggregate_id,
            "consumer": consumer, "op_id": op_id,
            "aggregate_uid": aggregate_uid,
            "version_registro": version_registro,
            "payload": json.dumps(payload) if payload is not None else None,
            "fingerprint": fingerprint,
            "provenance": json.dumps(provenance) if provenance is not None else None,
        })
        return result.rowcount == 1

    @staticmethod
    def _canonical_envelope_fingerprint(
        *, event_type: str, aggregate_type: str, aggregate_uid: str | None,
        version_registro: int | None, payload: dict[str, Any] | None,
        provenance: dict[str, Any] | None, op_id: str | None,
    ) -> str | None:
        """Hash RFC 8785 del material portable; nunca confía en un hash externo."""
        if op_id is None and payload is None and provenance is None:
            return None  # claim legacy sin envelope portable suficiente
        envelope = {
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_uid": aggregate_uid,
            "version_registro": version_registro,
            "payload": payload,
            "provenance": provenance,
        }
        return canonical_payload_hash(envelope)

    def list_eligible(self, *, limit: int, automatic_attempt_limit: int,
                      now: datetime | None = None) -> list[dict[str, Any]]:
        rows = self.db.execute(text("""
            SELECT * FROM inbox_event
             WHERE status = 'PENDING_DEPENDENCY'
               AND attempt_count < :attempt_limit
               AND (next_attempt_at IS NULL OR next_attempt_at <= :now)
             ORDER BY next_attempt_at NULLS FIRST, created_at, id LIMIT :limit
        """), {"attempt_limit": automatic_attempt_limit,
                 "now": now or datetime.now(UTC), "limit": limit}).mappings().all()
        return [self._map_row(row) for row in rows]

    def claim_pending(self, *, consumer: str, lease_owner: str,
                      lease_duration: timedelta, automatic_attempt_limit: int,
                      now: datetime | None = None, event_id: str | None = None,
                      manual: bool = False) -> dict[str, Any] | None:
        current = now or datetime.now(UTC)
        row = self.db.execute(text("""
            WITH candidate AS (
                SELECT id FROM inbox_event
                 WHERE consumer = :consumer AND status = 'PENDING_DEPENDENCY'
                   AND (CAST(:event_id AS uuid) IS NULL OR event_id = CAST(:event_id AS uuid))
                   AND (CAST(:manual AS boolean) OR attempt_count < :attempt_limit)
                   AND (CAST(:manual AS boolean) OR next_attempt_at IS NULL OR next_attempt_at <= :now)
                 ORDER BY next_attempt_at NULLS FIRST, created_at, id
                 FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE inbox_event i SET status='PROCESSING', lease_owner=:owner,
                lease_expires_at=:expires, attempt_count=i.attempt_count + 1,
                lease_generation=i.lease_generation + 1,
                last_attempt_at=:now, processed_at=NULL
              FROM candidate WHERE i.id=candidate.id RETURNING i.*
        """), {"consumer": consumer, "event_id": event_id, "manual": manual,
                 "attempt_limit": automatic_attempt_limit, "now": current,
                 "owner": lease_owner, "expires": current + lease_duration}).mappings().one_or_none()
        return self._map_row(row) if row else None

    def reclaim_expired(self, *, consumer: str, now: datetime | None = None) -> int:
        result = self.db.execute(text("""
            UPDATE inbox_event SET status='PENDING_DEPENDENCY', lease_owner=NULL,
                lease_expires_at=NULL, next_attempt_at=:now,
                error_detail='SYNC_WORKER_LEASE_EXPIRED'
             WHERE consumer=:consumer AND status='PROCESSING'
               AND lease_expires_at IS NOT NULL
               AND lease_expires_at <= :now
        """), {"consumer": consumer, "now": now or datetime.now(UTC)})
        return result.rowcount

    def get_operation_scope_deliveries(
        self, *, consumer: str, op_id: str, exclude_id: int
    ) -> list[dict[str, Any]]:
        """Entrega todo el scope relevante; REJECTED no es un receipt aplicable."""
        rows = self.db.execute(text("""
            SELECT * FROM inbox_event
             WHERE consumer=:consumer AND op_id=CAST(:op_id AS uuid) AND id<>:id
               AND status IN (
                   'PENDING_DEPENDENCY', 'PROCESSING', 'PROCESSED', 'CONFLICTO'
               )
             ORDER BY id
        """), {"consumer": consumer, "op_id": op_id, "id": exclude_id}).mappings().all()
        return [self._map_row(row) for row in rows]

    def mark_pending_dependency(self, *, event_id: str, consumer: str,
                                reason_code: str, next_attempt_at: datetime,
                                lease_owner: str | None = None,
                                lease_generation: int | None = None) -> None:
        self._transition(event_id, consumer, "PENDING_DEPENDENCY", reason_code,
                         next_attempt_at=next_attempt_at, lease_owner=lease_owner,
                         lease_generation=lease_generation)

    def mark_as_processed(self, *, event_id: str, consumer: str,
                          lease_owner: str | None = None,
                          lease_generation: int | None = None) -> None:
        self._transition(event_id, consumer, "PROCESSED", None,
                         processed_at=datetime.now(UTC), lease_owner=lease_owner,
                         lease_generation=lease_generation)

    def mark_as_rejected(self, *, event_id: str, consumer: str, error_detail: str,
                         lease_owner: str | None = None,
                         lease_generation: int | None = None) -> None:
        self._transition(event_id, consumer, "REJECTED", error_detail,
                         processed_at=datetime.now(UTC), lease_owner=lease_owner,
                         lease_generation=lease_generation)

    def mark_conflict(self, *, event_id: str, consumer: str,
                      reason_code: str = "SYNC_OPERATION_CONFLICT",
                      lease_owner: str | None = None,
                      lease_generation: int | None = None) -> None:
        self._transition(event_id, consumer, "CONFLICTO", reason_code,
                         processed_at=datetime.now(UTC), lease_owner=lease_owner,
                         lease_generation=lease_generation)

    def _transition(self, event_id: str, consumer: str, status: str,
                    reason: str | None, **timestamps: Any) -> None:
        if status not in INBOX_STATUSES:
            raise ValueError("SYNC_INBOX_TRANSITION_INVALID")
        lease_owner = timestamps.get("lease_owner")
        lease_generation = timestamps.get("lease_generation")
        if (lease_owner is None) != (lease_generation is None):
            raise InboxOwnershipLost(InboxOwnershipLost.code)
        fenced = lease_owner is not None
        result = self.db.execute(text("""
            UPDATE inbox_event SET status=:status, processed_at=:processed_at,
                error_detail=:reason, next_attempt_at=:next_attempt_at,
                lease_owner=NULL, lease_expires_at=NULL
             WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer
               AND status='PROCESSING'
               AND (
                    (NOT CAST(:fenced AS boolean)
                     AND lease_owner IS NULL AND lease_expires_at IS NULL)
                    OR
                    (CAST(:fenced AS boolean)
                     AND lease_owner=:lease_owner
                     AND lease_generation=:lease_generation
                     AND lease_expires_at > :ownership_now)
               )
        """), {"status": status, "processed_at": timestamps.get("processed_at"),
                 "next_attempt_at": timestamps.get("next_attempt_at"),
                 "reason": reason, "event_id": event_id, "consumer": consumer,
                 "fenced": fenced, "lease_owner": lease_owner,
                 "lease_generation": lease_generation,
                 "ownership_now": datetime.now(UTC)})
        if result.rowcount == 1:
            return
        stored_is_leased = self.db.execute(text("""
            SELECT 1 FROM inbox_event
             WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer
               AND status='PROCESSING'
               AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL
        """), {"event_id": event_id, "consumer": consumer}).scalar_one_or_none()
        if fenced or stored_is_leased is not None:
            raise InboxOwnershipLost(InboxOwnershipLost.code)

    def is_processed(self, *, event_id: str, consumer: str) -> bool:
        return self.db.execute(text("""SELECT 1 FROM inbox_event WHERE
            event_id=CAST(:event_id AS uuid) AND consumer=:consumer
            AND status='PROCESSED'"""), {"event_id": event_id,
                                         "consumer": consumer}).scalar_one_or_none() is not None

    def get(self, *, event_id: str, consumer: str) -> dict[str, Any] | None:
        row = self.db.execute(text("""SELECT * FROM inbox_event WHERE
            event_id=CAST(:event_id AS uuid) AND consumer=:consumer"""),
            {"event_id": event_id, "consumer": consumer}).mappings().one_or_none()
        return self._map_row(row) if row else None
