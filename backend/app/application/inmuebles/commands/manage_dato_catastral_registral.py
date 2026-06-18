from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DatoCatastralRegistralFields:
    nomenclatura_catastral: str | None
    partida_inmobiliaria: str | None
    matricula: str | None
    folio_real: str | None
    circunscripcion: str | None
    seccion: str | None
    chacra: str | None
    quinta: str | None
    fraccion: str | None
    manzana: str | None
    lote: str | None
    parcela: str | None
    subparcela: str | None
    superficie_titulo: Decimal | None
    superficie_mensura: Decimal | None
    medidas: str | None
    situacion_posesoria: str | None
    situacion_dominial: str | None
    organismo_origen: str | None
    fecha_desde: datetime | None
    fecha_hasta: datetime | None
    estado_dato: str
    observaciones: str | None


@dataclass(slots=True)
class CreateDatoCatastralRegistralCommand(DatoCatastralRegistralFields):
    context: CommandContext
    id_inmueble: int


@dataclass(slots=True)
class UpdateDatoCatastralRegistralCommand(DatoCatastralRegistralFields):
    context: CommandContext
    id_inmueble: int
    id_dato_catastral_registral: int
    if_match_version: int | None
    provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(slots=True)
class BajaDatoCatastralRegistralCommand:
    context: CommandContext
    id_inmueble: int
    id_dato_catastral_registral: int
    if_match_version: int | None
