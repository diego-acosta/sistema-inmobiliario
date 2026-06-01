from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ReservaVentaParticipacionCreateRequest(BaseModel):
    id_persona: int
    id_rol_participacion: int
    porcentaje_responsabilidad: Decimal | None = None
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


class DefineCondicionesComercialesVentaCuotaRequest(BaseModel):
    numero_cuota: int
    importe_cuota: Decimal
    fecha_vencimiento: date
    moneda: str | None = None
    observaciones: str | None = None


class DefineCondicionesComercialesVentaRequest(BaseModel):
    monto_total: Decimal
    tipo_plan_financiero: str | None = None
    moneda: str | None = None
    importe_anticipo: Decimal | None = None
    fecha_vencimiento_anticipo: date | None = None
    importe_saldo: Decimal | None = None
    fecha_vencimiento_saldo: date | None = None
    cuotas: list[DefineCondicionesComercialesVentaCuotaRequest] = []
    objetos: list[DefineCondicionesComercialesVentaObjetoRequest]


class GeneratePlanPagoVentaCuotasIgualesSimpleRequest(BaseModel):
    monto_total_plan: Decimal
    moneda: str = "ARS"
    cantidad_cuotas: int
    fecha_primer_vencimiento: date
    periodicidad: str = "MENSUAL"
    regla_redondeo: str = "ULTIMA_CUOTA"


class GeneratePlanPagoVentaAnticipoMasCuotasIgualesRequest(BaseModel):
    monto_total_plan: Decimal
    moneda: str = "ARS"
    importe_anticipo: Decimal
    fecha_vencimiento_anticipo: date
    cantidad_cuotas: int
    fecha_primer_vencimiento: date
    periodicidad: str = "MENSUAL"
    regla_redondeo: str = "ULTIMA_CUOTA"


class PlanPagoVentaBloqueV2Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_bloque: str
    etiqueta_bloque: str | None = None
    importe_total_bloque: Decimal | None = None
    fecha_vencimiento: date | None = None
    cantidad_cuotas: int | None = None
    importe_cuota: Decimal | None = None
    fecha_primer_vencimiento: date | None = None
    periodicidad: str | None = None
    regla_redondeo: str | None = None
    metodo_liquidacion: str | None = None
    tasa_interes_directo_periodica: Decimal | None = None
    cantidad_periodos: int | None = None
    base_calculo_interes: str | None = None
    id_indice_financiero: int | None = None
    fecha_base_indice: date | None = None
    valor_base_indice: Decimal | None = None
    modo_indexacion: str | None = None
    base_calculo_indexacion: str | None = None
    tipo_generacion_indexada: str | None = None
    politica_valor_no_disponible: str | None = None
    conserva_capital_original: bool | None = None
    genera_ajuste_por_diferencia: bool | None = None
    observaciones: str | None = None


class GeneratePlanPagoVentaV2PorBloquesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_pago: str
    monto_total_plan: Decimal
    moneda: str = "ARS"
    bloques: list[PlanPagoVentaBloqueV2Request]
    observaciones: str | None = None


class PreviewPlanPagoVentaV2PorBloquesRequest(GeneratePlanPagoVentaV2PorBloquesRequest):
    pass


class ConfirmVentaRequest(BaseModel):
    observaciones: str | None = None


class ConfirmVentaCompletaDesdeReservaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generar_venta: GenerateVentaFromReservaVentaRequest
    condiciones_comerciales: DefineCondicionesComercialesVentaRequest
    plan_pago_v2: GeneratePlanPagoVentaV2PorBloquesRequest
    confirmacion: ConfirmVentaRequest


class ConfirmVentaCompletaReservaResumenData(BaseModel):
    id_reserva_venta: int
    estado_reserva: str
    version_registro: int


class ConfirmVentaCompletaVentaResumenData(BaseModel):
    id_venta: int
    estado_venta: str
    version_registro: int


class ConfirmVentaCompletaPlanPagoV2ResumenData(BaseModel):
    id_plan_pago_venta: int
    estado_plan_pago: str


