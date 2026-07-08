from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any


_SEPARADORES_DOCUMENTO_RE = re.compile(r"[\s.\-_/]+")
_ESPACIOS_RE = re.compile(r"\s+")


class TipoDuplicadoPersona(str, Enum):
    FUERTE = "FUERTE"
    POSIBLE = "POSIBLE"


@dataclass(frozen=True, slots=True)
class PersonaNormalizada:
    tipo_persona: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    razon_social: str | None = None
    cuit_cuil: str | None = None
    tipo_documento: str | None = None
    numero_documento: str | None = None
    email: str | None = None


@dataclass(frozen=True, slots=True)
class DuplicadoPersona:
    tipo: TipoDuplicadoPersona
    criterio: str
    id_persona: int | None = None
    op_id_alta: Any | None = None


def normalizar_texto_basico(value: str | None) -> str | None:
    """Normaliza texto para comparaciones básicas: trim, espacios y case-insensitive."""
    if value is None:
        return None
    normalized = _ESPACIOS_RE.sub(" ", value.strip()).casefold()
    return normalized or None


def normalizar_documento_fiscal(value: str | None) -> str | None:
    """Normaliza CUIT/CUIL/CDI quitando guiones, puntos y espacios."""
    if value is None:
        return None
    normalized = re.sub(r"[\s.\-]+", "", value.strip()).casefold()
    return normalized or None


def normalizar_documento_principal(value: str | None) -> str | None:
    """Normaliza documento principal quitando espacios y separadores comunes."""
    if value is None:
        return None
    normalized = _SEPARADORES_DOCUMENTO_RE.sub("", value.strip()).casefold()
    return normalized or None


def normalizar_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def normalizar_persona_para_duplicados(
    *,
    tipo_persona: str | None = None,
    nombre: str | None = None,
    apellido: str | None = None,
    razon_social: str | None = None,
    cuit_cuil: str | None = None,
    tipo_documento: str | None = None,
    numero_documento: str | None = None,
    email: str | None = None,
) -> PersonaNormalizada:
    return PersonaNormalizada(
        tipo_persona=normalizar_texto_basico(tipo_persona),
        nombre=normalizar_texto_basico(nombre),
        apellido=normalizar_texto_basico(apellido),
        razon_social=normalizar_texto_basico(razon_social),
        cuit_cuil=normalizar_documento_fiscal(cuit_cuil),
        tipo_documento=normalizar_texto_basico(tipo_documento),
        numero_documento=normalizar_documento_principal(numero_documento),
        email=normalizar_email(email),
    )


def detectar_duplicado_persona(
    nueva: PersonaNormalizada,
    existente: PersonaNormalizada,
    *,
    id_persona: int | None = None,
    op_id_alta: Any | None = None,
) -> DuplicadoPersona | None:
    """Detecta duplicado fuerte o posible sin modificar ni fusionar registros."""
    if nueva.cuit_cuil and existente.cuit_cuil and nueva.cuit_cuil == existente.cuit_cuil:
        return DuplicadoPersona(TipoDuplicadoPersona.FUERTE, "cuit_cuil", id_persona, op_id_alta)

    if (
        nueva.tipo_documento
        and nueva.numero_documento
        and existente.tipo_documento
        and existente.numero_documento
        and nueva.tipo_documento == existente.tipo_documento
        and nueva.numero_documento == existente.numero_documento
    ):
        return DuplicadoPersona(
            TipoDuplicadoPersona.FUERTE,
            "documento_principal",
            id_persona,
            op_id_alta,
        )

    if nueva.email and existente.email and nueva.email == existente.email:
        return DuplicadoPersona(TipoDuplicadoPersona.POSIBLE, "email", id_persona, op_id_alta)

    if (
        nueva.tipo_persona == "fisica"
        and existente.tipo_persona == "fisica"
        and nueva.nombre
        and nueva.apellido
        and nueva.nombre == existente.nombre
        and nueva.apellido == existente.apellido
    ):
        return DuplicadoPersona(TipoDuplicadoPersona.POSIBLE, "nombre_apellido", id_persona, op_id_alta)

    if (
        nueva.tipo_persona == "juridica"
        and existente.tipo_persona == "juridica"
        and nueva.razon_social
        and nueva.razon_social == existente.razon_social
    ):
        return DuplicadoPersona(TipoDuplicadoPersona.POSIBLE, "razon_social", id_persona, op_id_alta)

    return None
