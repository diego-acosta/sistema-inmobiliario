from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol

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
from app.application.financiero.services.indexacion_cuota_calculator import (
    BASE_CALCULO_INDEXACION_CAPITAL_INICIAL_BLOQUE,
    ESTADO_INDEXACION_CON_INDICE,
    ESTADO_INDEXACION_PROYECTADA,
    MODO_INDEXACION_POR_COEFICIENTE,
    POLITICA_VALOR_NO_DISPONIBLE_ERROR,
    TIPO_GENERACION_INDEXADA_DEFINITIVA,
    IndexacionCuotaCalculator,
)

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
METODO_LIQUIDACION_SIN_INTERES = "SIN_INTERES"
METODO_LIQUIDACION_INTERES_DIRECTO = "INTERES_DIRECTO"
METODO_LIQUIDACION_INDEXACION = "INDEXACION"
METODOS_LIQUIDACION_VALIDOS = {
    METODO_LIQUIDACION_SIN_INTERES,
    METODO_LIQUIDACION_INTERES_DIRECTO,
    METODO_LIQUIDACION_INDEXACION,
}
BASE_CALCULO_INTERES_CAPITAL_INICIAL_BLOQUE = "CAPITAL_INICIAL_BLOQUE"
ESTADO_PREVIEW_INDEXACION_CON_INDICE = ESTADO_INDEXACION_CON_INDICE
ESTADO_PREVIEW_INDEXACION_PROYECTADA = ESTADO_INDEXACION_PROYECTADA


class IndiceFinancieroPreviewQuery(Protocol):
    def get_valor_publicado_por_id_y_fecha(
        self,
        id_indice_financiero: int,
        fecha_objetivo: date,
    ) -> dict[str, Any] | None: ...


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
    total_con_indexacion: Decimal | None = None
    total_ajuste_indexacion: Decimal | None = None
    cantidad_cuotas_con_indice: int = 0
    cantidad_cuotas_proyectadas_sin_indice: int = 0


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
    estado_preview_indexacion: str | None = None
    id_indice_financiero: int | None = None
    id_indice_financiero_valor: int | None = None
    fecha_valor_indice: Any | None = None
    valor_base_indice: Decimal | None = None
    valor_aplicado_indice: Decimal | None = None
    coeficiente_indexacion: Decimal | None = None
    capital_cuota: Decimal | None = None
    ajuste_indexacion_cuota: Decimal | None = None


