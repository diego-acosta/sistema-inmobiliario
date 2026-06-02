from contextlib import AbstractContextManager
from decimal import Decimal
from typing import Any

from app.application.comercial.commands.confirm_venta_completa_desde_reserva import (
    ConfirmVentaCompletaDesdeReservaCommand,
)
from app.application.comercial.commands.confirm_venta import ConfirmVentaCommand
from app.application.comercial.commands.define_condiciones_comerciales_venta import (
    DefineCondicionesComercialesVentaCommand,
    DefineCondicionesComercialesVentaCuotaCommand,
    DefineCondicionesComercialesVentaObjetoCommand,
)
from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    GeneratePlanPagoVentaV2PorBloquesCommand,
    PlanPagoVentaBloqueInput,
)
from app.application.comercial.commands.generate_venta_from_reserva_venta import (
    GenerateVentaFromReservaVentaCommand,
)
from app.application.comercial.services.confirm_venta_service import ConfirmVentaService
from app.application.comercial.services.define_condiciones_comerciales_venta_service import (
    DefineCondicionesComercialesVentaService,
)
from app.application.comercial.services.generate_plan_pago_venta_v2_por_bloques_service import (
    GeneratePlanPagoVentaV2PorBloquesService,
)
from app.application.comercial.services.generate_venta_from_reserva_venta_service import (
    GenerateVentaFromReservaVentaService,
)
from app.application.common.results import AppResult


class _TransactionalComercialRepository:
    def __init__(self, repository: Any) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repository, name)

    @property
    def db(self) -> Any:
        return self._repository.db

    def generate_venta_from_reserva(
        self,
        payload: Any,
        objetos: list[Any],
        participaciones: list[Any],
        reserva_payload: Any,
    ) -> dict[str, Any]:
        return self._repository._generate_venta_from_reserva_tx(
            payload,
            objetos,
            participaciones,
            reserva_payload,
        )

    def define_condiciones_comerciales_venta(
        self,
        payload: Any,
        objetos: list[Any],
        cuotas: list[Any],
    ) -> dict[str, Any]:
        return self._repository._define_condiciones_comerciales_venta_tx(
            payload,
            objetos,
            cuotas,
        )

    def confirm_venta(
        self,
        payload: Any,
        *,
        outbox_event: Any | None = None,
    ) -> dict[str, Any]:
        return self._repository._confirm_venta_tx(
            payload,
            outbox_event=outbox_event,
        )


class _StageFailed(Exception):
    def __init__(self, error: str) -> None:
        super().__init__(error)
        self.error = error


