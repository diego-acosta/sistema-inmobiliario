from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DeleteUnidadFuncionalCommand:
    context: CommandContext
    id_unidad_funcional: int
    if_match_version: int | None
