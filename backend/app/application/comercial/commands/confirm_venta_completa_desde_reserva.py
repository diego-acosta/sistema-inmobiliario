from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class ConfirmVentaCompletaGenerarVentaInput:
    codigo_venta: str
    fecha_venta: datetime
    monto_total: Decimal | None
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaCompletaCondicionObjetoInput:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    precio_asignado: Decimal | None


@dataclass(slots=True)
class ConfirmVentaCompletaCondicionCuotaInput:
    numero_cuota: int
    importe_cuota: Decimal
    fecha_vencimiento: date
    moneda: str | None
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaCompletaCondicionesComercialesInput:
    monto_total: Decimal
    tipo_plan_financiero: str | None
    moneda: str | None
    importe_anticipo: Decimal | None
    fecha_vencimiento_anticipo: date | None
    importe_saldo: Decimal | None
    fecha_vencimiento_saldo: date | None
    cuotas: list[ConfirmVentaCompletaCondicionCuotaInput]
    objetos: list[ConfirmVentaCompletaCondicionObjetoInput]


@dataclass(slots=True)
class ConfirmVentaCompletaPlanPagoBloqueInput:
    tipo_bloque: str
    etiqueta_bloque: str | None
    importe_total_bloque: Decimal | None
    fecha_vencimiento: date | None
    cantidad_cuotas: int | None
    importe_cuota: Decimal | None
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
    observaciones: str | None = None


@dataclass(slots=True)
class ConfirmVentaCompletaPlanPagoV2Input:
    tipo_pago: str
    monto_total_plan: Decimal
    moneda: str
    bloques: list[ConfirmVentaCompletaPlanPagoBloqueInput]
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaCompletaConfirmacionInput:
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaCompletaDesdeReservaCommand:
    context: CommandContext
    id_reserva_venta: int
    if_match_version_reserva: int | None
    generar_venta: ConfirmVentaCompletaGenerarVentaInput
    condiciones_comerciales: ConfirmVentaCompletaCondicionesComercialesInput
    plan_pago_v2: ConfirmVentaCompletaPlanPagoV2Input
    confirmacion: ConfirmVentaCompletaConfirmacionInput
