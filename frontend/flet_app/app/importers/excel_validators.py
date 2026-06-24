from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()
    if text == "":
        return None
    if "," in text and "." in text:
        decimal_separator = "," if text.rfind(",") > text.rfind(".") else "."
        thousands_separator = "." if decimal_separator == "," else ","
        text = text.replace(thousands_separator, "")
        if decimal_separator == ",":
            text = text.replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def positive_decimal_validator(value: Any) -> str | None:
    if value is None or value == "":
        return None
    decimal_value = value if isinstance(value, Decimal) else normalize_decimal(value)
    if decimal_value is None:
        return "Debe ser un número decimal válido."
    if decimal_value <= 0:
        return "Debe ser un decimal positivo."
    return None
