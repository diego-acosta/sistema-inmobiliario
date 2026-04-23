from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeleteDisponibilidadCommand:
    context: CommandContext
    id_disponibilidad: int
    if_match_version: int | None
