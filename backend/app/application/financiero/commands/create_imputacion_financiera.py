from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateImputacionFinancieraCommand:
    context: CommandContext
    id_obligacion_financiera: int
    monto: float
