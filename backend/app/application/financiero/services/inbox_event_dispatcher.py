from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.application.financiero.services.handle_contrato_alquiler_activado_event_service import (
    HandleContratoAlquilerActivadoEventService,
)
from app.application.financiero.services.handle_venta_confirmada_event_service import (
    HandleVentaConfirmadaEventService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)


class InboxEventDispatcher:
    def __init__(self, db: Session) -> None:
        self._db = db

    def dispatch(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {"event_type": event_type, "payload": payload}

        if event_type == "venta_confirmada":
            repository = FinancieroRepository(self._db)
            HandleVentaConfirmadaEventService(repository=repository).execute(event)
            return

        if event_type == "contrato_alquiler_activado":
            repository = FinancieroRepository(self._db)
            HandleContratoAlquilerActivadoEventService(repository=repository).execute(event)
            return

        # Evento no reconocido: ignorar silenciosamente.
        # Para agregar nuevos handlers, añadir elif aquí.
