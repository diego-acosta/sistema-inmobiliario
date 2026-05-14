from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.application.comercial.commands.generate_plan_pago_venta_anticipo_mas_cuotas_iguales import (
    GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand,
)
from app.application.comercial.services.generate_plan_pago_venta_cuotas_iguales_simple_service import (
    CONCEPTO_CAPITAL_VENTA,
    ESTADO_OBLIGACION_PROYECTADA,
    GeneracionCronogramaCreatePayload,
    METODO_CUOTAS_IGUALES_SIMPLE,
    ObligacionCronogramaV2CreatePayload,
    PERIODICIDAD_MENSUAL,
    PlanPagoVentaUpsertPayload,
    PlanPagoVentaV2Repository,
    REGLA_REDONDEO_ULTIMA_CUOTA,
    ROL_OBLIGADO_COMPRADOR,
    RelacionGeneradoraUpsertPayload,
    TIPO_GENERACION_PLAN_PAGO_VENTA_V2,
    TIPO_ITEM_CUOTA,
    TIPO_ORIGEN_VENTA,
    build_cuotas_iguales_mensuales,
)
from app.application.common.results import AppResult

METODO_ANTICIPO_MAS_CUOTAS_IGUALES = "ANTICIPO_MAS_CUOTAS_IGUALES"
CONCEPTO_ANTICIPO_VENTA = "ANTICIPO_VENTA"
TIPO_ITEM_ANTICIPO = "ANTICIPO"


