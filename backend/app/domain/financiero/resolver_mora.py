"""
Resolver centralizado de parámetros de mora.

Prioridad de resolución (de mayor a menor):
  1. Regla por origen (tipo_origen + id_origen)    e.g. "CONTRATO_ALQUILER:42" → tasa específica de ese contrato
  2. Regla por concepto financiero
     e.g. "CANON_LOCATIVO" → tasa asociada al concepto
  3. Default global (TASA_DIARIA_MORA_DEFAULT, DIAS_GRACIA_MORA_DEFAULT)

V1: no existen tablas de reglas. El resolver siempre retorna el default.
Las reglas se pueden inyectar vía el parámetro `reglas` (útil en tests y como
punto de extensión futuro sin cambiar la interfaz pública).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.financiero.parametros_mora import (
    DIAS_GRACIA_MORA_DEFAULT,
    TASA_DIARIA_MORA_DEFAULT,
)


@dataclass(frozen=True)
class ResolucionMora:
    tasa_diaria: Decimal
    dias_gracia: int


_DEFAULT_RESOLUCION = ResolucionMora(
    tasa_diaria=TASA_DIARIA_MORA_DEFAULT,
    dias_gracia=DIAS_GRACIA_MORA_DEFAULT,
)


def resolver_mora_params(
    tipo_origen: str | None = None,
    id_origen: int | None = None,
    codigo_concepto: str | None = None,
    *,
    reglas: dict[str, ResolucionMora] | None = None,
) -> ResolucionMora:
    """
    Resuelve tasa_diaria y dias_gracia según prioridad.

    Clave de origen:  "<TIPO_ORIGEN>:<id_origen>"  (ej. "CONTRATO_ALQUILER:42")
    Clave de concepto: "<codigo_concepto>"          (ej. "CANON_LOCATIVO")

    Si no hay reglas configuradas, retorna el default global.
    """
    if reglas:
        # 1. Por origen
        if tipo_origen is not None and id_origen is not None:
            clave_origen = f"{tipo_origen.upper()}:{id_origen}"
            if clave_origen in reglas:
                return reglas[clave_origen]
        # 2. Por concepto
        if codigo_concepto is not None and codigo_concepto in reglas:
            return reglas[codigo_concepto]

    return _DEFAULT_RESOLUCION
