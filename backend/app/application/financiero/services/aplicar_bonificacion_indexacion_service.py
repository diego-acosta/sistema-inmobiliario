from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult


_Q = Decimal("0.01")


class FinancieroRepository(Protocol):
    def get_obligacion_financiera(
        self, id_obligacion_financiera: int
    ) -> dict[str, Any] | None: ...

    def obligacion_tiene_aplicaciones_activas(
        self, id_obligacion_financiera: int
    ) -> bool: ...

    def aplicar_bonificacion_indexacion_obligacion(
        self,
        *,
        id_obligacion_financiera: int,
        importe_bonificacion: Decimal,
        motivo: str,
        fecha_bonificacion: date,
        uid_movimiento: str,
        uuid_generator: Any,
        id_instalacion: Any,
        op_id: UUID | None,
    ) -> dict[str, Any]: ...


class AplicarBonificacionIndexacionService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        *,
        id_obligacion_financiera: int,
        importe_bonificacion: float,
        motivo: str,
        fecha_bonificacion: date,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        importe = Decimal(str(importe_bonificacion)).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        if importe <= 0:
            return AppResult.fail("IMPORTE_BONIFICACION_INVALIDO")

        motivo_normalizado = motivo.strip()
        if not motivo_normalizado:
            return AppResult.fail("MOTIVO_REQUERIDO")

        obligacion = self.repository.get_obligacion_financiera(
            id_obligacion_financiera
        )
        if obligacion is None or obligacion.get("deleted_at") is not None:
            return AppResult.fail("NOT_FOUND_OBLIGACION")
        if obligacion.get("estado_obligacion") in {"ANULADA", "REEMPLAZADA"}:
            return AppResult.fail("ESTADO_NO_ACEPTA_BONIFICACION")
        if not self.repository.obligacion_tiene_aplicaciones_activas(
            id_obligacion_financiera
        ):
            return AppResult.fail("OBLIGACION_SIN_PAGOS_APLICADOS")

        try:
            data = self.repository.aplicar_bonificacion_indexacion_obligacion(
                id_obligacion_financiera=id_obligacion_financiera,
                importe_bonificacion=importe,
                motivo=motivo_normalizado,
                fecha_bonificacion=fecha_bonificacion,
                uid_movimiento=str(self.uuid_generator()),
                uuid_generator=self.uuid_generator,
                id_instalacion=getattr(context, "id_instalacion", None),
                op_id=getattr(context, "op_id", None),
            )
        except ValueError as exc:
            return AppResult.fail(str(exc))

        return AppResult.ok(data)
