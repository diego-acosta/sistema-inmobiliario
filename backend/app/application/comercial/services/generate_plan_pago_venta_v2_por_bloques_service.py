from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    GeneratePlanPagoVentaV2PorBloquesCommand,
)
from app.application.comercial.services.build_plan_pago_venta_v2_por_bloques_preview_service import (
    ESTADO_PREVIEW_INDEXACION_CON_INDICE,
    ESTADO_PREVIEW_INDEXACION_PROYECTADA,
    METODO_LIQUIDACION_INDEXACION,
    METODO_LIQUIDACION_INTERES_DIRECTO,
    BuildPlanPagoVentaV2PorBloquesPreviewService,
    METODO_PLAN_POR_BLOQUES,
    TIPO_BLOQUE_ANTICIPO,
    TIPO_BLOQUE_TRAMO_CUOTAS,
    PlanPagoVentaV2BloquePreview,
    PlanPagoVentaV2ObligacionPreview,
)
from app.application.comercial.services.generate_plan_pago_venta_cuotas_iguales_simple_service import (
    ESTADO_OBLIGACION_PROYECTADA,
    GeneracionCronogramaCreatePayload,
    ObligacionFinancieraIndexacionUpsertPayload,
    ObligacionCronogramaV2CreatePayload,
    ObligadoCronogramaV2CreatePayload,
    PERIODICIDAD_MENSUAL,
    PlanPagoVentaBloqueIndexacionUpsertPayload,
    PlanPagoVentaBloqueUpsertPayload,
    PlanPagoVentaUpsertPayload,
    PlanPagoVentaV2Repository,
    REGLA_REDONDEO_ULTIMA_CUOTA,
    ROL_OBLIGADO_COMPRADOR,
    RelacionGeneradoraUpsertPayload,
    TIPO_GENERACION_PLAN_PAGO_VENTA_V2,
    TIPO_ORIGEN_VENTA,
)
from app.application.common.results import AppResult

CONCEPTO_INTERES_FINANCIERO = "INTERES_FINANCIERO"
CONCEPTO_AJUSTE_INDEXACION = "AJUSTE_INDEXACION"
ERROR_OBLIGACION_INDEXACION_INCOMPATIBLE = (
    "PLAN_PAGO_VENTA_OBLIGACION_INDEXACION_INCOMPATIBLE"
)
ERROR_INDEXACION_AJUSTE_NEGATIVO = "INDEXACION_AJUSTE_NEGATIVO_NO_SOPORTADO"
PORCENTAJE_TOTAL_COMPRADORES = Decimal("100.00")


