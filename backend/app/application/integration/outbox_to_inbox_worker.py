from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.financiero.services.inbox_event_dispatcher import (
    INBOX_DISPATCHABLE_EVENT_TYPES,
    InboxEventDispatcher,
)
from app.application.common.synchronization_policy import (
    SYNC_EVENT_POLICIES,
    SynchronizationPolicyError,
    sanitize_sync_error,
    validate_sync_event,
)


def process_outbox_events(db: Session) -> None:
    events = db.execute(
        text(
            """
            SELECT id, event_type, aggregate_type, payload
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
            validate_sync_event(event_type, event["aggregate_type"], payload)
            if event_type not in INBOX_DISPATCHABLE_EVENT_TYPES:
                continue

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
        except SynchronizationPolicyError as exc:
            db.rollback()
            db.execute(
                text(
                    """
                    UPDATE outbox_event
                    SET status = 'REJECTED',
                        processed_at = :processed_at,
                        processing_reason = CAST(:reason AS jsonb)
                    WHERE id = :id
                      AND status = 'PENDING'
                    """
                ),
                {
                    "id": event["id"],
                    "processed_at": datetime.now(UTC),
                    "reason": json.dumps({"code": sanitize_sync_error(exc)}),
                },
            )
            db.commit()
        except Exception:
            db.rollback()
            continue


def run_outbox_worker_once(db: Session) -> None:
    process_outbox_events(db)


def _validate_payload(event_type: str, payload: Any) -> None:
    policy = SYNC_EVENT_POLICIES.get(event_type)
    validate_sync_event(event_type, policy.aggregate_type if policy else "", payload)
