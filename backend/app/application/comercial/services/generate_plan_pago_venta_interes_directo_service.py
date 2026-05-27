from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import uuid4

from app.application.comercial.commands.generate_plan_pago_venta_interes_directo import (
    GeneratePlanPagoVentaInteresDirectoCommand,
)
from app.application.comercial.services.generate_plan_pago_venta_cuotas_iguales_simple_service import (
    CONCEPTO_CAPITAL_VENTA,
    ESTADO_OBLIGACION_PROYECTADA,
    GeneracionCronogramaCreatePayload,
    ObligacionCronogramaV2CreatePayload,
    PERIODICIDAD_MENSUAL,
    PlanPagoVentaBloqueUpsertPayload,
    PlanPagoVentaUpsertPayload,
    PlanPagoVentaV2Repository,
    REGLA_REDONDEO_ULTIMA_CUOTA,
    ROL_OBLIGADO_COMPRADOR,
    RelacionGeneradoraUpsertPayload,
    TIPO_BLOQUE_TRAMO_CUOTAS,
    TIPO_GENERACION_PLAN_PAGO_VENTA_V2,
    TIPO_ITEM_CUOTA,
    TIPO_ORIGEN_VENTA,
    add_months,
)
from app.application.common.results import AppResult

METODO_INTERES_DIRECTO = "INTERES_DIRECTO"
CONCEPTO_INTERES_FINANCIERO = "INTERES_FINANCIERO"


