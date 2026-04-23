from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeletePersonaContactoCommand:
    context: CommandContext
    id_persona: int
    id_persona_contacto: int
    if_match_version: int | None
