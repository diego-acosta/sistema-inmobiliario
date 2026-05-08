from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
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
ROL_OBLIGADO_COMPRADOR = "COMPRADOR"


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
        obligacion_existente = None
        if relacion_generadora is not None:
            obligacion_existente = (
                self.repository.get_obligacion_activa_by_relacion_generadora(
                    relacion_generadora["id_relacion_generadora"]
                )
            )
            if obligacion_existente is not None:
                obligados = self.repository.get_obligados_by_obligacion(
                    obligacion_existente["id_obligacion_financiera"]
                )
                if obligados:
                    return AppResult.ok(
                        {
                            "id_venta": id_venta,
                            "id_relacion_generadora": relacion_generadora[
                                "id_relacion_generadora"
                            ],
                            "created": False,
                            "relacion_generadora_created": False,
                            "obligacion_created": False,
                            "obligado_created": False,
                            "id_obligacion_financiera": obligacion_existente[
                                "id_obligacion_financiera"
                            ],
                        }
                    )

        comprador = self._resolve_comprador_financiero(id_venta)

        if relacion_generadora is None:
            relacion_generadora = self._create_relacion_generadora(id_venta, event)
            relacion_generadora_created = True

        id_relacion_generadora = relacion_generadora["id_relacion_generadora"]
        if obligacion_existente is not None:
            self._create_obligado(
                id_obligacion_financiera=obligacion_existente[
                    "id_obligacion_financiera"
                ],
                id_persona=comprador["id_persona"],
                event=event,
            )
            return AppResult.ok(
                {
                    "id_venta": id_venta,
                    "id_relacion_generadora": id_relacion_generadora,
                    "created": False,
                    "relacion_generadora_created": False,
                    "obligacion_created": False,
                    "obligado_created": True,
                    "id_obligacion_financiera": obligacion_existente[
                        "id_obligacion_financiera"
                    ],
                }
            )

        concepto = self.repository.get_concepto_financiero_by_codigo(
            CONCEPTO_CAPITAL_VENTA
        )
        if concepto is None:
            raise _RollbackAppResult(
                AppResult.fail(f"NOT_FOUND_CONCEPTO:{CONCEPTO_CAPITAL_VENTA}")
            )

        now = datetime.now(UTC)
        fecha_venta = venta["fecha_venta"]
        fecha_vencimiento = (
            fecha_venta.date() if isinstance(fecha_venta, datetime) else fecha_venta
        )
        obligacion = self.repository.create_obligacion_financiera(
            ObligacionCreatePayload(
                id_relacion_generadora=id_relacion_generadora,
                fecha_emision=fecha_vencimiento,
                fecha_vencimiento=fecha_vencimiento,
                importe_total=float(monto_total),
                estado_obligacion="PROYECTADA",
                uid_global=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=None,
                id_instalacion_ultima_modificacion=None,
                op_id_alta=self._parse_op_id(event),
                op_id_ultima_modificacion=self._parse_op_id(event),
            ),
            [
                ComposicionCreatePayload(
                    id_concepto_financiero=concepto["id_concepto_financiero"],
                    codigo_concepto_financiero=CONCEPTO_CAPITAL_VENTA,
                    orden_composicion=1,
                    importe_componente=float(monto_total),
                    uid_global=str(self.uuid_generator()),
                    version_registro=1,
                    created_at=now,
                    updated_at=now,
                    id_instalacion_origen=None,
                    id_instalacion_ultima_modificacion=None,
                    op_id_alta=self._parse_op_id(event),
                    op_id_ultima_modificacion=self._parse_op_id(event),
                )
            ],
        )
        self._create_obligado(
            id_obligacion_financiera=obligacion["id_obligacion_financiera"],
            id_persona=comprador["id_persona"],
            event=event,
        )

        return AppResult.ok(
            {
                "id_venta": id_venta,
                "id_relacion_generadora": id_relacion_generadora,
                "created": relacion_generadora_created,
                "relacion_generadora_created": relacion_generadora_created,
                "obligacion_created": True,
                "obligado_created": True,
                "id_obligacion_financiera": obligacion[
                    "id_obligacion_financiera"
                ],
            }
        )

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
