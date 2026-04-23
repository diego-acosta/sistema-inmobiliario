import argparse
import os
from datetime import UTC, datetime
from pprint import pformat


INTERNAL_CONSUMER_MANAGED_EVENT_TYPES = {"escrituracion_registrada"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lee eventos PENDING de outbox_event, simula publish y los marca como publicados."
    )
    parser.add_argument("--env", choices=["dev", "test"], default="dev")
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.environ["ENV"] = args.env

    from app.config.database import SessionLocal
    from app.infrastructure.persistence.repositories.outbox_repository import (
        OutboxRepository,
    )

    db = SessionLocal()
    repository = OutboxRepository(db)

    try:
        events = repository.get_pending_events(limit=args.limit)
        if not events:
            print("No hay eventos PENDING.")
            return 0

        published_count = 0
        for event in events:
            if event["event_type"] in INTERNAL_CONSUMER_MANAGED_EVENT_TYPES:
                print(
                    f"Skipping consumer-managed event id={event['id']} "
                    f"type={event['event_type']}"
                )
                continue
            print(
                f"Publishing event id={event['id']} type={event['event_type']} "
                f"aggregate={event['aggregate_type']}#{event['aggregate_id']}"
            )
            print(pformat(event["payload"]))
            processed_at = datetime.now(UTC)
            repository.mark_as_published(
                event["id"],
                published_at=processed_at,
                processing_reason={
                    "code": "PUBLISHED_BY_PUBLISHER",
                    "category": "PUBLISHER_RESULT",
                    "detail": "event_published_by_outbox_publisher_script",
                },
                processing_metadata={
                    "processor": "scripts.outbox_publisher",
                    "mode": "publisher",
                    "processed_at": processed_at.isoformat(),
                    "object_count": len(event["payload"].get("objetos", []))
                    if isinstance(event.get("payload"), dict)
                    else 0,
                },
            )
            published_count += 1

        db.commit()
        print(f"Eventos publicados: {published_count}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
