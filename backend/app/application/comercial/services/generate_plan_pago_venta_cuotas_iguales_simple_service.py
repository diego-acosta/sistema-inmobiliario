from __future__ import annotations

import calendar
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.comercial.commands.generate_plan_pago_venta_cuotas_iguales_simple import (
    GeneratePlanPagoVentaCuotasIgualesSimpleCommand,
)
from app.application.common.results import AppResult

METODO_CUOTAS_IGUALES_SIMPLE = "CUOTAS_IGUALES_SIMPLE"
PERIODICIDAD_MENSUAL = "MENSUAL"
REGLA_REDONDEO_ULTIMA_CUOTA = "ULTIMA_CUOTA"
TIPO_ORIGEN_VENTA = "venta"
TIPO_GENERACION_PLAN_PAGO_VENTA_V2 = "PLAN_PAGO_VENTA_V2"
CONCEPTO_CAPITAL_VENTA = "CAPITAL_VENTA"
ROL_OBLIGADO_COMPRADOR = "COMPRADOR"
ESTADO_OBLIGACION_PROYECTADA = "PROYECTADA"
TIPO_ITEM_CUOTA = "CUOTA"
TIPO_BLOQUE_TRAMO_CUOTAS = "TRAMO_CUOTAS"
ETIQUETA_BLOQUE_CUOTAS_IGUALES = "Cuotas iguales"


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_cuotas_iguales_mensuales(
    *,
    monto_total: Decimal,
    cantidad_cuotas: int,
    fecha_primer_vencimiento: date,
) -> list[tuple[int, Decimal, date]]:
    base = (monto_total / Decimal(cantidad_cuotas)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    cuotas: list[tuple[int, Decimal, date]] = []
    acumulado = Decimal("0.00")
    for numero in range(1, cantidad_cuotas + 1):
        importe = (
            monto_total - acumulado if numero == cantidad_cuotas else base
        ).quantize(Decimal("0.01"))
        cuotas.append(
            (
                numero,
                importe,
                add_months(fecha_primer_vencimiento, numero - 1),
            )
        )
        acumulado += importe
    return cuotas


@dataclass(slots=True)
class PlanPagoVentaUpsertPayload:
    id_venta: int
    metodo_plan_pago: str
    estado_plan_pago: str
    moneda: str
    monto_total_plan: Decimal
    cantidad_cuotas: int
    periodicidad: str
    fecha_primer_vencimiento: date
    importe_anticipo: Decimal | None
    fecha_vencimiento_anticipo: date | None
    regla_redondeo: str
    observaciones: str | None
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class RelacionGeneradoraUpsertPayload:
    tipo_origen: str
    id_origen: int
    descripcion: str
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class GeneracionCronogramaCreatePayload:
    id_relacion_generadora: int
    id_plan_pago_venta: int
    tipo_generacion: str
    clave_generacion: str
    estado_generacion: str
    fecha_generacion: datetime
    observaciones: str | None
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class PlanPagoVentaBloqueUpsertPayload:
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
    metodo_liquidacion: str | None
    tasa_interes_directo_periodica: Decimal | None
    cantidad_periodos: int | None
    base_calculo_interes: str | None
    concepto_financiero_codigo: str | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class ObligacionCronogramaV2CreatePayload:
    id_relacion_generadora: int
    id_generacion_cronograma_financiero: int
    id_plan_pago_venta_bloque: int | None
    numero_obligacion: int
    tipo_item_cronograma: str
    etiqueta_obligacion: str
    clave_funcional_origen: str
    fecha_emision: date
    fecha_vencimiento: date
    importe_total: Decimal
    moneda: str
    estado_obligacion: str
    id_concepto_financiero: int
    codigo_concepto_financiero: str
    id_persona_obligado: int
    rol_obligado: str
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    composiciones: list[dict[str, Any]] | None = None


class PlanPagoVentaV2Repository(Protocol):
    db: Any

    def get_venta_minima(self, id_venta: int) -> dict[str, Any] | None: ...

    def get_plan_pago_venta_vivo(self, id_venta: int) -> dict[str, Any] | None: ...

    def upsert_plan_pago_venta_borrador(
        self, payload: PlanPagoVentaUpsertPayload
    ) -> dict[str, Any]: ...

    def mark_plan_pago_venta_generado(
        self,
        *,
        id_plan_pago_venta: int,
        updated_at: datetime,
        id_instalacion_ultima_modificacion: int | None,
        op_id_ultima_modificacion: UUID | None,
    ) -> dict[str, Any]: ...

    def get_or_create_relacion_generadora(
        self, payload: RelacionGeneradoraUpsertPayload
    ) -> dict[str, Any]: ...

    def get_or_create_generacion_cronograma(
        self, payload: GeneracionCronogramaCreatePayload
    ) -> dict[str, Any]: ...

    def get_or_create_plan_pago_venta_bloque(
        self, payload: PlanPagoVentaBloqueUpsertPayload
    ) -> dict[str, Any]: ...

    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None: ...

    def get_compradores_financieros_venta(
        self, id_venta: int
    ) -> list[dict[str, Any]]: ...

    def create_obligacion_cronograma_v2_if_not_exists(
        self, payload: ObligacionCronogramaV2CreatePayload
    ) -> dict[str, Any]: ...

    def get_obligaciones_cronograma_by_claves(
        self,
        *,
        id_relacion_generadora: int,
        claves_funcionales: list[str],
    ) -> list[dict[str, Any]]: ...


class GeneratePlanPagoVentaCuotasIgualesSimpleService:
    def __init__(
        self,
        repository: PlanPagoVentaV2Repository,
        uuid_generator=None,
    ) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: GeneratePlanPagoVentaCuotasIgualesSimpleCommand
    ) -> AppResult[dict[str, Any]]:
        validation_error = self._validate(command)
        if validation_error is not None:
            return AppResult.fail(validation_error)

        try:
            with self._transaction():
                return self._execute_in_transaction(command)
        except ValueError as exc:
            return AppResult.fail(str(exc))

    def _execute_in_transaction(
        self, command: GeneratePlanPagoVentaCuotasIgualesSimpleCommand
    ) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta_minima(command.id_venta)
        if venta is None:
            return AppResult.fail("NOT_FOUND_VENTA")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)
        now = datetime.now(UTC)
        moneda = command.moneda.strip().upper()
        periodicidad = command.periodicidad.strip().upper()
        regla_redondeo = command.regla_redondeo.strip().upper()

        plan_vivo = self.repository.get_plan_pago_venta_vivo(command.id_venta)
        if plan_vivo is not None and not self._plan_vivo_compatible(
            plan_vivo=plan_vivo,
            command=command,
            moneda=moneda,
            periodicidad=periodicidad,
            regla_redondeo=regla_redondeo,
        ):
            return AppResult.fail("PLAN_PAGO_VENTA_VIVO_INCOMPATIBLE")

        plan = self.repository.upsert_plan_pago_venta_borrador(
            PlanPagoVentaUpsertPayload(
                id_venta=command.id_venta,
                metodo_plan_pago=METODO_CUOTAS_IGUALES_SIMPLE,
                estado_plan_pago="BORRADOR",
                moneda=moneda,
                monto_total_plan=command.monto_total_plan,
                cantidad_cuotas=command.cantidad_cuotas,
                periodicidad=periodicidad,
                fecha_primer_vencimiento=command.fecha_primer_vencimiento,
                importe_anticipo=None,
                fecha_vencimiento_anticipo=None,
                regla_redondeo=regla_redondeo,
                observaciones=None,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
        )

        relacion = self.repository.get_or_create_relacion_generadora(
            RelacionGeneradoraUpsertPayload(
                tipo_origen=TIPO_ORIGEN_VENTA,
                id_origen=command.id_venta,
                descripcion="Relacion generadora creada desde plan pago venta V2",
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
        )

        clave_generacion = (
            f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:"
            f"{METODO_CUOTAS_IGUALES_SIMPLE}"
        )
        generacion = self.repository.get_or_create_generacion_cronograma(
            GeneracionCronogramaCreatePayload(
                id_relacion_generadora=relacion["id_relacion_generadora"],
                id_plan_pago_venta=plan["id_plan_pago_venta"],
                tipo_generacion=TIPO_GENERACION_PLAN_PAGO_VENTA_V2,
                clave_generacion=clave_generacion,
                estado_generacion="GENERADA",
                fecha_generacion=now,
                observaciones=None,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
        )

        concepto = self.repository.get_concepto_financiero_by_codigo(
            CONCEPTO_CAPITAL_VENTA
        )
        if concepto is None:
            raise ValueError("NOT_FOUND_CONCEPTO:CAPITAL_VENTA")

        comprador = self._resolve_comprador(command.id_venta)
        cuotas = self._build_cuotas(
            monto_total=command.monto_total_plan,
            cantidad_cuotas=command.cantidad_cuotas,
            fecha_primer_vencimiento=command.fecha_primer_vencimiento,
        )
        bloque_cuotas = self.repository.get_or_create_plan_pago_venta_bloque(
            PlanPagoVentaBloqueUpsertPayload(
                id_plan_pago_venta=plan["id_plan_pago_venta"],
                numero_bloque=1,
                tipo_bloque=TIPO_BLOQUE_TRAMO_CUOTAS,
                etiqueta_bloque=ETIQUETA_BLOQUE_CUOTAS_IGUALES,
                clave_bloque=(
                    f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:"
                    "BLOQUE:TRAMO_CUOTAS:1"
                ),
                cantidad_cuotas=command.cantidad_cuotas,
                importe_total_bloque=None,
                importe_cuota=cuotas[0][1],
                fecha_vencimiento=None,
                fecha_primer_vencimiento=command.fecha_primer_vencimiento,
                periodicidad=periodicidad,
                regla_redondeo=regla_redondeo,
                metodo_liquidacion=None,
                tasa_interes_directo_periodica=None,
                cantidad_periodos=None,
                base_calculo_interes=None,
                concepto_financiero_codigo=CONCEPTO_CAPITAL_VENTA,
                observaciones=None,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
        )
        claves = [
            f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:CUOTA:{numero}"
            for numero, _, _ in cuotas
        ]

        obligaciones: list[dict[str, Any]] = []
        for numero, importe, fecha_vencimiento in cuotas:
            clave_funcional = (
                f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:CUOTA:{numero}"
            )
            obligaciones.append(
                self.repository.create_obligacion_cronograma_v2_if_not_exists(
                    ObligacionCronogramaV2CreatePayload(
                        id_relacion_generadora=relacion["id_relacion_generadora"],
                        id_generacion_cronograma_financiero=generacion[
                            "id_generacion_cronograma_financiero"
                        ],
                        id_plan_pago_venta_bloque=bloque_cuotas[
                            "id_plan_pago_venta_bloque"
                        ],
                        numero_obligacion=numero,
                        tipo_item_cronograma=TIPO_ITEM_CUOTA,
                        etiqueta_obligacion=f"Cuota {numero}",
                        clave_funcional_origen=clave_funcional,
                        fecha_emision=fecha_vencimiento,
                        fecha_vencimiento=fecha_vencimiento,
                        importe_total=importe,
                        moneda=moneda,
                        estado_obligacion=ESTADO_OBLIGACION_PROYECTADA,
                        id_concepto_financiero=concepto["id_concepto_financiero"],
                        codigo_concepto_financiero=CONCEPTO_CAPITAL_VENTA,
                        id_persona_obligado=comprador["id_persona"],
                        rol_obligado=ROL_OBLIGADO_COMPRADOR,
                        created_at=now,
                        updated_at=now,
                        id_instalacion_origen=id_instalacion,
                        id_instalacion_ultima_modificacion=id_instalacion,
                        op_id_alta=op_id,
                        op_id_ultima_modificacion=op_id,
                    )
                )
            )

        plan = self.repository.mark_plan_pago_venta_generado(
            id_plan_pago_venta=plan["id_plan_pago_venta"],
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )
        obligaciones = self.repository.get_obligaciones_cronograma_by_claves(
            id_relacion_generadora=relacion["id_relacion_generadora"],
            claves_funcionales=claves,
        )

        return AppResult.ok(
            {
                "id_venta": command.id_venta,
                "plan_pago_venta": plan,
                "generacion_cronograma_financiero": generacion,
                "id_relacion_generadora": relacion["id_relacion_generadora"],
                "obligaciones": obligaciones,
            }
        )

    def _validate(
        self, command: GeneratePlanPagoVentaCuotasIgualesSimpleCommand
    ) -> str | None:
        if command.id_venta <= 0:
            return "INVALID_VENTA"
        if command.monto_total_plan <= 0:
            return "INVALID_MONTO_TOTAL_PLAN"
        if command.cantidad_cuotas <= 0:
            return "INVALID_CANTIDAD_CUOTAS"
        if not command.moneda or not command.moneda.strip():
            return "INVALID_MONEDA"
        if command.periodicidad.strip().upper() != PERIODICIDAD_MENSUAL:
            return "INVALID_PERIODICIDAD"
        if command.regla_redondeo.strip().upper() != REGLA_REDONDEO_ULTIMA_CUOTA:
            return "INVALID_REGLA_REDONDEO"
        return None

    def _resolve_comprador(self, id_venta: int) -> dict[str, Any]:
        compradores = self.repository.get_compradores_financieros_venta(id_venta)
        if not compradores:
            raise ValueError("COMPRADOR_VENTA_NO_RESUELTO")
        personas = {row["id_persona"] for row in compradores}
        if len(personas) != 1 or len(compradores) != 1:
            raise ValueError("COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO")
        return compradores[0]

    def _plan_vivo_compatible(
        self,
        *,
        plan_vivo: dict[str, Any],
        command: GeneratePlanPagoVentaCuotasIgualesSimpleCommand,
        moneda: str,
        periodicidad: str,
        regla_redondeo: str,
    ) -> bool:
        if plan_vivo["metodo_plan_pago"] != METODO_CUOTAS_IGUALES_SIMPLE:
            return False
        if plan_vivo["estado_plan_pago"] not in {"BORRADOR", "GENERADO"}:
            return False
        return (
            Decimal(str(plan_vivo["monto_total_plan"])) == command.monto_total_plan
            and plan_vivo["moneda"] == moneda
            and plan_vivo["cantidad_cuotas"] == command.cantidad_cuotas
            and plan_vivo["fecha_primer_vencimiento"]
            == command.fecha_primer_vencimiento
            and plan_vivo["periodicidad"] == periodicidad
            and plan_vivo["regla_redondeo"] == regla_redondeo
        )

    def _build_cuotas(
        self,
        *,
        monto_total: Decimal,
        cantidad_cuotas: int,
        fecha_primer_vencimiento: date,
    ) -> list[tuple[int, Decimal, date]]:
        return build_cuotas_iguales_mensuales(
            monto_total=monto_total,
            cantidad_cuotas=cantidad_cuotas,
            fecha_primer_vencimiento=fecha_primer_vencimiento,
        )

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()
