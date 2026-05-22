from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class ConfirmVentaDirectaCompletaGenerarVentaInput:
    codigo_venta: str
    fecha_venta: datetime
    monto_total: Decimal | None
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaDirectaCompletaObjetoInput:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    precio_asignado: Decimal
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaDirectaCompletaCompradorInput:
    id_persona: int
    id_rol_participacion: int
    fecha_desde: date | None
    fecha_hasta: date | None
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaDirectaCompletaCondicionCuotaInput:
    numero_cuota: int
    importe_cuota: Decimal
    fecha_vencimiento: date
    moneda: str | None
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaDirectaCompletaCondicionesComercialesInput:
    monto_total: Decimal
    tipo_plan_financiero: str | None
    moneda: str | None
    importe_anticipo: Decimal | None
    fecha_vencimiento_anticipo: date | None
    importe_saldo: Decimal | None
    fecha_vencimiento_saldo: date | None
    cuotas: list[ConfirmVentaDirectaCompletaCondicionCuotaInput]


@dataclass(slots=True)
class ConfirmVentaDirectaCompletaPlanPagoBloqueInput:
    tipo_bloque: str
    etiqueta_bloque: str | None
    importe_total_bloque: Decimal | None
    fecha_vencimiento: date | None
    cantidad_cuotas: int | None
    importe_cuota: Decimal | None
    fecha_primer_vencimiento: date | None
    periodicidad: str | None
    regla_redondeo: str | None
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaDirectaCompletaPlanPagoV2Input:
    tipo_pago: str
    monto_total_plan: Decimal
    moneda: str
    bloques: list[ConfirmVentaDirectaCompletaPlanPagoBloqueInput]
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaDirectaCompletaConfirmacionInput:
    observaciones: str | None


@dataclass(slots=True)
class ConfirmVentaDirectaCompletaCommand:
    context: CommandContext
    generar_venta: ConfirmVentaDirectaCompletaGenerarVentaInput
    objetos: list[ConfirmVentaDirectaCompletaObjetoInput]
    compradores: list[ConfirmVentaDirectaCompletaCompradorInput]
    condiciones_comerciales: ConfirmVentaDirectaCompletaCondicionesComercialesInput
    plan_pago_v2: ConfirmVentaDirectaCompletaPlanPagoV2Input
    confirmacion: ConfirmVentaDirectaCompletaConfirmacionInput
