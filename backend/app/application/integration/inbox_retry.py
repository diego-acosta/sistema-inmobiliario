"""Entry point reusable para retry de inbox; el consumer conserva la semántica."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository

DEFAULT_LEASE = timedelta(minutes=5)
DEFAULT_AUTOMATIC_ATTEMPT_LIMIT = 8
MAX_BACKOFF = timedelta(hours=6)
SANITIZED_REASON_CODES = frozenset({
    "SYNC_DEPENDENCY_UNAVAILABLE", "SYNC_PAYLOAD_INVALID",
    "SYNC_OPERATION_CONFLICT", "SYNC_FUNCTIONAL_FAILURE",
})


class InboxOutcomeKind(StrEnum):
    PROCESSED = "PROCESSED"
    PENDING_DEPENDENCY = "PENDING_DEPENDENCY"
    REJECTED = "REJECTED"
    CONFLICTO = "CONFLICTO"


@dataclass(frozen=True, slots=True)
class InboxOutcome:
    kind: InboxOutcomeKind
    reason_code: str | None = None


def retry_backoff(attempt_count: int) -> timedelta:
    seconds = min(30 * (2 ** max(attempt_count - 1, 0)), int(MAX_BACKOFF.total_seconds()))
    return timedelta(seconds=seconds)


class InboxRetryProcessor:
    def __init__(self, session: Session, *, consumer: str,
                 lease_duration: timedelta = DEFAULT_LEASE,
                 automatic_attempt_limit: int = DEFAULT_AUTOMATIC_ATTEMPT_LIMIT) -> None:
        self.session = session
        self.consumer = consumer
        self.repository = InboxRepository(session)
        self.lease_duration = lease_duration
        self.automatic_attempt_limit = automatic_attempt_limit

    def run_once(self, applicator: Callable[[dict], InboxOutcome], *, worker_id: str,
                 event_id: str | None = None, manual: bool = False,
                 now: datetime | None = None) -> InboxOutcome | None:
        current = now or datetime.now(UTC)
        self.repository.reclaim_expired(consumer=self.consumer, now=current)
        event = self.repository.claim_pending(
            consumer=self.consumer, lease_owner=worker_id,
            lease_duration=self.lease_duration,
            automatic_attempt_limit=self.automatic_attempt_limit,
            event_id=event_id, manual=manual, now=current,
        )
        if event is None:
            return None

        # Scope técnico consumer/op_id: serializa entregas distintas de una operación.
        if event.get("op_id"):
            self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:scope), hashtext(:op))"),
                                 {"scope": self.consumer, "op": event["op_id"]})
            deliveries = self.repository.get_operation_scope_deliveries(
                consumer=self.consumer, op_id=event["op_id"], exclude_id=event["id"]
            )
            if any(
                delivery["payload_fingerprint"] != event["payload_fingerprint"]
                for delivery in deliveries
            ):
                outcome = InboxOutcome(InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT")
                self.repository.mark_conflict(event_id=event["event_id"], consumer=self.consumer)
                return outcome
            if any(delivery["status"] == "PROCESSED" for delivery in deliveries):
                outcome = InboxOutcome(InboxOutcomeKind.PROCESSED)
                self.repository.mark_as_processed(event_id=event["event_id"], consumer=self.consumer)
                return outcome
            compatible_in_flight = [
                delivery for delivery in deliveries
                if delivery["status"] in {"PENDING_DEPENDENCY", "PROCESSING"}
            ]
            if any(delivery["status"] == "PROCESSING" for delivery in compatible_in_flight) or (
                compatible_in_flight
                and min(delivery["id"] for delivery in compatible_in_flight) < event["id"]
            ):
                outcome = InboxOutcome(
                    InboxOutcomeKind.PENDING_DEPENDENCY,
                    "SYNC_DEPENDENCY_UNAVAILABLE",
                )
                self.repository.mark_pending_dependency(
                    event_id=event["event_id"], consumer=self.consumer,
                    reason_code=outcome.reason_code,
                    next_attempt_at=current + retry_backoff(event["attempt_count"]),
                )
                return outcome

        nested = self.session.begin_nested()
        try:
            outcome = applicator(event)
            if not isinstance(outcome, InboxOutcome):
                raise TypeError("consumer must return InboxOutcome")
            if outcome.kind is InboxOutcomeKind.PROCESSED:
                nested.commit()
                self.repository.mark_as_processed(event_id=event["event_id"], consumer=self.consumer)
                return outcome
            nested.rollback()  # descarta cualquier efecto funcional parcial
        except Exception:
            nested.rollback()
            raise

        reason = outcome.reason_code
        if reason not in SANITIZED_REASON_CODES:
            reason = "SYNC_FUNCTIONAL_FAILURE"
        if outcome.kind is InboxOutcomeKind.PENDING_DEPENDENCY:
            self.repository.mark_pending_dependency(
                event_id=event["event_id"], consumer=self.consumer, reason_code=reason,
                next_attempt_at=current + retry_backoff(event["attempt_count"]),
            )
        elif outcome.kind is InboxOutcomeKind.REJECTED:
            self.repository.mark_as_rejected(event_id=event["event_id"],
                                             consumer=self.consumer, error_detail=reason)
        else:
            self.repository.mark_conflict(event_id=event["event_id"],
                                          consumer=self.consumer, reason_code=reason)
        return InboxOutcome(outcome.kind, reason)
