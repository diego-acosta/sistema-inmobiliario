from contextlib import AbstractContextManager
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

        if (
            command.condiciones_comerciales.monto_total
            != command.plan_pago_v2.monto_total_plan
        ):
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

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()
