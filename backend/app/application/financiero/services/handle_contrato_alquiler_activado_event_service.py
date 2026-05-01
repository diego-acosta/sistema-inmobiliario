from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult


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

        # Resolver condición vigente por período ANTES de tocar repositorio financiero
        periodos_aplicables: list[tuple[date, date, dict[str, Any]]] = []
        omitidas = 0
        for periodo_desde, periodo_hasta in periodos:
            condicion = get_condicion_vigente_para_periodo(condiciones, periodo_desde)
            if condicion is None:
                omitidas += 1
            else:
                periodos_aplicables.append((periodo_desde, periodo_hasta, condicion))

        if not periodos_aplicables:
            return AppResult.ok({"generadas": 0, "omitidas": omitidas, "razon": "sin_condicion_aplicable"})

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
                fecha_emision=periodo_desde,
                fecha_vencimiento=periodo_desde,
                periodo_desde=periodo_desde,
                periodo_hasta=periodo_hasta,
                importe_total=float(condicion["monto_base"]),
                moneda=condicion.get("moneda") or "ARS",
                estado_obligacion="EMITIDA",
                id_concepto_financiero=id_concepto,
                uid_global_obligacion=str(self.uuid_generator()),
                uid_global_composicion=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
            for periodo_desde, periodo_hasta, condicion in periodos_aplicables
        ]

        generadas = self.financiero_repo.create_cronograma_obligaciones(payloads)
        return AppResult.ok({"generadas": generadas, "omitidas": omitidas})
