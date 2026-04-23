from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateDesarrolloCommand:
    context: CommandContext
    codigo_desarrollo: str
    nombre_desarrollo: str
    descripcion: str | None
    estado_desarrollo: str
    observaciones: str | None
