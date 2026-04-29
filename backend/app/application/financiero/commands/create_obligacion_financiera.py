from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class ComposicionInput:
    codigo_concepto_financiero: str
    importe_componente: float


@dataclass(slots=True)
class CreateObligacionFinancieraCommand:
    context: CommandContext
    id_relacion_generadora: int
    fecha_vencimiento: date
    composiciones: list[ComposicionInput]
