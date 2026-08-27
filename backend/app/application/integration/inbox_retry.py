"""Entry point reusable para retry de inbox; el consumer conserva la semántica."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Callable, ContextManager

from sqlalchemy.orm import Session, sessionmaker

from app.application.common.synchronization_policy import (
    SynchronizationPolicyError,
    sanitize_sync_error,
    validate_retained_sync_envelope,
)
from app.infrastructure.persistence.repositories.inbox_repository import (
    InboxInvalidFingerprint,
    InboxRepository,
    has_valid_scoped_fingerprint,
)

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
                 automatic_attempt_limit: int = DEFAULT_AUTOMATIC_ATTEMPT_LIMIT,
                 lifecycle_session_factory: Callable[[], ContextManager[Session]] | None = None) -> None:
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

    @staticmethod
    def _ownership(event: dict, worker_id: str) -> dict[str, object]:
        return {
            "lease_owner": worker_id,
            "lease_generation": event["lease_generation"],
        }

    @staticmethod
    def _scope_leader_id(event: dict, compatible_in_flight: list[dict]) -> int:
        """El menor delivery compatible lidera, sin importar su estado técnico."""
        return min([event["id"], *(delivery["id"] for delivery in compatible_in_flight)])

    def _commit_outcome(self, outcome: InboxOutcome) -> InboxOutcome:
        """Hace durable el intento completo antes de exponer su resultado."""
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return outcome

    @staticmethod
    def _classify_scope_deliveries(
        deliveries: list[dict],
    ) -> tuple[list[dict], list[dict]]:
        """Separa evidencia vigente de siblings históricos inválidos, sin mutarlos."""
        trusted_siblings = []
        invalid_siblings = []
        for delivery in deliveries:
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
            except SynchronizationPolicyError:
                invalid_siblings.append(delivery)
            else:
                if has_valid_scoped_fingerprint(delivery):
                    trusted_siblings.append(delivery)
                else:
                    invalid_siblings.append(delivery)
        return trusted_siblings, invalid_siblings

    def run_once(self, applicator: Callable[[dict], InboxOutcome], *, worker_id: str,
                 event_id: str | None = None, manual: bool = False,
                 now: datetime | None = None) -> InboxOutcome | None:
        """Ejecuta un intento y nunca propaga dejando abierta su transacción."""
        try:
            return self._run_once(
                applicator, worker_id=worker_id, event_id=event_id,
                manual=manual, now=now,
            )
        except Exception:
            self.session.rollback()
            raise

    def _run_once(self, applicator: Callable[[dict], InboxOutcome], *, worker_id: str,
                  event_id: str | None = None, manual: bool = False,
                  now: datetime | None = None) -> InboxOutcome | None:
        current = now or datetime.now(UTC)
        # Fase técnica corta: reclaim + claim se confirman antes del applicator.
        with self.lifecycle_session_factory() as lifecycle_session:
            lifecycle_repository = InboxRepository(lifecycle_session)
            lifecycle_repository.reclaim_expired(consumer=self.consumer, now=current)
            lifecycle_session.commit()
            event = lifecycle_repository.claim_pending(
                consumer=self.consumer, lease_owner=worker_id,
                lease_duration=self.lease_duration,
                automatic_attempt_limit=self.automatic_attempt_limit,
                event_id=event_id, manual=manual, now=current,
            )
            lifecycle_session.commit()
        if event is None:
            return None
        ownership = self._ownership(event, worker_id)

        try:
            validate_retained_sync_envelope(
                event_type=event["event_type"],
                aggregate_type=event["aggregate_type"],
                payload=event.get("payload"), provenance=event.get("provenance"),
                op_id=event.get("op_id"), aggregate_uid=event.get("aggregate_uid"),
                version_registro=event.get("version_registro"),
            )
        except SynchronizationPolicyError as exc:
            reason = sanitize_sync_error(exc, preserve_invalid_payload=True)
            self.repository.mark_as_rejected(
                event_id=event["event_id"], consumer=self.consumer,
                error_detail=reason, **ownership,
            )
            return self._commit_outcome(
                InboxOutcome(InboxOutcomeKind.REJECTED, reason)
            )
        if not has_valid_scoped_fingerprint(event):
            reason = InboxInvalidFingerprint.code
            self.repository.mark_as_rejected(
                event_id=event["event_id"], consumer=self.consumer,
                error_detail=reason, **ownership,
            )
            return self._commit_outcome(
                InboxOutcome(InboxOutcomeKind.REJECTED, reason)
            )

        operation_ownership = None
        # La evidencia y el leader lógico se resuelven antes del ownership físico.
        if event.get("op_id"):
            deliveries = self.repository.get_operation_scope_deliveries(
                consumer=self.consumer, op_id=event["op_id"], exclude_id=event["id"]
            )
            trusted_siblings, _invalid_siblings = self._classify_scope_deliveries(
                deliveries
            )
            stored_scope = self.repository.get_operation_scope(
                consumer=self.consumer, op_id=event["op_id"]
            )
            if any(
                delivery["payload_fingerprint"] != event["payload_fingerprint"]
                for delivery in trusted_siblings
            ) or (
                stored_scope is not None
                and stored_scope["payload_fingerprint"] != event["payload_fingerprint"]
            ):
                outcome = InboxOutcome(
                    InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT"
                )
                self.repository.mark_conflict(
                    event_id=event["event_id"], consumer=self.consumer,
                    reason_code=outcome.reason_code, **ownership,
                )
                return self._commit_outcome(outcome)
            if (
                stored_scope is not None
                and stored_scope["terminal_status"] == "PROCESSED"
            ) or any(
                delivery["status"] == "PROCESSED" for delivery in trusted_siblings
            ):
                outcome = InboxOutcome(InboxOutcomeKind.PROCESSED)
                self.repository.mark_as_processed(
                    event_id=event["event_id"], consumer=self.consumer, **ownership
                )
                return self._commit_outcome(outcome)
            if (
                stored_scope is not None
                and stored_scope["terminal_status"] == "CONFLICTO"
            ) or any(
                delivery["status"] == "CONFLICTO" for delivery in trusted_siblings
            ):
                outcome = InboxOutcome(
                    InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT"
                )
                self.repository.mark_conflict(
                    event_id=event["event_id"], consumer=self.consumer,
                    reason_code=outcome.reason_code, **ownership,
                )
                return self._commit_outcome(outcome)

            compatible_in_flight = [
                delivery for delivery in trusted_siblings
                if delivery["status"] in {"PENDING_DEPENDENCY", "PROCESSING"}
            ]
            if self._scope_leader_id(event, compatible_in_flight) != event["id"]:
                if (
                    stored_scope is not None
                    and stored_scope["terminal_status"] is None
                    and stored_scope["lease_owner"] == worker_id
                ):
                    self.repository.finish_operation_scope(
                        consumer=self.consumer, op_id=event["op_id"],
                        lease_owner=worker_id,
                        lease_generation=stored_scope["lease_generation"],
                        terminal_status=None,
                    )
                outcome = InboxOutcome(
                    InboxOutcomeKind.PENDING_DEPENDENCY,
                    "SYNC_DEPENDENCY_UNAVAILABLE",
                )
                self.repository.mark_pending_dependency(
                    event_id=event["event_id"], consumer=self.consumer,
                    reason_code=outcome.reason_code,
                    retry_delay=retry_backoff(event["attempt_count"]), **ownership,
                )
                return self._commit_outcome(outcome)

            with self.lifecycle_session_factory() as lifecycle_session:
                scope = InboxRepository(lifecycle_session).claim_operation_scope(
                    consumer=self.consumer, op_id=event["op_id"],
                    payload_fingerprint=event["payload_fingerprint"],
                    lease_owner=worker_id,
                    lease_expires_at=event["lease_expires_at"],
                )
                lifecycle_session.commit()
            if not scope["acquired"]:
                if scope["payload_fingerprint"] != event["payload_fingerprint"]:
                    outcome = InboxOutcome(
                        InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT"
                    )
                    self.repository.mark_conflict(
                        event_id=event["event_id"], consumer=self.consumer,
                        reason_code=outcome.reason_code, **ownership,
                    )
                    return self._commit_outcome(outcome)
                if scope["terminal_status"] == "PROCESSED":
                    outcome = InboxOutcome(InboxOutcomeKind.PROCESSED)
                    self.repository.mark_as_processed(
                        event_id=event["event_id"], consumer=self.consumer, **ownership
                    )
                    return self._commit_outcome(outcome)
                if scope["terminal_status"] == "CONFLICTO":
                    outcome = InboxOutcome(
                        InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT"
                    )
                    self.repository.mark_conflict(
                        event_id=event["event_id"], consumer=self.consumer,
                        reason_code=outcome.reason_code, **ownership,
                    )
                    return self._commit_outcome(outcome)
                outcome = InboxOutcome(
                    InboxOutcomeKind.PENDING_DEPENDENCY,
                    "SYNC_DEPENDENCY_UNAVAILABLE",
                )
                self.repository.mark_pending_dependency(
                    event_id=event["event_id"], consumer=self.consumer,
                    reason_code=outcome.reason_code,
                    retry_delay=retry_backoff(event["attempt_count"]), **ownership,
                )
                return self._commit_outcome(outcome)
            operation_ownership = {
                "consumer": self.consumer, "op_id": event["op_id"],
                "lease_owner": worker_id,
                "lease_generation": scope["lease_generation"],
            }

        nested = self.session.begin_nested()
        try:
            outcome = applicator(event)
            if not isinstance(outcome, InboxOutcome):
                raise TypeError("consumer must return InboxOutcome")
            if outcome.kind is InboxOutcomeKind.PROCESSED:
                if operation_ownership is not None:
                    self.repository.finish_operation_scope(
                        terminal_status="PROCESSED", **operation_ownership
                    )
                self.repository.mark_as_processed(
                    event_id=event["event_id"], consumer=self.consumer, **ownership
                )
                nested.commit()
                return self._commit_outcome(outcome)
            nested.rollback()  # descarta cualquier efecto funcional parcial
        except Exception:
            nested.rollback()
            self.session.rollback()
            raise

        reason = outcome.reason_code
        if reason not in SANITIZED_REASON_CODES:
            reason = "SYNC_FUNCTIONAL_FAILURE"
        if outcome.kind is InboxOutcomeKind.PENDING_DEPENDENCY:
            if operation_ownership is not None:
                self.repository.finish_operation_scope(
                    terminal_status=None, **operation_ownership
                )
            self.repository.mark_pending_dependency(
                event_id=event["event_id"], consumer=self.consumer, reason_code=reason,
                retry_delay=retry_backoff(event["attempt_count"]),
                **ownership,
            )
        elif outcome.kind is InboxOutcomeKind.REJECTED:
            if operation_ownership is not None:
                self.repository.finish_operation_scope(
                    terminal_status=None, **operation_ownership
                )
            self.repository.mark_as_rejected(event_id=event["event_id"],
                                             consumer=self.consumer, error_detail=reason,
                                             **ownership)
        else:
            if operation_ownership is not None:
                self.repository.finish_operation_scope(
                    terminal_status="CONFLICTO", **operation_ownership
                )
            self.repository.mark_conflict(event_id=event["event_id"],
                                          consumer=self.consumer, reason_code=reason,
                                          **ownership)
        return self._commit_outcome(InboxOutcome(outcome.kind, reason))
