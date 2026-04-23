from typing import Any, Literal

from pydantic import BaseModel, Field


class DesarrolloCreateRequest(BaseModel):
    codigo_desarrollo: str
    nombre_desarrollo: str
    descripcion: str | None = None
    estado_desarrollo: str
    observaciones: str | None = None


class DesarrolloCreateData(BaseModel):
    id_desarrollo: int
    uid_global: str
    version_registro: int
    estado_desarrollo: str


class DesarrolloCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: DesarrolloCreateData


class DesarrolloDetailData(BaseModel):
    id_desarrollo: int
    codigo_desarrollo: str
    nombre_desarrollo: str
    descripcion: str | None
    estado_desarrollo: str
    observaciones: str | None


class DesarrolloDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: DesarrolloDetailData


class DesarrolloListItem(BaseModel):
    id_desarrollo: int
    codigo_desarrollo: str
    nombre_desarrollo: str
    descripcion: str | None
    estado_desarrollo: str
    observaciones: str | None


class DesarrolloListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[DesarrolloListItem]


class DesarrolloUpdateRequest(BaseModel):
    codigo_desarrollo: str
    nombre_desarrollo: str
    descripcion: str | None = None
    estado_desarrollo: str
    observaciones: str | None = None


class DesarrolloUpdateData(BaseModel):
    id_desarrollo: int
    version_registro: int
    codigo_desarrollo: str
    nombre_desarrollo: str
    descripcion: str | None
    estado_desarrollo: str
    observaciones: str | None


class DesarrolloUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: DesarrolloUpdateData


class DesarrolloBajaData(BaseModel):
    id_desarrollo: int
    version_registro: int
    deleted: Literal[True] = True


class DesarrolloBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: DesarrolloBajaData


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)