class GeneratePlanPagoVentaAnticipoMasCuotasIgualesService:
    def __init__(
        self,
        repository: PlanPagoVentaV2Repository,
        uuid_generator=None,
    ) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand
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
        self, command: GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand
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
                metodo_plan_pago=METODO_ANTICIPO_MAS_CUOTAS_IGUALES,
                estado_plan_pago="BORRADOR",
                moneda=moneda,
                monto_total_plan=command.monto_total_plan,
                cantidad_cuotas=command.cantidad_cuotas,
                periodicidad=periodicidad,
                fecha_primer_vencimiento=command.fecha_primer_vencimiento,
                importe_anticipo=command.importe_anticipo,
                fecha_vencimiento_anticipo=command.fecha_vencimiento_anticipo,
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
            f"{METODO_ANTICIPO_MAS_CUOTAS_IGUALES}"
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

        concepto_anticipo = self.repository.get_concepto_financiero_by_codigo(
            CONCEPTO_ANTICIPO_VENTA
        )
        if concepto_anticipo is None:
            raise ValueError("NOT_FOUND_CONCEPTO:ANTICIPO_VENTA")

        concepto_capital = self.repository.get_concepto_financiero_by_codigo(
            CONCEPTO_CAPITAL_VENTA
        )
        if concepto_capital is None:
            raise ValueError("NOT_FOUND_CONCEPTO:CAPITAL_VENTA")

        comprador = self._resolve_comprador(command.id_venta)
        saldo_financiado = command.monto_total_plan - command.importe_anticipo
        cuotas = build_cuotas_iguales_mensuales(
            monto_total=saldo_financiado,
            cantidad_cuotas=command.cantidad_cuotas,
            fecha_primer_vencimiento=command.fecha_primer_vencimiento,
        )

        claves = [
            f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:ANTICIPO:1",
            *[
                f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:CUOTA:{numero}"
                for numero, _, _ in cuotas
            ],
        ]

        self.repository.create_obligacion_cronograma_v2_if_not_exists(
            ObligacionCronogramaV2CreatePayload(
                id_relacion_generadora=relacion["id_relacion_generadora"],
                id_generacion_cronograma_financiero=generacion[
                    "id_generacion_cronograma_financiero"
                ],
                numero_obligacion=1,
                tipo_item_cronograma=TIPO_ITEM_ANTICIPO,
                etiqueta_obligacion="Anticipo",
                clave_funcional_origen=claves[0],
                fecha_emision=command.fecha_vencimiento_anticipo,
                fecha_vencimiento=command.fecha_vencimiento_anticipo,
                importe_total=command.importe_anticipo,
                moneda=moneda,
                estado_obligacion=ESTADO_OBLIGACION_PROYECTADA,
                id_concepto_financiero=concepto_anticipo["id_concepto_financiero"],
                codigo_concepto_financiero=CONCEPTO_ANTICIPO_VENTA,
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

        for numero_cuota, importe, fecha_vencimiento in cuotas:
            self.repository.create_obligacion_cronograma_v2_if_not_exists(
                ObligacionCronogramaV2CreatePayload(
                    id_relacion_generadora=relacion["id_relacion_generadora"],
                    id_generacion_cronograma_financiero=generacion[
                        "id_generacion_cronograma_financiero"
                    ],
                    numero_obligacion=numero_cuota + 1,
                    tipo_item_cronograma=TIPO_ITEM_CUOTA,
                    etiqueta_obligacion=f"Cuota {numero_cuota}",
                    clave_funcional_origen=(
                        f"PLAN_PAGO_VENTA:{plan['id_plan_pago_venta']}:"
                        f"CUOTA:{numero_cuota}"
                    ),
                    fecha_emision=fecha_vencimiento,
                    fecha_vencimiento=fecha_vencimiento,
                    importe_total=importe,
                    moneda=moneda,
                    estado_obligacion=ESTADO_OBLIGACION_PROYECTADA,
                    id_concepto_financiero=concepto_capital["id_concepto_financiero"],
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
        self, command: GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand
    ) -> str | None:
        if command.id_venta <= 0:
            return "INVALID_VENTA"
        if command.monto_total_plan <= 0:
            return "INVALID_MONTO_TOTAL_PLAN"
        if not self._has_cent_precision(command.monto_total_plan):
            return "INVALID_MONTO_TOTAL_PLAN"
        if command.importe_anticipo <= 0:
            return "INVALID_IMPORTE_ANTICIPO"
        if not self._has_cent_precision(command.importe_anticipo):
            return "INVALID_IMPORTE_ANTICIPO"
        if command.importe_anticipo >= command.monto_total_plan:
            return "INVALID_IMPORTE_ANTICIPO"
        if command.cantidad_cuotas <= 0:
            return "INVALID_CANTIDAD_CUOTAS"
        if command.fecha_vencimiento_anticipo is None:
            return "INVALID_FECHA_VENCIMIENTO_ANTICIPO"
        if command.fecha_primer_vencimiento is None:
            return "INVALID_FECHA_PRIMER_VENCIMIENTO"
        if not command.moneda or not command.moneda.strip():
            return "INVALID_MONEDA"
        if command.periodicidad.strip().upper() != PERIODICIDAD_MENSUAL:
            return "INVALID_PERIODICIDAD"
        if command.regla_redondeo.strip().upper() != REGLA_REDONDEO_ULTIMA_CUOTA:
            return "INVALID_REGLA_REDONDEO"
        return None

    @staticmethod
    def _has_cent_precision(value: Decimal) -> bool:
        return value == value.quantize(Decimal("0.01"))

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
        command: GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand,
        moneda: str,
        periodicidad: str,
        regla_redondeo: str,
    ) -> bool:
        if plan_vivo["metodo_plan_pago"] == METODO_CUOTAS_IGUALES_SIMPLE:
            return False
        if plan_vivo["metodo_plan_pago"] != METODO_ANTICIPO_MAS_CUOTAS_IGUALES:
            return False
        if plan_vivo["estado_plan_pago"] not in {"BORRADOR", "GENERADO"}:
            return False
        return (
            Decimal(str(plan_vivo["monto_total_plan"])) == command.monto_total_plan
            and plan_vivo["moneda"] == moneda
            and Decimal(str(plan_vivo["importe_anticipo"])) == command.importe_anticipo
            and plan_vivo["fecha_vencimiento_anticipo"]
            == command.fecha_vencimiento_anticipo
            and plan_vivo["cantidad_cuotas"] == command.cantidad_cuotas
            and plan_vivo["fecha_primer_vencimiento"]
            == command.fecha_primer_vencimiento
            and plan_vivo["periodicidad"] == periodicidad
            and plan_vivo["regla_redondeo"] == regla_redondeo
        )

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()
