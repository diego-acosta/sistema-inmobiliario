from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class UsuarioSistemaCreateRequest(BaseModel):
    codigo_usuario: str
    login: str
    email: str | None = None
    estado_usuario: str = "ACTIVO"
    usuario_sistema_interno: bool = False
    observaciones: str | None = None

    @field_validator("codigo_usuario", "login", "estado_usuario")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo no puede estar vacío.")
        return normalized

    @field_validator("estado_usuario")
    @classmethod
    def _valid_estado(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"ACTIVO", "INACTIVO"}:
            raise ValueError("estado_usuario debe ser ACTIVO o INACTIVO.")
        return normalized


class UsuarioSistemaData(BaseModel):
    id_usuario: int
    codigo_usuario: str
    login: str
    email: str | None
    estado_usuario: str
    fecha_alta: datetime
    fecha_baja: datetime | None
    fecha_ultimo_acceso: datetime | None
    usuario_sistema_interno: bool
    observaciones: str | None
    version_registro: int


class UsuarioSistemaCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: UsuarioSistemaData


class UsuarioSistemaDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: UsuarioSistemaData


class UsuarioSistemaListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[UsuarioSistemaData]


class UsuarioSistemaBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: UsuarioSistemaData


class RolSeguridadData(BaseModel):
    id_rol_seguridad: int
    codigo_rol: str
    nombre_rol: str
    descripcion: str | None
    estado_rol: str


class PermisoData(BaseModel):
    id_permiso: int
    codigo_permiso: str
    nombre_permiso: str
    descripcion: str | None
    estado_permiso: str


class RolSeguridadListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[RolSeguridadData]


class RolSeguridadDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: RolSeguridadData


class PermisoListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[PermisoData]


class RolSeguridadPermisosResponse(BaseModel):
    ok: Literal[True] = True
    data: list[PermisoData]


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)
