from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class AssociateInmuebleDesarrolloCommand:
    context: CommandContext
    id_inmueble: int
    id_desarrollo: int
    if_match_version: int | None
