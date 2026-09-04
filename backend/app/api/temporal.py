from datetime import UTC, datetime


def normalize_aware_datetime_to_utc_naive(value: datetime) -> datetime:
    """Convierte un instante con zona a la representación física UTC-naive."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("El datetime debe incluir un offset explícito.")
    return value.astimezone(UTC).replace(tzinfo=None)
