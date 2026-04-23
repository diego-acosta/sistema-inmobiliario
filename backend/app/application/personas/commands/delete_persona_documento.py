from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeletePersonaDocumentoCommand:
    context: CommandContext
    id_persona: int
    id_persona_documento: int
    if_match_version: int | None