class ConfirmVentaCompletaGeneracionCronogramaResumenData(BaseModel):
    id_generacion_cronograma_financiero: int
    estado_generacion: str


class ConfirmVentaCompletaObligacionesResumenData(BaseModel):
    cantidad: int
    ids: list[int]


class ConfirmVentaCompletaDesdeReservaData(BaseModel):
    reserva_venta: ConfirmVentaCompletaReservaResumenData
    venta: ConfirmVentaCompletaVentaResumenData
    plan_pago_v2: ConfirmVentaCompletaPlanPagoV2ResumenData
    generacion_cronograma_financiero: (
        ConfirmVentaCompletaGeneracionCronogramaResumenData
    )
    obligaciones: ConfirmVentaCompletaObligacionesResumenData


class ConfirmVentaCompletaDesdeReservaResponse(BaseModel):
    ok: Literal[True] = True
    data: ConfirmVentaCompletaDesdeReservaData


class ConfirmVentaDirectaCompletaObjetoRequest(BaseModel):
    id_inmueble: int | None = None
    id_unidad_funcional: int | None = None
    precio_asignado: Decimal
    observaciones: str | None = None


class ConfirmVentaDirectaCompletaCompradorRequest(BaseModel):
    id_persona: int
    id_rol_participacion: int
    porcentaje_responsabilidad: Decimal | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    observaciones: str | None = None


class ConfirmVentaDirectaCompletaCondicionesComercialesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monto_total: Decimal
    tipo_plan_financiero: str | None = None
    moneda: str | None = None
    importe_anticipo: Decimal | None = None
    fecha_vencimiento_anticipo: date | None = None
    importe_saldo: Decimal | None = None
    fecha_vencimiento_saldo: date | None = None
    cuotas: list[DefineCondicionesComercialesVentaCuotaRequest] = []


class ConfirmVentaDirectaCompletaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generar_venta: GenerateVentaFromReservaVentaRequest
    objetos: list[ConfirmVentaDirectaCompletaObjetoRequest]
    compradores: list[ConfirmVentaDirectaCompletaCompradorRequest]
    condiciones_comerciales: ConfirmVentaDirectaCompletaCondicionesComercialesRequest
    plan_pago_v2: GeneratePlanPagoVentaV2PorBloquesRequest
    confirmacion: ConfirmVentaRequest


class ConfirmVentaDirectaCompletaData(BaseModel):
    venta: ConfirmVentaCompletaVentaResumenData
    plan_pago_v2: ConfirmVentaCompletaPlanPagoV2ResumenData
    generacion_cronograma_financiero: (
        ConfirmVentaCompletaGeneracionCronogramaResumenData
    )
    obligaciones: ConfirmVentaCompletaObligacionesResumenData


class ConfirmVentaDirectaCompletaResponse(BaseModel):
    ok: Literal[True] = True
    data: ConfirmVentaDirectaCompletaData


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


class VentaPlanCuotaData(BaseModel):
    id_venta_plan_cuota: int | None = None
    numero_cuota: int
    importe_cuota: Decimal
    fecha_vencimiento: date
    moneda: str
    observaciones: str | None = None


class GenerateVentaFromReservaVentaData(BaseModel):
    id_venta: int
    uid_global: str
    version_registro: int
    id_reserva_venta: int | None
    codigo_venta: str
    fecha_venta: datetime
    estado_venta: str
    monto_total: Decimal | None
    tipo_plan_financiero: str
    moneda: str
    importe_anticipo: Decimal | None
    fecha_vencimiento_anticipo: date | None
    importe_saldo: Decimal | None
    fecha_vencimiento_saldo: date | None
    cuotas: list[VentaPlanCuotaData] = []
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


