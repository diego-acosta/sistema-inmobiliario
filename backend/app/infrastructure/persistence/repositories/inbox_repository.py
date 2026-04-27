from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class InboxRepository:
    """Garantiza idempotencia de consumidores registrando qué eventos ya fueron procesados."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _map_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row["id"],
            "event_id": str(row["event_id"]),
            "event_type": row["event_type"],
            "aggregate_type": row["aggregate_type"],
            "aggregate_id": row["aggregate_id"],
            "consumer": row["consumer"],
            "status": row["status"],
            "processed_at": row["processed_at"],
            "error_detail": row["error_detail"],
            "created_at": row["created_at"],
        }

    def claim(
        self,
        *,
        event_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: int,
        consumer: str,
    ) -> bool:
        """Intenta reservar el evento para este consumer.
        Retorna True si fue reclamado ahora (primera vez).
        Retorna False si ya existía (el consumer ya lo vio antes).
        """
        stmt = text(
            """
            INSERT INTO inbox_event (
                event_id, event_type, aggregate_type, aggregate_id,
                consumer, status, created_at
            )
            VALUES (
                CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
                :consumer, 'PROCESSING', now()
            )
            ON CONFLICT (event_id, consumer) DO NOTHING
            """
        )
        result = self.db.execute(
            stmt,
            {
                "event_id": event_id,
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "consumer": consumer,
            },
        )
        return result.rowcount == 1

    def is_processed(self, *, event_id: str, consumer: str) -> bool:
        """True si el consumer ya completó el procesamiento de este evento."""
        stmt = text(
            """
            SELECT 1 FROM inbox_event
            WHERE event_id = CAST(:event_id AS uuid)
              AND consumer = :consumer
              AND status = 'PROCESSED'
            """
        )
        return (
            self.db.execute(stmt, {"event_id": event_id, "consumer": consumer})
            .scalar_one_or_none()
            is not None
        )

    def mark_as_processed(self, *, event_id: str, consumer: str) -> None:
        stmt = text(
            """
            UPDATE inbox_event
            SET status = 'PROCESSED', processed_at = :now
            WHERE event_id = CAST(:event_id AS uuid)
              AND consumer = :consumer
              AND status = 'PROCESSING'
            """
        )
        self.db.execute(
            stmt,
            {"event_id": event_id, "consumer": consumer, "now": datetime.now(UTC)},
        )

    def mark_as_rejected(self, *, event_id: str, consumer: str, error_detail: str) -> None:
        """Error de negocio: el evento no puede procesarse y no debe reintentarse."""
        stmt = text(
            """
            UPDATE inbox_event
            SET status = 'REJECTED',
                processed_at = :now,
                error_detail = :error_detail
            WHERE event_id = CAST(:event_id AS uuid)
              AND consumer = :consumer
            """
        )
        self.db.execute(
            stmt,
            {
                "event_id": event_id,
                "consumer": consumer,
                "now": datetime.now(UTC),
                "error_detail": error_detail,
            },
        )

    def get(self, *, event_id: str, consumer: str) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT id, event_id, event_type, aggregate_type, aggregate_id,
                   consumer, status, processed_at, error_detail, created_at
            FROM inbox_event
            WHERE event_id = CAST(:event_id AS uuid) AND consumer = :consumer
            """
        )
        row = self.db.execute(
            stmt, {"event_id": event_id, "consumer": consumer}
        ).mappings().one_or_none()
        return self._map_row(row) if row is not None else None
