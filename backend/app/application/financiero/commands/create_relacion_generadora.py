from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateRelacionGeneradoraCommand:
    context: CommandContext
    tipo_origen: str
    id_origen: int
    descripcion: str | None
