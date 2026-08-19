from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.application.common.commands import CommandContext
from app.application.common.idempotency import (
    CANONICALIZATION_VERSION,
    ClaimDecision,
    ConflictKind,
    OperationClaim,
    OperationCompletion,
    canonical_payload_hash,
    claim_operation,
    complete_operation,
)
from app.application.financiero.services.handle_contrato_alquiler_activado_event_service import (
    HandleContratoAlquilerActivadoEventService,
)
from app.application.financiero.services.handle_venta_confirmada_event_service import (
    HandleVentaConfirmadaEventService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from app.infrastructure.persistence.repositories.locativo_repository import (
    LocativoRepository,
)
from app.application.common.synchronization_policy import (
    SYNC_EVENT_POLICIES,
    SyncDispatchError,
    validate_sync_event,
)

INBOX_DISPATCHABLE_EVENT_TYPES = frozenset(
    {
        "venta_confirmada",
        "contrato_alquiler_activado",
    }
)

assert INBOX_DISPATCHABLE_EVENT_TYPES <= SYNC_EVENT_POLICIES.keys()

INBOX_COMMAND_CODE = "FINANCIERO_INBOX_EVENT"
INBOX_TARGET_TYPE = "evento_sincronizacion_financiero"


class InboxIdempotencyConflict(RuntimeError):
    def __init__(self, conflict: ConflictKind) -> None:
        self.code = {
            ConflictKind.COMMAND: "IDEMPOTENCY_COMMAND_CONFLICT",
            ConflictKind.TARGET: "IDEMPOTENCY_TARGET_CONFLICT",
            ConflictKind.PAYLOAD: "IDEMPOTENCY_PAYLOAD_CONFLICT",
        }[conflict]
        super().__init__(self.code)


class InboxEventDispatcher:
    def __init__(self, db: Session) -> None:
        self._db = db

    def dispatch(
        self,
        event_type: str,
        payload: dict[str, Any],
        context: CommandContext | None = None,
    ) -> None:
        self.validate_dispatchable(event_type, payload)
        self._dispatch_validated(event_type, payload, context)

    def dispatch_idempotent(
        self,
        event_type: str,
        payload: dict[str, Any],
        context: CommandContext,
    ) -> ClaimDecision:
        """Ejecuta claim, negocio y completion en la Session del caller."""
        self.validate_dispatchable(event_type, payload)
        op_id = context.request_id
        payload_hash = canonical_payload_hash(
            {"event_type": event_type, "payload": payload}
        )
        claim = OperationClaim(
            op_id=op_id,
            command_code=INBOX_COMMAND_CODE,
            target_type=INBOX_TARGET_TYPE,
            target_uid=None,
            target_key=event_type,
            payload_hash=payload_hash,
            canonicalization_version=CANONICALIZATION_VERSION,
        )
        decision = claim_operation(self._db, claim)
        if decision.decision is ClaimDecision.REPLAY:
            return ClaimDecision.REPLAY
        if decision.decision is ClaimDecision.CONFLICT:
            raise InboxIdempotencyConflict(decision.conflict)

        self._dispatch_validated(event_type, payload, context)
        complete_operation(
            self._db,
            OperationCompletion(
                op_id=claim.op_id,
                command_code=claim.command_code,
                target_type=claim.target_type,
                target_uid=claim.target_uid,
                target_key=claim.target_key,
                payload_hash=claim.payload_hash,
                canonicalization_version=claim.canonicalization_version,
                result_code="FINANCIERO_INBOX_PROCESSED",
                result_http_status=204,
                result_target_uid=None,
                result_version=None,
                response_snapshot={},
                id_usuario=None,
                id_sucursal=int(context.metadata["x_sucursal_id"]),
                id_instalacion=int(context.metadata["x_instalacion_id"]),
            ),
        )
        return ClaimDecision.EXECUTE

    @staticmethod
    def validate_dispatchable(event_type: str, payload: dict[str, Any]) -> None:
        policy = SYNC_EVENT_POLICIES.get(event_type)
        validate_sync_event(event_type, policy.aggregate_type if policy else "", payload)
        if event_type not in INBOX_DISPATCHABLE_EVENT_TYPES:
            raise SyncDispatchError(SyncDispatchError.code)

    def _dispatch_validated(
        self,
        event_type: str,
        payload: dict[str, Any],
        context: CommandContext | None,
    ) -> None:
        event = {"event_type": event_type, "payload": payload}
        if context is not None:
            event["op_id"] = context.metadata.get("x_op_id")
            event["request_id"] = str(context.request_id)
            event["id_instalacion"] = getattr(context, "id_instalacion", None)

        if event_type == "venta_confirmada":
            repository = FinancieroRepository(self._db)
            result = HandleVentaConfirmadaEventService(repository=repository).execute(event)
            if not result.success:
                raise ValueError(";".join(result.errors))
            return

        if event_type == "contrato_alquiler_activado":
            locativo_repository = LocativoRepository(self._db)
            financiero_repository = FinancieroRepository(self._db)
            result = HandleContratoAlquilerActivadoEventService(
                locativo_repository=locativo_repository,
                financiero_repository=financiero_repository,
            ).execute(payload["id_contrato_alquiler"], context or CommandContext())
            if not result.success:
                raise ValueError(";".join(result.errors))
            return

        raise SyncDispatchError(SyncDispatchError.code)
