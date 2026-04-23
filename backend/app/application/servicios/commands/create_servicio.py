from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateServicioCommand:
    context: CommandContext
    codigo_servicio: str
    nombre_servicio: str
    descripcion: str | None
    estado_servicio: str
