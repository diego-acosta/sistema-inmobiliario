from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class GenerarMoraFinancieraCommand:
    context: CommandContext
    fecha_proceso: date | None = None
