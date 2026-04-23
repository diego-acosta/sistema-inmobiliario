from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeleteOcupacionCommand:
    context: CommandContext
    id_ocupacion: int
    if_match_version: int | None
