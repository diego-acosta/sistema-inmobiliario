from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    GeneratePlanPagoVentaV2PorBloquesCommand,
    PlanPagoVentaBloqueInput,
)
from app.application.comercial.services.generate_plan_pago_venta_anticipo_mas_cuotas_iguales_service import (
    CONCEPTO_ANTICIPO_VENTA,
)
from app.application.comercial.services.generate_plan_pago_venta_cuotas_iguales_simple_service import (
    CONCEPTO_CAPITAL_VENTA,
    PERIODICIDAD_MENSUAL,
    REGLA_REDONDEO_ULTIMA_CUOTA,
    TIPO_ITEM_CUOTA,
    add_months,
)
from app.application.common.results import AppResult

METODO_PLAN_POR_BLOQUES = "PLAN_POR_BLOQUES"
TIPO_PAGO_CONTADO = "CONTADO"
TIPO_PAGO_FINANCIADO = "FINANCIADO"
TIPO_BLOQUE_CONTADO = "CONTADO"
TIPO_BLOQUE_ANTICIPO = "ANTICIPO"
TIPO_BLOQUE_TRAMO_CUOTAS = "TRAMO_CUOTAS"
TIPO_BLOQUE_REFUERZO = "REFUERZO"
TIPO_BLOQUE_SALDO = "SALDO"
TIPO_ITEM_ANTICIPO = "ANTICIPO"
TIPO_ITEM_REFUERZO = "REFUERZO"
TIPO_ITEM_SALDO = "SALDO"
METODO_LIQUIDACION_INTERES_DIRECTO = "INTERES_DIRECTO"
BASE_CALCULO_INTERES_CAPITAL_INICIAL_BLOQUE = "CAPITAL_INICIAL_BLOQUE"


@dataclass(slots=True)
class PlanPagoVentaV2BloquePreview:
    input: PlanPagoVentaBloqueInput
    numero_bloque: int
    tipo_bloque: str
    etiqueta_bloque: str
    clave_bloque: str
    ordinal_tipo: int
    total_bloque: Decimal
    concepto_financiero_codigo: str
    importe_total_bloque: Decimal | None
    importe_cuota: Decimal | None
    redondeo_ajuste: Decimal


@dataclass(slots=True)
class PlanPagoVentaV2ObligacionPreview:
    bloque: PlanPagoVentaV2BloquePreview
    numero_obligacion: int
    tipo_item_cronograma: str
    etiqueta_obligacion: str
    item_numero: int
    fecha_vencimiento: Any
    importe_total: Decimal
    concepto_financiero_codigo: str


