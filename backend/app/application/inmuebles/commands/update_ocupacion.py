from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateOcupacionCommand:
    context: CommandContext
    id_ocupacion: int
    if_match_version: int | None
    id_inmueble: int | None
    id_unidad_funcional: int | None
    tipo_ocupacion: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    descripcion: str | None
    observaciones: str | None
