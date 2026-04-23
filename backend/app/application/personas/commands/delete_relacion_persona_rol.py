from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeleteRelacionPersonaRolCommand:
    context: CommandContext
    id_relacion_persona_rol: int
    if_match_version: int | None
