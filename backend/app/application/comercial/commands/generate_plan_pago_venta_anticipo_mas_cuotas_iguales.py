from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand:
    context: CommandContext
    id_venta: int
    monto_total_plan: Decimal
    moneda: str
    importe_anticipo: Decimal
    fecha_vencimiento_anticipo: date
    cantidad_cuotas: int
    fecha_primer_vencimiento: date
    periodicidad: str
    regla_redondeo: str
