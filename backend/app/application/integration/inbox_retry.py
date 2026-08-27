"""Entry point reusable para retry de inbox; el consumer conserva la semántica."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from sqlalchemy.orm import Session, sessionmaker

from app.application.common.synchronization_policy import (
    SynchronizationPolicyError,
    sanitize_sync_error,
    validate_retained_sync_envelope,
)
from app.infrastructure.persistence.repositories.inbox_repository import (
    DeliveryClaim,
    InboxInvalidFingerprint,
    InboxRepository,
    OperationClaim,
    OperationDecision,
    has_valid_scoped_fingerprint,
)

DEFAULT_LEASE = timedelta(minutes=5)
DEFAULT_AUTOMATIC_ATTEMPT_LIMIT = 8
MAX_BACKOFF = timedelta(hours=6)
SANITIZED_REASON_CODES = frozenset(
    {
        "SYNC_DEPENDENCY_UNAVAILABLE",
        "SYNC_PAYLOAD_INVALID",
        "SYNC_OPERATION_CONFLICT",
        "SYNC_FUNCTIONAL_FAILURE",
    }
)


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
    seconds = min(
        30 * (2 ** max(attempt_count - 1, 0)), int(MAX_BACKOFF.total_seconds())
    )
    return timedelta(seconds=seconds)


class InboxRetryProcessor:
    """Coordina delivery, operation scope y applicator en una Session dedicada.

    El applicator usa exclusivamente ``self.session``/la transacción administrada
    por este processor. No puede confirmar transacciones propias, otra conexión DB
    ni efectos externos irreversibles antes del commit coordinado.
    """

    def __init__(
        self,
        session: Session,
        *,
        consumer: str,
        lease_duration: timedelta = DEFAULT_LEASE,
        automatic_attempt_limit: int = DEFAULT_AUTOMATIC_ATTEMPT_LIMIT,
        lifecycle_session_factory: Callable[[], AbstractContextManager[Session]]
        | None = None,
    ) -> None:
        self.session = session
        self.consumer = consumer
        self.repository = InboxRepository(session)
        self.lease_duration = lease_duration
        self.automatic_attempt_limit = automatic_attempt_limit
        if lifecycle_session_factory is None:
            bind = session.get_bind()
            engine = getattr(bind, "engine", bind)
            lifecycle_session_factory = sessionmaker(
                bind=engine, expire_on_commit=False, class_=Session
            )
        self.lifecycle_session_factory = lifecycle_session_factory

    def _commit(self, outcome: InboxOutcome) -> InboxOutcome:
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return outcome

    def _claim_delivery(
        self,
        *,
        worker_id: str,
        event_id: str | None,
        manual: bool,
    ) -> DeliveryClaim | None:
        with self.lifecycle_session_factory() as lifecycle:
            repository = InboxRepository(lifecycle)
            delivery = repository.claim_pending(
                consumer=self.consumer,
                worker_id=worker_id,
                lease_duration=self.lease_duration,
                automatic_attempt_limit=self.automatic_attempt_limit,
                event_id=event_id,
                manual=manual,
            )
            lifecycle.commit()
            return delivery

    def _acquire_operation(self, delivery: DeliveryClaim):
        with self.lifecycle_session_factory() as lifecycle:
            decision = InboxRepository(lifecycle).acquire_operation_scope(
                delivery=delivery
            )
            lifecycle.commit()
            return decision

    def run_once(
        self,
        applicator: Callable[[dict], InboxOutcome],
        *,
        worker_id: str,
        event_id: str | None = None,
        manual: bool = False,
        now=None,
    ) -> InboxOutcome | None:
        """Ejecuta un intento y nunca retorna o propaga con transacción abierta."""
        del now  # compatibilidad; PostgreSQL es autoridad temporal
        try:
            return self._run_once(
                applicator, worker_id=worker_id, event_id=event_id, manual=manual
            )
        except Exception:
            self.session.rollback()
            raise

    def _run_once(
        self,
        applicator: Callable[[dict], InboxOutcome],
        *,
        worker_id: str,
        event_id: str | None,
        manual: bool,
    ) -> InboxOutcome | None:
        delivery = self._claim_delivery(
            worker_id=worker_id, event_id=event_id, manual=manual
        )
        if delivery is None:
            self.session.rollback()
            return None

        try:
            validate_retained_sync_envelope(
                event_type=delivery["event_type"],
                aggregate_type=delivery["aggregate_type"],
                payload=delivery.get("payload"),
                provenance=delivery.get("provenance"),
                op_id=delivery.get("op_id"),
                aggregate_uid=delivery.get("aggregate_uid"),
                version_registro=delivery.get("version_registro"),
            )
        except SynchronizationPolicyError as exc:
            reason = sanitize_sync_error(exc, preserve_invalid_payload=True)
            self.repository.mark_as_rejected(claim=delivery, error_detail=reason)
            return self._commit(InboxOutcome(InboxOutcomeKind.REJECTED, reason))

        if not has_valid_scoped_fingerprint(delivery):
            reason = InboxInvalidFingerprint.code
            self.repository.mark_as_rejected(claim=delivery, error_detail=reason)
            return self._commit(InboxOutcome(InboxOutcomeKind.REJECTED, reason))

        operation_claim: OperationClaim | None = None
        if delivery.get("op_id") is not None:
            scoped = self._acquire_operation(delivery)
            if scoped.decision is OperationDecision.BUSY:
                outcome = InboxOutcome(
                    InboxOutcomeKind.PENDING_DEPENDENCY,
                    "SYNC_DEPENDENCY_UNAVAILABLE",
                )
                self.repository.mark_pending_dependency(
                    claim=delivery,
                    reason_code=outcome.reason_code,
                    retry_delay=retry_backoff(delivery["attempt_count"]),
                    consume_attempt=False,
                )
                return self._commit(outcome)
            if scoped.decision is OperationDecision.INCOMPATIBLE:
                outcome = InboxOutcome(
                    InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT"
                )
                self.repository.mark_conflict(
                    claim=delivery, reason_code=outcome.reason_code
                )
                return self._commit(outcome)
            if scoped.decision is OperationDecision.REPLAY_PROCESSED:
                outcome = InboxOutcome(InboxOutcomeKind.PROCESSED)
                self.repository.mark_as_processed(claim=delivery)
                return self._commit(outcome)
            if scoped.decision is OperationDecision.REPLAY_CONFLICT:
                outcome = InboxOutcome(
                    InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT"
                )
                self.repository.mark_conflict(
                    claim=delivery, reason_code=outcome.reason_code
                )
                return self._commit(outcome)
            operation_claim = scoped.claim
            if operation_claim is None:
                raise RuntimeError("SYNC_OPERATION_SCOPE_DECISION_INVALID")

        nested = self.session.begin_nested()
        try:
            outcome = applicator(delivery.event)
            if not isinstance(outcome, InboxOutcome):
                raise TypeError("consumer must return InboxOutcome")
            if outcome.kind is InboxOutcomeKind.PROCESSED:
                if operation_claim is not None:
                    self.repository.finish_operation_scope(
                        claim=operation_claim, terminal_status="PROCESSED"
                    )
                self.repository.mark_as_processed(claim=delivery)
                nested.commit()
            else:
                nested.rollback()
        except Exception:
            if nested.is_active:
                nested.rollback()
            self.session.rollback()
            raise

        if outcome.kind is InboxOutcomeKind.PROCESSED:
            return self._commit(outcome)

        reason = outcome.reason_code
        if reason not in SANITIZED_REASON_CODES:
            reason = "SYNC_FUNCTIONAL_FAILURE"
        if outcome.kind is InboxOutcomeKind.PENDING_DEPENDENCY:
            if operation_claim is not None:
                self.repository.finish_operation_scope(
                    claim=operation_claim, terminal_status=None
                )
            self.repository.mark_pending_dependency(
                claim=delivery,
                reason_code=reason,
                retry_delay=retry_backoff(delivery["attempt_count"]),
            )
        elif outcome.kind is InboxOutcomeKind.REJECTED:
            if operation_claim is not None:
                self.repository.finish_operation_scope(
                    claim=operation_claim, terminal_status=None
                )
            self.repository.mark_as_rejected(claim=delivery, error_detail=reason)
        else:
            if operation_claim is not None:
                self.repository.finish_operation_scope(
                    claim=operation_claim, terminal_status="CONFLICTO"
                )
            self.repository.mark_conflict(claim=delivery, reason_code=reason)
        return self._commit(InboxOutcome(outcome.kind, reason))
