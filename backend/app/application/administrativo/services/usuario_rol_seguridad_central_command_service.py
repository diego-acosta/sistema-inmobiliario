from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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
from app.infrastructure.persistence.repositories.usuario_rol_seguridad_repository import (
    UsuarioRolSeguridadConcurrencyError,
    UsuarioRolSeguridadDuplicateActiveError,
    UsuarioRolSeguridadIneligibleTargetError,
    UsuarioRolSeguridadRepository,
    UsuarioRolSeguridadTechnicalError,
)

TARGET_TYPE = "USUARIO_ROL_SEGURIDAD"
ASSIGN_COMMAND = "ADMIN.SEGURIDAD.GRANT.ASSIGN"
REVOKE_COMMAND = "ADMIN.SEGURIDAD.GRANT.REVOKE"


class UsuarioRolSeguridadCommandError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code


def _conflict_code(kind: ConflictKind) -> str:
    return {
        ConflictKind.COMMAND: "IDEMPOTENCY_COMMAND_CONFLICT",
        ConflictKind.TARGET: "IDEMPOTENCY_TARGET_CONFLICT",
        ConflictKind.PAYLOAD: "IDEMPOTENCY_PAYLOAD_CONFLICT",
    }[kind]


def _target_key(id_usuario: int, id_rol_seguridad: int) -> str:
    return f"usuario:{id_usuario}:rol:{id_rol_seguridad}"


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "data": {
            key: value.isoformat() if hasattr(value, "isoformat") else value
            for key, value in row.items()
        },
    }


@dataclass
class UsuarioRolSeguridadCentralCommandService:
    session: Session

    def _run(
        self,
        *,
        metadata: CentralCommandMetadata,
        id_usuario_actor: int,
        command_code: str,
        target_key: str,
        payload: dict[str, Any],
        status: int,
        execute: Callable[[], dict[str, Any] | None],
    ) -> dict[str, Any]:
        payload_hash = canonical_payload_hash(
            {
                "actor": {"type": "HUMAN", "id_usuario": id_usuario_actor},
                "scope": {"mode": "GLOBAL", "id_sucursal": None},
                "payload": payload,
            }
        )
        claim = OperationClaim(
            op_id=metadata.op_id,
            command_code=command_code,
            target_type=TARGET_TYPE,
            target_uid=None,
            target_key=target_key,
            payload_hash=payload_hash,
            canonicalization_version=CANONICALIZATION_VERSION,
        )
        decision = claim_operation(self.session, claim)
        if decision.decision is ClaimDecision.REPLAY:
            snapshot = decision.replay.response_snapshot
            if not isinstance(snapshot, dict):
                raise UsuarioRolSeguridadCommandError(
                    500, "IDEMPOTENCY_TECHNICAL_ERROR"
                )
            return snapshot
        if decision.decision is ClaimDecision.CONFLICT:
            raise UsuarioRolSeguridadCommandError(
                409, _conflict_code(decision.conflict)
            )

        try:
            row = execute()
        except UsuarioRolSeguridadConcurrencyError as exc:
            raise UsuarioRolSeguridadCommandError(412, "CONCURRENCY_ERROR") from exc
        except UsuarioRolSeguridadDuplicateActiveError as exc:
            raise UsuarioRolSeguridadCommandError(409, "DUPLICATE_ACTIVE_GRANT") from exc
        except UsuarioRolSeguridadIneligibleTargetError as exc:
            raise UsuarioRolSeguridadCommandError(409, "INELIGIBLE_TARGET") from exc
        except UsuarioRolSeguridadTechnicalError as exc:
            raise UsuarioRolSeguridadCommandError(
                500, "TECHNICAL_INCONSISTENCY"
            ) from exc
        except LookupError as exc:
            raise UsuarioRolSeguridadCommandError(404, "NOT_FOUND") from exc
        except IntegrityError as exc:
            raise UsuarioRolSeguridadCommandError(
                409, "DUPLICATE_ACTIVE_GRANT"
            ) from exc
        if row is None:
            raise UsuarioRolSeguridadCommandError(404, "NOT_FOUND")

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
                result_code=command_code,
                result_http_status=status,
                result_target_uid=None,
                result_version=row["version_registro"],
                response_snapshot=snapshot,
                id_usuario=id_usuario_actor,
                id_sucursal=None,
                id_instalacion=None,
            ),
        )
        return snapshot

    def assign(
        self,
        *,
        id_usuario: int,
        id_rol_seguridad: int,
        metadata: CentralCommandMetadata,
        id_usuario_actor: int,
    ) -> dict[str, Any]:
        payload = {
            "id_usuario": id_usuario,
            "id_rol_seguridad": id_rol_seguridad,
        }
        return self._run(
            metadata=metadata,
            id_usuario_actor=id_usuario_actor,
            command_code=ASSIGN_COMMAND,
            target_key=_target_key(id_usuario, id_rol_seguridad),
            payload=payload,
            status=201,
            execute=lambda: UsuarioRolSeguridadRepository(
                self.session
            ).create_central(
                id_usuario,
                id_rol_seguridad,
                id_usuario_actor=id_usuario_actor,
                op_id=str(metadata.op_id),
            ),
        )

    def revoke(
        self,
        *,
        id_usuario: int,
        id_asignacion: int,
        metadata: CentralCommandMetadata,
        id_usuario_actor: int,
    ) -> dict[str, Any]:
        if metadata.expected_version is None:
            raise UsuarioRolSeguridadCommandError(
                500, "TECHNICAL_INCONSISTENCY"
            )
        repository = UsuarioRolSeguridadRepository(self.session)
        assignment = repository.get(id_asignacion)
        if assignment is None or assignment["id_usuario"] != id_usuario:
            raise UsuarioRolSeguridadCommandError(404, "NOT_FOUND")
        id_rol_seguridad = assignment["id_rol_seguridad"]
        payload = {
            "id_usuario": id_usuario,
            "id_asignacion": id_asignacion,
            "id_rol_seguridad": id_rol_seguridad,
            "if_match_version": metadata.expected_version,
        }
        return self._run(
            metadata=metadata,
            id_usuario_actor=id_usuario_actor,
            command_code=REVOKE_COMMAND,
            target_key=_target_key(id_usuario, id_rol_seguridad),
            payload=payload,
            status=200,
            execute=lambda: repository.revoke_central(
                id_usuario,
                id_asignacion,
                op_id=str(metadata.op_id),
                expected_version=metadata.expected_version,
            ),
        )