class GeneratePlanPagoVentaInteresDirectoService:
    def __init__(self, repository: PlanPagoVentaV2Repository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: GeneratePlanPagoVentaInteresDirectoCommand) -> AppResult[dict[str, Any]]:
        validation_error = self._validate(command)
        if validation_error is not None:
            return AppResult.fail(validation_error)
        try:
            with self._transaction():
                return self._execute_in_transaction(command)
        except ValueError as exc:
            return AppResult.fail(str(exc))

    def _execute_in_transaction(self, command: GeneratePlanPagoVentaInteresDirectoCommand) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta_minima(command.id_venta)
        if venta is None:
            return AppResult.fail("NOT_FOUND_VENTA")
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)
        now = datetime.now(UTC)
        moneda = command.moneda.strip().upper()
        periodicidad = command.periodicidad.strip().upper()
        regla_redondeo = command.regla_redondeo.strip().upper()

        plan = self.repository.upsert_plan_pago_venta_borrador(PlanPagoVentaUpsertPayload(
            id_venta=command.id_venta, metodo_plan_pago=METODO_INTERES_DIRECTO, estado_plan_pago="BORRADOR",
            moneda=moneda, monto_total_plan=command.monto_total_plan, cantidad_cuotas=command.cantidad_cuotas,
            periodicidad=periodicidad, fecha_primer_vencimiento=command.fecha_primer_vencimiento,
            importe_anticipo=None, fecha_vencimiento_anticipo=None, regla_redondeo=regla_redondeo, observaciones=None,
            created_at=now, updated_at=now, id_instalacion_origen=id_instalacion, id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id, op_id_ultima_modificacion=op_id
        ))
        relacion = self.repository.get_or_create_relacion_generadora(RelacionGeneradoraUpsertPayload(
            tipo_origen=TIPO_ORIGEN_VENTA, id_origen=command.id_venta, descripcion="Relacion generadora creada desde plan pago venta V2",
            created_at=now, updated_at=now, id_instalacion_origen=id_instalacion, id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id, op_id_ultima_modificacion=op_id
        ))
        generacion = self.repository.get_or_create_generacion_cronograma(GeneracionCronogramaCreatePayload(
            id_relacion_generadora=relacion["id_relacion_generadora"], id_plan_pago_venta=plan["id_plan_pago_venta"],
            tipo_generacion=TIPO_GENERACION_PLAN_PAGO_VENTA_V2,
            clave_generacion=f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:{METODO_INTERES_DIRECTO}",
            estado_generacion="GENERADA", fecha_generacion=now, observaciones=None, created_at=now, updated_at=now,
            id_instalacion_origen=id_instalacion, id_instalacion_ultima_modificacion=id_instalacion, op_id_alta=op_id, op_id_ultima_modificacion=op_id
        ))
        concepto_capital = self.repository.get_concepto_financiero_by_codigo(CONCEPTO_CAPITAL_VENTA)
        concepto_interes = self.repository.get_concepto_financiero_by_codigo(CONCEPTO_INTERES_FINANCIERO)
        if concepto_capital is None: raise ValueError("NOT_FOUND_CONCEPTO:CAPITAL_VENTA")
        if concepto_interes is None: raise ValueError("NOT_FOUND_CONCEPTO:INTERES_FINANCIERO")
        comprador = self._resolve_comprador(command.id_venta)

        total_interes = (command.monto_total_plan * command.tasa_interes_directo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        capital_base = (command.monto_total_plan / Decimal(command.cantidad_cuotas)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        interes_base = (total_interes / Decimal(command.cantidad_cuotas)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        bloque = self.repository.get_or_create_plan_pago_venta_bloque(PlanPagoVentaBloqueUpsertPayload(
            id_plan_pago_venta=plan["id_plan_pago_venta"], numero_bloque=1, tipo_bloque=TIPO_BLOQUE_TRAMO_CUOTAS,
            etiqueta_bloque="Cuotas interes directo", clave_bloque=f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:BLOQUE:TRAMO_CUOTAS:1",
            cantidad_cuotas=command.cantidad_cuotas, importe_total_bloque=None,
            importe_cuota=(capital_base+interes_base).quantize(Decimal("0.01")), fecha_vencimiento=None,
            fecha_primer_vencimiento=command.fecha_primer_vencimiento, periodicidad=periodicidad, regla_redondeo=regla_redondeo,
            concepto_financiero_codigo=CONCEPTO_CAPITAL_VENTA, observaciones="INTERES_DIRECTO tasa sobre capital total", created_at=now, updated_at=now,
            id_instalacion_origen=id_instalacion, id_instalacion_ultima_modificacion=id_instalacion, op_id_alta=op_id, op_id_ultima_modificacion=op_id
        ))

        acumulado_cap = Decimal("0.00"); acumulado_int = Decimal("0.00"); claves=[]
        for numero in range(1, command.cantidad_cuotas+1):
            cap = (command.monto_total_plan-acumulado_cap).quantize(Decimal("0.01")) if numero==command.cantidad_cuotas else capital_base
            inte = (total_interes-acumulado_int).quantize(Decimal("0.01")) if numero==command.cantidad_cuotas else interes_base
            total = (cap+inte).quantize(Decimal("0.01"))
            fv = add_months(command.fecha_primer_vencimiento, numero-1)
            clave=f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:CUOTA:{numero}"; claves.append(clave)
            self.repository.create_obligacion_cronograma_v2_if_not_exists(ObligacionCronogramaV2CreatePayload(
                id_relacion_generadora=relacion["id_relacion_generadora"], id_generacion_cronograma_financiero=generacion["id_generacion_cronograma_financiero"],
                id_plan_pago_venta_bloque=bloque["id_plan_pago_venta_bloque"], numero_obligacion=numero, tipo_item_cronograma=TIPO_ITEM_CUOTA,
                etiqueta_obligacion=f"Cuota {numero}", clave_funcional_origen=clave, fecha_emision=fv, fecha_vencimiento=fv, importe_total=total, moneda=moneda,
                estado_obligacion=ESTADO_OBLIGACION_PROYECTADA, id_concepto_financiero=concepto_capital["id_concepto_financiero"],
                codigo_concepto_financiero=CONCEPTO_CAPITAL_VENTA, id_persona_obligado=comprador["id_persona"], rol_obligado=ROL_OBLIGADO_COMPRADOR,
                created_at=now, updated_at=now, id_instalacion_origen=id_instalacion, id_instalacion_ultima_modificacion=id_instalacion, op_id_alta=op_id, op_id_ultima_modificacion=op_id,
                composiciones=[
                    {"id_concepto_financiero": concepto_capital["id_concepto_financiero"], "importe_componente": cap, "moneda_componente": moneda},
                    {"id_concepto_financiero": concepto_interes["id_concepto_financiero"], "importe_componente": inte, "moneda_componente": moneda},
                ],
            ))
            acumulado_cap += cap; acumulado_int += inte

        plan_generado=self.repository.mark_plan_pago_venta_generado(id_plan_pago_venta=plan["id_plan_pago_venta"],updated_at=now,id_instalacion_ultima_modificacion=id_instalacion,op_id_ultima_modificacion=op_id)
        obligaciones=self.repository.get_obligaciones_cronograma_by_claves(id_relacion_generadora=relacion["id_relacion_generadora"], claves_funcionales=claves)
        return AppResult.ok({"id_venta":command.id_venta,"id_relacion_generadora":relacion["id_relacion_generadora"],"plan_pago_venta":plan_generado,"generacion_cronograma_financiero":generacion,"obligaciones":obligaciones})

    def _validate(self, command):
        if command.monto_total_plan <= 0: return "INVALID_MONTO_TOTAL_PLAN"
        if command.cantidad_cuotas <= 0: return "INVALID_CANTIDAD_CUOTAS"
        if command.tasa_interes_directo < 0: return "INVALID_TASA_INTERES_DIRECTO"
        if command.fecha_primer_vencimiento is None: return "INVALID_FECHA_PRIMER_VENCIMIENTO"
        if command.periodicidad.strip().upper() != PERIODICIDAD_MENSUAL: return "INVALID_PERIODICIDAD"
        if command.regla_redondeo.strip().upper() != REGLA_REDONDEO_ULTIMA_CUOTA: return "INVALID_REGLA_REDONDEO"
        return None

    def _resolve_comprador(self, id_venta: int) -> dict[str, Any]:
        compradores = self.repository.get_compradores_financieros_venta(id_venta)
        if not compradores: raise ValueError("COMPRADOR_VENTA_NO_RESUELTO")
        if len(compradores) != 1: raise ValueError("COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO")
        return compradores[0]

    def _transaction(self) -> AbstractContextManager:
        return self.db.begin_nested() if self.db.in_transaction() else self.db.begin()
