from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.api.core_ef_headers import TechnicalCoreEFHeaders
from app.application.common.idempotency import (
    CANONICALIZATION_VERSION, ClaimDecision, ConflictKind, OperationClaim,
    OperationCompletion, canonical_payload_hash, claim_operation,
    complete_operation,
)
from app.infrastructure.persistence.repositories.calendario_comercial_command_repository import (
    CalendarioComercialCommandRepository,
)
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)

COMMAND_CODE = "ADMIN.CONFIG.CALENDARIO_COMERCIAL.BOOTSTRAP"
TARGET_TYPE = "CALENDARIO_COMERCIAL"
TARGET_KEY = "GLOBAL"


class BootstrapCalendarioComercialError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status, self.code = status, code


@dataclass
class BootstrapCalendarioComercialService:
    session: Session
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def execute(self, *, dia_cierre_comercial: int,
                dia_vencimiento_predeterminado_cuotas: int,
                vigente_desde: date, headers: TechnicalCoreEFHeaders,
                id_usuario: int) -> dict[str, Any]:
        payload_hash = canonical_payload_hash({
            "dia_cierre_comercial": dia_cierre_comercial,
            "dia_vencimiento_predeterminado_cuotas": dia_vencimiento_predeterminado_cuotas,
            "vigente_desde": vigente_desde.isoformat(),
        })
        claim = OperationClaim(headers.x_op_id, COMMAND_CODE, TARGET_TYPE, None,
                               TARGET_KEY, payload_hash)
        decision = claim_operation(self.session, claim)
        if decision.decision is ClaimDecision.REPLAY:
            snapshot = decision.replay.response_snapshot
            if not isinstance(snapshot, dict):
                raise BootstrapCalendarioComercialError(500, "IDEMPOTENCY_TECHNICAL_ERROR")
            return snapshot
        if decision.decision is ClaimDecision.CONFLICT:
            codes = {ConflictKind.COMMAND: "IDEMPOTENCY_COMMAND_CONFLICT",
                     ConflictKind.TARGET: "IDEMPOTENCY_TARGET_CONFLICT",
                     ConflictKind.PAYLOAD: "IDEMPOTENCY_PAYLOAD_CONFLICT"}
            raise BootstrapCalendarioComercialError(409, codes[decision.conflict])
        repository = CalendarioComercialCommandRepository(self.session)
        uid_instalacion_origen = repository.validate_context(
            headers.x_sucursal_id, headers.x_instalacion_id
        )
        if uid_instalacion_origen is None:
            raise BootstrapCalendarioComercialError(400, "inconsistencia_contexto_tecnico")
        repository.lock_global()
        empty, definitions = repository.inspect_bootstrap_state()
        if not empty:
            raise BootstrapCalendarioComercialError(409, "CONFIGURACION_CALENDARIO_COMERCIAL_CONFLICTO")
        values = {"DIA_CIERRE_COMERCIAL": dia_cierre_comercial,
                  "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS": (
                      dia_vencimiento_predeterminado_cuotas)}
        created = repository.create(definitions=definitions, values=values,
            vigente_desde=vigente_desde, op_id=headers.x_op_id,
            id_instalacion=headers.x_instalacion_id)
        root = created["root"]
        self._add_outbox(
            created=created,
            values=values,
            vigente_desde=vigente_desde,
            op_id=headers.x_op_id,
            uid_instalacion_origen=uid_instalacion_origen,
        )
        snapshot = {"ok": True, "data": {
            "estado": "COMPLETA", "uid_global": str(root["uid_global"]),
            "dia_cierre_comercial": dia_cierre_comercial,
            "dia_vencimiento_predeterminado_cuotas": dia_vencimiento_predeterminado_cuotas,
            "version_agregada": root["version_registro"],
            "fecha_desde": vigente_desde.isoformat() + "T00:00:00",
            "fecha_hasta": None,
        }}
        complete_operation(self.session, OperationCompletion(
            op_id=claim.op_id, command_code=claim.command_code,
            target_type=claim.target_type, target_uid=None,
            target_key=claim.target_key, payload_hash=claim.payload_hash,
            canonicalization_version=CANONICALIZATION_VERSION,
            result_code="CALENDARIO_COMERCIAL_CREADO", result_http_status=201,
            result_target_uid=root["uid_global"], result_version=1,
            response_snapshot=snapshot, id_usuario=id_usuario,
            id_sucursal=headers.x_sucursal_id,
            id_instalacion=headers.x_instalacion_id))
        return snapshot

    def _add_outbox(
        self,
        *,
        created: dict[str, Any],
        values: dict[str, int],
        vigente_desde: date,
        op_id: Any,
        uid_instalacion_origen: Any,
    ) -> None:
        root = created["root"]
        cierre = created["values"]["DIA_CIERRE_COMERCIAL"]
        vencimiento = created["values"][
            "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS"
        ]
        data = {
            "uid_global": str(root["uid_global"]),
            "version_agregada": root["version_registro"],
            "vigente_desde": vigente_desde.isoformat(),
            "fecha_hasta": None,
            "dia_cierre_comercial": values["DIA_CIERRE_COMERCIAL"],
            "dia_vencimiento_predeterminado_cuotas": values[
                "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS"
            ],
            "valor_dia_cierre_comercial": {
                "uid_global": str(cierre["uid_global"]),
                "version_registro": cierre["version_registro"],
            },
            "valor_dia_vencimiento_predeterminado_cuotas": {
                "uid_global": str(vencimiento["uid_global"]),
                "version_registro": vencimiento["version_registro"],
            },
            "op_id": str(op_id),
        }
        origin = str(uid_instalacion_origen)
        hash_input = {"metadata": {"uid_instalacion_origen": origin}, "data": data}
        payload = {
            "metadata": {
                "uid_instalacion_origen": origin,
                "payload_hash": canonical_payload_hash(hash_input),
            },
            "data": data,
        }
        occurred_at = self.clock()
        if occurred_at.tzinfo is None or occurred_at.utcoffset() != UTC.utcoffset(
            occurred_at
        ):
            raise BootstrapCalendarioComercialError(
                500, "TECHNICAL_INCONSISTENCY"
            )
        OutboxRepository(self.session).add_event(
            event_type="calendario_comercial_creado",
            aggregate_type="calendario_comercial",
            aggregate_id=root["id_configuracion_calendario_comercial"],
            payload=payload,
            occurred_at=occurred_at.replace(tzinfo=None),
            status="PENDING",
        )
