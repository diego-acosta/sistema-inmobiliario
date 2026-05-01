from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateContratoAlquilerObjetoCommand:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


@dataclass(slots=True)
class CreateContratoAlquilerCommand:
    context: CommandContext
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    observaciones: str | None
    objetos: list[CreateContratoAlquilerObjetoCommand]
    id_reserva_locativa: int | None = None
    dia_vencimiento_canon: int | None = None
