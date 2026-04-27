from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext
from app.application.locativo.commands.create_reserva_locativa import (
    CreateReservaLocativaObjetoCommand,
)


@dataclass(slots=True)
class ConvertSolicitudAlquilerToReservaLocativaCommand:
    context: CommandContext
    id_solicitud_alquiler: int
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_vencimiento: datetime | None
    observaciones: str | None
    objetos: list[CreateReservaLocativaObjetoCommand]
    confirmar: bool
