from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, field_validator


class RelacionGeneradoraCreateRequest(BaseModel):
    tipo_origen: str
    id_origen: int
    descripcion: str | None = None

    @field_validator("tipo_origen")
    @classmethod
    def tipo_origen_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tipo_origen no puede estar vacío.")
        return v

    @field_validator("id_origen")
    @classmethod
    def id_origen_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("id_origen debe ser mayor que cero.")
        return v


class RelacionGeneradoraData(BaseModel):
    id_relacion_generadora: int
    uid_global: str
    version_registro: int
    tipo_origen: str
    id_origen: int
    descripcion: str | None
    estado_relacion_generadora: str
    fecha_alta: datetime


class RelacionGeneradoraResponse(BaseModel):
    ok: bool = True
    data: RelacionGeneradoraData


class RelacionGeneradoraListData(BaseModel):
    items: list[RelacionGeneradoraData]
    total: int


class RelacionGeneradoraListResponse(BaseModel):
    ok: bool = True
    data: RelacionGeneradoraListData


class ErrorResponse(BaseModel):
    ok: bool = False
    error_code: str
    error_message: str
    details: dict[str, Any] | None = None


# ── concepto_financiero ───────────────────────────────────────────────────────

class ConceptoFinancieroData(BaseModel):
    id_concepto_financiero: int
    codigo_concepto_financiero: str
    nombre_concepto_financiero: str
    descripcion_concepto_financiero: str | None
    tipo_concepto_financiero: str
    naturaleza_concepto: str
    estado_concepto_financiero: str


class ConceptoFinancieroListData(BaseModel):
    items: list[ConceptoFinancieroData]
    total: int


class ConceptoFinancieroListResponse(BaseModel):
    ok: bool = True
    data: ConceptoFinancieroListData


# ── obligacion_financiera create ──────────────────────────────────────────────

class ComposicionCreateItem(BaseModel):
    codigo_concepto_financiero: str
    importe_componente: float

    @field_validator("importe_componente")
    @classmethod
    def importe_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("importe_componente debe ser mayor que cero.")
        return v


class ObligacionFinancieraCreateRequest(BaseModel):
    id_relacion_generadora: int
    fecha_vencimiento: date
    composiciones: list[ComposicionCreateItem]

    @field_validator("id_relacion_generadora")
    @classmethod
    def id_rg_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("id_relacion_generadora debe ser mayor que cero.")
        return v

    @field_validator("composiciones")
    @classmethod
    def composiciones_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("Debe incluir al menos una composición.")
        return v


# ── obligacion_financiera ─────────────────────────────────────────────────────

class ComposicionObligacionData(BaseModel):
    id_composicion_obligacion: int
    orden_composicion: int
    estado_composicion_obligacion: str
    importe_componente: float
    saldo_componente: float
    moneda_componente: str
    codigo_concepto_financiero: str


class ObligacionFinancieraData(BaseModel):
    id_obligacion_financiera: int
    uid_global: str
    version_registro: int
    id_relacion_generadora: int
    codigo_obligacion_financiera: str | None
    descripcion_operativa: str | None
    fecha_emision: date
    fecha_vencimiento: date | None
    periodo_desde: date | None
    periodo_hasta: date | None
    importe_total: float
    saldo_pendiente: float
    estado_obligacion: str
    composiciones: list[ComposicionObligacionData]


class ObligacionFinancieraResponse(BaseModel):
    ok: bool = True
    data: ObligacionFinancieraData
