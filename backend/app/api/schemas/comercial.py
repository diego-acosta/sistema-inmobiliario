from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel


class ReservaVentaParticipacionCreateRequest(BaseModel):
    id_persona: int
    id_rol_participacion: int
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    observaciones: str | None = None


class ReservaVentaObjetoCreateRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    observaciones: str | None = None


class ReservaVentaCreateRequest(BaseModel):
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_vencimiento: datetime | None = None
    observaciones: str | None = None
    objetos: list[ReservaVentaObjetoCreateRequest]
    participaciones: list[ReservaVentaParticipacionCreateRequest]


class ReservaVentaUpdateRequest(BaseModel):
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_vencimiento: datetime | None = None
    observaciones: str | None = None


class ReservaVentaObjetoCreateData(BaseModel):
    id_reserva_venta_objeto: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


class ReservaVentaCreateData(BaseModel):
    id_reserva_venta: int
    uid_global: str
    version_registro: int
    codigo_reserva: str
    fecha_reserva: datetime
    estado_reserva: str
    fecha_vencimiento: datetime | None
    observaciones: str | None
    objetos: list[ReservaVentaObjetoCreateData]


class ReservaVentaCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: ReservaVentaCreateData


class ReservaVentaUpdateData(ReservaVentaCreateData):
    pass


class ReservaVentaUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: ReservaVentaUpdateData


class ReservaVentaBajaData(BaseModel):
    id_reserva_venta: int
    version_registro: int
    deleted: Literal[True] = True


class ReservaVentaBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: ReservaVentaBajaData


class ReservaVentaDetailData(ReservaVentaCreateData):
    pass


class ReservaVentaDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: ReservaVentaDetailData


class ReservaVentaListItemData(ReservaVentaCreateData):
    pass


class ReservaVentaListData(BaseModel):
    items: list[ReservaVentaListItemData]
    total: int


class ReservaVentaListResponse(BaseModel):
    ok: Literal[True] = True
    data: ReservaVentaListData


class ReservaVentaConfirmData(ReservaVentaCreateData):
    pass


class ReservaVentaConfirmResponse(BaseModel):
    ok: Literal[True] = True
    data: ReservaVentaConfirmData


class ReservaVentaActivateData(ReservaVentaCreateData):
    pass


class ReservaVentaActivateResponse(BaseModel):
    ok: Literal[True] = True
    data: ReservaVentaActivateData


class ReservaVentaCancelData(ReservaVentaCreateData):
    pass


class ReservaVentaCancelResponse(BaseModel):
    ok: Literal[True] = True
    data: ReservaVentaCancelData


class ReservaVentaExpireData(ReservaVentaCreateData):
    pass


class ReservaVentaExpireResponse(BaseModel):
    ok: Literal[True] = True
    data: ReservaVentaExpireData


class GenerateVentaFromReservaVentaRequest(BaseModel):
    codigo_venta: str
    fecha_venta: datetime
    monto_total: Decimal | None = None
    observaciones: str | None = None


class DefineCondicionesComercialesVentaObjetoRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    precio_asignado: Decimal


class DefineCondicionesComercialesVentaRequest(BaseModel):
    monto_total: Decimal
    objetos: list[DefineCondicionesComercialesVentaObjetoRequest]


class ConfirmVentaRequest(BaseModel):
    observaciones: str | None = None


class InstrumentoCompraventaObjetoRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    observaciones: str | None = None


class CreateInstrumentoCompraventaRequest(BaseModel):
    tipo_instrumento: str
    numero_instrumento: str | None = None
    fecha_instrumento: datetime
    estado_instrumento: str
    observaciones: str | None = None
    objetos: list[InstrumentoCompraventaObjetoRequest] = []


class CreateCesionRequest(BaseModel):
    fecha_cesion: datetime
    tipo_cesion: str | None = None
    observaciones: str | None = None


class CreateEscrituracionRequest(BaseModel):
    fecha_escrituracion: datetime
    numero_escritura: str | None = None
    observaciones: str | None = None


class VentaObjetoData(BaseModel):
    id_venta_objeto: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    precio_asignado: Decimal | None
    observaciones: str | None


class GenerateVentaFromReservaVentaData(BaseModel):
    id_venta: int
    uid_global: str
    version_registro: int
    id_reserva_venta: int | None
    codigo_venta: str
    fecha_venta: datetime
    estado_venta: str
    monto_total: Decimal | None
    observaciones: str | None
    objetos: list[VentaObjetoData]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class GenerateVentaFromReservaVentaResponse(BaseModel):
    ok: Literal[True] = True
    data: GenerateVentaFromReservaVentaData