class BuildPlanPagoVentaV2PorBloquesPreviewService:
    def execute(
        self,
        command: GeneratePlanPagoVentaV2PorBloquesCommand,
        *,
        id_plan_pago_venta: int = 0,
    ) -> AppResult[dict[str, Any]]:
        validation_error = self._validate(command)
        if validation_error is not None:
            return AppResult.fail(validation_error)

        try:
            bloques = self._prepare_bloques(
                command, id_plan_pago_venta=id_plan_pago_venta
            )
            obligaciones = self._build_obligaciones(bloques)
        except ValueError as exc:
            return AppResult.fail(str(exc))
        total_calculado = sum(
            (self._bloque_total_capital(bloque.input) for bloque in bloques), Decimal("0.00")
        ).quantize(Decimal("0.01"))
        total_con_interes = sum(
            (bloque.total_bloque for bloque in bloques), Decimal("0.00")
        ).quantize(Decimal("0.01"))
        redondeos = [
            {
                "numero_bloque": bloque.numero_bloque,
                "tipo_bloque": bloque.tipo_bloque,
                "ajuste_ultima_cuota": bloque.redondeo_ajuste,
            }
            for bloque in bloques
            if bloque.redondeo_ajuste != Decimal("0.00")
        ]
        return AppResult.ok(
            {
                "bloques": bloques,
                "obligaciones": obligaciones,
                "total_calculado": total_calculado,
                "total_con_interes": total_con_interes,
                "diferencia": (command.monto_total_plan - total_calculado).quantize(
                    Decimal("0.01")
                ),
                "redondeos": redondeos,
            }
        )

    def _validate(
        self, command: GeneratePlanPagoVentaV2PorBloquesCommand
    ) -> str | None:
        if command.id_venta <= 0:
            return "INVALID_VENTA"
        if command.monto_total_plan <= 0:
            return "INVALID_MONTO_TOTAL_PLAN"
        if not self._has_cent_precision(command.monto_total_plan):
            return "INVALID_MONTO_TOTAL_PLAN"
        if not command.moneda or not command.moneda.strip():
            return "INVALID_MONEDA"
        tipo_pago = command.tipo_pago.strip().upper() if command.tipo_pago else ""
        if tipo_pago not in {TIPO_PAGO_CONTADO, TIPO_PAGO_FINANCIADO}:
            return "INVALID_TIPO_PAGO"
        if not command.bloques:
            return "INVALID_BLOQUES"

        tipos = [bloque.tipo_bloque.strip().upper() for bloque in command.bloques]
        if tipo_pago == TIPO_PAGO_CONTADO:
            if len(command.bloques) != 1 or tipos[0] != TIPO_BLOQUE_CONTADO:
                return "CONTADO_BLOQUES_INVALIDOS"
        if tipo_pago == TIPO_PAGO_FINANCIADO:
            if TIPO_BLOQUE_CONTADO in tipos:
                return "FINANCIADO_NO_PERMITE_CONTADO"

        total = Decimal("0.00")
        for bloque in command.bloques:
            error = self._validate_bloque(bloque, tipo_pago=tipo_pago)
            if error is not None:
                return error
            total += self._bloque_total_capital(bloque)

        if total.quantize(Decimal("0.01")) != command.monto_total_plan:
            return "SUMA_BLOQUES_INVALIDA"
        return None

    def _validate_bloque(
        self, bloque: PlanPagoVentaBloqueInput, *, tipo_pago: str
    ) -> str | None:
        tipo_bloque = bloque.tipo_bloque.strip().upper() if bloque.tipo_bloque else ""
        if tipo_bloque not in {
            TIPO_BLOQUE_CONTADO,
            TIPO_BLOQUE_ANTICIPO,
            TIPO_BLOQUE_TRAMO_CUOTAS,
            TIPO_BLOQUE_REFUERZO,
            TIPO_BLOQUE_SALDO,
        }:
            return "BLOQUE_INVALIDO"

        if tipo_bloque == TIPO_BLOQUE_CONTADO:
            if tipo_pago != TIPO_PAGO_CONTADO:
                return "BLOQUE_INVALIDO"
            return self._validate_pago_unico(bloque)

        if tipo_bloque == TIPO_BLOQUE_ANTICIPO:
            if tipo_pago != TIPO_PAGO_FINANCIADO:
                return "BLOQUE_INVALIDO"
            return self._validate_pago_unico(bloque)

        if tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS:
            if (bloque.cantidad_cuotas or 0) <= 0:
                return "BLOQUE_INVALIDO"
            if self._tramo_usa_capital_total(bloque):
                if not self._has_cent_precision(bloque.importe_total_bloque):
                    return "BLOQUE_INVALIDO"
            elif bloque.importe_cuota is None or bloque.importe_cuota <= 0:
                return "BLOQUE_INVALIDO"
            elif not self._has_cent_precision(bloque.importe_cuota):
                return "BLOQUE_INVALIDO"
            if bloque.fecha_primer_vencimiento is None:
                return "BLOQUE_INVALIDO"
            periodicidad = (bloque.periodicidad or "").strip().upper()
            if periodicidad != PERIODICIDAD_MENSUAL:
                return "INVALID_PERIODICIDAD"
            regla_redondeo = (
                (bloque.regla_redondeo or REGLA_REDONDEO_ULTIMA_CUOTA).strip().upper()
            )
            if regla_redondeo != REGLA_REDONDEO_ULTIMA_CUOTA:
                return "INVALID_REGLA_REDONDEO"
            liquidacion_error = self._validate_metodo_liquidacion_tramo(bloque)
            if liquidacion_error is not None:
                return liquidacion_error
            return None

        return self._validate_pago_unico(bloque)

    def _validate_metodo_liquidacion_tramo(
        self, bloque: PlanPagoVentaBloqueInput
    ) -> str | None:
        metodo = self._normalize_upper_or_none(bloque.metodo_liquidacion)
        bloque.metodo_liquidacion = metodo
        if not metodo:
            return None
        if metodo != METODO_LIQUIDACION_INTERES_DIRECTO:
            return "VALIDATION_ERROR"
        base_calculo = self._normalize_upper_or_none(bloque.base_calculo_interes)
        bloque.base_calculo_interes = base_calculo
        if (
            bloque.tasa_interes_directo_periodica is None
            or bloque.cantidad_periodos is None
            or not base_calculo
        ):
            return "VALIDATION_ERROR"
        if base_calculo != BASE_CALCULO_INTERES_CAPITAL_INICIAL_BLOQUE:
            return "VALIDATION_ERROR"
        return None

    @staticmethod
    def _normalize_upper_or_none(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    def _validate_pago_unico(self, bloque: PlanPagoVentaBloqueInput) -> str | None:
        if bloque.importe_total_bloque is None or bloque.importe_total_bloque <= 0:
            return "BLOQUE_INVALIDO"
        if not self._has_cent_precision(bloque.importe_total_bloque):
            return "BLOQUE_INVALIDO"
        if bloque.fecha_vencimiento is None:
            return "BLOQUE_INVALIDO"
        return None

    def _prepare_bloques(
        self,
        command: GeneratePlanPagoVentaV2PorBloquesCommand,
        *,
        id_plan_pago_venta: int,
    ) -> list[PlanPagoVentaV2BloquePreview]:
        counts: dict[str, int] = {}
        prepared: list[PlanPagoVentaV2BloquePreview] = []
        for index, bloque in enumerate(command.bloques, start=1):
            tipo_bloque = bloque.tipo_bloque.strip().upper()
            counts[tipo_bloque] = counts.get(tipo_bloque, 0) + 1
            ordinal_tipo = counts[tipo_bloque]
            clave_bloque = (
                f"PLAN_PAGO_VENTA:{id_plan_pago_venta}:"
                f"BLOQUE:{tipo_bloque}:{ordinal_tipo}"
            )
            total_bloque = self._bloque_total(bloque)
            importe_cuota = (
                self._cuota_base_por_total(bloque)
                if tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
                and self._tramo_usa_capital_total(bloque)
                else bloque.importe_cuota
            )
            redondeo_ajuste = Decimal("0.00")
            if (
                tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
                and self._tramo_usa_capital_total(bloque)
            ):
                cuotas = self._importes_cuotas_por_total(bloque)
                redondeo_ajuste = (cuotas[-1] - cuotas[0]).quantize(Decimal("0.01"))
            prepared.append(
                PlanPagoVentaV2BloquePreview(
                    input=bloque,
                    numero_bloque=index,
                    tipo_bloque=tipo_bloque,
                    etiqueta_bloque=bloque.etiqueta_bloque
                    or self._default_etiqueta_bloque(tipo_bloque),
                    clave_bloque=clave_bloque,
                    ordinal_tipo=ordinal_tipo,
                    total_bloque=total_bloque,
                    concepto_financiero_codigo=self._concepto_codigo(tipo_bloque),
                    importe_total_bloque=(
                        total_bloque
                        if tipo_bloque != TIPO_BLOQUE_TRAMO_CUOTAS
                        or self._tramo_usa_capital_total(bloque)
                        else None
                    ),
                    importe_cuota=importe_cuota,
                    redondeo_ajuste=redondeo_ajuste,
                )
            )
        return prepared

    def _build_obligaciones(
        self, bloques: list[PlanPagoVentaV2BloquePreview]
    ) -> list[PlanPagoVentaV2ObligacionPreview]:
        obligaciones: list[PlanPagoVentaV2ObligacionPreview] = []
        for bloque in bloques:
            if bloque.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS:
                importes = self._importes_cuotas(bloque.input)
                for cuota_numero, importe in enumerate(importes, start=1):
                    obligaciones.append(
                        PlanPagoVentaV2ObligacionPreview(
                            bloque=bloque,
                            numero_obligacion=len(obligaciones) + 1,
                            tipo_item_cronograma=TIPO_ITEM_CUOTA,
                            etiqueta_obligacion=f"Cuota {cuota_numero}",
                            item_numero=cuota_numero,
                            fecha_vencimiento=add_months(
                                bloque.input.fecha_primer_vencimiento, cuota_numero - 1
                            ),
                            importe_total=importe,
                            concepto_financiero_codigo=bloque.concepto_financiero_codigo,
                        )
                    )
                continue

            obligaciones.append(
                PlanPagoVentaV2ObligacionPreview(
                    bloque=bloque,
                    numero_obligacion=len(obligaciones) + 1,
                    tipo_item_cronograma=self._tipo_item_cronograma(bloque.tipo_bloque),
                    etiqueta_obligacion=bloque.etiqueta_bloque,
                    item_numero=1,
                    fecha_vencimiento=bloque.input.fecha_vencimiento,
                    importe_total=bloque.input.importe_total_bloque,
                    concepto_financiero_codigo=bloque.concepto_financiero_codigo,
                )
            )
        return obligaciones

    def _importes_cuotas(self, bloque: PlanPagoVentaBloqueInput) -> list[Decimal]:
        if self._tramo_usa_interes_directo(bloque):
            return self._importes_cuotas_interes_directo(bloque)
        if self._tramo_usa_capital_total(bloque):
            return self._importes_cuotas_por_total(bloque)
        return [
            (bloque.importe_cuota or Decimal("0.00")).quantize(Decimal("0.01"))
            for _ in range(bloque.cantidad_cuotas or 0)
        ]

    def _importes_cuotas_por_total(
        self, bloque: PlanPagoVentaBloqueInput
    ) -> list[Decimal]:
        total = bloque.importe_total_bloque or Decimal("0.00")
        cantidad = bloque.cantidad_cuotas or 0
        cuota_base = self._cuota_base_por_total(bloque)
        cuotas = [cuota_base for _ in range(max(cantidad - 1, 0))]
        ultima = (total - sum(cuotas, Decimal("0.00"))).quantize(Decimal("0.01"))
        if ultima <= 0:
            raise ValueError("BLOQUE_INVALIDO")
        cuotas.append(ultima)
        return cuotas

    def _importes_cuotas_interes_directo(
        self, bloque: PlanPagoVentaBloqueInput
    ) -> list[Decimal]:
        capital_total = (bloque.importe_total_bloque or Decimal("0.00")).quantize(
            Decimal("0.01")
        )
        interes_total = self._interes_total_directo(bloque)
        total = (capital_total + interes_total).quantize(Decimal("0.01"))
        cantidad = bloque.cantidad_cuotas or 0
        cuota_base = (total / Decimal(cantidad or 1)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        cuotas = [cuota_base for _ in range(max(cantidad - 1, 0))]
        ultima = (total - sum(cuotas, Decimal("0.00"))).quantize(Decimal("0.01"))
        if ultima <= 0:
            raise ValueError("BLOQUE_INVALIDO")
        cuotas.append(ultima)
        return cuotas

    @staticmethod
    def _cuota_base_por_total(bloque: PlanPagoVentaBloqueInput) -> Decimal:
        total = bloque.importe_total_bloque or Decimal("0.00")
        return (total / Decimal(bloque.cantidad_cuotas or 1)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _tramo_usa_capital_total(bloque: PlanPagoVentaBloqueInput) -> bool:
        return (
            bloque.importe_total_bloque is not None and bloque.importe_total_bloque > 0
        )

    @staticmethod
    def _has_cent_precision(value: Decimal | None) -> bool:
        return value is not None and value == value.quantize(Decimal("0.01"))

    def _bloque_total(self, bloque: PlanPagoVentaBloqueInput) -> Decimal:
        tipo_bloque = bloque.tipo_bloque.strip().upper()
        if tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS:
            if self._tramo_usa_interes_directo(bloque):
                capital_total = (bloque.importe_total_bloque or Decimal("0.00")).quantize(
                    Decimal("0.01")
                )
                return (capital_total + self._interes_total_directo(bloque)).quantize(
                    Decimal("0.01")
                )
            if self._tramo_usa_capital_total(bloque):
                return (bloque.importe_total_bloque or Decimal("0.00")).quantize(
                    Decimal("0.01")
                )
            return (bloque.importe_cuota or Decimal("0.00")) * Decimal(
                bloque.cantidad_cuotas or 0
            )
        return bloque.importe_total_bloque or Decimal("0.00")

    def _bloque_total_capital(self, bloque: PlanPagoVentaBloqueInput) -> Decimal:
        tipo_bloque = bloque.tipo_bloque.strip().upper()
        if tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS:
            if self._tramo_usa_capital_total(bloque):
                return (bloque.importe_total_bloque or Decimal("0.00")).quantize(
                    Decimal("0.01")
                )
            return ((bloque.importe_cuota or Decimal("0.00")) * Decimal(
                bloque.cantidad_cuotas or 0
            )).quantize(Decimal("0.01"))
        return (bloque.importe_total_bloque or Decimal("0.00")).quantize(Decimal("0.01"))

    def _tramo_usa_interes_directo(self, bloque: PlanPagoVentaBloqueInput) -> bool:
        return (
            self._normalize_upper_or_none(bloque.metodo_liquidacion)
            == METODO_LIQUIDACION_INTERES_DIRECTO
        )

    def _interes_total_directo(self, bloque: PlanPagoVentaBloqueInput) -> Decimal:
        capital_total = bloque.importe_total_bloque or Decimal("0.00")
        tasa = bloque.tasa_interes_directo_periodica or Decimal("0.00")
        periodos = Decimal(bloque.cantidad_periodos or 0)
        return (capital_total * tasa * periodos).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _default_etiqueta_bloque(tipo_bloque: str) -> str:
        return {
            TIPO_BLOQUE_CONTADO: "Contado",
            TIPO_BLOQUE_ANTICIPO: "Anticipo",
            TIPO_BLOQUE_TRAMO_CUOTAS: "Cuotas",
            TIPO_BLOQUE_REFUERZO: "Refuerzo",
            TIPO_BLOQUE_SALDO: "Saldo",
        }[tipo_bloque]

    @staticmethod
    def _concepto_codigo(tipo_bloque: str) -> str:
        if tipo_bloque == TIPO_BLOQUE_ANTICIPO:
            return CONCEPTO_ANTICIPO_VENTA
        return CONCEPTO_CAPITAL_VENTA

    @staticmethod
    def _tipo_item_cronograma(tipo_bloque: str) -> str:
        if tipo_bloque == TIPO_BLOQUE_CONTADO:
            return TIPO_ITEM_SALDO
        if tipo_bloque == TIPO_BLOQUE_ANTICIPO:
            return TIPO_ITEM_ANTICIPO
        if tipo_bloque == TIPO_BLOQUE_REFUERZO:
            return TIPO_ITEM_REFUERZO
        if tipo_bloque == TIPO_BLOQUE_SALDO:
            return TIPO_ITEM_SALDO
        raise ValueError("BLOQUE_INVALIDO")
