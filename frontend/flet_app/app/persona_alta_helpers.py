"""Helpers compartidos para el alta Flet de personas."""

from __future__ import annotations

from datetime import date
from typing import Any

TIPOS_PERSONA = ("FISICA", "JURIDICA")
ESTADOS_PERSONA = ("ACTIVA", "INACTIVA")


def clean_text(value: str | None) -> str:
    return (value or "").strip()


def validate_persona_form(values: dict[str, str | None]) -> list[str]:
    errors: list[str] = []
    tipo_persona = clean_text(values.get("tipo_persona"))
    estado_persona = clean_text(values.get("estado_persona"))

    if tipo_persona not in TIPOS_PERSONA:
        errors.append("Tipo de persona es requerido y debe ser FISICA o JURIDICA.")
    if estado_persona not in ESTADOS_PERSONA:
        errors.append("Estado de persona es requerido y debe ser ACTIVA o INACTIVA.")

    if tipo_persona == "FISICA":
        if not clean_text(values.get("nombre")):
            errors.append("Nombre es requerido para persona física.")
        if not clean_text(values.get("apellido")):
            errors.append("Apellido es requerido para persona física.")
    elif tipo_persona == "JURIDICA" and not clean_text(values.get("razon_social")):
        errors.append("Razón social es requerida para persona jurídica.")

    fecha_nacimiento = clean_text(values.get("fecha_nacimiento"))
    if fecha_nacimiento:
        try:
            date.fromisoformat(fecha_nacimiento)
        except ValueError:
            errors.append("Fecha debe tener formato AAAA-MM-DD.")

    return errors


def build_persona_payload(values: dict[str, str | None]) -> dict[str, Any]:
    tipo_persona = clean_text(values.get("tipo_persona"))
    payload: dict[str, Any] = {
        "tipo_persona": tipo_persona,
        "nombre": clean_text(values.get("nombre")) or None,
        "apellido": clean_text(values.get("apellido")) or None,
        "razon_social": clean_text(values.get("razon_social")) or None,
        "estado_persona": clean_text(values.get("estado_persona")),
        "observaciones": clean_text(values.get("observaciones")) or None,
    }

    fecha_nacimiento = clean_text(values.get("fecha_nacimiento"))
    payload["fecha_nacimiento"] = fecha_nacimiento or None

    if tipo_persona == "FISICA":
        payload["razon_social"] = None
    elif tipo_persona == "JURIDICA":
        # El contrato backend actual tipa nombre y apellido como str requeridos;
        # para persona jurídica se envían vacíos y la identidad visible queda
        # representada por razon_social.
        payload["nombre"] = ""
        payload["apellido"] = ""

    return payload
