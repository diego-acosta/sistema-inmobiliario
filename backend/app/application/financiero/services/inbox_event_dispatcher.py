from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.application.common.commands import CommandContext
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


class InboxEventDispatcher:
    def __init__(self, db: Session) -> None:
        self._db = db

    def dispatch(
        self,
        event_type: str,
        payload: dict[str, Any],
        context: CommandContext | None = None,
    ) -> None:
        policy = SYNC_EVENT_POLICIES.get(event_type)
        validate_sync_event(event_type, policy.aggregate_type if policy else "", payload)
        if event_type not in INBOX_DISPATCHABLE_EVENT_TYPES:
            raise SyncDispatchError(SyncDispatchError.code)
        event = {"event_type": event_type, "payload": payload}
        if context is not None:
            event["op_id"] = context.metadata.get("x_op_id")
            event["request_id"] = str(context.request_id)

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
