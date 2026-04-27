from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateSolicitudAlquilerCommand:
    context: CommandContext
    codigo_solicitud: str
    fecha_solicitud: datetime
    observaciones: str | None
