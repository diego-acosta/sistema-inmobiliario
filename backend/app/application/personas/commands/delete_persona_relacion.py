from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeletePersonaRelacionCommand:
    context: CommandContext
    id_persona_origen: int
    id_persona_relacion: int
    if_match_version: int | None
