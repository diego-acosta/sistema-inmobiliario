from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

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
from app.infrastructure.persistence.repositories.usuario_sistema_repository import (
    UsuarioConcurrencyError,
    UsuarioSistemaRepository,
)

TARGET_USUARIO = "USUARIO"
KNOWN_USER_STATES = frozenset({"ACTIVO", "INACTIVO"})


class UsuariosCommandError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    fields = {
        key: (value.isoformat() if hasattr(value, "isoformat") else value)
        for key, value in row.items()
        if key
        not in {
            "uid_global",
            "deleted_at",
            "updated_at",
            "id_instalacion_origen",
            "id_instalacion_ultima_modificacion",
            "op_id_alta",
            "op_id_ultima_modificacion",
        }
    }
    return {"ok": True, "data": fields}


def _conflict_code(kind: ConflictKind) -> str:
    return {
        ConflictKind.COMMAND: "IDEMPOTENCY_COMMAND_CONFLICT",
        ConflictKind.TARGET: "IDEMPOTENCY_TARGET_CONFLICT",
        ConflictKind.PAYLOAD: "IDEMPOTENCY_PAYLOAD_CONFLICT",
    }[kind]


@dataclass
class UsuariosCentralCommandService:
    session: Session

    def _run(
        self,
        *,
        metadata: CentralCommandMetadata,
        id_usuario_actor: int,
        command_code: str,
        target_uid: str | None,
        target_key: str | None,
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
            target_type=TARGET_USUARIO,
            target_uid=UUID(str(target_uid)) if target_uid else None,
            target_key=target_key,
            payload_hash=payload_hash,
            canonicalization_version=CANONICALIZATION_VERSION,
        )
        decision = claim_operation(self.session, claim)
        if decision.decision is ClaimDecision.REPLAY:
            snapshot = decision.replay.response_snapshot
            if not isinstance(snapshot, dict):
                raise UsuariosCommandError(500, "IDEMPOTENCY_TECHNICAL_ERROR")
            return snapshot
        if decision.decision is ClaimDecision.CONFLICT:
            raise UsuariosCommandError(409, _conflict_code(decision.conflict))

        try:
            row = execute()
        except UsuarioConcurrencyError as exc:
            raise UsuariosCommandError(412, "CONCURRENCY_ERROR") from exc
        except IntegrityError as exc:
            raise UsuariosCommandError(409, "DUPLICATE_USER") from exc
        if row is None:
            raise UsuariosCommandError(404, "NOT_FOUND")

        snapshot = _snapshot(row)
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
                result_code=command_code,
                result_http_status=status,
                result_target_uid=UUID(str(row["uid_global"])),
                result_version=row["version_registro"],
                response_snapshot=snapshot,
                id_usuario=id_usuario_actor,
                id_sucursal=None,
                id_instalacion=None,
            ),
        )
        return snapshot

    def create(self, *, payload, metadata, id_usuario_actor):
        key = payload["codigo_usuario"].strip().upper()
        return self._run(
            metadata=metadata,
            id_usuario_actor=id_usuario_actor,
            command_code="ADMIN.USUARIO.CREATE",
            target_uid=None,
            target_key=key,
            payload=payload,
            status=201,
            execute=lambda: UsuarioSistemaRepository(self.session).create_central(
                payload, op_id=str(metadata.op_id)
            ),
        )

    def deactivate(self, *, id_usuario, metadata, id_usuario_actor):
        if metadata.expected_version is None:
            raise UsuariosCommandError(500, "TECHNICAL_INCONSISTENCY")
        repo = UsuarioSistemaRepository(self.session)
        target = repo.get(id_usuario)
        if target is None:
            raise UsuariosCommandError(404, "NOT_FOUND")
        if target["estado_usuario"] not in KNOWN_USER_STATES:
            raise UsuariosCommandError(500, "TECHNICAL_INCONSISTENCY")
        payload = {
            "id_usuario": id_usuario,
            "if_match_version": metadata.expected_version,
        }
        return self._run(
            metadata=metadata,
            id_usuario_actor=id_usuario_actor,
            command_code="ADMIN.USUARIO.DEACTIVATE",
            target_uid=target["uid_global"],
            target_key=None,
            payload=payload,
            status=200,
            execute=lambda: repo.deactivate_central(
                id_usuario,
                id_usuario_actor=id_usuario_actor,
                op_id=str(metadata.op_id),
                expected_version=metadata.expected_version,
            ),
        )
