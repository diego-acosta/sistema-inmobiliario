"""Entry point manual de transporte/proceso de calendario; no es un scheduler."""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.application.administrativo.services.calendario_comercial_sync_service import (
    run_calendario_inbox_once,
    transport_calendario_outbox_once,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transporta y/o procesa calendario comercial sin daemon productivo."
    )
    parser.add_argument("mode", choices=("transport", "process", "both"))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--worker-id", default="calendario-sync-manual")
    return parser.parse_args()


def _required_url(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"{name} no configurada")
    return value


def main() -> int:
    args = parse_args()
    destination_engine = create_engine(
        _required_url("CALENDARIO_SYNC_DESTINATION_DATABASE_URL"),
        future=True,
        pool_pre_ping=True,
    )
    if args.mode in {"transport", "both"}:
        source_engine = create_engine(
            _required_url("CALENDARIO_SYNC_SOURCE_DATABASE_URL"),
            future=True,
            pool_pre_ping=True,
        )
        with Session(source_engine) as source, Session(destination_engine) as destination:
            transported, registered = transport_calendario_outbox_once(
                source, destination, limit=args.limit
            )
        print(f"transported={transported} registered={registered}")
    if args.mode in {"process", "both"}:
        processed = 0
        with Session(destination_engine) as destination:
            while processed < args.limit:
                outcome = run_calendario_inbox_once(
                    destination, worker_id=args.worker_id
                )
                if outcome is None:
                    break
                processed += 1
        print(f"processed={processed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
