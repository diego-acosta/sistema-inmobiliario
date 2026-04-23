from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class OutboxEventPayload:
    event_type: str
    aggregate_type: str
    aggregate_id: int
    payload: dict[str, Any]
    occurred_at: datetime
    status: str = "PENDING"
    published_at: datetime | None = None
    processing_reason: dict[str, Any] | None = None
    processing_metadata: dict[str, Any] | None = None
