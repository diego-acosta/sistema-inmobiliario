from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeleteInmuebleCommand:
    context: CommandContext
    id_inmueble: int
    if_match_version: int | None
