from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


class CalendarioComercialQuery(Protocol):
    def obtener(self, fecha_efectiva: date): ...


class PrimerVencimientoSugeridoFueraDeRango(Exception):
    code = "PRIMER_VENCIMIENTO_SUGERIDO_FUERA_DE_RANGO"


@dataclass(frozen=True)
class PrimerVencimientoSugerido:
    fecha_primer_vencimiento_sugerida: date


@dataclass(frozen=True)
class ResolverPrimerVencimientoSugeridoService:
    calendario_query: CalendarioComercialQuery

    def resolver(self, fecha_venta: date) -> PrimerVencimientoSugerido:
        if not isinstance(fecha_venta, date) or isinstance(fecha_venta, datetime):
            raise TypeError("fecha_venta debe ser date")

        calendario = self.calendario_query.obtener(fecha_venta)
        meses_hasta_vencimiento = (
            1
            if fecha_venta.day <= calendario.dia_cierre_comercial
            else 2
        )
        fecha_sugerida = _construir_fecha_en_mes_destino(
            fecha_venta=fecha_venta,
            meses=meses_hasta_vencimiento,
            dia=calendario.dia_vencimiento_predeterminado_cuotas,
        )
        return PrimerVencimientoSugerido(
            fecha_primer_vencimiento_sugerida=fecha_sugerida
        )


def _construir_fecha_en_mes_destino(
    *, fecha_venta: date, meses: int, dia: int
) -> date:
    indice_mes = fecha_venta.month - 1 + meses
    anio_destino = fecha_venta.year + indice_mes // 12
    mes_destino = indice_mes % 12 + 1
    if anio_destino > date.max.year:
        raise PrimerVencimientoSugeridoFueraDeRango
    ultimo_dia = calendar.monthrange(anio_destino, mes_destino)[1]
    return date(anio_destino, mes_destino, min(dia, ultimo_dia))
