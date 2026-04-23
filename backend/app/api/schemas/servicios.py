from typing import Any, Literal

from pydantic import BaseModel, Field


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


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)
