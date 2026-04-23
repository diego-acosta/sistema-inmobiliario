from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateReservaVentaCommand:
    context: CommandContext
    id_reserva_venta: int
    if_match_version: int | None
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_vencimiento: datetime | None
    observaciones: str | None
