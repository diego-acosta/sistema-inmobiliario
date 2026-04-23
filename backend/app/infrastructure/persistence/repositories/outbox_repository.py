import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class OutboxRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _json_dumps(self, value: Any) -> str:
        def _default_serializer(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, UUID):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        return json.dumps(value, default=_default_serializer)

    def _map_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "event_type": row["event_type"],
            "aggregate_type": row["aggregate_type"],
            "aggregate_id": row["aggregate_id"],
            "payload": row["payload"],
            "occurred_at": row["occurred_at"],
            "published_at": row["published_at"],
            "status": row["status"],
            "processing_reason": row["processing_reason"],
            "processing_metadata": row["processing_metadata"],
        }

    def add_event(
        self,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: int,
        payload: dict[str, Any],
        occurred_at: datetime,
        published_at: datetime | None = None,
        status: str = "PENDING",
        processing_reason: dict[str, Any] | None = None,
        processing_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        statement = text(
            """
            INSERT INTO outbox_event (
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                occurred_at,
                published_at,
                status,
                processing_reason,
                processing_metadata
            )
            VALUES (
                :event_type,
                :aggregate_type,
                :aggregate_id,
                CAST(:payload AS jsonb),
                :occurred_at,
                :published_at,
                :status,
                CAST(:processing_reason AS jsonb),
                CAST(:processing_metadata AS jsonb)
            )
            RETURNING
                id,
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                occurred_at,
                published_at,
                status,
                processing_reason,
                processing_metadata
            """
        )
        row = self.db.execute(
            statement,
            {
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "payload": self._json_dumps(payload),
                "occurred_at": occurred_at,
                "published_at": published_at,
                "status": status,
                "processing_reason": self._json_dumps(processing_reason),
                "processing_metadata": self._json_dumps(processing_metadata),
            },
        ).mappings().one()
        return self._map_row(row)

    def get_pending_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id,
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                occurred_at,
                published_at,
                status,
                processing_reason,
                processing_metadata
            FROM outbox_event
            WHERE status = 'PENDING'
              AND published_at IS NULL
            ORDER BY occurred_at, id
            LIMIT :limit
            """
        )
        rows = self.db.execute(statement, {"limit": limit}).mappings().all()
        return [self._map_row(row) for row in rows]

    def mark_as_published(
        self,
        event_id: int,
        *,
        published_at: datetime | None = None,
        processing_reason: dict[str, Any] | None = None,
        processing_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        timestamp = published_at or datetime.now(UTC)
        statement = text(
            """
            UPDATE outbox_event
            SET
                published_at = :published_at,
                status = 'PUBLISHED',
                processing_reason = CAST(:processing_reason AS jsonb),
                processing_metadata = CAST(:processing_metadata AS jsonb)
            WHERE id = :id
              AND status = 'PENDING'
            RETURNING
                id,
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                occurred_at,
                published_at,
                status,
                processing_reason,
                processing_metadata
            """
        )
        row = self.db.execute(
            statement,
            {
                "id": event_id,
                "published_at": timestamp,
                "processing_reason": self._json_dumps(processing_reason),
                "processing_metadata": self._json_dumps(processing_metadata),
            },
        ).mappings().one_or_none()
        if row is None:
            return None
        return self._map_row(row)

    def mark_as_terminal(
        self,
        event_id: int,
        *,
        terminal_status: str = "REJECTED",
        processing_reason: dict[str, Any] | None = None,
        processing_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        statement = text(
            """
            UPDATE outbox_event
            SET
                status = :terminal_status,
                processing_reason = CAST(:processing_reason AS jsonb),
                processing_metadata = CAST(:processing_metadata AS jsonb)
            WHERE id = :id
              AND status = 'PENDING'
              AND published_at IS NULL
            RETURNING
                id,
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                occurred_at,
                published_at,
                status,
                processing_reason,
                processing_metadata
            """
        )
        row = self.db.execute(
            statement,
            {
                "id": event_id,
                "terminal_status": terminal_status,
                "processing_reason": self._json_dumps(processing_reason),
                "processing_metadata": self._json_dumps(processing_metadata),
            },
        ).mappings().one_or_none()
        if row is None:
            return None
        return self._map_row(row)
