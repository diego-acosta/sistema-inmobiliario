from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateUnidadFuncionalServicioCommand:
    context: CommandContext
    id_unidad_funcional: int
    id_servicio: int
    estado: str | None
