from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeletePersonaCommand:
    context: CommandContext
    id_persona: int
    if_match_version: int | None
