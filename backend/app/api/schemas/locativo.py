from __future__ import annotations

from datetime import date
from decimal import Decimal
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


class ContratoAlquilerParticipacionRequest(BaseModel):
    id_persona: int
    id_rol_participacion: int
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    observaciones: str | None = None


class ContratoAlquilerCreateRequest(BaseModel):
    codigo_contrato: str
    fecha_contrato: date | None = None
    fecha_inicio: date
    fecha_fin: date | None = None
    canon_inicial: Decimal | None = None
    moneda: str | None = None
    observaciones: str | None = None
    objetos: list[ContratoAlquilerObjetoRequest]
    participaciones: list[ContratoAlquilerParticipacionRequest]


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
    canon_inicial: Decimal | None
    moneda: str | None
    observaciones: str | None
    objetos: list[ContratoAlquilerObjetoData]


class ContratoAlquilerCreateResponse(BaseModel):
    data: ContratoAlquilerCreateData


class ContratoAlquilerParticipacionData(BaseModel):
    id_relacion_persona_rol: int
    id_persona: int
    id_rol_participacion: int
    fecha_desde: date
    fecha_hasta: date | None
    observaciones: str | None


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
    participaciones: list[ContratoAlquilerParticipacionData]


class ContratoAlquilerGetResponse(BaseModel):
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


class ContratoAlquilerActivateResponse(BaseModel):
    data: ContratoAlquilerActivateData


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
    data: ContratoAlquilerListData


class ErrorResponse(BaseModel):
    error_code: str
    error_message: str
    details: dict[str, Any] | None = None
