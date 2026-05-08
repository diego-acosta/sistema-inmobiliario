from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.services.create_obligacion_financiera_service import (
    ComposicionCreatePayload,
    ObligacionCreatePayload,
)
from app.application.financiero.services.create_relacion_generadora_service import (
    RelacionGeneradoraCreatePayload,
)


EVENT_TYPE_VENTA_CONFIRMADA = "venta_confirmada"
TIPO_ORIGEN_VENTA = "venta"
CONCEPTO_CAPITAL_VENTA = "CAPITAL_VENTA"
CONCEPTO_ANTICIPO_VENTA = "ANTICIPO_VENTA"
ROL_OBLIGADO_COMPRADOR = "COMPRADOR"
TIPO_PLAN_CONTADO = "CONTADO"
TIPO_PLAN_ANTICIPO_Y_SALDO = "ANTICIPO_Y_SALDO"


@dataclass(slots=True)
class HandleVentaConfirmadaEventData:
    id_venta: int
    id_relacion_generadora: int
    relacion_generadora_created: bool
    obligacion_created: bool
    id_obligacion_financiera: int | None


@dataclass(slots=True)
class ObligadoVentaCreatePayload:
    id_obligacion_financiera: int
    id_persona: int
    rol_obligado: str
    porcentaje_responsabilidad: float
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: int | None
    id_instalacion_ultima_modificacion: int | None
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class VentaObligacionPlan:
    codigo_concepto_financiero: str
    importe: Decimal
    fecha_vencimiento: date


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[dict[str, Any]]) -> None:
        self.result = result


class FinancieroRepository(Protocol):
    db: Any

    def get_venta_minima_para_financiero(
        self, id_venta: int
    ) -> dict[str, Any] | None:
        ...

    def get_relacion_generadora_by_origen(
        self, tipo_origen: str, id_origen: int
    ) -> dict[str, Any] | None:
        ...

    def create_relacion_generadora(
        self, payload: RelacionGeneradoraCreatePayload
    ) -> dict[str, Any]:
        ...

    def has_obligaciones_by_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> bool:
        ...

    def get_obligacion_activa_by_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> dict[str, Any] | None:
        ...

    def get_obligaciones_activas_by_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> list[dict[str, Any]]:
        ...

    def get_obligados_by_obligacion(
        self, id_obligacion_financiera: int
    ) -> list[dict[str, Any]]:
        ...

    def get_compradores_financieros_venta(
        self, id_venta: int
    ) -> list[dict[str, Any]]:
        ...

    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None:
        ...

    def create_obligacion_financiera(
        self,
        obligacion: ObligacionCreatePayload,
        composiciones: list[ComposicionCreatePayload],
    ) -> dict[str, Any]:
        ...

    def create_obligacion_obligado(
        self,
        payload: ObligadoVentaCreatePayload,
    ) -> dict[str, Any]:
        ...


