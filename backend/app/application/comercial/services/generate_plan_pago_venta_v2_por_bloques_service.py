from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    GeneratePlanPagoVentaV2PorBloquesCommand,
    PlanPagoVentaBloqueInput,
)
from app.application.comercial.services.generate_plan_pago_venta_anticipo_mas_cuotas_iguales_service import (
    CONCEPTO_ANTICIPO_VENTA,
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
    TIPO_GENERACION_PLAN_PAGO_VENTA_V2,
    TIPO_ITEM_CUOTA,
    TIPO_ORIGEN_VENTA,
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


@dataclass(slots=True)
class _PreparedBloque:
    input: PlanPagoVentaBloqueInput
    numero_bloque: int
    tipo_bloque: str
    etiqueta_bloque: str
    clave_bloque: str
    ordinal_tipo: int
    total_bloque: Decimal
    concepto_financiero_codigo: str


class GeneratePlanPagoVentaV2PorBloquesService:
    def __init__(
        self,
        repository: PlanPagoVentaV2Repository,
        uuid_generator=None,
    ) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: GeneratePlanPagoVentaV2PorBloquesCommand
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
        self, command: GeneratePlanPagoVentaV2PorBloquesCommand
    ) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta_minima(command.id_venta)
        if venta is None:
            return AppResult.fail("NOT_FOUND_VENTA")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)
        now = datetime.now(UTC)
        tipo_pago = command.tipo_pago.strip().upper()
        moneda = command.moneda.strip().upper()
        prepared_without_plan = self._prepare_bloques(command, id_plan_pago_venta=0)

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

        prepared_bloques = self._prepare_bloques(
            command, id_plan_pago_venta=plan["id_plan_pago_venta"]
        )
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
        comprador = self._resolve_comprador(command.id_venta)

        clave_funcionales: list[str] = []
        numero_obligacion = 1
        for prepared, bloque in zip(prepared_bloques, bloques, strict=True):
            obligaciones_bloque = self._build_obligaciones_bloque(
                prepared=prepared,
                bloque=bloque,
                numero_obligacion_inicial=numero_obligacion,
                id_relacion_generadora=relacion["id_relacion_generadora"],
                id_generacion_cronograma_financiero=generacion[
                    "id_generacion_cronograma_financiero"
                ],
                concepto=conceptos[prepared.concepto_financiero_codigo],
                comprador=comprador,
                moneda=moneda,
                now=now,
                id_instalacion=id_instalacion,
                op_id=op_id,
            )
            for payload in obligaciones_bloque:
                clave_funcionales.append(payload.clave_funcional_origen)
                self.repository.create_obligacion_cronograma_v2_if_not_exists(payload)
                numero_obligacion += 1

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

    def _validate(self, command: GeneratePlanPagoVentaV2PorBloquesCommand) -> str | None:
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
            total += self._bloque_total(bloque)

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
            if bloque.importe_cuota is None or bloque.importe_cuota <= 0:
                return "BLOQUE_INVALIDO"
            if not self._has_cent_precision(bloque.importe_cuota):
                return "BLOQUE_INVALIDO"
            if bloque.fecha_primer_vencimiento is None:
                return "BLOQUE_INVALIDO"
            periodicidad = (bloque.periodicidad or "").strip().upper()
            if periodicidad != PERIODICIDAD_MENSUAL:
                return "INVALID_PERIODICIDAD"
            regla_redondeo = (bloque.regla_redondeo or REGLA_REDONDEO_ULTIMA_CUOTA).strip().upper()
            if regla_redondeo != REGLA_REDONDEO_ULTIMA_CUOTA:
                return "INVALID_REGLA_REDONDEO"
            return None

        return self._validate_pago_unico(bloque)

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
    ) -> list[_PreparedBloque]:
        counts: dict[str, int] = {}
        prepared: list[_PreparedBloque] = []
        for index, bloque in enumerate(command.bloques, start=1):
            tipo_bloque = bloque.tipo_bloque.strip().upper()
            counts[tipo_bloque] = counts.get(tipo_bloque, 0) + 1
            ordinal_tipo = counts[tipo_bloque]
            clave_bloque = (
                f"PLAN_PAGO_VENTA:{id_plan_pago_venta}:"
                f"BLOQUE:{tipo_bloque}:{ordinal_tipo}"
            )
            prepared.append(
                _PreparedBloque(
                    input=bloque,
                    numero_bloque=index,
                    tipo_bloque=tipo_bloque,
                    etiqueta_bloque=bloque.etiqueta_bloque
                    or self._default_etiqueta_bloque(tipo_bloque),
                    clave_bloque=clave_bloque,
                    ordinal_tipo=ordinal_tipo,
                    total_bloque=self._bloque_total(bloque),
                    concepto_financiero_codigo=self._concepto_codigo(tipo_bloque),
                )
            )
        return prepared

    def _build_bloque_payload(
        self,
        *,
        bloque: _PreparedBloque,
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
            importe_total_bloque=(
                input_bloque.importe_total_bloque
                if bloque.tipo_bloque != TIPO_BLOQUE_TRAMO_CUOTAS
                else None
            ),
            importe_cuota=input_bloque.importe_cuota,
            fecha_vencimiento=input_bloque.fecha_vencimiento,
            fecha_primer_vencimiento=input_bloque.fecha_primer_vencimiento,
            periodicidad=periodicidad,
            regla_redondeo=regla_redondeo,
            concepto_financiero_codigo=bloque.concepto_financiero_codigo,
            observaciones=input_bloque.observaciones,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

    def _build_obligaciones_bloque(
        self,
        *,
        prepared: _PreparedBloque,
        bloque: dict[str, Any],
        numero_obligacion_inicial: int,
        id_relacion_generadora: int,
        id_generacion_cronograma_financiero: int,
        concepto: dict[str, Any],
        comprador: dict[str, Any],
        moneda: str,
        now: datetime,
        id_instalacion: int | None,
        op_id: Any,
    ) -> list[ObligacionCronogramaV2CreatePayload]:
        if prepared.tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS:
            payloads: list[ObligacionCronogramaV2CreatePayload] = []
            for cuota_numero in range(1, (prepared.input.cantidad_cuotas or 0) + 1):
                fecha_vencimiento = add_months(
                    prepared.input.fecha_primer_vencimiento, cuota_numero - 1
                )
                payloads.append(
                    self._obligacion_payload(
                        prepared=prepared,
                        bloque=bloque,
                        numero_obligacion=numero_obligacion_inicial + cuota_numero - 1,
                        tipo_item_cronograma=TIPO_ITEM_CUOTA,
                        etiqueta_obligacion=f"Cuota {cuota_numero}",
                        item_numero=cuota_numero,
                        fecha_vencimiento=fecha_vencimiento,
                        importe_total=prepared.input.importe_cuota,
                        id_relacion_generadora=id_relacion_generadora,
                        id_generacion_cronograma_financiero=id_generacion_cronograma_financiero,
                        concepto=concepto,
                        comprador=comprador,
                        moneda=moneda,
                        now=now,
                        id_instalacion=id_instalacion,
                        op_id=op_id,
                    )
                )
            return payloads

        tipo_item = self._tipo_item_cronograma(prepared.tipo_bloque)
        return [
            self._obligacion_payload(
                prepared=prepared,
                bloque=bloque,
                numero_obligacion=numero_obligacion_inicial,
                tipo_item_cronograma=tipo_item,
                etiqueta_obligacion=prepared.etiqueta_bloque,
                item_numero=1,
                fecha_vencimiento=prepared.input.fecha_vencimiento,
                importe_total=prepared.input.importe_total_bloque,
                id_relacion_generadora=id_relacion_generadora,
                id_generacion_cronograma_financiero=id_generacion_cronograma_financiero,
                concepto=concepto,
                comprador=comprador,
                moneda=moneda,
                now=now,
                id_instalacion=id_instalacion,
                op_id=op_id,
            )
        ]

    def _obligacion_payload(
        self,
        *,
        prepared: _PreparedBloque,
        bloque: dict[str, Any],
        numero_obligacion: int,
        tipo_item_cronograma: str,
        etiqueta_obligacion: str,
        item_numero: int,
        fecha_vencimiento: date,
        importe_total: Decimal,
        id_relacion_generadora: int,
        id_generacion_cronograma_financiero: int,
        concepto: dict[str, Any],
        comprador: dict[str, Any],
        moneda: str,
        now: datetime,
        id_instalacion: int | None,
        op_id: Any,
    ) -> ObligacionCronogramaV2CreatePayload:
        clave_funcional = (
            f"PLAN_PAGO_VENTA:{bloque['id_plan_pago_venta']}:"
            f"BLOQUE:{prepared.numero_bloque}:{tipo_item_cronograma}:{item_numero}"
        )
        return ObligacionCronogramaV2CreatePayload(
            id_relacion_generadora=id_relacion_generadora,
            id_generacion_cronograma_financiero=id_generacion_cronograma_financiero,
            id_plan_pago_venta_bloque=bloque["id_plan_pago_venta_bloque"],
            numero_obligacion=numero_obligacion,
            tipo_item_cronograma=tipo_item_cronograma,
            etiqueta_obligacion=etiqueta_obligacion,
            clave_funcional_origen=clave_funcional,
            fecha_emision=fecha_vencimiento,
            fecha_vencimiento=fecha_vencimiento,
            importe_total=importe_total,
            moneda=moneda,
            estado_obligacion=ESTADO_OBLIGACION_PROYECTADA,
            id_concepto_financiero=concepto["id_concepto_financiero"],
            codigo_concepto_financiero=concepto["codigo_concepto_financiero"],
            id_persona_obligado=comprador["id_persona"],
            rol_obligado=ROL_OBLIGADO_COMPRADOR,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

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
        expected = self._prepare_bloques(
            command, id_plan_pago_venta=plan_vivo["id_plan_pago_venta"]
        )
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
        self, existing: dict[str, Any], expected: _PreparedBloque
    ) -> bool:
        return (
            existing["numero_bloque"] == expected.numero_bloque
            and existing["tipo_bloque"] == expected.tipo_bloque
            and existing["etiqueta_bloque"] == expected.etiqueta_bloque
            and existing["clave_bloque"] == expected.clave_bloque
            and existing["cantidad_cuotas"] == expected.input.cantidad_cuotas
            and self._decimal_or_none(existing["importe_total_bloque"])
            == self._decimal_or_none(expected.input.importe_total_bloque)
            and self._decimal_or_none(existing["importe_cuota"])
            == self._decimal_or_none(expected.input.importe_cuota)
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
        )

    def _resolve_conceptos(
        self, bloques: list[_PreparedBloque]
    ) -> dict[str, dict[str, Any]]:
        conceptos: dict[str, dict[str, Any]] = {}
        for codigo in {bloque.concepto_financiero_codigo for bloque in bloques}:
            concepto = self.repository.get_concepto_financiero_by_codigo(codigo)
            if concepto is None:
                raise ValueError(f"NOT_FOUND_CONCEPTO:{codigo}")
            conceptos[codigo] = concepto
        return conceptos

    def _resolve_comprador(self, id_venta: int) -> dict[str, Any]:
        compradores = self.repository.get_compradores_financieros_venta(id_venta)
        if not compradores:
            raise ValueError("COMPRADOR_VENTA_NO_RESUELTO")
        personas = {row["id_persona"] for row in compradores}
        if len(personas) != 1 or len(compradores) != 1:
            raise ValueError("COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO")
        return compradores[0]

    @staticmethod
    def _has_cent_precision(value: Decimal) -> bool:
        return value == value.quantize(Decimal("0.01"))

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def _bloque_total(self, bloque: PlanPagoVentaBloqueInput) -> Decimal:
        tipo_bloque = bloque.tipo_bloque.strip().upper()
        if tipo_bloque == TIPO_BLOQUE_TRAMO_CUOTAS:
            return (bloque.importe_cuota or Decimal("0.00")) * Decimal(
                bloque.cantidad_cuotas or 0
            )
        return bloque.importe_total_bloque or Decimal("0.00")

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

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()