class PlanPagoVentaV2Data(BaseModel):
    id_plan_pago_venta: int
    id_venta: int
    metodo_plan_pago: str
    estado_plan_pago: str
    moneda: str
    monto_total_plan: Decimal
    cantidad_cuotas: int | None
    periodicidad: str | None
    fecha_primer_vencimiento: date | None
    importe_anticipo: Decimal | None
    fecha_vencimiento_anticipo: date | None
    regla_redondeo: str | None
    observaciones: str | None


class GeneracionCronogramaFinancieroData(BaseModel):
    id_generacion_cronograma_financiero: int
    id_relacion_generadora: int
    id_plan_pago_venta: int | None
    tipo_generacion: str
    clave_generacion: str
    estado_generacion: str
    fecha_generacion: datetime


class ObligacionCronogramaVentaV2Data(BaseModel):
    id_obligacion_financiera: int
    id_relacion_generadora: int
    id_generacion_cronograma_financiero: int | None
    numero_obligacion: int | None
    tipo_item_cronograma: str | None
    etiqueta_obligacion: str | None
    clave_funcional_origen: str | None
    fecha_vencimiento: date | None
    importe_total: Decimal
    saldo_pendiente: Decimal
    moneda: str
    estado_obligacion: str


class ObligacionCronogramaVentaPorBloquesV2Data(ObligacionCronogramaVentaV2Data):
    id_plan_pago_venta_bloque: int | None


class PlanPagoVentaBloqueV2Data(BaseModel):
    id_plan_pago_venta_bloque: int
    id_plan_pago_venta: int
    numero_bloque: int
    tipo_bloque: str
    etiqueta_bloque: str
    clave_bloque: str
    cantidad_cuotas: int | None
    importe_total_bloque: Decimal | None
    importe_cuota: Decimal | None
    fecha_vencimiento: date | None
    fecha_primer_vencimiento: date | None
    periodicidad: str | None
    regla_redondeo: str | None
    metodo_liquidacion: str | None = None
    tasa_interes_directo_periodica: Decimal | None = None
    cantidad_periodos: int | None = None
    base_calculo_interes: str | None = None
    id_indice_financiero: int | None = None
    fecha_base_indice: date | None = None
    valor_base_indice: Decimal | None = None
    modo_indexacion: str | None = None
    base_calculo_indexacion: str | None = None
    tipo_generacion_indexada: str | None = None
    politica_valor_no_disponible: str | None = None
    conserva_capital_original: bool | None = None
    genera_ajuste_por_diferencia: bool | None = None
    concepto_financiero_codigo: str


class GeneratePlanPagoVentaCuotasIgualesSimpleData(BaseModel):
    id_venta: int
    id_relacion_generadora: int
    plan_pago_venta: PlanPagoVentaV2Data
    generacion_cronograma_financiero: GeneracionCronogramaFinancieroData
    obligaciones: list[ObligacionCronogramaVentaV2Data]


class GeneratePlanPagoVentaCuotasIgualesSimpleResponse(BaseModel):
    ok: Literal[True] = True
    data: GeneratePlanPagoVentaCuotasIgualesSimpleData


class GeneratePlanPagoVentaAnticipoMasCuotasIgualesData(
    GeneratePlanPagoVentaCuotasIgualesSimpleData
):
    pass


class GeneratePlanPagoVentaAnticipoMasCuotasIgualesResponse(BaseModel):
    ok: Literal[True] = True
    data: GeneratePlanPagoVentaAnticipoMasCuotasIgualesData


class GeneratePlanPagoVentaV2PorBloquesData(BaseModel):
    id_venta: int
    id_relacion_generadora: int
    plan_pago_venta: PlanPagoVentaV2Data
    bloques: list[PlanPagoVentaBloqueV2Data]
    generacion_cronograma_financiero: GeneracionCronogramaFinancieroData
    obligaciones: list[ObligacionCronogramaVentaPorBloquesV2Data]


class GeneratePlanPagoVentaV2PorBloquesResponse(BaseModel):
    ok: Literal[True] = True
    data: GeneratePlanPagoVentaV2PorBloquesData


