from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CerrarVigenciaCondicionEconomicaAlquilerCommand:
    context: CommandContext
    id_contrato_alquiler: int
    id_condicion_economica: int
    if_match_version: int | None
    fecha_hasta: date
