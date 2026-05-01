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


class InboxEventDispatcher:
    def __init__(self, db: Session) -> None:
        self._db = db

    def dispatch(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {"event_type": event_type, "payload": payload}

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
            ).execute(payload["id_contrato_alquiler"], CommandContext())
            if not result.success:
                raise ValueError(";".join(result.errors))
            return

        # Evento no reconocido: ignorar silenciosamente.
        # Para agregar nuevos handlers, añadir elif aquí.
