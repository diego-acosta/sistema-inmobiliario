from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeleteReservaVentaCommand:
    context: CommandContext
    id_reserva_venta: int
    if_match_version: int | None
