from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class GenerarContratoDesdeReservaLocativaCommand:
    context: CommandContext
    id_reserva_locativa: int
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    observaciones: str | None