class ConfirmVentaCompletaDesdeReservaService:
    def __init__(
        self,
        *,
        comercial_repository: Any,
        plan_pago_v2_service: GeneratePlanPagoVentaV2PorBloquesService,
    ) -> None:
        self.comercial_repository = comercial_repository
        self.plan_pago_v2_service = plan_pago_v2_service
        self.db = comercial_repository.db

    def execute(
        self, command: ConfirmVentaCompletaDesdeReservaCommand
    ) -> AppResult[dict[str, Any]]:
        if command.if_match_version_reserva is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        total_derivado_result = self._normalizar_precios_y_total(command)
        if not total_derivado_result.success or total_derivado_result.data is None:
            return AppResult.fail(total_derivado_result.errors[0])

        total_derivado = total_derivado_result.data
        if total_derivado != command.plan_pago_v2.monto_total_plan:
            return AppResult.fail("MONTO_TOTAL_PLAN_MISMATCH")

        tx_repository = _TransactionalComercialRepository(self.comercial_repository)

        try:
            with self._transaction():
                generated = GenerateVentaFromReservaVentaService(tx_repository).execute(
                    GenerateVentaFromReservaVentaCommand(
                        context=command.context,
                        id_reserva_venta=command.id_reserva_venta,
                        if_match_version=command.if_match_version_reserva,
                        codigo_venta=command.generar_venta.codigo_venta,
                        fecha_venta=command.generar_venta.fecha_venta,
                        monto_total=command.generar_venta.monto_total,
                        observaciones=command.generar_venta.observaciones,
                    )
                )
                if not generated.success or generated.data is None:
                    raise _StageFailed(generated.errors[0])

                id_venta = generated.data["id_venta"]
                condiciones = DefineCondicionesComercialesVentaService(
                    tx_repository
                ).execute(
                    DefineCondicionesComercialesVentaCommand(
                        context=command.context,
                        id_venta=id_venta,
                        if_match_version=generated.data["version_registro"],
                        monto_total=command.condiciones_comerciales.monto_total,
                        tipo_plan_financiero=command.condiciones_comerciales.tipo_plan_financiero,
                        moneda=command.condiciones_comerciales.moneda,
                        importe_anticipo=command.condiciones_comerciales.importe_anticipo,
                        fecha_vencimiento_anticipo=command.condiciones_comerciales.fecha_vencimiento_anticipo,
                        importe_saldo=command.condiciones_comerciales.importe_saldo,
                        fecha_vencimiento_saldo=command.condiciones_comerciales.fecha_vencimiento_saldo,
                        cuotas=[
                            DefineCondicionesComercialesVentaCuotaCommand(
                                numero_cuota=cuota.numero_cuota,
                                importe_cuota=cuota.importe_cuota,
                                fecha_vencimiento=cuota.fecha_vencimiento,
                                moneda=cuota.moneda,
                                observaciones=cuota.observaciones,
                            )
                            for cuota in command.condiciones_comerciales.cuotas
                        ],
                        objetos=[
                            DefineCondicionesComercialesVentaObjetoCommand(
                                id_inmueble=objeto.id_inmueble,
                                id_unidad_funcional=objeto.id_unidad_funcional,
                                precio_asignado=objeto.precio_asignado,
                            )
                            for objeto in command.condiciones_comerciales.objetos
                        ],
                    )
                )
                if not condiciones.success or condiciones.data is None:
                    raise _StageFailed(condiciones.errors[0])

                plan = self.plan_pago_v2_service.execute_in_existing_transaction(
                    GeneratePlanPagoVentaV2PorBloquesCommand(
                        context=command.context,
                        id_venta=id_venta,
                        tipo_pago=command.plan_pago_v2.tipo_pago,
                        monto_total_plan=command.plan_pago_v2.monto_total_plan,
                        moneda=command.plan_pago_v2.moneda,
                        bloques=[
                            PlanPagoVentaBloqueInput(
                                tipo_bloque=bloque.tipo_bloque,
                                etiqueta_bloque=bloque.etiqueta_bloque,
                                importe_total_bloque=bloque.importe_total_bloque,
                                fecha_vencimiento=bloque.fecha_vencimiento,
                                cantidad_cuotas=bloque.cantidad_cuotas,
                                importe_cuota=bloque.importe_cuota,
                                fecha_primer_vencimiento=bloque.fecha_primer_vencimiento,
                                periodicidad=bloque.periodicidad,
                                regla_redondeo=bloque.regla_redondeo,
                                metodo_liquidacion=bloque.metodo_liquidacion,
                                tasa_interes_directo_periodica=bloque.tasa_interes_directo_periodica,
                                cantidad_periodos=bloque.cantidad_periodos,
                                base_calculo_interes=bloque.base_calculo_interes,
                                id_indice_financiero=bloque.id_indice_financiero,
                                fecha_base_indice=bloque.fecha_base_indice,
                                valor_base_indice=bloque.valor_base_indice,
                                modo_indexacion=bloque.modo_indexacion,
                                base_calculo_indexacion=bloque.base_calculo_indexacion,
                                tipo_generacion_indexada=bloque.tipo_generacion_indexada,
                                politica_valor_no_disponible=bloque.politica_valor_no_disponible,
                                conserva_capital_original=bloque.conserva_capital_original,
                                genera_ajuste_por_diferencia=bloque.genera_ajuste_por_diferencia,
                                observaciones=bloque.observaciones,
                            )
                            for bloque in command.plan_pago_v2.bloques
                        ],
                        observaciones=command.plan_pago_v2.observaciones,
                    )
                )
                if not plan.success or plan.data is None:
                    raise _StageFailed(plan.errors[0])

                confirmed = ConfirmVentaService(tx_repository).execute(
                    ConfirmVentaCommand(
                        context=command.context,
                        id_venta=id_venta,
                        if_match_version=condiciones.data["version_registro"],
                        observaciones=command.confirmacion.observaciones,
                    )
                )
                if not confirmed.success or confirmed.data is None:
                    raise _StageFailed(confirmed.errors[0])

                reserva = self.comercial_repository.get_reserva_venta(
                    command.id_reserva_venta
                )
                if reserva is None:
                    raise _StageFailed("NOT_FOUND_RESERVA_VENTA")

                return AppResult.ok(
                    {
                        "ok": True,
                        "data": {
                            "reserva_venta": {
                                "id_reserva_venta": reserva["id_reserva_venta"],
                                "estado_reserva": reserva["estado_reserva"],
                                "version_registro": reserva["version_registro"],
                            },
                            "venta": {
                                "id_venta": confirmed.data["id_venta"],
                                "estado_venta": confirmed.data["estado_venta"],
                                "version_registro": confirmed.data["version_registro"],
                            },
                            "plan_pago_v2": {
                                "id_plan_pago_venta": plan.data["plan_pago_venta"][
                                    "id_plan_pago_venta"
                                ],
                                "estado_plan_pago": plan.data["plan_pago_venta"][
                                    "estado_plan_pago"
                                ],
                            },
                            "generacion_cronograma_financiero": {
                                "id_generacion_cronograma_financiero": plan.data[
                                    "generacion_cronograma_financiero"
                                ]["id_generacion_cronograma_financiero"],
                                "estado_generacion": plan.data[
                                    "generacion_cronograma_financiero"
                                ]["estado_generacion"],
                            },
                            "obligaciones": {
                                "cantidad": len(plan.data["obligaciones"]),
                                "ids": [
                                    obligacion["id_obligacion_financiera"]
                                    for obligacion in plan.data["obligaciones"]
                                ],
                            },
                        },
                    }
                )
        except _StageFailed as exc:
            return AppResult.fail(exc.error)

    def _normalizar_precios_y_total(
        self, command: ConfirmVentaCompletaDesdeReservaCommand
    ) -> AppResult[Decimal]:
        if not command.condiciones_comerciales.objetos:
            return AppResult.fail("VENTA_WITHOUT_OBJECTS")

        monto_redundante = command.generar_venta.monto_total
        if monto_redundante is None:
            monto_redundante = command.condiciones_comerciales.monto_total

        objetos = command.condiciones_comerciales.objetos
        seen_objects: set[tuple[str, int]] = set()
        ids_inmueble_payload: set[int] = set()
        ids_unidad_funcional_payload: set[int] = set()
        for objeto in objetos:
            if (objeto.id_inmueble is None) == (objeto.id_unidad_funcional is None):
                return AppResult.fail("INVALID_VENTA_OBJECTS")
            object_key = (
                ("inmueble", objeto.id_inmueble)
                if objeto.id_inmueble is not None
                else ("unidad_funcional", objeto.id_unidad_funcional)
            )
            if object_key in seen_objects:
                return AppResult.fail("OBJETO_VENTA_DUPLICADO")
            seen_objects.add(object_key)
            if objeto.id_inmueble is not None:
                ids_inmueble_payload.add(objeto.id_inmueble)
            elif objeto.id_unidad_funcional is not None:
                ids_unidad_funcional_payload.add(objeto.id_unidad_funcional)

        if self._hay_solapamiento_jerarquico_objetos(
            ids_inmueble_payload, ids_unidad_funcional_payload
        ):
            return AppResult.fail("OBJETO_VENTA_JERARQUIA_SOLAPADA")

        precios: list[Decimal] = []
        for objeto in objetos:
            precio = objeto.precio_asignado
            if precio is None:
                if (
                    len(command.condiciones_comerciales.objetos) == 1
                    and monto_redundante is not None
                ):
                    precio = Decimal(str(monto_redundante))
                    objeto.precio_asignado = precio
                else:
                    return AppResult.fail("VALOR_ASIGNADO_OBJETO_REQUERIDO")

            precio_decimal = Decimal(str(precio))
            if precio_decimal <= 0:
                return AppResult.fail("VALOR_ASIGNADO_OBJETO_INVALIDO")
            objeto.precio_asignado = precio_decimal
            precios.append(precio_decimal)

        total_derivado = sum(precios, Decimal("0"))
        montos_redundantes = [
            command.generar_venta.monto_total,
            command.condiciones_comerciales.monto_total,
        ]
        for monto in montos_redundantes:
            if monto is not None and Decimal(str(monto)) != total_derivado:
                return AppResult.fail("SUMA_VALORES_OBJETOS_NO_COINCIDE_MONTO_VENTA")

        command.generar_venta.monto_total = total_derivado
        command.condiciones_comerciales.monto_total = total_derivado
        return AppResult.ok(total_derivado)

    def _hay_solapamiento_jerarquico_objetos(
        self,
        ids_inmueble_payload: set[int],
        ids_unidad_funcional_payload: set[int],
    ) -> bool:
        if not ids_inmueble_payload or not ids_unidad_funcional_payload:
            return False

        for id_unidad_funcional in ids_unidad_funcional_payload:
            id_inmueble_padre = (
                self.comercial_repository.get_id_inmueble_by_unidad_funcional(
                    id_unidad_funcional
                )
            )
            if id_inmueble_padre in ids_inmueble_payload:
                return True
        return False

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()
