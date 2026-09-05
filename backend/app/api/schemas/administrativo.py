import re
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from app.api.temporal import normalize_aware_datetime_to_utc_naive
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

_EXPLICIT_DATETIME_OFFSET = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


class LoginData(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    session_id: str


class LoginResponse(BaseModel):
    ok: Literal[True] = True
    data: LoginData


class AuthenticatedPrincipalData(BaseModel):
    id_usuario: int
    codigo_usuario: str
    login: str
    id_sesion: UUID
    mecanismo_autenticacion: Literal["SESION_SERVIDOR"]
    autenticado_en: datetime
    id_instalacion_origen_sesion: int
    id_sucursal_operativa: int | None


class AuthenticatedPrincipalResponse(BaseModel):
    ok: Literal[True] = True
    data: AuthenticatedPrincipalData


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


class CatalogoMaestroData(BaseModel):
    id_catalogo_maestro: int
    codigo_catalogo_maestro: str
    nombre_catalogo_maestro: str
    descripcion: str | None


class CatalogoMaestroCreateRequest(BaseModel):
    codigo_catalogo_maestro: str
    nombre_catalogo_maestro: str
    descripcion: str | None = None

    @field_validator("codigo_catalogo_maestro", "nombre_catalogo_maestro")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo no puede estar vacío.")
        return normalized


class CatalogoMaestroUpdateRequest(CatalogoMaestroCreateRequest):
    pass


class CatalogoMaestroWriteData(CatalogoMaestroData):
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CatalogoMaestroCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: CatalogoMaestroWriteData


class CatalogoMaestroUpdateResponse(CatalogoMaestroCreateResponse):
    pass


class CatalogoMaestroBajaResponse(CatalogoMaestroCreateResponse):
    pass


class CatalogoMaestroListData(BaseModel):
    items: list[CatalogoMaestroData]
    total: int
    page: int
    page_size: int


class CatalogoMaestroListResponse(BaseModel):
    ok: Literal[True] = True
    data: CatalogoMaestroListData


class CatalogoMaestroDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: CatalogoMaestroData


class ItemCatalogoData(BaseModel):
    id_item_catalogo: int
    id_catalogo_maestro: int
    codigo_item_catalogo: str
    nombre_item_catalogo: str
    descripcion: str | None
    estado_item_catalogo: str | None


class ItemCatalogoCreateRequest(BaseModel):
    codigo_item_catalogo: str = Field(max_length=50)
    nombre_item_catalogo: str = Field(max_length=150)
    descripcion: str | None = None

    @field_validator("codigo_item_catalogo", "nombre_item_catalogo")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío.")
        return value


class ItemCatalogoUpdateRequest(ItemCatalogoCreateRequest):
    pass


class ItemCatalogoEstadoRequest(BaseModel):
    estado_item_catalogo: Literal["ACTIVO", "INACTIVO"]


class ItemCatalogoWriteData(ItemCatalogoData):
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ItemCatalogoCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: ItemCatalogoWriteData


class ItemCatalogoUpdateResponse(ItemCatalogoCreateResponse):
    pass


class ItemCatalogoEstadoResponse(ItemCatalogoCreateResponse):
    pass


class ItemCatalogoBajaResponse(ItemCatalogoCreateResponse):
    pass


class ItemCatalogoListData(BaseModel):
    items: list[ItemCatalogoData]
    total: int
    page: int
    page_size: int


class ItemCatalogoListResponse(BaseModel):
    ok: Literal[True] = True
    data: ItemCatalogoListData


class ParametroSistemaTipoData(BaseModel):
    id_tipo_dato_parametro: int
    codigo_tipo_dato: str
    nombre_tipo_dato: str


class ParametroSistemaAlcanceData(BaseModel):
    id_alcance_parametro: int
    codigo_alcance: str
    nombre_alcance: str


class ParametroSistemaData(BaseModel):
    id_parametro_sistema: int
    codigo_parametro: str
    nombre_parametro: str
    descripcion: str | None
    tipo: ParametroSistemaTipoData
    alcance: ParametroSistemaAlcanceData


class ParametroSistemaListData(BaseModel):
    items: list[ParametroSistemaData]
    total: int


class ParametroSistemaListResponse(BaseModel):
    ok: Literal[True] = True
    data: ParametroSistemaListData


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

    @field_validator("fecha_desde", "fecha_hasta", mode="before")
    @classmethod
    def _require_text_with_explicit_offset(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str) or not _EXPLICIT_DATETIME_OFFSET.search(value):
            raise ValueError(
                "El datetime debe ser ISO-8601 textual con offset explícito."
            )
        return value

    @field_validator("fecha_desde", "fecha_hasta")
    @classmethod
    def _normalize_utc_boundary(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_aware_datetime_to_utc_naive(value)

    @model_validator(mode="after")
    def _validate_date_range(self) -> "UsuarioSucursalCreateRequest":
        if self.fecha_hasta is not None and self.fecha_hasta < self.fecha_desde:
            raise ValueError("fecha_hasta no puede ser menor que fecha_desde.")
        return self

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


class ParametroGlobalTipoData(BaseModel):
    id_tipo_dato_parametro: int
    codigo_tipo_dato: str
    nombre_tipo_dato: str
    descripcion_tipo_dato: str | None


class ParametroGlobalAlcanceData(BaseModel):
    id_alcance_parametro: int
    codigo_alcance: str
    nombre_alcance: str
    descripcion_alcance: str | None


class ParametroGlobalDefinicionData(BaseModel):
    id_parametro_sistema: int
    codigo_parametro: str
    nombre_parametro: str
    descripcion: str | None
    tipo: ParametroGlobalTipoData
    alcance: ParametroGlobalAlcanceData


class ParametroGlobalValorData(BaseModel):
    id_valor_parametro: int
    uid_global: str
    valor_raw: str
    valor_tipado: int
    version_registro: int
    es_valor_vigente: Literal[True]
    fecha_desde: datetime | None
    fecha_hasta: datetime | None
    created_at: datetime
    updated_at: datetime


class ParametroGlobalValorResponseData(BaseModel):
    definicion: ParametroGlobalDefinicionData
    estado_valor: Literal["SIN_VALOR", "CON_VALOR_MARCADO_VIGENTE"]
    valor_marcado_vigente: ParametroGlobalValorData | None


class ParametroGlobalValorResponse(BaseModel):
    ok: Literal[True] = True
    data: ParametroGlobalValorResponseData


class CalendarioComercialCompletoData(BaseModel):
    estado: Literal["COMPLETA"] = "COMPLETA"
    dia_cierre_comercial: int
    dia_vencimiento_predeterminado_cuotas: int
    version_agregada: int
    fecha_desde: datetime
    fecha_hasta: datetime | None


class CalendarioComercialIncompletoData(BaseModel):
    estado: Literal["INCOMPLETA"] = "INCOMPLETA"


class CalendarioComercialResponse(BaseModel):
    ok: Literal[True] = True
    data: CalendarioComercialCompletoData | CalendarioComercialIncompletoData


class BootstrapCalendarioComercialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dia_cierre_comercial: StrictInt = Field(ge=1, le=31)
    dia_vencimiento_predeterminado_cuotas: StrictInt = Field(ge=1, le=31)
    vigente_desde: date

    @field_validator("vigente_desde", mode="before")
    @classmethod
    def _vigente_desde_fecha_ascii_estricta(cls, value: object) -> date:
        if not isinstance(value, str) or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
        ) is None:
            raise ValueError("vigente_desde debe usar el formato YYYY-MM-DD")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                "vigente_desde debe representar una fecha válida"
            ) from exc


class BootstrapCalendarioComercialData(CalendarioComercialCompletoData):
    uid_global: UUID


class BootstrapCalendarioComercialResponse(BaseModel):
    ok: Literal[True] = True
    data: BootstrapCalendarioComercialData


class ProgramarCalendarioComercialRequest(BootstrapCalendarioComercialRequest):
    """La programación reutiliza el contrato estricto de días y fecha."""


class ProgramarCalendarioComercialResponse(BootstrapCalendarioComercialResponse):
    pass


class ActualizarValorParametroGlobalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valor_tipado: StrictInt


class ValorParametroGlobalActualizadoData(BaseModel):
    codigo_parametro: str
    uid_global: UUID
    valor_tipado: int
    version_registro: int
    updated_at: datetime


class ActualizarValorParametroGlobalResponse(BaseModel):
    ok: Literal[True] = True
    data: ValorParametroGlobalActualizadoData
