from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult


ROL_OBLIGADO_LOCATARIO = "LOCATARIO_PRINCIPAL"
_Q = Decimal("0.01")


# ── helpers de período ────────────────────────────────────────────────────────

def generate_monthly_periods(
    fecha_inicio: date, fecha_fin: date
) -> list[tuple[date, date]]:
    """
    Divide [fecha_inicio, fecha_fin] en tramos mensuales reales.

    Ejemplo: 01/01 → 15/03
      → (01/01, 31/01), (01/02, 28/02), (01/03, 15/03)
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
    Retorna la condición económica vigente para periodo_desde, o None.

    Vigente si:
      fecha_desde <= periodo_desde
      y (fecha_hasta is None OR fecha_hasta >= periodo_desde)

    Si hay más de una, gana la de fecha_desde más reciente.
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
    Si es NULL, retorna periodo_desde como fallback técnico (RN-LOC-FIN-003).
    Si el día no existe en el mes, usa el último día real del mes.
    Si el día calculado quedara antes de periodo_desde, usa periodo_desde.
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
    Divide [periodo_desde, periodo_hasta] en segmentos según cambios de condición.

    Un cambio de condición ocurre cuando fecha_desde de una condición cae
    estrictamente dentro del período (> periodo_desde y <= periodo_hasta).

    Si no hay cambios internos → devuelve un único segmento (comportamiento original).
    Si no hay condición aplicable para un segmento → ese segmento se omite.
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
    Calcula el importe de cada segmento prorateado sobre días reales del mes.

    Fórmula:  importe = monto_base * dias_segmento / dias_mes
    Redondeo: ROUND_HALF_UP a 2 decimales.
    Residuo:  cuando todos los segmentos comparten el mismo monto_base,
              el último segmento absorbe la diferencia de redondeo para
              garantizar que la suma sea exactamente la del período completo.
    Segmento único: devuelve monto_base completo (sin prorrateo, igual que antes).
    """
    if not segmentos:
        return []

    if len(segmentos) == 1:
        return [float(Decimal(str(segmentos[0][2]["monto_base"])))]

    dias_mes = Decimal(calendar.monthrange(periodo_desde.year, periodo_desde.month)[1])
    importes: list[Decimal] = []

    for seg_desde, seg_hasta, condicion in segmentos:
        dias_seg = Decimal((seg_hasta - seg_desde).days + 1)
        imp = (Decimal(str(condicion["monto_base"])) * dias_seg / dias_mes).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        importes.append(imp)

    # Residuo: aplica solo cuando todos los segmentos tienen el mismo monto_base
    montos_base = {Decimal(str(s[2]["monto_base"])) for s in segmentos}
    if len(montos_base) == 1:
        monto_base = next(iter(montos_base))
        total_dias = Decimal(sum((s[1] - s[0]).days + 1 for s in segmentos))
        total_esperado = (monto_base * total_dias / dias_mes).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        importes[-1] = total_esperado - sum(importes[:-1])

    return [float(imp) for imp in importes]


# ── payloads ──────────────────────────────────────────────────────────────────

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


# ── protocols ─────────────────────────────────────────────────────────────────

