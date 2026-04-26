from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, model_validator


class ContratoAlquilerObjetoRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    observaciones: str | None = None

    @model_validator(mode="after")
    def exactly_one_parent(self) -> ContratoAlquilerObjetoRequest:
        if (self.id_inmueble is None) == (self.id_unidad_funcional is None):
            raise ValueError(
                "Debe indicarse exactamente uno entre id_inmueble e id_unidad_funcional."
            )
        return self


class ContratoAlquilerCreateRequest(BaseModel):
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None = None
    observaciones: str | None = None
    objetos: list[ContratoAlquilerObjetoRequest]


class ContratoAlquilerObjetoData(BaseModel):
    id_contrato_objeto: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


class ContratoAlquilerCreateData(BaseModel):
    id_contrato_alquiler: int
    uid_global: str
    version_registro: int
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    estado_contrato: str
    observaciones: str | None
    objetos: list[ContratoAlquilerObjetoData]
    condiciones_economicas_alquiler: list[Any] = []


class ContratoAlquilerCreateResponse(BaseModel):
    ok: bool = True
    data: ContratoAlquilerCreateData


class ContratoAlquilerGetData(BaseModel):
    id_contrato_alquiler: int
    uid_global: str
    version_registro: int
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    estado_contrato: str
    observaciones: str | None
    objetos: list[ContratoAlquilerObjetoData]
    condiciones_economicas_alquiler: list[Any] = []
    deleted_at: datetime | None


class ContratoAlquilerGetResponse(BaseModel):
    ok: bool = True
    data: ContratoAlquilerGetData


class ContratoAlquilerActivateData(BaseModel):
    id_contrato_alquiler: int
    uid_global: str
    version_registro: int
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    estado_contrato: str
    observaciones: str | None
    objetos: list[ContratoAlquilerObjetoData]
    condiciones_economicas_alquiler: list[Any] = []


class ContratoAlquilerActivateResponse(BaseModel):
    ok: bool = True
    data: ContratoAlquilerActivateData


class ContratoAlquilerFinalizeData(BaseModel):
    id_contrato_alquiler: int
    uid_global: str
    version_registro: int
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    estado_contrato: str
    observaciones: str | None
    objetos: list[ContratoAlquilerObjetoData]
    condiciones_economicas_alquiler: list[Any] = []


class ContratoAlquilerFinalizeResponse(BaseModel):
    ok: bool = True
    data: ContratoAlquilerFinalizeData


class ContratoAlquilerCancelData(BaseModel):
    id_contrato_alquiler: int
    uid_global: str
    version_registro: int
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    estado_contrato: str
    observaciones: str | None
    objetos: list[ContratoAlquilerObjetoData]
    condiciones_economicas_alquiler: list[Any] = []


class ContratoAlquilerCancelResponse(BaseModel):
    ok: bool = True
    data: ContratoAlquilerCancelData


class ContratoAlquilerBajaData(BaseModel):
    id_contrato_alquiler: int
    uid_global: str
    version_registro: int
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    estado_contrato: str
    observaciones: str | None
    objetos: list[ContratoAlquilerObjetoData]
    condiciones_economicas_alquiler: list[Any] = []
    deleted_at: datetime


class ContratoAlquilerBajaResponse(BaseModel):
    ok: bool = True
    data: ContratoAlquilerBajaData


class ContratoAlquilerListItemData(BaseModel):
    id_contrato_alquiler: int
    uid_global: str
    version_registro: int
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    estado_contrato: str
    observaciones: str | None


class ContratoAlquilerListData(BaseModel):
    items: list[ContratoAlquilerListItemData]
    total: int


class ContratoAlquilerListResponse(BaseModel):
    ok: bool = True
    data: ContratoAlquilerListData


class ErrorResponse(BaseModel):
    ok: bool = False
    error_code: str
    error_message: str
    details: dict[str, Any] | None = None
