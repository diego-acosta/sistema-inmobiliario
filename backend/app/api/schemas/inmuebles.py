from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class InmuebleCreateRequest(BaseModel):
    id_desarrollo: int | None = None
    codigo_inmueble: str
    nombre_inmueble: str | None = None
    superficie: Decimal | None = None
    estado_administrativo: str
    estado_juridico: str
    observaciones: str | None = None


class InmuebleCreateData(BaseModel):
    id_inmueble: int
    uid_global: str
    version_registro: int
    codigo_inmueble: str
    estado_administrativo: str
    estado_juridico: str


class InmuebleCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: InmuebleCreateData


class InmuebleDetailData(BaseModel):
    id_inmueble: int
    id_desarrollo: int | None
    codigo_inmueble: str
    nombre_inmueble: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_juridico: str
    observaciones: str | None


class InmuebleDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: InmuebleDetailData


class InmuebleListItem(BaseModel):
    id_inmueble: int
    id_desarrollo: int | None
    codigo_inmueble: str
    nombre_inmueble: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_juridico: str
    observaciones: str | None


class InmuebleListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[InmuebleListItem]


class InmuebleUpdateRequest(BaseModel):
    id_desarrollo: int | None = None
    codigo_inmueble: str
    nombre_inmueble: str | None = None
    superficie: Decimal | None = None
    estado_administrativo: str
    estado_juridico: str
    observaciones: str | None = None


class InmuebleUpdateData(BaseModel):
    id_inmueble: int
    version_registro: int
    id_desarrollo: int | None
    codigo_inmueble: str
    nombre_inmueble: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_juridico: str
    observaciones: str | None


class InmuebleUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: InmuebleUpdateData


class InmuebleBajaData(BaseModel):
    id_inmueble: int
    version_registro: int
    deleted: Literal[True] = True


class InmuebleBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: InmuebleBajaData


class InmuebleAsociarDesarrolloRequest(BaseModel):
    id_desarrollo: int


class InmuebleAsociarDesarrolloData(BaseModel):
    id_inmueble: int
    id_desarrollo: int
    version_registro: int


class InmuebleAsociarDesarrolloResponse(BaseModel):
    ok: Literal[True] = True
    data: InmuebleAsociarDesarrolloData


class InmuebleDesasociarDesarrolloData(BaseModel):
    id_inmueble: int
    id_desarrollo: None = None
    version_registro: int


class InmuebleDesasociarDesarrolloResponse(BaseModel):
    ok: Literal[True] = True
    data: InmuebleDesasociarDesarrolloData


class UnidadFuncionalCreateRequest(BaseModel):
    codigo_unidad: str
    nombre_unidad: str | None = None
    superficie: Decimal | None = None
    estado_administrativo: str
    estado_operativo: str
    observaciones: str | None = None


class UnidadFuncionalCreateData(BaseModel):
    id_unidad_funcional: int
    id_inmueble: int
    uid_global: str
    version_registro: int
    codigo_unidad: str
    estado_administrativo: str
    estado_operativo: str


class UnidadFuncionalCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: UnidadFuncionalCreateData


class UnidadFuncionalListItem(BaseModel):
    id_unidad_funcional: int
    id_inmueble: int
    codigo_unidad: str
    nombre_unidad: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_operativo: str
    observaciones: str | None


class UnidadFuncionalListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[UnidadFuncionalListItem]


class UnidadFuncionalDetailData(BaseModel):
    id_unidad_funcional: int
    id_inmueble: int | None
    codigo_unidad: str
    nombre_unidad: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_operativo: str
    observaciones: str | None


class UnidadFuncionalDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: UnidadFuncionalDetailData


class UnidadFuncionalUpdateRequest(BaseModel):
    codigo_unidad: str
    nombre_unidad: str | None = None
    superficie: Decimal | None = None
    estado_administrativo: str
    estado_operativo: str
    observaciones: str | None = None


class UnidadFuncionalUpdateData(BaseModel):
    id_unidad_funcional: int
    id_inmueble: int | None
    version_registro: int
    codigo_unidad: str
    nombre_unidad: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_operativo: str
    observaciones: str | None


class UnidadFuncionalUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: UnidadFuncionalUpdateData


class UnidadFuncionalBajaData(BaseModel):
    id_unidad_funcional: int
    version_registro: int
    deleted: Literal[True] = True


class UnidadFuncionalBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: UnidadFuncionalBajaData


class DisponibilidadCreateRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime | None = None
    motivo: str | None = None
    observaciones: str | None = None


class DisponibilidadCreateData(BaseModel):
    id_disponibilidad: int
    uid_global: str
    version_registro: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    motivo: str | None
    observaciones: str | None


class DisponibilidadCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: DisponibilidadCreateData


class DisponibilidadReemplazarVigenteRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    estado_disponibilidad: str
    fecha_desde: datetime
    motivo: str | None = None
    observaciones: str | None = None


class DisponibilidadUpdateRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime | None = None
    motivo: str | None = None
    observaciones: str | None = None


