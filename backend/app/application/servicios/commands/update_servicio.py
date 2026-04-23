from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateServicioCommand:
    context: CommandContext
    id_servicio: int
    if_match_version: int | None
    codigo_servicio: str
    nombre_servicio: str
    descripcion: str | None
    estado_servicio: str
