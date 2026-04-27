from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateReservaLocativaObjetoCommand:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


@dataclass(slots=True)
class CreateReservaLocativaCommand:
    context: CommandContext
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_vencimiento: datetime | None
    observaciones: str | None
    objetos: list[CreateReservaLocativaObjetoCommand]
