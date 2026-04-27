import argparse
import os
from datetime import UTC, datetime
from pprint import pformat


INTERNAL_CONSUMER_MANAGED_EVENT_TYPES = {"escrituracion_registrada"}

MAX_RETRIES = 5


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
        skipped_count = 0
        failed_count = 0

        for event in events:
            event_db_id = event["id"]
            event_type = event["event_type"]

            if event_type in INTERNAL_CONSUMER_MANAGED_EVENT_TYPES:
                print(
                    f"Skipping consumer-managed event id={event_db_id} "
                    f"type={event_type}"
                )
                skipped_count += 1
                continue

            if event["retry_count"] >= MAX_RETRIES:
                print(
                    f"Rejecting event id={event_db_id} type={event_type} "
                    f"retry_count={event['retry_count']} (max {MAX_RETRIES} reached)"
                )
                repository.mark_as_terminal(
                    event_db_id,
                    terminal_status="REJECTED",
                    processing_reason={
                        "code": "MAX_RETRIES_EXCEEDED",
                        "category": "PUBLISHER_RESULT",
                        "detail": f"retry_count={event['retry_count']} exceeded MAX_RETRIES={MAX_RETRIES}",
                    },
                    processing_metadata={
                        "processor": "scripts.outbox_publisher",
                        "mode": "publisher",
                        "processed_at": datetime.now(UTC).isoformat(),
                        "last_error": event.get("last_error"),
                    },
                )
                failed_count += 1
                continue

            try:
                print(
                    f"Publishing event id={event_db_id} type={event_type} "
                    f"aggregate={event['aggregate_type']}#{event['aggregate_id']} "
                    f"event_id={event['event_id']}"
                )
                print(pformat(event["payload"]))
                processed_at = datetime.now(UTC)

                # ── simulated publish (replace with real broker call) ──────────
                # broker.publish(topic=event_type, message=event["payload"], event_id=event["event_id"])

                repository.mark_as_published(
                    event_db_id,
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

            except Exception as exc:
                # Error técnico: registrar intento, mantener PENDING para reintento
                error_msg = str(exc)
                print(
                    f"Technical error publishing event id={event_db_id}: {error_msg}"
                )
                repository.mark_as_failed(event_db_id, error=error_msg)
                failed_count += 1

        db.commit()
        print(
            f"Eventos publicados: {published_count} | "
            f"skipped: {skipped_count} | "
            f"failed/rejected: {failed_count}"
        )
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
