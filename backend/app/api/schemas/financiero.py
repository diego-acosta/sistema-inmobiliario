from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class RelacionGeneradoraCreateRequest(BaseModel):
    tipo_origen: str
    id_origen: int
    descripcion: str | None = None

    @field_validator("tipo_origen")
    @classmethod
    def tipo_origen_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tipo_origen no puede estar vacío.")
        return v

    @field_validator("id_origen")
    @classmethod
    def id_origen_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("id_origen debe ser mayor que cero.")
        return v


class RelacionGeneradoraData(BaseModel):
    id_relacion_generadora: int
    uid_global: str
    version_registro: int
    tipo_origen: str
    id_origen: int
    descripcion: str | None
    fecha_alta: datetime


class RelacionGeneradoraResponse(BaseModel):
    ok: bool = True
    data: RelacionGeneradoraData


class RelacionGeneradoraListData(BaseModel):
    items: list[RelacionGeneradoraData]
    total: int


class RelacionGeneradoraListResponse(BaseModel):
    ok: bool = True
    data: RelacionGeneradoraListData


class ErrorResponse(BaseModel):
    ok: bool = False
    error_code: str
    error_message: str
    details: dict[str, Any] | None = None
