from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class PlanPagoVentaBloqueInput:
    tipo_bloque: str
    etiqueta_bloque: str | None = None
    importe_total_bloque: Decimal | None = None
    fecha_vencimiento: date | None = None
    cantidad_cuotas: int | None = None
    importe_cuota: Decimal | None = None
    fecha_primer_vencimiento: date | None = None
    periodicidad: str | None = None
    regla_redondeo: str | None = None
    metodo_liquidacion: str | None = None
    tasa_interes_directo_periodica: Decimal | None = None
    cantidad_periodos: int | None = None
    base_calculo_interes: str | None = None
    observaciones: str | None = None


@dataclass(slots=True)
class GeneratePlanPagoVentaV2PorBloquesCommand:
    context: CommandContext
    id_venta: int
    tipo_pago: str
    monto_total_plan: Decimal
    moneda: str
    bloques: list[PlanPagoVentaBloqueInput]
    observaciones: str | None = None
