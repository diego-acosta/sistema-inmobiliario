from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateContratoAlquilerObjetoCommand:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


@dataclass(slots=True)
class UpdateContratoAlquilerCommand:
    context: CommandContext
    id_contrato_alquiler: int
    if_match_version: int | None
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    observaciones: str | None
    objetos: list[UpdateContratoAlquilerObjetoCommand]
