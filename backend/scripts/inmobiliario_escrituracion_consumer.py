import argparse
import os


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Consume eventos PENDING de outbox_event para "
            "`escrituracion_registrada` y materializa "
            "`RESERVADA -> NO_DISPONIBLE` en inmobiliario."
        )
    )
    parser.add_argument("--env", choices=["dev", "test"], default="dev")
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.environ["ENV"] = args.env

    from app.application.inmuebles.services.consume_escrituracion_registrada_service import (
        ConsumeEscrituracionRegistradaService,
    )
    from app.config.database import SessionLocal
    from app.infrastructure.persistence.repositories.inmueble_repository import (
        InmuebleRepository,
    )
    from app.infrastructure.persistence.repositories.outbox_repository import (
        OutboxRepository,
    )

    db = SessionLocal()
    service = ConsumeEscrituracionRegistradaService(
        db=db,
        inmueble_repository=InmuebleRepository(db),
        outbox_repository=OutboxRepository(db),
    )

    try:
        result = service.execute(limit=args.limit)
        if not result.success:
            print(f"Error consumiendo escrituraciones: {', '.join(result.errors)}")
            return 1

        data = result.data or {}
        print(f"Eventos procesados: {data.get('processed_events', 0)}")
        for event in data.get("events", []):
            print(
                f"event_id={event['event_id']} "
                f"venta={event['id_venta']} "
                f"objetos={len(event['objects'])}"
            )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
