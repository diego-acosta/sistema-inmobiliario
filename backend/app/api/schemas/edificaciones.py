from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class EdificacionCreateRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    descripcion: str | None = None
    tipo_edificacion: str | None = None
    superficie: Decimal | None = None
    observaciones: str | None = None


class EdificacionCreateData(BaseModel):
    id_edificacion: int
    uid_global: str
    version_registro: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    tipo_edificacion: str | None


class EdificacionCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: EdificacionCreateData


class EdificacionDetailData(BaseModel):
    id_edificacion: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    descripcion: str | None
    tipo_edificacion: str | None
    superficie: Decimal | None
    observaciones: str | None


class EdificacionDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: EdificacionDetailData


class EdificacionListItem(BaseModel):
    id_edificacion: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    descripcion: str | None
    tipo_edificacion: str | None
    superficie: Decimal | None
    observaciones: str | None


class EdificacionListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[EdificacionListItem]


class EdificacionUpdateRequest(BaseModel):
    descripcion: str | None = None
    tipo_edificacion: str | None = None
    superficie: Decimal | None = None
    observaciones: str | None = None


class EdificacionUpdateData(BaseModel):
    id_edificacion: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    version_registro: int
    descripcion: str | None
    tipo_edificacion: str | None
    superficie: Decimal | None
    observaciones: str | None


class EdificacionUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: EdificacionUpdateData


class EdificacionBajaData(BaseModel):
    id_edificacion: int
    version_registro: int
    deleted: Literal[True] = True


class EdificacionBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: EdificacionBajaData


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)
