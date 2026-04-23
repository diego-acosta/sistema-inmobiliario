from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateDesarrolloCommand:
    context: CommandContext
    id_desarrollo: int
    if_match_version: int | None
    codigo_desarrollo: str
    nombre_desarrollo: str
    descripcion: str | None
    estado_desarrollo: str
    observaciones: str | None
