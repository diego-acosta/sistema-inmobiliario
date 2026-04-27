from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class RegistrarEntregaLocativaCommand:
    context: CommandContext
    id_contrato_alquiler: int
    fecha_entrega: date
    observaciones: str | None
