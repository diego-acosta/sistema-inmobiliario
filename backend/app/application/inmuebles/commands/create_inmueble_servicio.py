from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateInmuebleServicioCommand:
    context: CommandContext
    id_inmueble: int
    id_servicio: int
    estado: str | None
