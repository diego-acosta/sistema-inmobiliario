from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class GenerateVentaFromReservaVentaCommand:
    context: CommandContext
    id_reserva_venta: int
    if_match_version: int | None
    codigo_venta: str
    fecha_venta: datetime
    monto_total: Decimal | None
    observaciones: str | None
