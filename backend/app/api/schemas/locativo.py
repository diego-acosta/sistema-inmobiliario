from __future__ import annotations

from datetime import date, datetime
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


class CondicionEconomicaAlquilerCreateRequest(BaseModel):
    monto_base: Decimal
    periodicidad: str | None = None
    moneda: str | None = None
    fecha_desde: date
    fecha_hasta: date | None = None
    observaciones: str | None = None


class CondicionEconomicaAlquilerCerrarVigenciaRequest(BaseModel):
    fecha_hasta: date


class CondicionEconomicaAlquilerData(BaseModel):
    id_condicion_economica: int
    uid_global: str
    version_registro: int
    id_contrato_alquiler: int
    monto_base: Decimal
    periodicidad: str | None
    moneda: str | None
    fecha_desde: date
    fecha_hasta: date | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CondicionEconomicaAlquilerCreateResponse(BaseModel):
    ok: bool = True
    data: CondicionEconomicaAlquilerData


class CondicionEconomicaAlquilerListData(BaseModel):
    items: list[CondicionEconomicaAlquilerData]
    total: int


class CondicionEconomicaAlquilerListResponse(BaseModel):
    ok: bool = True
    data: CondicionEconomicaAlquilerListData


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
    condiciones_economicas_alquiler: list[CondicionEconomicaAlquilerData] = []
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


class SolicitudAlquilerCreateRequest(BaseModel):
    codigo_solicitud: str
    fecha_solicitud: datetime
    observaciones: str | None = None


class SolicitudAlquilerData(BaseModel):
    id_solicitud_alquiler: int
    uid_global: str
    version_registro: int
    codigo_solicitud: str
    fecha_solicitud: datetime
    estado_solicitud: str
    observaciones: str | None
    deleted_at: datetime | None = None


class SolicitudAlquilerResponse(BaseModel):
    ok: bool = True
    data: SolicitudAlquilerData


class ReservaLocativaObjetoRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    observaciones: str | None = None

    @model_validator(mode="after")
    def exactly_one_parent(self) -> ReservaLocativaObjetoRequest:
        if (self.id_inmueble is None) == (self.id_unidad_funcional is None):
            raise ValueError(
                "Debe indicarse exactamente uno entre id_inmueble e id_unidad_funcional."
            )
        return self


class ReservaLocativaCreateRequest(BaseModel):
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_vencimiento: datetime | None = None
    observaciones: str | None = None
    objetos: list[ReservaLocativaObjetoRequest]


class ReservaLocativaObjetoData(BaseModel):
    id_reserva_locativa_objeto: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


class ReservaLocativaData(BaseModel):
    id_reserva_locativa: int
    uid_global: str
    version_registro: int
    codigo_reserva: str
    fecha_reserva: datetime
    estado_reserva: str
    fecha_vencimiento: datetime | None
    observaciones: str | None
    objetos: list[ReservaLocativaObjetoData]
    deleted_at: datetime | None = None


class ReservaLocativaResponse(BaseModel):
    ok: bool = True
    data: ReservaLocativaData


class EntregaLocativaRequest(BaseModel):
    fecha_entrega: date
    observaciones: str | None = None


class EntregaLocativaData(BaseModel):
    id_entrega_locativa: int
    uid_global: str
    version_registro: int
    id_contrato_alquiler: int
    fecha_entrega: date
    observaciones: str | None
    deleted_at: datetime | None = None


class EntregaLocativaResponse(BaseModel):
    ok: bool = True
    data: EntregaLocativaData


class GenerarContratoDesdeReservaRequest(BaseModel):
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None = None
    observaciones: str | None = None


class ConvertirSolicitudAlquilerRequest(BaseModel):
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_vencimiento: datetime | None = None
    observaciones: str | None = None
    objetos: list[ReservaLocativaObjetoRequest]
    confirmar: bool = False


class ErrorResponse(BaseModel):
    ok: bool = False
    error_code: str
    error_message: str
    details: dict[str, Any] | None = None