class LocativoRepository(Protocol):
    def get_contrato_alquiler(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None: ...

    def get_locatario_principal_contrato(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None: ...


class FinancieroRepository(Protocol):
    def get_relacion_generadora_by_origen(
        self, tipo_origen: str, id_origen: int
    ) -> dict[str, Any] | None: ...

    def create_relacion_generadora(
        self, payload: RelacionGeneradoraForCronogramaPayload
    ) -> dict[str, Any]: ...

    def obligaciones_exist_for_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> bool: ...

    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None: ...

    def create_cronograma_obligaciones(
        self, periodos: list[PeriodoCronogramaPayload]
    ) -> int: ...


# ── service ───────────────────────────────────────────────────────────────────

class HandleContratoAlquilerActivadoEventService:
    def __init__(
        self,
        locativo_repository: LocativoRepository,
        financiero_repository: FinancieroRepository,
        uuid_generator=None,
    ) -> None:
        self.locativo_repo = locativo_repository
        self.financiero_repo = financiero_repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        id_contrato_alquiler: int,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        contrato = self.locativo_repo.get_contrato_alquiler(id_contrato_alquiler)
        if contrato is None or contrato.get("deleted_at") is not None:
            return AppResult.fail("NOT_FOUND_CONTRATO")

        fecha_fin = contrato.get("fecha_fin")
        if fecha_fin is None:
            return AppResult.ok({"generadas": 0, "omitidas": 0, "razon": "sin_fecha_fin"})

        condiciones = contrato.get("condiciones_economicas_alquiler") or []
        periodos = generate_monthly_periods(contrato["fecha_inicio"], fecha_fin)

        # Resolver segmentos por período con prorrateo ante cambios de condición.
        # Cada período mensual puede producir 1..N segmentos (obligaciones).
        # Tupla: (seg_desde, seg_hasta, condicion, importe, fecha_vencimiento, emision_mes)
        # emision_mes = periodo_desde_mes, usado como fecha_emision para satisfacer
        # la constraint DB: fecha_vencimiento >= fecha_emision.
        segmentos_todos: list[tuple[date, date, dict[str, Any], float, date, date]] = []
        omitidas = 0

        for periodo_desde_mes, periodo_hasta_mes in periodos:
            segs = get_segmentos_para_periodo(condiciones, periodo_desde_mes, periodo_hasta_mes)
            if not segs:
                omitidas += 1
                continue
            importes = calcular_importes_prorateados(segs, periodo_desde_mes)
            fecha_venc = calcular_fecha_vencimiento_canon(
                periodo_desde_mes, contrato.get("dia_vencimiento_canon")
            )
            for (seg_desde, seg_hasta, condicion), importe in zip(segs, importes):
                segmentos_todos.append(
                    (seg_desde, seg_hasta, condicion, importe, fecha_venc, periodo_desde_mes)
                )

        if not segmentos_todos:
            return AppResult.ok({"generadas": 0, "omitidas": omitidas, "razon": "sin_condicion_aplicable"})

        locatario = self.locativo_repo.get_locatario_principal_contrato(
            id_contrato_alquiler
        )
        if locatario is None:
            return AppResult.fail("SIN_LOCATARIO_PRINCIPAL")

        id_instalacion = getattr(context, "id_instalacion", None)
        op_id = getattr(context, "op_id", None)
        now = datetime.now(UTC)

        # Obtener o crear relacion_generadora (solo si hay períodos a generar)
        relacion = self.financiero_repo.get_relacion_generadora_by_origen(
            "contrato_alquiler", id_contrato_alquiler
        )
        if relacion is None:
            rg_payload = RelacionGeneradoraForCronogramaPayload(
                tipo_origen="contrato_alquiler",
                id_origen=id_contrato_alquiler,
                descripcion=None,
                uid_global=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
            relacion = self.financiero_repo.create_relacion_generadora(rg_payload)

        id_rg = relacion["id_relacion_generadora"]

        if self.financiero_repo.obligaciones_exist_for_relacion_generadora(id_rg):
            return AppResult.ok({"generadas": 0, "omitidas": 0, "razon": "ya_generado"})

        concepto = self.financiero_repo.get_concepto_financiero_by_codigo("CANON_LOCATIVO")
        if concepto is None:
            return AppResult.fail("NOT_FOUND_CONCEPTO_CANON_LOCATIVO")

        id_concepto = concepto["id_concepto_financiero"]

        payloads = [
            PeriodoCronogramaPayload(
                id_relacion_generadora=id_rg,
                fecha_emision=emision_mes,
                fecha_vencimiento=fecha_vencimiento,
                periodo_desde=seg_desde,
                periodo_hasta=seg_hasta,
                importe_total=importe,
                moneda=condicion.get("moneda") or "ARS",
                estado_obligacion="EMITIDA",
                id_concepto_financiero=id_concepto,
                uid_global_obligacion=str(self.uuid_generator()),
                uid_global_composicion=str(self.uuid_generator()),
                uid_global_obligado=str(self.uuid_generator()),
                id_persona_obligado=locatario["id_persona"],
                rol_obligado=ROL_OBLIGADO_LOCATARIO,
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
            for seg_desde, seg_hasta, condicion, importe, fecha_vencimiento, emision_mes
            in segmentos_todos
        ]

        generadas = self.financiero_repo.create_cronograma_obligaciones(payloads)
        return AppResult.ok({"generadas": generadas, "omitidas": omitidas})
