from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateInstrumentoCompraventaObjetoCommand:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


@dataclass(slots=True)
class CreateInstrumentoCompraventaCommand:
    context: CommandContext
    id_venta: int
    tipo_instrumento: str
    numero_instrumento: str | None
    fecha_instrumento: datetime
    estado_instrumento: str
    observaciones: str | None
    objetos: list[CreateInstrumentoCompraventaObjetoCommand]