class GeneratePlanPagoVentaV2PorBloquesService:
    def __init__(
        self,
        repository: PlanPagoVentaV2Repository,
        uuid_generator=None,
        preview_service: BuildPlanPagoVentaV2PorBloquesPreviewService | None = None,
    ) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4
        self.preview_service = (
            preview_service
            or BuildPlanPagoVentaV2PorBloquesPreviewService(
                indice_financiero_query=repository
            )
        )

    def execute(
        self, command: GeneratePlanPagoVentaV2PorBloquesCommand
    ) -> AppResult[dict[str, Any]]:
        preview_without_plan = self.preview_service.execute(command)
        if not preview_without_plan.success:
            return AppResult.fail(preview_without_plan.errors[0])
        if self._has_ajuste_indexacion_negativo(
            preview_without_plan.data["obligaciones"]
        ):
            return AppResult.fail(ERROR_INDEXACION_AJUSTE_NEGATIVO)
        try:
            with self._transaction():
                return self._execute_in_transaction(
                    command, preview_without_plan.data["bloques"]
                )
        except ValueError as exc:
            return AppResult.fail(str(exc))

    def execute_in_existing_transaction(
        self, command: GeneratePlanPagoVentaV2PorBloquesCommand
    ) -> AppResult[dict[str, Any]]:
        preview_without_plan = self.preview_service.execute(command)
        if not preview_without_plan.success:
            return AppResult.fail(preview_without_plan.errors[0])
        if self._has_ajuste_indexacion_negativo(
            preview_without_plan.data["obligaciones"]
        ):
            return AppResult.fail(ERROR_INDEXACION_AJUSTE_NEGATIVO)
        try:
            return self._execute_in_transaction(
                command,
                preview_without_plan.data["bloques"],
            )
        except ValueError as exc:
            return AppResult.fail(str(exc))

    def _execute_in_transaction(
        self,
        command: GeneratePlanPagoVentaV2PorBloquesCommand,
        prepared_without_plan: list[PlanPagoVentaV2BloquePreview],
    ) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta_minima(command.id_venta)
        if venta is None:
            return AppResult.fail("NOT_FOUND_VENTA")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)
        now = datetime.now(UTC)
        tipo_pago = command.tipo_pago.strip().upper()
        moneda = command.moneda.strip().upper()
        plan_vivo = self.repository.get_plan_pago_venta_vivo(command.id_venta)
        if plan_vivo is not None and not self._plan_vivo_compatible(
            plan_vivo=plan_vivo,
            command=command,
            tipo_pago=tipo_pago,
            moneda=moneda,
        ):
            return AppResult.fail("PLAN_PAGO_VENTA_VIVO_INCOMPATIBLE")

        total_cuotas = sum(
            bloque.input.cantidad_cuotas or 0
            for bloque in prepared_without_plan
            if bloque.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
        )
        primer_tramo = next(
            (
                bloque
                for bloque in prepared_without_plan
                if bloque.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
            ),
            None,
        )
        anticipo = next(
            (
                bloque
                for bloque in prepared_without_plan
                if bloque.tipo_bloque == TIPO_BLOQUE_ANTICIPO
            ),
            None,
        )

        plan = self.repository.upsert_plan_pago_venta_borrador(
            PlanPagoVentaUpsertPayload(
                id_venta=command.id_venta,
                metodo_plan_pago=METODO_PLAN_POR_BLOQUES,
                estado_plan_pago="BORRADOR",
                moneda=moneda,
                monto_total_plan=command.monto_total_plan,
                cantidad_cuotas=total_cuotas or None,
                periodicidad=PERIODICIDAD_MENSUAL if total_cuotas else None,
                fecha_primer_vencimiento=(
                    primer_tramo.input.fecha_primer_vencimiento
                    if primer_tramo is not None
                    else None
                ),
                importe_anticipo=(
                    anticipo.input.importe_total_bloque
                    if anticipo is not None
                    else None
                ),
                fecha_vencimiento_anticipo=(
                    anticipo.input.fecha_vencimiento if anticipo is not None else None
                ),
                regla_redondeo=REGLA_REDONDEO_ULTIMA_CUOTA if total_cuotas else None,
                observaciones=command.observaciones,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
        )

        preview = self.preview_service.execute(
            command, id_plan_pago_venta=plan["id_plan_pago_venta"]
        )
        if not preview.success:
            return AppResult.fail(preview.errors[0])
        if self._has_ajuste_indexacion_negativo(preview.data["obligaciones"]):
            raise ValueError(ERROR_INDEXACION_AJUSTE_NEGATIVO)
        prepared_bloques = preview.data["bloques"]
        obligaciones_preview = preview.data["obligaciones"]
        bloques = [
            self.repository.get_or_create_plan_pago_venta_bloque(
                self._build_bloque_payload(
                    bloque=bloque,
                    id_plan_pago_venta=plan["id_plan_pago_venta"],
                    now=now,
                    id_instalacion=id_instalacion,
                    op_id=op_id,
                )
            )
            for bloque in prepared_bloques
        ]
        bloques_indexacion_by_numero = self._persist_indexacion_bloques(
            prepared_bloques=prepared_bloques,
            bloques=bloques,
            now=now,
            id_instalacion=id_instalacion,
            op_id=op_id,
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
            f"{METODO_PLAN_POR_BLOQUES}"
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

        conceptos = self._resolve_conceptos(prepared_bloques)
        compradores = self._resolve_compradores(command.id_venta)

        bloques_by_numero = {
            prepared.numero_bloque: bloque
            for prepared, bloque in zip(prepared_bloques, bloques, strict=True)
        }
        clave_funcionales: list[str] = []
        for obligacion_preview in obligaciones_preview:
            bloque = bloques_by_numero[obligacion_preview.bloque.numero_bloque]
            payload = self._obligacion_payload(
                obligacion_preview=obligacion_preview,
                bloque=bloque,
                id_relacion_generadora=relacion["id_relacion_generadora"],
                id_generacion_cronograma_financiero=generacion[
                    "id_generacion_cronograma_financiero"
                ],
                concepto=conceptos[obligacion_preview.concepto_financiero_codigo],
                compradores=compradores,
                moneda=moneda,
                now=now,
                id_instalacion=id_instalacion,
                op_id=op_id,
                conceptos=conceptos,
            )
            clave_funcionales.append(payload.clave_funcional_origen)
            obligacion = self.repository.create_obligacion_cronograma_v2_if_not_exists(
                payload
            )
            self._persist_indexacion_obligacion(
                obligacion_preview=obligacion_preview,
                obligacion=obligacion,
                bloque_indexacion=bloques_indexacion_by_numero.get(
                    obligacion_preview.bloque.numero_bloque
                ),
                now=now,
                id_instalacion=id_instalacion,
                op_id=op_id,
            )

        plan = self.repository.mark_plan_pago_venta_generado(
            id_plan_pago_venta=plan["id_plan_pago_venta"],
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )
        obligaciones = self.repository.get_obligaciones_cronograma_by_claves(
            id_relacion_generadora=relacion["id_relacion_generadora"],
            claves_funcionales=clave_funcionales,
        )

        return AppResult.ok(
            {
                "id_venta": command.id_venta,
                "id_relacion_generadora": relacion["id_relacion_generadora"],
                "plan_pago_venta": plan,
                "bloques": bloques,
                "generacion_cronograma_financiero": generacion,
                "obligaciones": obligaciones,
            }
        )

    def _build_bloque_payload(
        self,
        *,
        bloque: PlanPagoVentaV2BloquePreview,
        id_plan_pago_venta: int,
        now: datetime,
        id_instalacion: int | None,
        op_id: Any,
    ) -> PlanPagoVentaBloqueUpsertPayload:
        input_bloque = bloque.input
        periodicidad = (
            PERIODICIDAD_MENSUAL
            if bloque.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
            else None
        )
        regla_redondeo = (
            REGLA_REDONDEO_ULTIMA_CUOTA
            if bloque.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
            else None
        )
        return PlanPagoVentaBloqueUpsertPayload(
            id_plan_pago_venta=id_plan_pago_venta,
            numero_bloque=bloque.numero_bloque,
            tipo_bloque=bloque.tipo_bloque,
            etiqueta_bloque=bloque.etiqueta_bloque,
            clave_bloque=bloque.clave_bloque,
            cantidad_cuotas=input_bloque.cantidad_cuotas,
            importe_total_bloque=bloque.importe_total_bloque,
            importe_cuota=bloque.importe_cuota,
            fecha_vencimiento=input_bloque.fecha_vencimiento,
            fecha_primer_vencimiento=input_bloque.fecha_primer_vencimiento,
            periodicidad=periodicidad,
            regla_redondeo=regla_redondeo,
            metodo_liquidacion=input_bloque.metodo_liquidacion,
            tasa_interes_directo_periodica=input_bloque.tasa_interes_directo_periodica,
            cantidad_periodos=input_bloque.cantidad_periodos,
            base_calculo_interes=input_bloque.base_calculo_interes,
            concepto_financiero_codigo=bloque.concepto_financiero_codigo,
            observaciones=input_bloque.observaciones,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

    @staticmethod
    def _has_ajuste_indexacion_negativo(
        obligaciones: list[PlanPagoVentaV2ObligacionPreview],
    ) -> bool:
        return any(
            obligacion.ajuste_indexacion_cuota is not None
            and obligacion.ajuste_indexacion_cuota < Decimal("0.00")
            for obligacion in obligaciones
        )

    def _persist_indexacion_bloques(
        self,
        *,
        prepared_bloques: list[PlanPagoVentaV2BloquePreview],
        bloques: list[dict[str, Any]],
        now: datetime,
        id_instalacion: int | None,
        op_id: Any,
    ) -> dict[int, dict[str, Any]]:
        indexacion_by_numero: dict[int, dict[str, Any]] = {}
        for prepared, bloque in zip(prepared_bloques, bloques, strict=True):
            if not self._bloque_usa_indexacion(prepared):
                continue
            input_bloque = prepared.input
            if (
                self.repository.get_indice_financiero_activo(
                    input_bloque.id_indice_financiero or 0
                )
                is None
            ):
                raise ValueError("NOT_FOUND_INDICE_FINANCIERO")
            indexacion_by_numero[prepared.numero_bloque] = (
                self.repository.get_or_create_plan_pago_venta_bloque_indexacion(
                    PlanPagoVentaBloqueIndexacionUpsertPayload(
                        id_plan_pago_venta_bloque=bloque["id_plan_pago_venta_bloque"],
                        id_indice_financiero=input_bloque.id_indice_financiero or 0,
                        fecha_base_indice=input_bloque.fecha_base_indice,
                        valor_base_indice=input_bloque.valor_base_indice,
                        modo_indexacion=input_bloque.modo_indexacion,
                        base_calculo_indexacion=input_bloque.base_calculo_indexacion,
                        tipo_generacion_indexada=input_bloque.tipo_generacion_indexada,
                        politica_valor_no_disponible=input_bloque.politica_valor_no_disponible,
                        conserva_capital_original=bool(
                            input_bloque.conserva_capital_original
                        ),
                        genera_ajuste_por_diferencia=bool(
                            input_bloque.genera_ajuste_por_diferencia
                        ),
                        observaciones=input_bloque.observaciones,
                        created_at=now,
                        updated_at=now,
                        id_instalacion_origen=id_instalacion,
                        id_instalacion_ultima_modificacion=id_instalacion,
                        op_id_alta=op_id,
                        op_id_ultima_modificacion=op_id,
                    )
                )
            )
        return indexacion_by_numero

    def _persist_indexacion_obligacion(
        self,
        *,
        obligacion_preview: PlanPagoVentaV2ObligacionPreview,
        obligacion: dict[str, Any],
        bloque_indexacion: dict[str, Any] | None,
        now: datetime,
        id_instalacion: int | None,
        op_id: Any,
    ) -> None:
        existing_indexacion = self.repository.get_obligacion_financiera_indexacion(
            obligacion["id_obligacion_financiera"]
        )
        if existing_indexacion is not None:
            if (
                obligacion_preview.estado_preview_indexacion
                == ESTADO_PREVIEW_INDEXACION_CON_INDICE
            ):
                self.repository.ensure_obligacion_financiera_indexacion_compatible(
                    existing_indexacion,
                    self._obligacion_indexacion_expected_values(
                        obligacion_preview=obligacion_preview,
                        id_obligacion_financiera=obligacion["id_obligacion_financiera"],
                        bloque_indexacion=bloque_indexacion,
                    ),
                )
            return
        if (
            obligacion_preview.estado_preview_indexacion
            != ESTADO_PREVIEW_INDEXACION_CON_INDICE
        ):
            return
        if not obligacion.get("__created"):
            return
        self.repository.get_or_create_obligacion_financiera_indexacion(
            ObligacionFinancieraIndexacionUpsertPayload(
                **self._obligacion_indexacion_expected_values(
                    obligacion_preview=obligacion_preview,
                    id_obligacion_financiera=obligacion["id_obligacion_financiera"],
                    bloque_indexacion=bloque_indexacion,
                ),
                observaciones=None,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
        )

    def _obligacion_indexacion_expected_values(
        self,
        *,
        obligacion_preview: PlanPagoVentaV2ObligacionPreview,
        id_obligacion_financiera: int,
        bloque_indexacion: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if bloque_indexacion is None:
            raise ValueError(f"{ERROR_OBLIGACION_INDEXACION_INCOMPATIBLE}:SIN_BLOQUE")
        return {
            "id_obligacion_financiera": id_obligacion_financiera,
            "id_plan_pago_venta_bloque_indexacion": bloque_indexacion[
                "id_plan_pago_venta_bloque_indexacion"
            ],
            "id_indice_financiero": obligacion_preview.id_indice_financiero,
            "id_indice_financiero_valor": obligacion_preview.id_indice_financiero_valor,
            "fecha_base_indice": obligacion_preview.bloque.input.fecha_base_indice,
            "valor_base_indice": obligacion_preview.valor_base_indice,
            "fecha_aplicacion_indice": obligacion_preview.fecha_valor_indice,
            "valor_aplicado_indice": obligacion_preview.valor_aplicado_indice,
            "coeficiente_indexacion": obligacion_preview.coeficiente_indexacion,
            "modo_indexacion": obligacion_preview.bloque.input.modo_indexacion,
            "base_calculo_indexacion": obligacion_preview.bloque.input.base_calculo_indexacion,
            "tipo_generacion_indexada": obligacion_preview.bloque.input.tipo_generacion_indexada,
        }

    def _obligacion_payload(
        self,
        *,
        obligacion_preview: PlanPagoVentaV2ObligacionPreview,
        bloque: dict[str, Any],
        id_relacion_generadora: int,
        id_generacion_cronograma_financiero: int,
        concepto: dict[str, Any],
        compradores: list[dict[str, Any]],
        moneda: str,
        now: datetime,
        id_instalacion: int | None,
        op_id: Any,
        conceptos: dict[str, dict[str, Any]],
    ) -> ObligacionCronogramaV2CreatePayload:
        clave_funcional = (
            f"PLAN_PAGO_VENTA:{bloque['id_plan_pago_venta']}:"
            f"BLOQUE:{obligacion_preview.bloque.numero_bloque}:"
            f"{obligacion_preview.tipo_item_cronograma}:"
            f"{obligacion_preview.item_numero}"
        )
        composiciones = self._build_composiciones_obligacion(
            obligacion_preview=obligacion_preview,
            concepto_capital=concepto,
            conceptos=conceptos,
        )
        importe_total = obligacion_preview.importe_total
        if self._obligacion_indexacion_sin_indice(obligacion_preview):
            importe_total = obligacion_preview.capital_cuota or importe_total
        return ObligacionCronogramaV2CreatePayload(
            id_relacion_generadora=id_relacion_generadora,
            id_generacion_cronograma_financiero=id_generacion_cronograma_financiero,
            id_plan_pago_venta_bloque=bloque["id_plan_pago_venta_bloque"],
            numero_obligacion=obligacion_preview.numero_obligacion,
            tipo_item_cronograma=obligacion_preview.tipo_item_cronograma,
            etiqueta_obligacion=obligacion_preview.etiqueta_obligacion,
            clave_funcional_origen=clave_funcional,
            fecha_emision=obligacion_preview.fecha_vencimiento,
            fecha_vencimiento=obligacion_preview.fecha_vencimiento,
            importe_total=importe_total,
            moneda=moneda,
            estado_obligacion=ESTADO_OBLIGACION_PROYECTADA,
            id_concepto_financiero=concepto["id_concepto_financiero"],
            codigo_concepto_financiero=concepto["codigo_concepto_financiero"],
            id_persona_obligado=compradores[0]["id_persona"],
            rol_obligado=ROL_OBLIGADO_COMPRADOR,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
            composiciones=composiciones,
            obligados=[
                ObligadoCronogramaV2CreatePayload(
                    id_persona=comprador["id_persona"],
                    rol_obligado=ROL_OBLIGADO_COMPRADOR,
                    porcentaje_responsabilidad=comprador["porcentaje_responsabilidad"],
                )
                for comprador in compradores
            ],
        )

    def _build_composiciones_obligacion(
        self,
        *,
        obligacion_preview: PlanPagoVentaV2ObligacionPreview,
        concepto_capital: dict[str, Any],
        conceptos: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]] | None:
        bloque_input = obligacion_preview.bloque.input
        if obligacion_preview.bloque.tipo_bloque != TIPO_BLOQUE_TRAMO_CUOTAS:
            return None
        metodo = (bloque_input.metodo_liquidacion or "").strip().upper()
        if metodo == METODO_LIQUIDACION_INDEXACION:
            capital = (
                obligacion_preview.capital_cuota or obligacion_preview.importe_total
            ).quantize(Decimal("0.01"))
            composiciones = [
                {
                    "id_concepto_financiero": concepto_capital[
                        "id_concepto_financiero"
                    ],
                    "codigo_concepto_financiero": concepto_capital[
                        "codigo_concepto_financiero"
                    ],
                    "importe_componente": capital,
                }
            ]
            ajuste_indexacion = obligacion_preview.ajuste_indexacion_cuota or Decimal(
                "0.00"
            )
            if ajuste_indexacion < Decimal("0.00"):
                raise ValueError(ERROR_INDEXACION_AJUSTE_NEGATIVO)
            if (
                obligacion_preview.estado_preview_indexacion
                == ESTADO_PREVIEW_INDEXACION_CON_INDICE
                and ajuste_indexacion != Decimal("0.00")
            ):
                composiciones.append(
                    {
                        "id_concepto_financiero": conceptos[CONCEPTO_AJUSTE_INDEXACION][
                            "id_concepto_financiero"
                        ],
                        "codigo_concepto_financiero": CONCEPTO_AJUSTE_INDEXACION,
                        "importe_componente": ajuste_indexacion,
                    }
                )
            return composiciones
        if metodo != METODO_LIQUIDACION_INTERES_DIRECTO:
            return None
        cantidad = Decimal(bloque_input.cantidad_cuotas or 1)
        tasa = bloque_input.tasa_interes_directo_periodica or Decimal("0.00")
        periodos = Decimal(bloque_input.cantidad_periodos or 0)
        capital_total = (bloque_input.importe_total_bloque or Decimal("0.00")).quantize(
            Decimal("0.01")
        )
        interes_total = (capital_total * tasa * periodos).quantize(Decimal("0.01"))
        capital_cuota_base = (capital_total / cantidad).quantize(Decimal("0.01"))
        interes_cuota_base = (interes_total / cantidad).quantize(Decimal("0.01"))
        idx = Decimal(obligacion_preview.item_numero)
        if idx < cantidad:
            capital = capital_cuota_base
            interes = interes_cuota_base
        else:
            capital = (capital_total - capital_cuota_base * (cantidad - 1)).quantize(
                Decimal("0.01")
            )
            interes = (interes_total - interes_cuota_base * (cantidad - 1)).quantize(
                Decimal("0.01")
            )
        return [
            {
                "id_concepto_financiero": concepto_capital["id_concepto_financiero"],
                "codigo_concepto_financiero": concepto_capital[
                    "codigo_concepto_financiero"
                ],
                "importe_componente": capital,
            },
            {
                "id_concepto_financiero": conceptos[CONCEPTO_INTERES_FINANCIERO][
                    "id_concepto_financiero"
                ],
                "codigo_concepto_financiero": CONCEPTO_INTERES_FINANCIERO,
                "importe_componente": interes,
            },
        ]

    def _plan_vivo_compatible(
        self,
        *,
        plan_vivo: dict[str, Any],
        command: GeneratePlanPagoVentaV2PorBloquesCommand,
        tipo_pago: str,
        moneda: str,
    ) -> bool:
        if plan_vivo["metodo_plan_pago"] != METODO_PLAN_POR_BLOQUES:
            return False
        if plan_vivo["estado_plan_pago"] not in {"BORRADOR", "GENERADO"}:
            return False
        if Decimal(str(plan_vivo["monto_total_plan"])) != command.monto_total_plan:
            return False
        if plan_vivo["moneda"] != moneda:
            return False
        expected_result = self.preview_service.execute(
            command, id_plan_pago_venta=plan_vivo["id_plan_pago_venta"]
        )
        if not expected_result.success:
            return False
        expected = expected_result.data["bloques"]
        existing = self.repository.get_plan_pago_venta_bloques(
            plan_vivo["id_plan_pago_venta"]
        )
        if len(existing) != len(expected):
            return False
        return all(
            self._bloque_compatible(existing_bloque, expected_bloque)
            for existing_bloque, expected_bloque in zip(existing, expected, strict=True)
        )

    def _bloque_compatible(
        self, existing: dict[str, Any], expected: PlanPagoVentaV2BloquePreview
    ) -> bool:
        return (
            existing["numero_bloque"] == expected.numero_bloque
            and existing["tipo_bloque"] == expected.tipo_bloque
            and existing["etiqueta_bloque"] == expected.etiqueta_bloque
            and existing["clave_bloque"] == expected.clave_bloque
            and existing["cantidad_cuotas"] == expected.input.cantidad_cuotas
            and self._decimal_or_none(existing["importe_total_bloque"])
            == self._decimal_or_none(expected.importe_total_bloque)
            and self._decimal_or_none(existing["importe_cuota"])
            == self._decimal_or_none(expected.importe_cuota)
            and existing["fecha_vencimiento"] == expected.input.fecha_vencimiento
            and existing["fecha_primer_vencimiento"]
            == expected.input.fecha_primer_vencimiento
            and existing["periodicidad"]
            == (
                PERIODICIDAD_MENSUAL
                if expected.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
                else None
            )
            and existing["regla_redondeo"]
            == (
                REGLA_REDONDEO_ULTIMA_CUOTA
                if expected.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
                else None
            )
            and existing["concepto_financiero_codigo"]
            == expected.concepto_financiero_codigo
            and (existing.get("metodo_liquidacion") or None)
            == (expected.input.metodo_liquidacion or None)
            and self._decimal_or_none(existing.get("tasa_interes_directo_periodica"))
            == self._decimal_or_none(expected.input.tasa_interes_directo_periodica)
            and existing.get("cantidad_periodos") == expected.input.cantidad_periodos
            and (existing.get("base_calculo_interes") or None)
            == (expected.input.base_calculo_interes or None)
        )

    def _resolve_conceptos(
        self, bloques: list[PlanPagoVentaV2BloquePreview]
    ) -> dict[str, dict[str, Any]]:
        conceptos: dict[str, dict[str, Any]] = {}
        codigos = {bloque.concepto_financiero_codigo for bloque in bloques}
        if any(
            (bloque.input.metodo_liquidacion or "").strip().upper()
            == METODO_LIQUIDACION_INTERES_DIRECTO
            and bloque.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
            for bloque in bloques
        ):
            codigos.add(CONCEPTO_INTERES_FINANCIERO)
        if any(self._bloque_usa_indexacion(bloque) for bloque in bloques):
            codigos.add(CONCEPTO_AJUSTE_INDEXACION)
        for codigo in codigos:
            concepto = self.repository.get_concepto_financiero_by_codigo(codigo)
            if concepto is None:
                raise ValueError(f"NOT_FOUND_CONCEPTO:{codigo}")
            conceptos[codigo] = concepto
        return conceptos

    @staticmethod
    def _bloque_usa_indexacion(bloque: PlanPagoVentaV2BloquePreview) -> bool:
        return (
            bloque.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS
            and (bloque.input.metodo_liquidacion or "").strip().upper()
            == METODO_LIQUIDACION_INDEXACION
        )

    @staticmethod
    def _obligacion_indexacion_sin_indice(
        obligacion_preview: PlanPagoVentaV2ObligacionPreview,
    ) -> bool:
        metodo = (
            (obligacion_preview.bloque.input.metodo_liquidacion or "").strip().upper()
        )
        return (
            metodo == METODO_LIQUIDACION_INDEXACION
            and obligacion_preview.estado_preview_indexacion
            == ESTADO_PREVIEW_INDEXACION_PROYECTADA
        )

    def _resolve_compradores(self, id_venta: int) -> list[dict[str, Any]]:
        compradores = self.repository.get_compradores_financieros_venta(id_venta)
        if not compradores:
            raise ValueError("COMPRADOR_VENTA_NO_RESUELTO")

        personas: set[int] = set()
        normalizados: list[dict[str, Any]] = []
        for comprador in compradores:
            id_persona = comprador["id_persona"]
            if id_persona in personas:
                raise ValueError("COMPRADOR_DUPLICADO")
            personas.add(id_persona)

            porcentaje = self._decimal_or_none(
                comprador.get("porcentaje_responsabilidad")
            )
            if porcentaje is None and len(compradores) == 1:
                porcentaje = PORCENTAJE_TOTAL_COMPRADORES
            elif porcentaje is None:
                raise ValueError("PORCENTAJE_COMPRADORES_NO_DEFINIDO")
            if porcentaje <= 0:
                raise ValueError("PORCENTAJE_COMPRADOR_INVALIDO")
            normalizados.append(
                {
                    **comprador,
                    "porcentaje_responsabilidad": porcentaje,
                }
            )

        total = sum(
            (row["porcentaje_responsabilidad"] for row in normalizados),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))
        if total != PORCENTAJE_TOTAL_COMPRADORES:
            raise ValueError("PORCENTAJE_COMPRADORES_NO_SUMA_100")
        return normalizados

    def _resolve_comprador(self, id_venta: int) -> dict[str, Any]:
        return self._resolve_compradores(id_venta)[0]

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()
