"""Helpers compartidos para el alta Flet de inmuebles."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

ESTADOS_ADMINISTRATIVOS = ("ACTIVO", "INACTIVO")
ESTADOS_JURIDICOS = ("REGULAR", "OBSERVADO")
ESTADOS_DATO_CATASTRAL = ("ACTIVO", "INACTIVO", "HISTORICO")
CATASTRAL_ADVANCED_FIELDS = (
    "nomenclatura_catastral",
    "partida_inmobiliaria",
    "matricula",
    "folio_real",
    "circunscripcion",
    "seccion",
    "chacra",
    "quinta",
    "fraccion",
    "parcela",
    "subparcela",
    "superficie_titulo",
    "superficie_mensura",
    "medidas",
    "situacion_posesoria",
    "situacion_dominial",
    "organismo_origen",
    "fecha_desde",
    "fecha_hasta",
    "estado_dato",
    "observaciones",
    "observaciones_catastrales",
)


def clean_text(value: str | None) -> str:
    return (value or "").strip()


def _validate_positive_decimal(value: str | None, field_label: str) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        number = Decimal(text)
        if not number.is_finite():
            return f"{field_label} debe ser un decimal positivo."
        if number <= 0:
            return f"{field_label} debe ser un decimal positivo."
    except InvalidOperation:
        return f"{field_label} debe ser un decimal positivo."
    return None


def _validate_positive_int(value: str | None, field_label: str) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        number = int(text)
    except ValueError:
        return f"{field_label} debe ser un entero positivo."
    if number <= 0:
        return f"{field_label} debe ser un entero positivo."
    return None


def validate_form(values: dict[str, str | None]) -> list[str]:
    errors: list[str] = []
    if not clean_text(values.get("codigo_inmueble")):
        errors.append("Código de inmueble es requerido.")
    if not clean_text(values.get("estado_administrativo")):
        errors.append("Estado administrativo es requerido.")
    if not clean_text(values.get("estado_juridico")):
        errors.append("Estado jurídico es requerido.")

    superficie_error = _validate_positive_decimal(
        values.get("superficie"), "Superficie"
    )
    if superficie_error:
        errors.append(superficie_error)
    desarrollo_error = _validate_positive_int(
        values.get("id_desarrollo"), "ID desarrollo"
    )
    if desarrollo_error:
        errors.append(desarrollo_error)
    return errors


def build_inmueble_payload(values: dict[str, str | None]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "codigo_inmueble": clean_text(values.get("codigo_inmueble")),
        "estado_administrativo": clean_text(values.get("estado_administrativo")),
        "estado_juridico": clean_text(values.get("estado_juridico")),
    }
    for field_name in ("nombre_inmueble", "observaciones"):
        clean_value = clean_text(values.get(field_name))
        if clean_value:
            payload[field_name] = clean_value

    superficie = clean_text(values.get("superficie"))
    if superficie:
        payload["superficie"] = str(Decimal(superficie))

    id_desarrollo = clean_text(values.get("id_desarrollo"))
    if id_desarrollo:
        payload["id_desarrollo"] = int(id_desarrollo)

    return payload


def validate_dato_catastral_form(values: dict[str, str | None]) -> list[str]:
    errors: list[str] = []
    for field_name, label in (
        ("superficie_titulo", "Superficie título"),
        ("superficie_mensura", "Superficie mensura"),
    ):
        error = _validate_positive_decimal(values.get(field_name), label)
        if error:
            errors.append(error)
    return errors


def has_dato_catastral_avanzado_util(values: dict[str, str | None]) -> bool:
    return any(
        clean_text(values.get(field_name)) for field_name in CATASTRAL_ADVANCED_FIELDS
    )


def has_manzana_o_lote(values: dict[str, str | None]) -> bool:
    return bool(clean_text(values.get("manzana")) or clean_text(values.get("lote")))


def has_dato_catastral_util(
    values: dict[str, str | None], *, incluir_avanzados: bool
) -> bool:
    return has_manzana_o_lote(values) or (
        incluir_avanzados and has_dato_catastral_avanzado_util(values)
    )


def should_create_dato_catastral(
    mostrar_datos_catastrales_avanzados: bool, values: dict[str, str | None]
) -> bool:
    return has_dato_catastral_util(
        values, incluir_avanzados=mostrar_datos_catastrales_avanzados
    )


def build_dato_catastral_payload(
    values: dict[str, str | None], *, incluir_avanzados: bool
) -> dict[str, Any]:
    payload: dict[str, Any] = {"estado_dato": "ACTIVO"}
    for field_name in ("manzana", "lote"):
        clean_value = clean_text(values.get(field_name))
        if clean_value:
            payload[field_name] = clean_value
    if not incluir_avanzados:
        return payload

    estado_dato = clean_text(values.get("estado_dato"))
    if estado_dato:
        payload["estado_dato"] = estado_dato
    for field_name in (
        "nomenclatura_catastral",
        "partida_inmobiliaria",
        "matricula",
        "folio_real",
        "circunscripcion",
        "seccion",
        "chacra",
        "quinta",
        "fraccion",
        "parcela",
        "subparcela",
        "medidas",
        "situacion_posesoria",
        "situacion_dominial",
        "organismo_origen",
        "fecha_desde",
        "fecha_hasta",
    ):
        clean_value = clean_text(values.get(field_name))
        if clean_value:
            payload[field_name] = clean_value
    observaciones_catastrales = clean_text(values.get("observaciones_catastrales"))
    observaciones = clean_text(values.get("observaciones"))
    if observaciones_catastrales:
        payload["observaciones"] = observaciones_catastrales
    elif observaciones:
        payload["observaciones"] = observaciones
    for field_name in ("superficie_titulo", "superficie_mensura"):
        clean_value = clean_text(values.get(field_name))
        if clean_value:
            payload[field_name] = str(Decimal(clean_value))
    return payload
