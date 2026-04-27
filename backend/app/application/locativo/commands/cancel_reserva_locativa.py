from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CancelReservaLocativaCommand:
    context: CommandContext
    id_reserva_locativa: int
    if_match_version: int | None