class PlanPagoVentaV2RelacionGeneradoraData(BaseModel):
    id_relacion_generadora: int
    tipo_origen: str
    id_origen: int
    estado_relacion_generadora: str


class PlanPagoVentaV2BloqueIndexacionData(BaseModel):
    id_plan_pago_venta_bloque_indexacion: int
    id_indice_financiero: int
    codigo_indice_financiero: str | None
    nombre_indice_financiero: str | None
    fecha_base_indice: date
    valor_base_indice: Decimal
    modo_indexacion: str
    base_calculo_indexacion: str
    tipo_generacion_indexada: str
    politica_valor_no_disponible: str
    conserva_capital_original: bool
    genera_ajuste_por_diferencia: bool


class PlanPagoVentaV2ObligacionComposicionData(BaseModel):
    id_composicion_obligacion: int
    id_obligacion_financiera: int
    id_concepto_financiero: int
    codigo_concepto_financiero: str
    orden_composicion: int
    importe_componente: Decimal
    saldo_componente: Decimal
    moneda_componente: str


class PlanPagoVentaV2ObligacionObligadoData(BaseModel):
    id_obligacion_obligado: int
    id_obligacion_financiera: int
    id_persona: int
    codigo_persona: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    razon_social: str | None = None
    rol_obligado: str | None = None
    porcentaje_responsabilidad: Decimal | None = None
    importe_responsabilidad_informativo: Decimal | None = None


class PlanPagoVentaV2ObligacionIndexacionData(BaseModel):
    id_obligacion_financiera_indexacion: int
    id_indice_financiero: int
    id_indice_financiero_valor: int
    fecha_base_indice: date
    valor_base_indice: Decimal
    fecha_aplicacion_indice: date
    valor_aplicado_indice: Decimal
    coeficiente_indexacion: Decimal
    modo_indexacion: str
    base_calculo_indexacion: str
    tipo_generacion_indexada: str


class PlanPagoVentaV2ObligacionIntegralData(ObligacionCronogramaVentaPorBloquesV2Data):
    composiciones: list[PlanPagoVentaV2ObligacionComposicionData]
    obligados: list[PlanPagoVentaV2ObligacionObligadoData]
    indexacion: PlanPagoVentaV2ObligacionIndexacionData | None = None


class PlanPagoVentaV2BloqueIntegralData(PlanPagoVentaBloqueV2Data):
    observaciones: str | None = None
    indexacion: PlanPagoVentaV2BloqueIndexacionData | None = None
    obligaciones: list[PlanPagoVentaV2ObligacionIntegralData]


class PlanPagoVentaV2ResumenData(BaseModel):
    cantidad_bloques: int
    cantidad_obligaciones: int
    total_capital: Decimal
    total_interes: Decimal
    total_ajuste_indexacion: Decimal
    total_obligaciones: Decimal
    cantidad_obligaciones_con_indexacion: int
    cantidad_obligados_total: int
    cantidad_obligaciones_con_multiples_obligados: int
    cantidad_obligaciones_proyectadas_sin_indexacion: int


class PlanPagoVentaV2IntegralData(BaseModel):
    id_venta: int
    plan_pago_venta: PlanPagoVentaV2Data
    relacion_generadora: PlanPagoVentaV2RelacionGeneradoraData | None = None
    generaciones: list[GeneracionCronogramaFinancieroData]
    bloques: list[PlanPagoVentaV2BloqueIntegralData]
    resumen: PlanPagoVentaV2ResumenData


class PlanPagoVentaV2IntegralResponse(BaseModel):
    ok: Literal[True] = True
    data: PlanPagoVentaV2IntegralData


