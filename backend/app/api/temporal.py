from datetime import UTC, datetime


def normalize_aware_datetime_to_utc_naive(value: datetime) -> datetime:
    """Convierte un instante con zona a la representación física UTC-naive."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("El datetime debe incluir un offset explícito.")
    try:
        utc_value = value.astimezone(UTC)
    except OverflowError as exc:
        raise ValueError("El datetime no es representable en UTC.") from exc
    return utc_value.replace(tzinfo=None)
