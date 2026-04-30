from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
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


EVENT_TYPE_CONTRATO_ALQUILER_ACTIVADO = "contrato_alquiler_activado"
TIPO_ORIGEN_CONTRATO_ALQUILER = "contrato_alquiler"
CONCEPTO_CANON_LOCATIVO = "CANON_LOCATIVO"


@dataclass(slots=True)
class HandleContratoAlquilerActivadoEventData:
    id_contrato_alquiler: int
    id_relacion_generadora: int
    relacion_generadora_created: bool
    obligacion_created: bool
    id_obligacion_financiera: int | None


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[dict[str, Any]]) -> None:
        self.result = result


class FinancieroRepository(Protocol):
    db: Any

    def get_contrato_alquiler_para_financiero(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None: ...

    def get_condicion_economica_vigente_para_financiero(
        self, id_contrato_alquiler: int, fecha_referencia: date
    ) -> dict[str, Any] | None: ...

    def get_relacion_generadora_by_origen(
        self, tipo_origen: str, id_origen: int
    ) -> dict[str, Any] | None: ...

    def create_relacion_generadora(
        self, payload: RelacionGeneradoraCreatePayload
    ) -> dict[str, Any]: ...

    def has_obligaciones_by_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> bool: ...

    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None: ...

    def create_obligacion_financiera(
        self,
        obligacion: ObligacionCreatePayload,
        composiciones: list[ComposicionCreatePayload],
    ) -> dict[str, Any]: ...


class HandleContratoAlquilerActivadoEventService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, event: dict[str, Any]) -> AppResult[dict[str, Any]]:
        if event.get("event_type") != EVENT_TYPE_CONTRATO_ALQUILER_ACTIVADO:
            return AppResult.fail("INVALID_EVENT_TYPE")

        payload = event.get("payload")
        if not isinstance(payload, dict):
            return AppResult.fail("INVALID_EVENT_PAYLOAD")

        id_contrato_alquiler = payload.get("id_contrato_alquiler")
        if not isinstance(id_contrato_alquiler, int) or id_contrato_alquiler <= 0:
            return AppResult.fail("INVALID_EVENT_PAYLOAD")

        try:
            with self._transaction():
                return self._execute_in_transaction(event, id_contrato_alquiler)
        except _RollbackAppResult as exc:
            return exc.result

    def _execute_in_transaction(
        self, event: dict[str, Any], id_contrato_alquiler: int
    ) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler_para_financiero(id_contrato_alquiler)
        if contrato is None:
            return AppResult.fail("NOT_FOUND_CONTRATO_ALQUILER")

        relacion_generadora = self.repository.get_relacion_generadora_by_origen(
            TIPO_ORIGEN_CONTRATO_ALQUILER, id_contrato_alquiler
        )
        relacion_generadora_created = False
        if relacion_generadora is None:
            relacion_generadora = self._create_relacion_generadora(id_contrato_alquiler, event)
            relacion_generadora_created = True

        id_relacion_generadora = relacion_generadora["id_relacion_generadora"]

        if self.repository.has_obligaciones_by_relacion_generadora(id_relacion_generadora):
            return AppResult.ok(
                {
                    "id_contrato_alquiler": id_contrato_alquiler,
                    "id_relacion_generadora": id_relacion_generadora,
                    "relacion_generadora_created": relacion_generadora_created,
                    "obligacion_created": False,
                    "id_obligacion_financiera": None,
                }
            )

        fecha_inicio = contrato["fecha_inicio"]
        fecha_ref = fecha_inicio.date() if isinstance(fecha_inicio, datetime) else fecha_inicio

        condicion = self.repository.get_condicion_economica_vigente_para_financiero(
            id_contrato_alquiler, fecha_ref
        )
        if condicion is None:
            raise _RollbackAppResult(AppResult.fail("NOT_FOUND_CONDICION_ECONOMICA"))

        concepto = self.repository.get_concepto_financiero_by_codigo(CONCEPTO_CANON_LOCATIVO)
        if concepto is None:
            raise _RollbackAppResult(
                AppResult.fail(f"NOT_FOUND_CONCEPTO:{CONCEPTO_CANON_LOCATIVO}")
            )

        now = datetime.now(UTC)
        monto_base = float(condicion["monto_base"])
        moneda = condicion.get("moneda") or "ARS"
        op_id = self._parse_op_id(event)

        obligacion = self.repository.create_obligacion_financiera(
            ObligacionCreatePayload(
                id_relacion_generadora=id_relacion_generadora,
                fecha_emision=fecha_ref,
                fecha_vencimiento=fecha_ref,
                importe_total=monto_base,
                estado_obligacion="PROYECTADA",
                uid_global=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=None,
                id_instalacion_ultima_modificacion=None,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            ),
            [
                ComposicionCreatePayload(
                    id_concepto_financiero=concepto["id_concepto_financiero"],
                    codigo_concepto_financiero=CONCEPTO_CANON_LOCATIVO,
                    orden_composicion=1,
                    importe_componente=monto_base,
                    uid_global=str(self.uuid_generator()),
                    version_registro=1,
                    created_at=now,
                    updated_at=now,
                    id_instalacion_origen=None,
                    id_instalacion_ultima_modificacion=None,
                    op_id_alta=op_id,
                    op_id_ultima_modificacion=op_id,
                )
            ],
        )

        return AppResult.ok(
            {
                "id_contrato_alquiler": id_contrato_alquiler,
                "id_relacion_generadora": id_relacion_generadora,
                "relacion_generadora_created": relacion_generadora_created,
                "obligacion_created": True,
                "id_obligacion_financiera": obligacion["id_obligacion_financiera"],
            }
        )

    def _create_relacion_generadora(
        self, id_contrato_alquiler: int, event: dict[str, Any]
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        return self.repository.create_relacion_generadora(
            RelacionGeneradoraCreatePayload(
                tipo_origen=TIPO_ORIGEN_CONTRATO_ALQUILER,
                id_origen=id_contrato_alquiler,
                descripcion="Relacion generadora creada desde contrato_alquiler_activado",
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
