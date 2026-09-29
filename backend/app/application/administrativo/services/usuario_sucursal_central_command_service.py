from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from app.infrastructure.persistence.repositories.usuario_sucursal_repository import (
    UsuarioSucursalDuplicateActiveError,
    UsuarioSucursalIneligibleTargetError,
    UsuarioSucursalRepository,
    UsuarioSucursalTechnicalError,
)

COMMAND_CODE = "ADMIN.USUARIO_SUCURSAL.ASIGNAR"
TARGET_TYPE = "USUARIO_SUCURSAL"


class UsuarioSucursalCommandError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code


def _conflict_code(kind: ConflictKind) -> str:
    return {
        ConflictKind.COMMAND: "IDEMPOTENCY_COMMAND_CONFLICT",
        ConflictKind.TARGET: "IDEMPOTENCY_TARGET_CONFLICT",
        ConflictKind.PAYLOAD: "IDEMPOTENCY_PAYLOAD_CONFLICT",
    }[kind]


def _target_key(id_usuario: int, id_sucursal: int) -> str:
    return f"usuario:{id_usuario}:sucursal:{id_sucursal}"


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "data": {
            key: value.isoformat() if hasattr(value, "isoformat") else value
            for key, value in row.items()
        },
    }


@dataclass
class UsuarioSucursalCentralCommandService:
    session: Session

    def assign(
        self,
        *,
        id_usuario: int,
        payload: dict[str, Any],
        metadata: CentralCommandMetadata,
        id_usuario_actor: int,
    ) -> dict[str, Any]:
        id_sucursal = payload["id_sucursal"]
        canonical_payload = {
            "id_usuario": id_usuario,
            "id_sucursal": id_sucursal,
            "tipo_habilitacion_sucursal": payload[
                "tipo_habilitacion_sucursal"
            ],
            "es_sucursal_predeterminada": payload[
                "es_sucursal_predeterminada"
            ],
            "puede_operar": payload["puede_operar"],
            "puede_consultar": payload["puede_consultar"],
            "puede_administrar": payload["puede_administrar"],
            "fecha_desde": payload["fecha_desde"].isoformat(),
            "fecha_hasta": (
                payload["fecha_hasta"].isoformat()
                if payload["fecha_hasta"] is not None
                else None
            ),
            "observaciones": payload["observaciones"],
        }
        payload_hash = canonical_payload_hash(
            {
                "actor": {"type": "HUMAN", "id_usuario": id_usuario_actor},
                "scope": {"mode": "GLOBAL", "id_sucursal": None},
                "payload": canonical_payload,
            }
        )
        claim = OperationClaim(
            op_id=metadata.op_id,
            command_code=COMMAND_CODE,
            target_type=TARGET_TYPE,
            target_uid=None,
            target_key=_target_key(id_usuario, id_sucursal),
            payload_hash=payload_hash,
            canonicalization_version=CANONICALIZATION_VERSION,
        )
        decision = claim_operation(self.session, claim)
        if decision.decision is ClaimDecision.REPLAY:
            snapshot = decision.replay.response_snapshot
            if not isinstance(snapshot, dict):
                raise UsuarioSucursalCommandError(
                    500, "IDEMPOTENCY_TECHNICAL_ERROR"
                )
            return snapshot
        if decision.decision is ClaimDecision.CONFLICT:
            raise UsuarioSucursalCommandError(
                409, _conflict_code(decision.conflict)
            )

        try:
            row = UsuarioSucursalRepository(self.session).create_central(
                id_usuario,
                payload,
                op_id=str(metadata.op_id),
            )
        except UsuarioSucursalDuplicateActiveError as exc:
            raise UsuarioSucursalCommandError(
                409, "DUPLICATE_ACTIVE_SCOPE"
            ) from exc
        except UsuarioSucursalIneligibleTargetError as exc:
            raise UsuarioSucursalCommandError(409, "INELIGIBLE_TARGET") from exc
        except UsuarioSucursalTechnicalError as exc:
            raise UsuarioSucursalCommandError(
                500, "TECHNICAL_INCONSISTENCY"
            ) from exc
        except LookupError as exc:
            raise UsuarioSucursalCommandError(404, "NOT_FOUND") from exc
        except IntegrityError as exc:
            raise UsuarioSucursalCommandError(
                409, "DUPLICATE_ACTIVE_SCOPE"
            ) from exc

        snapshot = _snapshot(row)
        complete_operation(
            self.session,
            OperationCompletion(
                op_id=claim.op_id,
                command_code=claim.command_code,
                target_type=claim.target_type,
                target_uid=None,
                target_key=claim.target_key,
                payload_hash=claim.payload_hash,
                canonicalization_version=claim.canonicalization_version,
                result_code=COMMAND_CODE,
                result_http_status=201,
                result_target_uid=None,
                result_version=row["version_registro"],
                response_snapshot=snapshot,
                id_usuario=id_usuario_actor,
                id_sucursal=None,
                id_instalacion=None,
            ),
        )
        return snapshot
