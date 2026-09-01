from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from itertools import pairwise
from typing import Any

from sqlalchemy.orm import Session

from app.api.core_ef_headers import AuthenticatedCoreEFHeaders
from app.application.administrativo.parametro_entero import parse_parametro_entero
from app.application.common.idempotency import (
    CANONICALIZATION_VERSION,
    ClaimDecision,
    ConflictKind,
    OperationClaim,
    OperationCompletion,
    canonical_payload_hash,
    claim_operation,
    complete_operation,
)
from app.infrastructure.persistence.repositories.calendario_comercial_command_repository import (
    CODIGOS,
    CalendarioComercialCommandRepository,
)
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)

COMMAND_CODE = "ADMIN.CONFIG.CALENDARIO_COMERCIAL.PROGRAMAR"
TARGET_TYPE = "CALENDARIO_COMERCIAL"
TARGET_KEY = "GLOBAL"


class ProgramarCalendarioComercialError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status, self.code = status, code


@dataclass
class ProgramarCalendarioComercialService:
    session: Session
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def execute(
        self,
        *,
        dia_cierre_comercial: int,
        dia_vencimiento_predeterminado_cuotas: int,
        vigente_desde: date,
        headers: AuthenticatedCoreEFHeaders,
        id_usuario: int,
    ) -> dict[str, Any]:
        request_hash = canonical_payload_hash(
            {
                "dia_cierre_comercial": dia_cierre_comercial,
                "dia_vencimiento_predeterminado_cuotas": dia_vencimiento_predeterminado_cuotas,
                "vigente_desde": vigente_desde.isoformat(),
                "if_match_version": headers.if_match_version,
            }
        )
        claim = OperationClaim(
            headers.x_op_id, COMMAND_CODE, TARGET_TYPE, None, TARGET_KEY, request_hash
        )
        decision = claim_operation(self.session, claim)
        if decision.decision is ClaimDecision.REPLAY:
            snapshot = decision.replay.response_snapshot
            if not isinstance(snapshot, dict):
                raise ProgramarCalendarioComercialError(
                    500, "IDEMPOTENCY_TECHNICAL_ERROR"
                )
            return snapshot
        if decision.decision is ClaimDecision.CONFLICT:
            codes = {
                ConflictKind.COMMAND: "IDEMPOTENCY_COMMAND_CONFLICT",
                ConflictKind.TARGET: "IDEMPOTENCY_TARGET_CONFLICT",
                ConflictKind.PAYLOAD: "IDEMPOTENCY_PAYLOAD_CONFLICT",
            }
            raise ProgramarCalendarioComercialError(409, codes[decision.conflict])

        repository = CalendarioComercialCommandRepository(self.session)
        origin = repository.validate_context(
            headers.x_sucursal_id, headers.x_instalacion_id
        )
        if origin is None:
            raise ProgramarCalendarioComercialError(
                400, "inconsistencia_contexto_tecnico"
            )
        # Jerarquía única de todos los writers del singleton calendario:
        # advisory aggregate → raíz total → definiciones → historia.
        repository.lock_global()
        root = repository.lock_active_root()
        if root is None:
            raise ProgramarCalendarioComercialError(
                409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
            )
        previous_version = root["version_registro"]
        if headers.if_match_version != previous_version:
            raise ProgramarCalendarioComercialError(412, "CONCURRENCY_ERROR")
        definitions, history = repository.lock_and_inspect_history()
        previous = self._validate_history(definitions, history)
        previous_start = previous[0]["fecha_desde"]
        new_start = datetime.combine(vigente_desde, datetime.min.time())
        if new_start <= previous_start:
            raise ProgramarCalendarioComercialError(
                409, "CALENDARIO_COMERCIAL_VIGENCIA_NO_APPEND_ONLY"
            )
        values = {
            CODIGOS[0]: dia_cierre_comercial,
            CODIGOS[1]: dia_vencimiento_predeterminado_cuotas,
        }
        changed = repository.program(
            root_id=root["id_configuracion_calendario_comercial"],
            definitions=definitions,
            previous=previous,
            values=values,
            vigente_desde=vigente_desde,
            op_id=headers.x_op_id,
            id_instalacion=headers.x_instalacion_id,
        )
        new_version = changed["root"]["version_registro"]
        if new_version != previous_version + 1:
            raise ProgramarCalendarioComercialError(500, "TECHNICAL_INCONSISTENCY")
        self._add_outbox(
            changed,
            values,
            vigente_desde,
            previous_start,
            headers.x_op_id,
            origin,
            previous_version,
        )
        snapshot = {
            "ok": True,
            "data": {
                "estado": "COMPLETA",
                "uid_global": str(root["uid_global"]),
                "dia_cierre_comercial": dia_cierre_comercial,
                "dia_vencimiento_predeterminado_cuotas": dia_vencimiento_predeterminado_cuotas,
                "version_agregada": new_version,
                "fecha_desde": vigente_desde.isoformat() + "T00:00:00",
                "fecha_hasta": None,
            },
        }
        complete_operation(
            self.session,
            OperationCompletion(
                op_id=claim.op_id,
                command_code=claim.command_code,
                target_type=claim.target_type,
                target_uid=None,
                target_key=claim.target_key,
                payload_hash=claim.payload_hash,
                canonicalization_version=CANONICALIZATION_VERSION,
                result_code="CALENDARIO_COMERCIAL_PROGRAMADO",
                result_http_status=200,
                result_target_uid=root["uid_global"],
                result_version=new_version,
                response_snapshot=snapshot,
                id_usuario=id_usuario,
                id_sucursal=headers.x_sucursal_id,
                id_instalacion=headers.x_instalacion_id,
            ),
        )
        return snapshot

    @staticmethod
    def _validate_history(
        definitions: dict[str, int], history: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if set(definitions) != set(CODIGOS) or not history:
            raise ProgramarCalendarioComercialError(
                409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
            )
        intervals: dict[tuple[Any, Any], dict[str, dict[str, Any]]] = {}
        for row in history:
            try:
                value = parse_parametro_entero(row["valor_parametro"])
            except ValueError as exc:
                raise ProgramarCalendarioComercialError(
                    409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
                ) from exc
            if not 1 <= value <= 31:
                raise ProgramarCalendarioComercialError(
                    409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
                )
            start, end = row["fecha_desde"], row["fecha_hasta"]
            if start is None or (end is not None and start >= end):
                raise ProgramarCalendarioComercialError(
                    409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
                )
            if row["es_valor_vigente"] is not (end is None):
                raise ProgramarCalendarioComercialError(
                    409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
                )
            pair = intervals.setdefault((start, end), {})
            if row["codigo_parametro"] in pair:
                raise ProgramarCalendarioComercialError(
                    409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
                )
            pair[row["codigo_parametro"]] = row
        ordered = sorted(intervals, key=lambda interval: interval[0])
        if any(set(pair) != set(CODIGOS) for pair in intervals.values()):
            raise ProgramarCalendarioComercialError(
                409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
            )
        if any(a[1] != b[0] for a, b in pairwise(ordered)):
            raise ProgramarCalendarioComercialError(
                409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
            )
        if ordered[-1][1] is not None or sum(end is None for _, end in ordered) != 1:
            raise ProgramarCalendarioComercialError(
                409, "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
            )
        return [intervals[ordered[-1]][code] for code in CODIGOS]

    def _add_outbox(
        self,
        changed: dict[str, Any],
        values: dict[str, int],
        vigente_desde: date,
        previous_start: datetime,
        op_id: Any,
        origin: Any,
        previous_version: int,
    ) -> None:
        root, created, previous = (
            changed["root"],
            changed["values"],
            changed["previous"],
        )
        data = {
            "uid_global": str(root["uid_global"]),
            "version_agregada": root["version_registro"],
            "version_agregada_anterior": previous_version,
            "vigente_desde": vigente_desde.isoformat(),
            "fecha_desde_vigencia_anterior": previous_start.date().isoformat(),
            "fecha_hasta_vigencia_anterior": vigente_desde.isoformat(),
            "dia_cierre_comercial": values[CODIGOS[0]],
            "dia_vencimiento_predeterminado_cuotas": values[CODIGOS[1]],
            "valor_dia_cierre_comercial": self._portable(created[CODIGOS[0]]),
            "valor_dia_vencimiento_predeterminado_cuotas": self._portable(
                created[CODIGOS[1]]
            ),
            "valor_anterior_dia_cierre_comercial": self._portable_previous(
                previous[CODIGOS[0]]
            ),
            "valor_anterior_dia_vencimiento_predeterminado_cuotas": self._portable_previous(
                previous[CODIGOS[1]]
            ),
            "op_id": str(op_id),
        }
        origin_text = str(origin)
        hash_input = {"metadata": {"uid_instalacion_origen": origin_text}, "data": data}
        payload = {
            "metadata": {
                "uid_instalacion_origen": origin_text,
                "payload_hash": canonical_payload_hash(hash_input),
            },
            "data": data,
        }
        occurred_at = self.clock()
        if occurred_at.tzinfo is None or occurred_at.utcoffset() != UTC.utcoffset(
            occurred_at
        ):
            raise ProgramarCalendarioComercialError(500, "TECHNICAL_INCONSISTENCY")
        OutboxRepository(self.session).add_event(
            event_type="calendario_comercial_programado",
            aggregate_type="calendario_comercial",
            aggregate_id=root["id_configuracion_calendario_comercial"],
            payload=payload,
            occurred_at=occurred_at.replace(tzinfo=None),
            status="PENDING",
        )

    @staticmethod
    def _portable(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"],
        }

    @staticmethod
    def _portable_previous(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"] + 1,
        }
