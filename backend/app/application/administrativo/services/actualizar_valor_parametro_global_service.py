from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.application.administrativo.parametro_entero import parse_parametro_entero
from app.application.common.central_command import CentralCommandMetadata
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
from app.infrastructure.persistence.repositories.valor_parametro_global_command_repository import (
    ValorParametroGlobalCommandRepository,
)

COMMAND_CODE = "ADMIN.CONFIG.PARAMETRO.VALOR_GLOBAL.UPDATE"
TARGET_TYPE = "VALOR_PARAMETRO"
CALENDARIO_COMERCIAL_PARAMETER_CODES = frozenset(
    {
        "DIA_CIERRE_COMERCIAL",
        "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS",
    }
)


class ParametroCommandError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code


@dataclass
class ActualizarValorParametroGlobalService:
    session: Session

    def execute(
        self,
        *,
        codigo_parametro: str,
        valor_tipado: int,
        metadata: CentralCommandMetadata,
        id_usuario: int,
    ) -> dict[str, Any]:
        if metadata.expected_version is None:
            raise ParametroCommandError(500, "TECHNICAL_INCONSISTENCY")
        if codigo_parametro in CALENDARIO_COMERCIAL_PARAMETER_CODES:
            raise ParametroCommandError(409, "conflicto_parametro")

        repository = ValorParametroGlobalCommandRepository(self.session)
        eligibility, target_id = repository.preflight_target(codigo_parametro)
        if eligibility == "NOT_FOUND":
            raise ParametroCommandError(404, "parametro_no_encontrado")
        if eligibility != "OK" or target_id is None:
            raise ParametroCommandError(409, "conflicto_parametro")

        payload_hash = canonical_payload_hash(
            {
                "actor": {"type": "HUMAN", "id_usuario": id_usuario},
                "scope": {"mode": "GLOBAL", "id_sucursal": None},
                "payload": {
                    "codigo_parametro": codigo_parametro,
                    "valor": str(valor_tipado),
                    "if_match_version": metadata.expected_version,
                },
            }
        )
        claim = OperationClaim(
            op_id=metadata.op_id,
            command_code=COMMAND_CODE,
            target_type=TARGET_TYPE,
            target_uid=None,
            target_key=codigo_parametro,
            payload_hash=payload_hash,
            canonicalization_version=CANONICALIZATION_VERSION,
        )
        decision = claim_operation(self.session, claim)
        if decision.decision is ClaimDecision.REPLAY:
            snapshot = decision.replay.response_snapshot
            if not isinstance(snapshot, dict):
                raise ParametroCommandError(500, "IDEMPOTENCY_TECHNICAL_ERROR")
            return snapshot
        if decision.decision is ClaimDecision.CONFLICT:
            codes = {
                ConflictKind.COMMAND: "IDEMPOTENCY_COMMAND_CONFLICT",
                ConflictKind.TARGET: "IDEMPOTENCY_TARGET_CONFLICT",
                ConflictKind.PAYLOAD: "IDEMPOTENCY_PAYLOAD_CONFLICT",
            }
            raise ParametroCommandError(409, codes[decision.conflict])

        locked = repository.lock_target(target_id)
        if locked is None or not self._operable(locked):
            raise ParametroCommandError(409, "conflicto_parametro")
        if locked["version_registro"] != metadata.expected_version:
            raise ParametroCommandError(412, "CONCURRENCY_ERROR")
        try:
            current = parse_parametro_entero(locked["valor_raw"])
        except ValueError as exc:
            raise ParametroCommandError(500, "inconsistencia_parametro") from exc

        changed = current != valor_tipado
        result = locked
        if changed:
            result = repository.cas_update(
                id_valor_parametro=target_id,
                valor_parametro=str(valor_tipado),
                op_id=metadata.op_id,
                if_match_version=metadata.expected_version,
            )
            if result is None:
                raise ParametroCommandError(412, "CONCURRENCY_ERROR")

        snapshot = {
            "ok": True,
            "data": {
                "codigo_parametro": codigo_parametro,
                "uid_global": str(result["uid_global"]),
                "valor_tipado": valor_tipado,
                "version_registro": result["version_registro"],
                "updated_at": result["updated_at"].isoformat(),
            },
        }
        complete_operation(
            self.session,
            OperationCompletion(
                op_id=claim.op_id,
                command_code=claim.command_code,
                target_type=claim.target_type,
                target_uid=claim.target_uid,
                target_key=claim.target_key,
                payload_hash=claim.payload_hash,
                canonicalization_version=claim.canonicalization_version,
                result_code=(
                    "PARAMETRO_GLOBAL_MODIFICADO"
                    if changed
                    else "PARAMETRO_GLOBAL_SIN_CAMBIOS"
                ),
                result_http_status=200,
                result_target_uid=result["uid_global"],
                result_version=result["version_registro"],
                response_snapshot=snapshot,
                id_usuario=id_usuario,
                id_sucursal=None,
                id_instalacion=None,
            ),
        )
        return snapshot

    @staticmethod
    def _operable(row: dict[str, Any]) -> bool:
        return (
            row["id_sucursal"] is None
            and row["id_instalacion"] is None
            and row["es_valor_vigente"] is True
            and row["deleted_at"] is None
            and row["version_registro"] >= 1
            and row["exponible_api_administrativa"] is True
            and row["es_sensible"] is False
            and row["editable_administrativamente"] is True
            and row["codigo_tipo_dato"] == "ENTERO"
            and row["codigo_alcance"] == "GLOBAL"
        )
