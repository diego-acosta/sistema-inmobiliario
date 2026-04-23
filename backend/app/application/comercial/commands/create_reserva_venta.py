from dataclasses import dataclass
from datetime import date, datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateReservaVentaParticipacionCommand:
    id_persona: int
    id_rol_participacion: int
    fecha_desde: date | None
    fecha_hasta: date | None
    observaciones: str | None


@dataclass(slots=True)
class CreateReservaVentaObjetoCommand:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


@dataclass(slots=True)
class CreateReservaVentaCommand:
    context: CommandContext
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_vencimiento: datetime | None
    observaciones: str | None
    objetos: list[CreateReservaVentaObjetoCommand]
    participaciones: list[CreateReservaVentaParticipacionCommand]
