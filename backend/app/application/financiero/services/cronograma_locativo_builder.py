from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID


ROL_OBLIGADO_LOCATARIO = "LOCATARIO_PRINCIPAL"
_Q = Decimal("0.01")


def generate_monthly_periods(
    fecha_inicio: date, fecha_fin: date
) -> list[tuple[date, date]]:
    """
    Divide [fecha_inicio, fecha_fin] en tramos mensuales reales.

    Ejemplo: 01/01 -> 15/03
      -> (01/01, 31/01), (01/02, 28/02), (01/03, 15/03)
    """
    periods: list[tuple[date, date]] = []
    current = fecha_inicio
    while current <= fecha_fin:
        period_desde = current
        last_day = date(
            current.year,
            current.month,
            calendar.monthrange(current.year, current.month)[1],
        )
        period_hasta = min(last_day, fecha_fin)
        periods.append((period_desde, period_hasta))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return periods


def get_condicion_vigente_para_periodo(
    condiciones: list[dict[str, Any]], periodo_desde: date
) -> dict[str, Any] | None:
    """
    Retorna la condicion economica vigente para periodo_desde, o None.

    Vigente si:
      fecha_desde <= periodo_desde
      y (fecha_hasta is None OR fecha_hasta >= periodo_desde)

    Si hay mas de una, gana la de fecha_desde mas reciente.
    """
    vigentes = [
        c for c in condiciones
        if c["fecha_desde"] <= periodo_desde
        and (c.get("fecha_hasta") is None or c["fecha_hasta"] >= periodo_desde)
    ]
    if not vigentes:
        return None
    return max(vigentes, key=lambda c: c["fecha_desde"])


def calcular_fecha_vencimiento_canon(
    periodo_desde: date,
    dia_vencimiento_canon: int | None,
) -> date:
    """
    Calcula fecha_vencimiento para el canon locativo.

    Fuente: contrato_alquiler.dia_vencimiento_canon.
    Si es NULL, retorna periodo_desde como fallback tecnico (RN-LOC-FIN-003).
    Si el dia no existe en el mes, usa el ultimo dia real del mes.
    Si el dia calculado quedara antes de periodo_desde, usa periodo_desde.
    """
    if dia_vencimiento_canon is None:
        return periodo_desde

    ultimo_dia = calendar.monthrange(periodo_desde.year, periodo_desde.month)[1]
    vencimiento = date(periodo_desde.year, periodo_desde.month, min(dia_vencimiento_canon, ultimo_dia))
    if vencimiento < periodo_desde:
        return periodo_desde
    return vencimiento


def get_segmentos_para_periodo(
    condiciones: list[dict[str, Any]],
    periodo_desde: date,
    periodo_hasta: date,
) -> list[tuple[date, date, dict[str, Any]]]:
    """
    Divide [periodo_desde, periodo_hasta] en segmentos segun cambios de condicion.

    Un cambio de condicion ocurre cuando fecha_desde de una condicion cae
    estrictamente dentro del periodo (> periodo_desde y <= periodo_hasta).

    Si no hay cambios internos -> devuelve un unico segmento (comportamiento original).
    Si no hay condicion aplicable para un segmento -> ese segmento se omite.
    """
    puntos: set[date] = {periodo_desde}
    for c in condiciones:
        fd = c["fecha_desde"]
        if periodo_desde < fd <= periodo_hasta:
            puntos.add(fd)

    segmentos: list[tuple[date, date, dict[str, Any]]] = []
    puntos_ord = sorted(puntos)

    for i, seg_desde in enumerate(puntos_ord):
        seg_hasta = (
            puntos_ord[i + 1] - timedelta(days=1)
            if i + 1 < len(puntos_ord)
            else periodo_hasta
        )
        condicion = get_condicion_vigente_para_periodo(condiciones, seg_desde)
        if condicion is not None:
            segmentos.append((seg_desde, seg_hasta, condicion))

    return segmentos


def calcular_importes_prorateados(
    segmentos: list[tuple[date, date, dict[str, Any]]],
    periodo_desde: date,
) -> list[float]:
    """
    Calcula el importe de cada segmento prorateado sobre dias reales del mes.

    Formula:  importe = monto_base * dias_segmento / dias_mes
    Redondeo: ROUND_HALF_UP a 2 decimales.
    Residuo:  cuando todos los segmentos comparten el mismo monto_base,
              el ultimo segmento absorbe la diferencia de redondeo para
              garantizar que la suma sea exactamente la del periodo completo.
    Segmento unico: devuelve monto_base completo solo si cubre el mes real completo.
    """
    if not segmentos:
        return []

    def _cubre_mes_completo(seg_desde: date, seg_hasta: date) -> bool:
        ultimo_dia = calendar.monthrange(seg_desde.year, seg_desde.month)[1]
        return (
            seg_desde.day == 1
            and seg_hasta == date(seg_desde.year, seg_desde.month, ultimo_dia)
        )

    if len(segmentos) == 1:
        seg_desde, seg_hasta, condicion = segmentos[0]
        if _cubre_mes_completo(seg_desde, seg_hasta):
            return [float(Decimal(str(condicion["monto_base"])))]

    dias_mes = Decimal(calendar.monthrange(periodo_desde.year, periodo_desde.month)[1])
    importes: list[Decimal] = []

    for seg_desde, seg_hasta, condicion in segmentos:
        dias_seg = Decimal((seg_hasta - seg_desde).days + 1)
        imp = (Decimal(str(condicion["monto_base"])) * dias_seg / dias_mes).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        importes.append(imp)

    montos_base = {Decimal(str(s[2]["monto_base"])) for s in segmentos}
    if len(montos_base) == 1:
        monto_base = next(iter(montos_base))
        total_dias = Decimal(sum((s[1] - s[0]).days + 1 for s in segmentos))
        total_esperado = (monto_base * total_dias / dias_mes).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        importes[-1] = total_esperado - sum(importes[:-1])

    return [float(imp) for imp in importes]


@dataclass(slots=True)
class RelacionGeneradoraForCronogramaPayload:
    tipo_origen: str
    id_origen: int
    descripcion: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class PeriodoCronogramaPayload:
    id_relacion_generadora: int
    fecha_emision: date
    fecha_vencimiento: date
    periodo_desde: date
    periodo_hasta: date
    importe_total: float
    moneda: str
    estado_obligacion: str
    id_concepto_financiero: int
    uid_global_obligacion: str
    uid_global_composicion: str
    uid_global_obligado: str
    id_persona_obligado: int
    rol_obligado: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