class PlanPagoVentaBloqueV2PreviewData(BaseModel):
    numero_bloque: int
    tipo_bloque: str
    etiqueta_bloque: str
    cantidad_cuotas: int | None
    importe_total_bloque: Decimal | None
    importe_cuota: Decimal | None
    fecha_vencimiento: date | None
    fecha_primer_vencimiento: date | None
    periodicidad: str | None
    regla_redondeo: str | None
    metodo_liquidacion: str | None = None
    tasa_interes_directo_periodica: Decimal | None = None
    cantidad_periodos: int | None = None
    base_calculo_interes: str | None = None
    id_indice_financiero: int | None = None
    fecha_base_indice: date | None = None
    valor_base_indice: Decimal | None = None
    modo_indexacion: str | None = None
    base_calculo_indexacion: str | None = None
    tipo_generacion_indexada: str | None = None
    politica_valor_no_disponible: str | None = None
    conserva_capital_original: bool | None = None
    genera_ajuste_por_diferencia: bool | None = None
    total_con_indexacion: Decimal | None = None
    total_ajuste_indexacion: Decimal | None = None
    cantidad_cuotas_con_indice: int = 0
    cantidad_cuotas_proyectadas_sin_indice: int = 0
    concepto_financiero_codigo: str


class ObligacionPlanPagoVentaV2PreviewData(BaseModel):
    numero_obligacion: int
    numero_bloque: int
    tipo_bloque: str
    tipo_item_cronograma: str
    etiqueta_obligacion: str
    item_numero: int
    fecha_vencimiento: date
    importe_total: Decimal
    moneda: str
    concepto_financiero_codigo: str
    estado_preview_indexacion: str | None = None
    id_indice_financiero: int | None = None
    id_indice_financiero_valor: int | None = None
    fecha_valor_indice: date | None = None
    valor_base_indice: Decimal | None = None
    valor_aplicado_indice: Decimal | None = None
    coeficiente_indexacion: Decimal | None = None
    capital_cuota: Decimal | None = None
    ajuste_indexacion_cuota: Decimal | None = None


class RedondeoPlanPagoVentaV2PreviewData(BaseModel):
    numero_bloque: int
    tipo_bloque: str
    ajuste_ultima_cuota: Decimal


class PreviewPlanPagoVentaV2PorBloquesData(BaseModel):
    id_venta: int
    metodo_plan_pago: str
    tipo_pago: str
    moneda: str
    monto_total_plan: Decimal
    total_calculado: Decimal
    total_con_interes: Decimal
    total_con_indexacion: Decimal
    total_ajuste_indexacion: Decimal
    diferencia: Decimal
    bloques: list[PlanPagoVentaBloqueV2PreviewData]
    obligaciones: list[ObligacionPlanPagoVentaV2PreviewData]
    redondeos: list[RedondeoPlanPagoVentaV2PreviewData]


class PreviewPlanPagoVentaV2PorBloquesResponse(BaseModel):
    ok: Literal[True] = True
    data: PreviewPlanPagoVentaV2PorBloquesData


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
    tipo_plan_financiero: str
    moneda: str
    importe_anticipo: Decimal | None
    fecha_vencimiento_anticipo: date | None
    importe_saldo: Decimal | None
    fecha_vencimiento_saldo: date | None
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


class VentaListItemData(BaseModel):
    id_venta: int
    uid_global: str
    version_registro: int
    codigo_venta: str
    fecha_venta: datetime
    estado_venta: str
    monto_total: Decimal | None
    moneda: str
    tipo_plan_financiero: str
    comprador_resumen: list[dict[str, Any]] = []
    objetos_resumen: list[dict[str, Any]] = []
    relacion_financiera: dict[str, Any] | None = None
    acciones_ui: dict[str, Any] | None = None


class VentaListData(BaseModel):
    items: list[VentaListItemData]
    total: int
    limit: int | None = None
    offset: int | None = None


class VentaListResponse(BaseModel):
    ok: Literal[True] = True
    data: VentaListData


class VentaParteData(BaseModel):
    id_relacion_persona_rol: int
    id_persona: int
    tipo_persona: str
    codigo_persona: str | None
    nombre: str | None
    apellido: str | None
    razon_social: str | None
    estado_persona: str
    id_rol_participacion: int
    codigo_rol: str
    nombre_rol: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    observaciones: str | None


