from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class RegistrarRestitucionLocativaCommand:
    context: CommandContext
    id_contrato_alquiler: int
    fecha_restitucion: date
    estado_inmueble: str | None
    observaciones: str | None
