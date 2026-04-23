from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeleteServicioCommand:
    context: CommandContext
    id_servicio: int
    if_match_version: int | None
