from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ServicioCreateRequest(BaseModel):
    codigo_servicio: str
    nombre_servicio: str
    descripcion: str | None = None
    estado_servicio: str


class ServicioCreateData(BaseModel):
    id_servicio: int
    uid_global: str
    version_registro: int
    codigo_servicio: str
    nombre_servicio: str
    estado_servicio: str


class ServicioCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: ServicioCreateData


class ServicioDetailData(BaseModel):
    id_servicio: int
    codigo_servicio: str
    nombre_servicio: str
    descripcion: str | None
    estado_servicio: str


class ServicioDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: ServicioDetailData


class ServicioListItem(BaseModel):
    id_servicio: int
    codigo_servicio: str
    nombre_servicio: str
    descripcion: str | None
    estado_servicio: str


class ServicioListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[ServicioListItem]


class ServicioInmuebleListItem(BaseModel):
    id_inmueble_servicio: int
    id_inmueble: int
    id_servicio: int
    estado: str | None
    fecha_alta: str | None


class ServicioInmuebleListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[ServicioInmuebleListItem]


class ServicioUnidadFuncionalListItem(BaseModel):
    id_unidad_funcional_servicio: int
    id_unidad_funcional: int
    id_servicio: int
    estado: str | None
    fecha_alta: str | None


class ServicioUnidadFuncionalListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[ServicioUnidadFuncionalListItem]


class ServicioUpdateRequest(BaseModel):
    codigo_servicio: str
    nombre_servicio: str
    descripcion: str | None = None
    estado_servicio: str


class ServicioUpdateData(BaseModel):
    id_servicio: int
    version_registro: int
    codigo_servicio: str
    nombre_servicio: str
    descripcion: str | None
    estado_servicio: str


class ServicioUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: ServicioUpdateData


class ServicioBajaData(BaseModel):
    id_servicio: int
    version_registro: int
    deleted: Literal[True] = True


class ServicioBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: ServicioBajaData


class FacturaServicioCreateRequest(BaseModel):
    id_servicio: int
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    proveedor: str
    numero_factura: str
    fecha_emision: date
    fecha_vencimiento: date | None = None
    periodo_desde: date | None = None
    periodo_hasta: date | None = None
    importe_total: Decimal = Field(ge=0)
    observaciones: str | None = None

    @model_validator(mode="after")
    def validar_factura_servicio(self) -> "FacturaServicioCreateRequest":
        if (self.id_inmueble is not None) == (self.id_unidad_funcional is not None):
            raise ValueError("Debe informar id_inmueble o id_unidad_funcional, no ambos.")
        if not self.proveedor.strip():
            raise ValueError("proveedor es obligatorio.")
        if not self.numero_factura.strip():
            raise ValueError("numero_factura es obligatorio.")
        if (
            self.fecha_vencimiento is not None
            and self.fecha_vencimiento < self.fecha_emision
        ):
            raise ValueError("fecha_vencimiento debe ser mayor o igual a fecha_emision.")
        if (
            self.periodo_desde is not None
            and self.periodo_hasta is not None
            and self.periodo_hasta < self.periodo_desde
        ):
            raise ValueError("periodo_hasta debe ser mayor o igual a periodo_desde.")
        return self


class FacturaServicioData(BaseModel):
    id_factura_servicio: int
    uid_global: str
    version_registro: int
    id_servicio: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    proveedor: str
    numero_factura: str
    fecha_emision: str
    fecha_vencimiento: str | None
    periodo_desde: str | None
    periodo_hasta: str | None
    importe_total: float
    estado_factura_servicio: str
    observaciones: str | None


class FacturaServicioCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: FacturaServicioData


class FacturaServicioDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: FacturaServicioData


class FacturaServicioListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[FacturaServicioData]


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)