class BuildPlanPagoVentaV2PorBloquesPreviewService:
    def __init__(
        self, indice_financiero_query: IndiceFinancieroPreviewQuery | None = None
    ) -> None:
        self.indice_financiero_query = indice_financiero_query
        self.indexacion_cuota_calculator = IndexacionCuotaCalculator(
            indice_financiero_query
        )

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
            self._aplicar_resumen_indexacion(bloques, obligaciones)
        except ValueError as exc:
            return AppResult.fail(str(exc))
        total_calculado = sum(
            (self._bloque_total_capital(bloque.input) for bloque in bloques),
            Decimal("0.00"),
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
        total_ajuste_indexacion = sum(
            (
                obligacion.ajuste_indexacion_cuota or Decimal("0.00")
                for obligacion in obligaciones
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))
        total_con_indexacion = (total_con_interes + total_ajuste_indexacion).quantize(
            Decimal("0.01")
        )
        return AppResult.ok(
            {
                "bloques": bloques,
                "obligaciones": obligaciones,
                "total_calculado": total_calculado,
                "total_con_interes": total_con_interes,
                "total_con_indexacion": total_con_indexacion,
                "total_ajuste_indexacion": total_ajuste_indexacion,
                "diferencia": (command.monto_total_plan - total_calculado).quantize(
                    Decimal("0.01")
                ),
                "redondeos": redondeos,
            }
        )

    def _validate(
        self, command: GeneratePlanPagoVentaV2PorBloquesCommand
    ) -> str | None:
        if command.id_venta is not None and command.id_venta <= 0:
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

        metodo = self._normalize_upper_or_none(bloque.metodo_liquidacion)
        bloque.metodo_liquidacion = metodo
        if metodo is not None and metodo not in METODOS_LIQUIDACION_VALIDOS:
            return "VALIDATION_ERROR"
        if (
            metodo == METODO_LIQUIDACION_INDEXACION
            and tipo_bloque != TIPO_BLOQUE_TRAMO_CUOTAS
        ):
            return "VALIDATION_ERROR"
        if tipo_bloque != TIPO_BLOQUE_TRAMO_CUOTAS and bloque.cuotas_refuerzo:
            return "CUOTA_REFUERZO_NO_COMPATIBLE_CON_TIPO_BLOQUE"

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
            refuerzo_error = self._validate_cuotas_refuerzo_tramo(bloque)
            if refuerzo_error is not None:
                return refuerzo_error
            liquidacion_error = self._validate_metodo_liquidacion_tramo(bloque)
            if liquidacion_error is not None:
                return liquidacion_error
            return None

        return self._validate_pago_unico(bloque)

    def _validate_cuotas_refuerzo_tramo(
        self, bloque: PlanPagoVentaBloqueInput
    ) -> str | None:
        cuotas_refuerzo = bloque.cuotas_refuerzo or []
        if not cuotas_refuerzo:
            return None
        cantidad_cuotas = bloque.cantidad_cuotas or 0
        if len(cuotas_refuerzo) > cantidad_cuotas:
            return "CUOTA_REFUERZO_EXCEDE_CANTIDAD_CUOTAS"
        numeros: set[int] = set()
        for cuota_refuerzo in cuotas_refuerzo:
            if (
                cuota_refuerzo.numero_cuota <= 0
                or cuota_refuerzo.numero_cuota > cantidad_cuotas
            ):
                return "CUOTA_REFUERZO_NUMERO_INVALIDO"
            if cuota_refuerzo.numero_cuota in numeros:
                return "CUOTA_REFUERZO_DUPLICADA"
            numeros.add(cuota_refuerzo.numero_cuota)
            unidades = (
                Decimal("1.00")
                if cuota_refuerzo.unidades_refuerzo is None
                else cuota_refuerzo.unidades_refuerzo
            )
            if unidades <= 0:
                return "CUOTA_REFUERZO_UNIDADES_INVALIDAS"
            if unidades != Decimal("1.00"):
                return "CUOTA_REFUERZO_UNIDADES_NO_SOPORTADAS"
            cuota_refuerzo.unidades_refuerzo = unidades.quantize(Decimal("0.01"))
        return None

    def _validate_metodo_liquidacion_tramo(
        self, bloque: PlanPagoVentaBloqueInput
    ) -> str | None:
        metodo = self._normalize_upper_or_none(bloque.metodo_liquidacion)
        bloque.metodo_liquidacion = metodo
        if not metodo or metodo == METODO_LIQUIDACION_SIN_INTERES:
            return None
        if metodo == METODO_LIQUIDACION_INDEXACION:
            return self._validate_indexacion_tramo(bloque)
        if metodo != METODO_LIQUIDACION_INTERES_DIRECTO:
            return "VALIDATION_ERROR"
        if self._has_indexacion_config(bloque):
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

    def _validate_indexacion_tramo(
        self, bloque: PlanPagoVentaBloqueInput
    ) -> str | None:
        bloque.modo_indexacion = self._normalize_upper_or_none(bloque.modo_indexacion)
        bloque.base_calculo_indexacion = self._normalize_upper_or_none(
            bloque.base_calculo_indexacion
        )
        bloque.tipo_generacion_indexada = self._normalize_upper_or_none(
            bloque.tipo_generacion_indexada
        )
        bloque.politica_valor_no_disponible = self._normalize_upper_or_none(
            bloque.politica_valor_no_disponible
        )
        if self._has_interes_directo_config(bloque):
            return "VALIDATION_ERROR"
        if not self._tramo_usa_capital_total(bloque):
            return "VALIDATION_ERROR"
        if (
            bloque.id_indice_financiero is None
            or bloque.id_indice_financiero <= 0
            or bloque.fecha_base_indice is None
            or bloque.valor_base_indice is None
            or bloque.modo_indexacion is None
            or bloque.base_calculo_indexacion is None
            or bloque.tipo_generacion_indexada is None
            or bloque.politica_valor_no_disponible is None
            or bloque.conserva_capital_original is None
            or bloque.genera_ajuste_por_diferencia is None
        ):
            return "VALIDATION_ERROR"
        if bloque.valor_base_indice <= 0:
            return "VALIDATION_ERROR"
        if bloque.modo_indexacion != MODO_INDEXACION_POR_COEFICIENTE:
            return "VALIDATION_ERROR"
        if (
            bloque.base_calculo_indexacion
            != BASE_CALCULO_INDEXACION_CAPITAL_INICIAL_BLOQUE
        ):
            return "VALIDATION_ERROR"
        if bloque.tipo_generacion_indexada != TIPO_GENERACION_INDEXADA_DEFINITIVA:
            return "VALIDATION_ERROR"
        if bloque.politica_valor_no_disponible != POLITICA_VALOR_NO_DISPONIBLE_ERROR:
            return "VALIDATION_ERROR"
        if bloque.conserva_capital_original is not True:
            return "VALIDATION_ERROR"
        if bloque.genera_ajuste_por_diferencia is not True:
            return "VALIDATION_ERROR"
        return None

    @staticmethod
    def _has_interes_directo_config(bloque: PlanPagoVentaBloqueInput) -> bool:
        return (
            bloque.tasa_interes_directo_periodica is not None
            or bloque.cantidad_periodos is not None
            or bloque.base_calculo_interes is not None
        )

    @staticmethod
    def _has_indexacion_config(bloque: PlanPagoVentaBloqueInput) -> bool:
        return any(
            value is not None
            for value in (
                bloque.id_indice_financiero,
                bloque.fecha_base_indice,
                bloque.valor_base_indice,
                bloque.modo_indexacion,
                bloque.base_calculo_indexacion,
                bloque.tipo_generacion_indexada,
                bloque.politica_valor_no_disponible,
                bloque.conserva_capital_original,
                bloque.genera_ajuste_por_diferencia,
            )
        )

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
            total_con_indexacion = None
            total_ajuste_indexacion = None
            if self._tramo_usa_indexacion(bloque):
                total_con_indexacion = self._bloque_total_capital(bloque)
                total_ajuste_indexacion = Decimal("0.00")
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
                    total_con_indexacion=total_con_indexacion,
                    total_ajuste_indexacion=total_ajuste_indexacion,
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
                    fecha_vencimiento = add_months(
                        bloque.input.fecha_primer_vencimiento, cuota_numero - 1
                    )
                    indexacion = self._preview_indexacion_cuota(
                        bloque.input,
                        capital_cuota=importe,
                        fecha_vencimiento=fecha_vencimiento,
                    )
                    cuota_refuerzo = self._cuota_refuerzo_por_numero(bloque.input).get(
                        cuota_numero
                    )
                    tipo_item = (
                        TIPO_ITEM_REFUERZO
                        if cuota_refuerzo is not None
                        else TIPO_ITEM_CUOTA
                    )
                    etiqueta = (
                        cuota_refuerzo.etiqueta
                        if cuota_refuerzo is not None and cuota_refuerzo.etiqueta
                        else (
                            f"Refuerzo cuota {cuota_numero}"
                            if cuota_refuerzo is not None
                            else f"Cuota {cuota_numero}"
                        )
                    )
                    obligaciones.append(
                        PlanPagoVentaV2ObligacionPreview(
                            bloque=bloque,
                            numero_obligacion=len(obligaciones) + 1,
                            tipo_item_cronograma=tipo_item,
                            etiqueta_obligacion=etiqueta,
                            item_numero=cuota_numero,
                            fecha_vencimiento=fecha_vencimiento,
                            importe_total=indexacion.get("importe_total", importe),
                            concepto_financiero_codigo=bloque.concepto_financiero_codigo,
                            estado_preview_indexacion=indexacion.get(
                                "estado_preview_indexacion"
                            ),
                            id_indice_financiero=indexacion.get("id_indice_financiero"),
                            id_indice_financiero_valor=indexacion.get(
                                "id_indice_financiero_valor"
                            ),
                            fecha_valor_indice=indexacion.get("fecha_valor_indice"),
                            valor_base_indice=indexacion.get("valor_base_indice"),
                            valor_aplicado_indice=indexacion.get(
                                "valor_aplicado_indice"
                            ),
                            coeficiente_indexacion=indexacion.get(
                                "coeficiente_indexacion"
                            ),
                            capital_cuota=indexacion.get("capital_cuota"),
                            ajuste_indexacion_cuota=indexacion.get(
                                "ajuste_indexacion_cuota"
                            ),
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

    @staticmethod
    def _cuota_refuerzo_por_numero(
        bloque: PlanPagoVentaBloqueInput,
    ) -> dict[int, Any]:
        return {
            cuota_refuerzo.numero_cuota: cuota_refuerzo
            for cuota_refuerzo in (bloque.cuotas_refuerzo or [])
        }

    def _aplicar_resumen_indexacion(
        self,
        bloques: list[PlanPagoVentaV2BloquePreview],
        obligaciones: list[PlanPagoVentaV2ObligacionPreview],
    ) -> None:
        for bloque in bloques:
            if not self._tramo_usa_indexacion(bloque.input):
                continue
            obligaciones_bloque = [
                obligacion
                for obligacion in obligaciones
                if obligacion.bloque.numero_bloque == bloque.numero_bloque
            ]
            total_ajuste = sum(
                (
                    obligacion.ajuste_indexacion_cuota or Decimal("0.00")
                    for obligacion in obligaciones_bloque
                ),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))
            bloque.total_ajuste_indexacion = total_ajuste
            bloque.total_con_indexacion = (
                self._bloque_total_capital(bloque.input) + total_ajuste
            ).quantize(Decimal("0.01"))
            bloque.cantidad_cuotas_con_indice = sum(
                1
                for obligacion in obligaciones_bloque
                if obligacion.estado_preview_indexacion
                == ESTADO_PREVIEW_INDEXACION_CON_INDICE
            )
            bloque.cantidad_cuotas_proyectadas_sin_indice = sum(
                1
                for obligacion in obligaciones_bloque
                if obligacion.estado_preview_indexacion
                == ESTADO_PREVIEW_INDEXACION_PROYECTADA
            )

    def _preview_indexacion_cuota(
        self,
        bloque: PlanPagoVentaBloqueInput,
        *,
        capital_cuota: Decimal,
        fecha_vencimiento: date,
    ) -> dict[str, Any]:
        if not self._tramo_usa_indexacion(bloque):
            return {"importe_total": capital_cuota}

        resultado = self.indexacion_cuota_calculator.calcular(
            id_indice_financiero=bloque.id_indice_financiero or 0,
            valor_base_indice=bloque.valor_base_indice or Decimal("0.00"),
            fecha_objetivo=fecha_vencimiento,
            capital_cuota=capital_cuota,
            modo_indexacion=bloque.modo_indexacion or "",
            base_calculo_indexacion=bloque.base_calculo_indexacion or "",
            tipo_generacion_indexada=bloque.tipo_generacion_indexada or "",
            politica_valor_no_disponible=bloque.politica_valor_no_disponible or "",
        )

        return {
            "estado_preview_indexacion": resultado.estado_indexacion,
            "id_indice_financiero": resultado.id_indice_financiero,
            "id_indice_financiero_valor": resultado.id_indice_financiero_valor,
            "fecha_valor_indice": resultado.fecha_valor_indice,
            "valor_base_indice": resultado.valor_base_indice,
            "valor_aplicado_indice": resultado.valor_aplicado_indice,
            "coeficiente_indexacion": resultado.coeficiente_indexacion,
            "capital_cuota": resultado.capital_cuota,
            "ajuste_indexacion_cuota": resultado.ajuste_indexacion_cuota,
            "importe_total": resultado.importe_total,
        }

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
                capital_total = (
                    bloque.importe_total_bloque or Decimal("0.00")
                ).quantize(Decimal("0.01"))
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
            return (
                (bloque.importe_cuota or Decimal("0.00"))
                * Decimal(bloque.cantidad_cuotas or 0)
            ).quantize(Decimal("0.01"))
        return (bloque.importe_total_bloque or Decimal("0.00")).quantize(
            Decimal("0.01")
        )

    def _tramo_usa_interes_directo(self, bloque: PlanPagoVentaBloqueInput) -> bool:
        return (
            self._normalize_upper_or_none(bloque.metodo_liquidacion)
            == METODO_LIQUIDACION_INTERES_DIRECTO
        )

    def _tramo_usa_indexacion(self, bloque: PlanPagoVentaBloqueInput) -> bool:
        return (
            self._normalize_upper_or_none(bloque.metodo_liquidacion)
            == METODO_LIQUIDACION_INDEXACION
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
