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


class UsuarioRolSeguridadCreateRequest(BaseModel):
    id_rol_seguridad: int


class UsuarioRolSeguridadData(BaseModel):
    id_usuario_rol_seguridad: int
    id_usuario: int
    id_rol_seguridad: int
    fecha_desde: datetime
    fecha_hasta: datetime | None
    version_registro: int
    updated_at: datetime
    deleted_at: datetime | None
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: str | None
    op_id_ultima_modificacion: str | None
    codigo_rol: str
    nombre_rol: str
    descripcion: str | None
    estado_rol: str


class UsuarioRolSeguridadListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[UsuarioRolSeguridadData]


class UsuarioRolSeguridadCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: UsuarioRolSeguridadData


class UsuarioRolSeguridadBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: UsuarioRolSeguridadData


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)

class UsuarioSucursalCreateRequest(BaseModel):
    id_sucursal: int
    tipo_habilitacion_sucursal: str | None = None
    es_sucursal_predeterminada: bool = False
    puede_operar: bool = True
    puede_consultar: bool = True
    puede_administrar: bool = False
    fecha_desde: datetime
    fecha_hasta: datetime | None = None
    observaciones: str | None = None

    @field_validator("tipo_habilitacion_sucursal")
    @classmethod
    def _empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class UsuarioSucursalData(BaseModel):
    id_usuario_sucursal: int
    uid_global: str
    id_usuario: int
    id_sucursal: int
    tipo_habilitacion_sucursal: str | None
    es_sucursal_predeterminada: bool
    puede_operar: bool
    puede_consultar: bool
    puede_administrar: bool
    fecha_desde: datetime
    fecha_hasta: datetime | None
    estado_vinculo: str
    observaciones: str | None
    version_registro: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: str | None
    op_id_ultima_modificacion: str | None
    codigo_sucursal: str
    nombre_sucursal: str
    estado_sucursal: str


class UsuarioSucursalCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: UsuarioSucursalData


class UsuarioSucursalListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[UsuarioSucursalData]


class UsuarioAlcanceOperativoData(BaseModel):
    usuario: UsuarioSistemaData
    sucursales_asignadas: list[UsuarioSucursalData]
    sucursal_predeterminada: UsuarioSucursalData | None
    puede_operar: bool
    puede_consultar: bool
    puede_administrar: bool
    estado_vigencia: str


class UsuarioAlcanceOperativoResponse(BaseModel):
    ok: Literal[True] = True
    data: UsuarioAlcanceOperativoData
