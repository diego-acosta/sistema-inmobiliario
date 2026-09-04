"""Valores CORE-EF sintácticamente validados para un command local."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LocalCommandCoreEFHeaders:
    x_op_id: UUID
    x_sucursal_id: int
    x_instalacion_id: int | None
    if_match_version: int | None
