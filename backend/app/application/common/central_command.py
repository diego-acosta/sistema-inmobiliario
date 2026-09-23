"""Metadata mínima de commands centrales, independiente de HTTP."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CentralCommandMetadata:
    op_id: UUID
    expected_version: int | None = None
