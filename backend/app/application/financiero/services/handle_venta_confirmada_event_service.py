from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.services.create_relacion_generadora_service import (
    RelacionGeneradoraCreatePayload,
)


EVENT_TYPE_VENTA_CONFIRMADA = "venta_confirmada"
TIPO_ORIGEN_VENTA = "venta"


@dataclass(slots=True)
class HandleVentaConfirmadaEventData:
    id_venta: int
    id_relacion_generadora: int
    created: bool


class FinancieroRepository(Protocol):
    def get_relacion_generadora_by_origen(
        self, tipo_origen: str, id_origen: int
    ) -> dict[str, Any] | None:
        ...

    def create_relacion_generadora(
        self, payload: RelacionGeneradoraCreatePayload
    ) -> dict[str, Any]:
        ...


class HandleVentaConfirmadaEventService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
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

        existing = self.repository.get_relacion_generadora_by_origen(
            TIPO_ORIGEN_VENTA,
            id_venta,
        )
        if existing is not None:
            return AppResult.ok(
                {
                    "id_venta": id_venta,
                    "id_relacion_generadora": existing["id_relacion_generadora"],
                    "created": False,
                }
            )

        now = datetime.now(UTC)
        created = self.repository.create_relacion_generadora(
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

        return AppResult.ok(
            {
                "id_venta": id_venta,
                "id_relacion_generadora": created["id_relacion_generadora"],
                "created": True,
            }
        )

    @staticmethod
    def _parse_op_id(event: dict[str, Any]) -> UUID | None:
        value = event.get("op_id") or event.get("request_id")
        if not isinstance(value, str):
            return None
        try:
            return UUID(value)
        except ValueError:
            return None
