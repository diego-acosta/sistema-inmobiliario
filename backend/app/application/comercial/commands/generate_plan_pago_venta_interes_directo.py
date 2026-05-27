from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class GeneratePlanPagoVentaInteresDirectoCommand:
    context: CommandContext
    id_venta: int
    monto_total_plan: Decimal
    moneda: str
    cantidad_cuotas: int
    tasa_interes_directo: Decimal
    fecha_primer_vencimiento: date
    periodicidad: str = "MENSUAL"
    regla_redondeo: str = "ULTIMA_CUOTA"
