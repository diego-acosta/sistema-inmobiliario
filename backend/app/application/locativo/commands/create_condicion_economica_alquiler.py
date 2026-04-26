from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateCondicionEconomicaAlquilerCommand:
    context: CommandContext
    id_contrato_alquiler: int
    monto_base: Decimal
    periodicidad: str | None
    moneda: str | None
    fecha_desde: date
    fecha_hasta: date | None
    observaciones: str | None