class DefineCondicionesComercialesVentaData(GenerateVentaFromReservaVentaData):
    pass


class DefineCondicionesComercialesVentaResponse(BaseModel):
    ok: Literal[True] = True
    data: DefineCondicionesComercialesVentaData


class ConfirmVentaData(GenerateVentaFromReservaVentaData):
    pass


class ConfirmVentaResponse(BaseModel):
    ok: Literal[True] = True
    data: ConfirmVentaData


class VentaOrigenConReservaData(BaseModel):
    id_reserva_venta: int
    estado_reserva_venta: str


class VentaOrigenData(BaseModel):
    venta_directa: bool
    con_reserva: VentaOrigenConReservaData | None


class VentaObjetoDetalleData(BaseModel):
    id_venta_objeto_inmobiliario: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    precio_asignado: Decimal | None
    observaciones: str | None
    disponibilidad_actual: str | None
    ocupacion_actual: str | None


class InstrumentoCompraventaObjetoData(BaseModel):
    id_instrumento_objeto: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


class InstrumentoCompraventaData(BaseModel):
    id_instrumento_compraventa: int
    uid_global: str
    version_registro: int
    id_venta: int
    tipo_instrumento: str
    numero_instrumento: str | None
    fecha_instrumento: datetime
    estado_instrumento: str
    observaciones: str | None
    objetos: list[InstrumentoCompraventaObjetoData]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CreateInstrumentoCompraventaResponse(BaseModel):
    ok: Literal[True] = True
    data: InstrumentoCompraventaData


class InstrumentoCompraventaListData(BaseModel):
    items: list[InstrumentoCompraventaData]
    total: int


class InstrumentoCompraventaListResponse(BaseModel):
    ok: Literal[True] = True
    data: InstrumentoCompraventaListData


class CesionData(BaseModel):
    id_cesion: int
    uid_global: str
    version_registro: int
    id_venta: int
    fecha_cesion: datetime
    tipo_cesion: str | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CreateCesionResponse(BaseModel):
    ok: Literal[True] = True
    data: CesionData


class CesionListData(BaseModel):
    items: list[CesionData]
    total: int


class CesionListResponse(BaseModel):
    ok: Literal[True] = True
    data: CesionListData


class EscrituracionData(BaseModel):
    id_escrituracion: int
    uid_global: str
    version_registro: int
    id_venta: int
    fecha_escrituracion: datetime
    numero_escritura: str | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CreateEscrituracionResponse(BaseModel):
    ok: Literal[True] = True
    data: EscrituracionData


class EscrituracionListData(BaseModel):
    items: list[EscrituracionData]
    total: int


class EscrituracionListResponse(BaseModel):
    ok: Literal[True] = True
    data: EscrituracionListData


class VentaResumenData(BaseModel):
    venta_cerrada_logica: bool
    estado_operativo_conocido_del_activo: str | None


class IntegracionInmobiliariaEfectoData(BaseModel):
    disponibilidad: str | None
    ocupacion: str | None


class IntegracionInmobiliariaObjetoData(BaseModel):
    id_inmueble: int | None
    id_unidad_funcional: int | None
    efecto_inmobiliario: IntegracionInmobiliariaEfectoData


class IntegracionInmobiliariaEventoData(BaseModel):
    id_evento_outbox: int
    nombre_evento: str
    estado: str
    ocurrido_en: datetime
    publicado_en: datetime | None
    objetos: list[IntegracionInmobiliariaObjetoData]


class IntegracionInmobiliariaData(BaseModel):
    eventos: list[IntegracionInmobiliariaEventoData]


class VentaDetailData(BaseModel):
    id_venta: int
    version_registro: int
    codigo_venta: str
    fecha_venta: datetime
    estado_venta: str
    monto_total: Decimal | None
    deleted_at: datetime | None
    origen: VentaOrigenData
    objetos: list[VentaObjetoDetalleData]
    instrumentos_compraventa: list[InstrumentoCompraventaData]
    cesiones: list[CesionData]
    escrituraciones: list[EscrituracionData]
    integracion_inmobiliaria: IntegracionInmobiliariaData
    resumen: VentaResumenData


class VentaDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: VentaDetailData


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] | None = None
