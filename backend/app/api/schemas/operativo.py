from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ESTADOS_SUCURSAL_VALIDOS = {"ACTIVA", "INACTIVA", "DADA_DE_BAJA"}
ESTADOS_INSTALACION_VALIDOS = {"ACTIVA", "INACTIVA", "DADA_DE_BAJA"}


class SucursalCreateRequest(BaseModel):
    codigo_sucursal: str
    nombre_sucursal: str
    descripcion_sucursal: str | None = None
    estado_sucursal: str = "ACTIVA"
    es_casa_central: bool = False
    permite_operacion: bool = True
    observaciones: str | None = None

    @field_validator("codigo_sucursal", "nombre_sucursal", "estado_sucursal")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo no puede estar vacío.")
        return normalized

    @field_validator("estado_sucursal")
    @classmethod
    def _valid_estado(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("El campo no puede estar vacío.")
        if normalized not in ESTADOS_SUCURSAL_VALIDOS:
            raise ValueError(
                "estado_sucursal debe ser ACTIVA, INACTIVA o DADA_DE_BAJA."
            )
        return normalized


class InstalacionCreateRequest(BaseModel):
    id_sucursal: int
    codigo_instalacion: str
    nombre_instalacion: str
    descripcion_instalacion: str | None = None
    estado_instalacion: str = "ACTIVA"
    es_principal: bool = False
    permite_sincronizacion: bool = True
    identificador_tecnico: str | None = None
    direccion_local: str | None = None
    observaciones: str | None = None

    @field_validator("codigo_instalacion", "nombre_instalacion", "estado_instalacion")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo no puede estar vacío.")
        return normalized

    @field_validator("estado_instalacion")
    @classmethod
    def _valid_estado(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("El campo no puede estar vacío.")
        if normalized not in ESTADOS_INSTALACION_VALIDOS:
            raise ValueError(
                "estado_instalacion debe ser ACTIVA, INACTIVA o DADA_DE_BAJA."
            )
        return normalized


class SucursalData(BaseModel):
    id_sucursal: int
    uid_global: str
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
    descripcion_sucursal: str | None
    estado_sucursal: str
    es_casa_central: bool
    permite_operacion: bool
    fecha_alta: datetime
    fecha_baja: datetime | None
    observaciones: str | None


class InstalacionData(BaseModel):
    id_instalacion: int
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: str | None
    op_id_ultima_modificacion: str | None
    id_sucursal: int
    codigo_instalacion: str
    nombre_instalacion: str
    descripcion_instalacion: str | None
    estado_instalacion: str
    es_principal: bool
    permite_sincronizacion: bool
    identificador_tecnico: str | None
    direccion_local: str | None
    fecha_alta: datetime
    fecha_baja: datetime | None
    observaciones: str | None


class SucursalCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: SucursalData


class SucursalListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[SucursalData]


class SucursalDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: SucursalData


class InstalacionCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: InstalacionData


class InstalacionListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[InstalacionData]


class InstalacionDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: InstalacionData


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)


TIPOS_VALOR_CONFIGURACION_LOCAL_VALIDOS = {
    "TEXTO",
    "NUMERO",
    "DECIMAL",
    "BOOLEANO",
    "FECHA",
    "JSON",
}
ESTADOS_CONFIGURACION_LOCAL_VALIDOS = {"ACTIVA", "INACTIVA"}


class ConfiguracionLocalRequest(BaseModel):
    id_sucursal: int
    id_instalacion: int
    clave_configuracion: str
    valor_configuracion: str | None = None
    tipo_valor: str = "TEXTO"
    descripcion: str | None = None
    estado_configuracion: str = "ACTIVA"

    @field_validator("clave_configuracion", "tipo_valor", "estado_configuracion")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo no puede estar vacío.")
        return normalized

    @field_validator("clave_configuracion")
    @classmethod
    def _valid_clave(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in {
            "modo_operacion_local",
            "permite_operar_offline",
            "requiere_jornada_abierta",
            "requiere_caja_abierta",
            "observaciones_locales",
        }:
            raise ValueError(
                "clave_configuracion no pertenece al catálogo mínimo local."
            )
        return normalized

    @field_validator("tipo_valor")
    @classmethod
    def _valid_tipo(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in TIPOS_VALOR_CONFIGURACION_LOCAL_VALIDOS:
            raise ValueError("tipo_valor inválido.")
        return normalized

    @field_validator("estado_configuracion")
    @classmethod
    def _valid_estado_configuracion(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ESTADOS_CONFIGURACION_LOCAL_VALIDOS:
            raise ValueError("estado_configuracion debe ser ACTIVA o INACTIVA.")
        return normalized


class ConfiguracionLocalData(BaseModel):
    id_configuracion_local: int
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: str | None
    op_id_ultima_modificacion: str | None
    id_sucursal: int
    id_instalacion: int
    clave_configuracion: str
    valor_configuracion: str | None
    tipo_valor: str
    descripcion: str | None
    estado_configuracion: str


class ConfiguracionLocalResponse(BaseModel):
    ok: Literal[True] = True
    data: ConfiguracionLocalData


class ConfiguracionLocalListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[ConfiguracionLocalData]


ESTADOS_CAJA_VALIDOS = {"ACTIVA", "INACTIVA", "DADA_DE_BAJA"}
TIPOS_CAJA_VALIDOS = {"GENERAL", "EFECTIVO", "TESORERIA", "ADMINISTRATIVA"}
MONEDAS_CAJA_VALIDAS = {"ARS", "USD"}


class CajaOperativaCreateRequest(BaseModel):
    id_sucursal: int
    id_instalacion: int
    codigo_caja: str
    nombre_caja: str
    tipo_caja: str = "GENERAL"
    moneda_base: str = "ARS"
    estado_caja: str = "ACTIVA"
    permite_efectivo: bool = True
    permite_transferencia: bool = False
    permite_cheque: bool = False
    descripcion: str | None = None
    observaciones: str | None = None

    @field_validator(
        "codigo_caja", "nombre_caja", "tipo_caja", "moneda_base", "estado_caja"
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo no puede estar vacío.")
        return normalized

    @field_validator("tipo_caja")
    @classmethod
    def _valid_tipo_caja(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in TIPOS_CAJA_VALIDOS:
            raise ValueError("tipo_caja inválido.")
        return normalized

    @field_validator("moneda_base")
    @classmethod
    def _valid_moneda_base(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in MONEDAS_CAJA_VALIDAS:
            raise ValueError("moneda_base inválida.")
        return normalized

    @field_validator("estado_caja")
    @classmethod
    def _valid_estado_caja(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ESTADOS_CAJA_VALIDOS:
            raise ValueError("estado_caja debe ser ACTIVA, INACTIVA o DADA_DE_BAJA.")
        return normalized


class CajaOperativaData(BaseModel):
    id_caja: int
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: str | None
    op_id_ultima_modificacion: str | None
    id_sucursal: int
    id_instalacion: int
    codigo_caja: str
    nombre_caja: str
    tipo_caja: str
    moneda_base: str
    estado_caja: str
    permite_efectivo: bool
    permite_transferencia: bool
    permite_cheque: bool
    descripcion: str | None
    observaciones: str | None


class CajaOperativaCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: CajaOperativaData


class CajaOperativaListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[CajaOperativaData]


class CajaOperativaDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: CajaOperativaData
