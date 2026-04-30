from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.financiero.services.inbox_event_dispatcher import (
    InboxEventDispatcher,
)


SUPPORTED_EVENT_REQUIRED_IDS = {
    "venta_confirmada": "id_venta",
    "contrato_alquiler_activado": "id_contrato_alquiler",
}


def process_outbox_events(db: Session) -> None:
    events = db.execute(
        text(
            """
            SELECT id, event_type, payload
            FROM outbox_event
            WHERE status = 'PENDING'
              AND published_at IS NULL
            ORDER BY occurred_at, id
            """
        )
    ).mappings().all()

    dispatcher = InboxEventDispatcher(db)

    for event in events:
        try:
            event_type = event["event_type"]
            payload = event["payload"]
            _validate_payload(event_type, payload)

            dispatcher.dispatch(event_type, payload)
            db.execute(
                text(
                    """
                    UPDATE outbox_event
                    SET
                        status = 'PUBLISHED',
                        published_at = :processed_at,
                        processed_at = :processed_at
                    WHERE id = :id
                      AND status = 'PENDING'
                    """
                ),
                {"id": event["id"], "processed_at": datetime.now(UTC)},
            )
            db.commit()
        except Exception:
            db.rollback()
            continue


def run_outbox_worker_once(db: Session) -> None:
    process_outbox_events(db)


def _validate_payload(event_type: str, payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("INVALID_EVENT_PAYLOAD")

    required_id = SUPPORTED_EVENT_REQUIRED_IDS.get(event_type)
    if required_id is None:
        return

    value = payload.get(required_id)
    if not isinstance(value, int) or value <= 0:
        raise ValueError("INVALID_EVENT_PAYLOAD")