class VentaCondicionesComercialesData(BaseModel):
    monto_total: Decimal | None
    moneda: str | None
    tipo_plan_financiero: str
    importe_anticipo: Decimal | None
    fecha_vencimiento_anticipo: date | None
    importe_saldo: Decimal | None
    fecha_vencimiento_saldo: date | None
    cuotas: list[VentaPlanCuotaData] = []
    observaciones: str | None
    objetos: list[VentaObjetoData]


class VentaRelacionFinancieraData(BaseModel):
    id_relacion_generadora: int
    uid_global: str
    version_registro: int
    tipo_origen: str
    id_origen: int
    descripcion: str | None
    estado_relacion_generadora: str
    fecha_alta: datetime


class VentaObligacionComposicionData(BaseModel):
    id_composicion_obligacion: int
    id_concepto_financiero: int
    codigo_concepto_financiero: str
    nombre_concepto_financiero: str
    tipo_concepto_financiero: str
    naturaleza_concepto: str
    orden_composicion: int
    estado_composicion_obligacion: str
    importe_componente: Decimal
    saldo_componente: Decimal
    moneda_componente: str
    observaciones: str | None


class VentaObligacionObligadoData(BaseModel):
    id_obligacion_obligado: int
    id_persona: int
    rol_obligado: str
    porcentaje_responsabilidad: Decimal


class VentaObligacionFinancieraData(BaseModel):
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
    importe_total: Decimal
    saldo_pendiente: Decimal
    importe_cancelado_acumulado: Decimal
    importe_bonificado_acumulado: Decimal
    importe_anulado_acumulado: Decimal
    moneda: str
    estado_obligacion: str
    composiciones: list[VentaObligacionComposicionData]
    obligados: list[VentaObligacionObligadoData]


class VentaPlanPagoV2ObligacionData(BaseModel):
    id_obligacion_financiera: int
    numero_obligacion: int | None
    tipo_item_cronograma: str | None
    etiqueta_obligacion: str | None
    fecha_vencimiento: date | None
    importe_total: Decimal
    saldo_pendiente: Decimal
    estado_obligacion: str
    composiciones: list[VentaObligacionComposicionData]


class VentaPlanPagoV2BloqueData(BaseModel):
    id_plan_pago_venta_bloque: int
    numero_bloque: int
    tipo_bloque: str
    etiqueta_bloque: str
    clave_bloque: str
    cantidad_cuotas: int | None
    importe_total_bloque: Decimal | None
    importe_cuota: Decimal | None
    fecha_vencimiento: date | None
    fecha_primer_vencimiento: date | None
    periodicidad: str | None
    regla_redondeo: str | None
    obligaciones: list[VentaPlanPagoV2ObligacionData]


class VentaPlanPagoV2Data(BaseModel):
    id_plan_pago_venta: int
    metodo_plan_pago: str
    estado_plan_pago: str
    monto_total_plan: Decimal
    moneda: str
    bloques: list[VentaPlanPagoV2BloqueData]


class VentaResumenFinancieroData(BaseModel):
    cantidad_obligaciones: int
    saldo_total: Decimal
    saldo_pendiente: Decimal
    importe_cancelado: Decimal
    cantidad_vencidas: int
    cantidad_canceladas: int
    cantidad_anuladas: int


class VentaDetalleIntegralData(VentaDetailData):
    uid_global: str
    id_reserva_venta: int | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime
    reserva_origen: VentaOrigenConReservaData | None
    condiciones_comerciales: VentaCondicionesComercialesData
    partes: list[VentaParteData]
    relacion_financiera: VentaRelacionFinancieraData | None
    obligaciones_financieras: list[VentaObligacionFinancieraData]
    plan_pago_v2: VentaPlanPagoV2Data | None
    resumen_financiero: VentaResumenFinancieroData


class VentaDetalleIntegralResponse(BaseModel):
    ok: Literal[True] = True
    data: VentaDetalleIntegralData


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] | None = None
