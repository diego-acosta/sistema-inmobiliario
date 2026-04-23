from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateEscrituracionCommand:
    context: CommandContext
    id_venta: int
    fecha_escrituracion: datetime
    numero_escritura: str | None
    observaciones: str | None
