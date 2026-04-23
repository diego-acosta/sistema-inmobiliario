from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeleteRepresentacionPoderCommand:
    context: CommandContext
    id_persona_representado: int
    id_representacion_poder: int
    if_match_version: int | None