class HandleVentaConfirmadaEventService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, event: dict[str, Any]) -> AppResult[dict[str, Any]]:
        if event.get("event_type") != EVENT_TYPE_VENTA_CONFIRMADA:
            return AppResult.fail("INVALID_EVENT_TYPE")

        payload = event.get("payload")
        if not isinstance(payload, dict):
            return AppResult.fail("INVALID_EVENT_PAYLOAD")

        id_venta = payload.get("id_venta")
        if not isinstance(id_venta, int) or id_venta <= 0:
            return AppResult.fail("INVALID_EVENT_PAYLOAD")

        try:
            with self._transaction():
                return self._execute_in_transaction(event, id_venta)
        except _RollbackAppResult as exc:
            return exc.result

    def _execute_in_transaction(
        self, event: dict[str, Any], id_venta: int
    ) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta_minima_para_financiero(id_venta)
        if venta is None:
            return AppResult.fail("NOT_FOUND_VENTA")

        estado_venta = (venta["estado_venta"] or "").strip().lower()
        if estado_venta != "confirmada":
            return AppResult.fail("INVALID_VENTA_STATE")

        monto_total = venta["monto_total"]
        if monto_total is None or monto_total <= 0:
            return AppResult.fail("INVALID_MONTO_TOTAL")

        relacion_generadora = self.repository.get_relacion_generadora_by_origen(
            TIPO_ORIGEN_VENTA,
            id_venta,
        )
        relacion_generadora_created = False
        obligaciones_existentes: list[dict[str, Any]] = []
        if relacion_generadora is not None:
            obligaciones_existentes = (
                self.repository.get_obligaciones_activas_by_relacion_generadora(
                    relacion_generadora["id_relacion_generadora"]
                )
            )
            if obligaciones_existentes:
                obligaciones_sin_obligado = [
                    obligacion
                    for obligacion in obligaciones_existentes
                    if not self.repository.get_obligados_by_obligacion(
                        obligacion["id_obligacion_financiera"]
                    )
                ]
                if not obligaciones_sin_obligado:
                    return AppResult.ok(
                        self._result_payload(
                            id_venta=id_venta,
                            id_relacion_generadora=relacion_generadora[
                                "id_relacion_generadora"
                            ],
                            relacion_generadora_created=False,
                            obligacion_created=False,
                            obligado_created=False,
                            obligaciones=obligaciones_existentes,
                        )
                    )

        comprador = self._resolve_comprador_financiero(id_venta)

        if relacion_generadora is None:
            relacion_generadora = self._create_relacion_generadora(id_venta, event)
            relacion_generadora_created = True

        id_relacion_generadora = relacion_generadora["id_relacion_generadora"]
        if obligaciones_existentes:
            obligado_created = False
            for obligacion_existente in obligaciones_existentes:
                obligados = self.repository.get_obligados_by_obligacion(
                    obligacion_existente["id_obligacion_financiera"]
                )
                if obligados:
                    continue
                self._create_obligado(
                    id_obligacion_financiera=obligacion_existente[
                        "id_obligacion_financiera"
                    ],
                    id_persona=comprador["id_persona"],
                    event=event,
                )
                obligado_created = True
            return AppResult.ok(
                self._result_payload(
                    id_venta=id_venta,
                    id_relacion_generadora=id_relacion_generadora,
                    relacion_generadora_created=False,
                    obligacion_created=False,
                    obligado_created=obligado_created,
                    obligaciones=obligaciones_existentes,
                )
            )

        plan_result = self._build_plan(venta)
        if not plan_result.success or plan_result.data is None:
            raise _RollbackAppResult(AppResult.fail(plan_result.errors[0]))

        conceptos: dict[str, dict[str, Any]] = {}
        for item in plan_result.data:
            concepto = self.repository.get_concepto_financiero_by_codigo(
                item.codigo_concepto_financiero
            )
            if concepto is not None:
                conceptos[item.codigo_concepto_financiero] = concepto
        missing = [
            item.codigo_concepto_financiero
            for item in plan_result.data
            if item.codigo_concepto_financiero not in conceptos
        ]
        if missing:
            raise _RollbackAppResult(
                AppResult.fail(f"NOT_FOUND_CONCEPTO:{missing[0]}")
            )

        now = datetime.now(UTC)
        moneda = (venta.get("moneda") or "ARS").strip().upper()
        obligaciones_creadas: list[dict[str, Any]] = []
        for item in plan_result.data:
            concepto = conceptos[item.codigo_concepto_financiero]
            obligacion = self.repository.create_obligacion_financiera(
                ObligacionCreatePayload(
                    id_relacion_generadora=id_relacion_generadora,
                    fecha_emision=item.fecha_vencimiento,
                    fecha_vencimiento=item.fecha_vencimiento,
                    importe_total=float(item.importe),
                    estado_obligacion="PROYECTADA",
                    uid_global=str(self.uuid_generator()),
                    version_registro=1,
                    created_at=now,
                    updated_at=now,
                    id_instalacion_origen=None,
                    id_instalacion_ultima_modificacion=None,
                    op_id_alta=self._parse_op_id(event),
                    op_id_ultima_modificacion=self._parse_op_id(event),
                    moneda=moneda,
                ),
                [
                    ComposicionCreatePayload(
                        id_concepto_financiero=concepto["id_concepto_financiero"],
                        codigo_concepto_financiero=item.codigo_concepto_financiero,
                        orden_composicion=1,
                        importe_componente=float(item.importe),
                        uid_global=str(self.uuid_generator()),
                        version_registro=1,
                        created_at=now,
                        updated_at=now,
                        id_instalacion_origen=None,
                        id_instalacion_ultima_modificacion=None,
                        op_id_alta=self._parse_op_id(event),
                        op_id_ultima_modificacion=self._parse_op_id(event),
                        moneda_componente=moneda,
                    )
                ],
            )
            self._create_obligado(
                id_obligacion_financiera=obligacion["id_obligacion_financiera"],
                id_persona=comprador["id_persona"],
                event=event,
            )
            obligaciones_creadas.append(obligacion)

        return AppResult.ok(
            self._result_payload(
                id_venta=id_venta,
                id_relacion_generadora=id_relacion_generadora,
                relacion_generadora_created=relacion_generadora_created,
                obligacion_created=True,
                obligado_created=True,
                obligaciones=obligaciones_creadas,
            )
        )

    def _build_plan(self, venta: dict[str, Any]) -> AppResult[list[VentaObligacionPlan]]:
        tipo_plan = (venta.get("tipo_plan_financiero") or TIPO_PLAN_CONTADO).strip().upper()
        if tipo_plan == TIPO_PLAN_CONTADO:
            fecha_venta = venta["fecha_venta"]
            fecha_vencimiento = (
                fecha_venta.date() if isinstance(fecha_venta, datetime) else fecha_venta
            )
            return AppResult.ok(
                [
                    VentaObligacionPlan(
                        codigo_concepto_financiero=CONCEPTO_CAPITAL_VENTA,
                        importe=Decimal(str(venta["monto_total"])),
                        fecha_vencimiento=fecha_vencimiento,
                    )
                ]
            )

        if tipo_plan != TIPO_PLAN_ANTICIPO_Y_SALDO:
            return AppResult.fail("INVALID_TIPO_PLAN_FINANCIERO")

        importe_anticipo = venta.get("importe_anticipo")
        importe_saldo = venta.get("importe_saldo")
        fecha_anticipo = venta.get("fecha_vencimiento_anticipo")
        fecha_saldo = venta.get("fecha_vencimiento_saldo")
        if (
            importe_anticipo is None
            or importe_saldo is None
            or fecha_anticipo is None
            or fecha_saldo is None
        ):
            return AppResult.fail("INVALID_PLAN_ANTICIPO_Y_SALDO")

        anticipo = Decimal(str(importe_anticipo))
        saldo = Decimal(str(importe_saldo))
        total = Decimal(str(venta["monto_total"]))
        if anticipo <= 0 or saldo <= 0 or anticipo + saldo != total:
            return AppResult.fail("INVALID_PLAN_ANTICIPO_Y_SALDO")

        return AppResult.ok(
            [
                VentaObligacionPlan(
                    codigo_concepto_financiero=CONCEPTO_ANTICIPO_VENTA,
                    importe=anticipo,
                    fecha_vencimiento=fecha_anticipo,
                ),
                VentaObligacionPlan(
                    codigo_concepto_financiero=CONCEPTO_CAPITAL_VENTA,
                    importe=saldo,
                    fecha_vencimiento=fecha_saldo,
                ),
            ]
        )

    @staticmethod
    def _result_payload(
        *,
        id_venta: int,
        id_relacion_generadora: int,
        relacion_generadora_created: bool,
        obligacion_created: bool,
        obligado_created: bool,
        obligaciones: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ids = [item["id_obligacion_financiera"] for item in obligaciones]
        return {
            "id_venta": id_venta,
            "id_relacion_generadora": id_relacion_generadora,
            "created": relacion_generadora_created,
            "relacion_generadora_created": relacion_generadora_created,
            "obligacion_created": obligacion_created,
            "obligado_created": obligado_created,
            "id_obligacion_financiera": ids[0] if ids else None,
            "id_obligaciones_financieras": ids,
        }

    def _resolve_comprador_financiero(self, id_venta: int) -> dict[str, Any]:
        compradores = self.repository.get_compradores_financieros_venta(id_venta)
        if not compradores:
            raise _RollbackAppResult(AppResult.fail("COMPRADOR_VENTA_NO_RESUELTO"))
        personas = {row["id_persona"] for row in compradores}
        if len(personas) != 1 or len(compradores) != 1:
            raise _RollbackAppResult(
                AppResult.fail("COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO")
            )
        return compradores[0]

    def _create_obligado(
        self,
        *,
        id_obligacion_financiera: int,
        id_persona: int,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        return self.repository.create_obligacion_obligado(
            ObligadoVentaCreatePayload(
                id_obligacion_financiera=id_obligacion_financiera,
                id_persona=id_persona,
                rol_obligado=ROL_OBLIGADO_COMPRADOR,
                porcentaje_responsabilidad=100.00,
                uid_global=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=None,
                id_instalacion_ultima_modificacion=None,
                op_id_alta=self._parse_op_id(event),
                op_id_ultima_modificacion=self._parse_op_id(event),
            )
        )

    def _create_relacion_generadora(
        self, id_venta: int, event: dict[str, Any]
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        return self.repository.create_relacion_generadora(
            RelacionGeneradoraCreatePayload(
                tipo_origen=TIPO_ORIGEN_VENTA,
                id_origen=id_venta,
                descripcion="Relacion generadora creada desde venta_confirmada",
                uid_global=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=None,
                id_instalacion_ultima_modificacion=None,
                op_id_alta=self._parse_op_id(event),
                op_id_ultima_modificacion=self._parse_op_id(event),
            )
        )

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()

    @staticmethod
    def _parse_op_id(event: dict[str, Any]) -> UUID | None:
        value = event.get("op_id") or event.get("request_id")
        if not isinstance(value, str):
            return None
        try:
            return UUID(value)
        except ValueError:
            return None