class DisponibilidadUpdateData(BaseModel):
    id_disponibilidad: int
    version_registro: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    motivo: str | None
    observaciones: str | None


class DisponibilidadUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: DisponibilidadUpdateData


class DisponibilidadCerrarRequest(BaseModel):
    fecha_hasta: datetime


class DisponibilidadCerrarData(BaseModel):
    id_disponibilidad: int
    version_registro: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime
    motivo: str | None
    observaciones: str | None


class DisponibilidadCerrarResponse(BaseModel):
    ok: Literal[True] = True
    data: DisponibilidadCerrarData


class DisponibilidadBajaData(BaseModel):
    id_disponibilidad: int
    version_registro: int
    deleted: Literal[True] = True


class DisponibilidadBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: DisponibilidadBajaData


class DisponibilidadListItem(BaseModel):
    id_disponibilidad: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    motivo: str | None
    observaciones: str | None


class DisponibilidadListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[DisponibilidadListItem]


class OcupacionCreateRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    tipo_ocupacion: str
    fecha_desde: datetime
    fecha_hasta: datetime | None = None
    descripcion: str | None = None
    observaciones: str | None = None


class OcupacionCreateData(BaseModel):
    id_ocupacion: int
    uid_global: str
    version_registro: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    tipo_ocupacion: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    descripcion: str | None
    observaciones: str | None


class OcupacionCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: OcupacionCreateData


class OcupacionReemplazarVigenteRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    tipo_ocupacion: str
    fecha_desde: datetime
    descripcion: str | None = None
    observaciones: str | None = None


class OcupacionUpdateRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    tipo_ocupacion: str
    fecha_desde: datetime
    fecha_hasta: datetime | None = None
    descripcion: str | None = None
    observaciones: str | None = None


class OcupacionUpdateData(BaseModel):
    id_ocupacion: int
    version_registro: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    tipo_ocupacion: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    descripcion: str | None
    observaciones: str | None


class OcupacionUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: OcupacionUpdateData


class OcupacionCerrarRequest(BaseModel):
    fecha_hasta: datetime


class OcupacionCerrarData(BaseModel):
    id_ocupacion: int
    version_registro: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    tipo_ocupacion: str
    fecha_desde: datetime
    fecha_hasta: datetime
    descripcion: str | None
    observaciones: str | None


class OcupacionCerrarResponse(BaseModel):
    ok: Literal[True] = True
    data: OcupacionCerrarData


class OcupacionBajaData(BaseModel):
    id_ocupacion: int
    version_registro: int
    deleted: Literal[True] = True


class OcupacionBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: OcupacionBajaData


class OcupacionListItem(BaseModel):
    id_ocupacion: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    tipo_ocupacion: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    descripcion: str | None
    observaciones: str | None


class OcupacionListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[OcupacionListItem]


class InmuebleServicioCreateRequest(BaseModel):
    id_servicio: int
    estado: str | None = None


class InmuebleServicioCreateData(BaseModel):
    id_inmueble_servicio: int
    id_inmueble: int
    id_servicio: int
    uid_global: str
    version_registro: int
    estado: str | None


class InmuebleServicioCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: InmuebleServicioCreateData


class InmuebleServicioListItem(BaseModel):
    id_inmueble_servicio: int
    id_inmueble: int
    id_servicio: int
    estado: str | None
    fecha_alta: str | None


class InmuebleServicioListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[InmuebleServicioListItem]


class UnidadFuncionalServicioCreateRequest(BaseModel):
    id_servicio: int
    estado: str | None = None


class UnidadFuncionalServicioCreateData(BaseModel):
    id_unidad_funcional_servicio: int
    id_unidad_funcional: int
    id_servicio: int
    uid_global: str
    version_registro: int
    estado: str | None


class UnidadFuncionalServicioCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: UnidadFuncionalServicioCreateData


class UnidadFuncionalServicioListItem(BaseModel):
    id_unidad_funcional_servicio: int
    id_unidad_funcional: int
    id_servicio: int
    estado: str | None
    fecha_alta: str | None


class UnidadFuncionalServicioListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[UnidadFuncionalServicioListItem]


class ActivoIntegracionEfectoOperativoData(BaseModel):
    disponibilidad: str | None
    ocupacion: str | None


class ActivoIntegracionEventoItem(BaseModel):
    id_evento_outbox: int
    nombre_evento: str
    estado: str
    ocurrido_en: datetime
    publicado_en: datetime | None
    efecto_operativo_aplicado: ActivoIntegracionEfectoOperativoData


class ActivoIntegracionVentaItem(BaseModel):
    id_venta: int
    id_reserva_venta: int | None
    codigo_venta: str
    fecha_venta: datetime
    estado_venta: str
    eventos: list[ActivoIntegracionEventoItem]


class ActivoIntegracionTraceResponse(BaseModel):
    ok: Literal[True] = True
    data: list[ActivoIntegracionVentaItem]


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)
