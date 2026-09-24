from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

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
from app.infrastructure.persistence.repositories.catalogo_maestro_repository import (
    CatalogoMaestroConcurrencyError,
    CatalogoMaestroDuplicateCodeError,
    CatalogoMaestroRepository,
)
from app.infrastructure.persistence.repositories.item_catalogo_repository import (
    ItemCatalogoConcurrencyError,
    ItemCatalogoDuplicateCodeError,
    ItemCatalogoInvalidStateTransitionError,
    ItemCatalogoRepository,
)

TARGET_CATALOGO = "CATALOGO_MAESTRO"
TARGET_ITEM = "ITEM_CATALOGO"


class CatalogosCommandError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    fields = {
        key: (value.isoformat() if hasattr(value, "isoformat") else value)
        for key, value in row.items()
        if key not in {
            "id_instalacion_origen", "id_instalacion_ultima_modificacion",
            "op_id_alta", "op_id_ultima_modificacion",
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
class CatalogosCentralCommandService:
    session: Session

    def _run(
        self,
        *,
        metadata: CentralCommandMetadata,
        id_usuario: int,
        command_code: str,
        target_type: str,
        target_uid: str | None,
        target_key: str | None,
        payload: dict[str, Any],
        status: int,
        execute,
    ) -> dict[str, Any]:
        payload_hash = canonical_payload_hash({
            "actor": {"type": "HUMAN", "id_usuario": id_usuario},
            "scope": {"mode": "GLOBAL", "id_sucursal": None},
            "payload": payload,
        })
        claim = OperationClaim(
            op_id=metadata.op_id,
            command_code=command_code,
            target_type=target_type,
            target_uid=UUID(target_uid) if target_uid else None,
            target_key=target_key,
            payload_hash=payload_hash,
            canonicalization_version=CANONICALIZATION_VERSION,
        )
        decision = claim_operation(self.session, claim)
        if decision.decision is ClaimDecision.REPLAY:
            snapshot = decision.replay.response_snapshot
            if not isinstance(snapshot, dict):
                raise CatalogosCommandError(500, "IDEMPOTENCY_TECHNICAL_ERROR")
            return snapshot
        if decision.decision is ClaimDecision.CONFLICT:
            raise CatalogosCommandError(409, _conflict_code(decision.conflict))

        try:
            row = execute()
        except (CatalogoMaestroConcurrencyError, ItemCatalogoConcurrencyError) as exc:
            raise CatalogosCommandError(412, "CONCURRENCY_ERROR") from exc
        except (CatalogoMaestroDuplicateCodeError, ItemCatalogoDuplicateCodeError) as exc:
            raise CatalogosCommandError(409, "DUPLICATE_CODE") from exc
        except ItemCatalogoInvalidStateTransitionError as exc:
            raise CatalogosCommandError(409, "INVALID_STATE_TRANSITION") from exc
        if row is None:
            raise CatalogosCommandError(404, "NOT_FOUND")

        snapshot = _snapshot(row)
        complete_operation(self.session, OperationCompletion(
            op_id=claim.op_id, command_code=claim.command_code,
            target_type=claim.target_type, target_uid=claim.target_uid,
            target_key=claim.target_key, payload_hash=claim.payload_hash,
            canonicalization_version=claim.canonicalization_version,
            result_code=command_code, result_http_status=status,
            result_target_uid=UUID(row["uid_global"]),
            result_version=row["version_registro"], response_snapshot=snapshot,
            id_usuario=id_usuario, id_sucursal=None, id_instalacion=None,
        ))
        return snapshot

    def create_catalogo(self, *, payload, metadata, id_usuario):
        repo = CatalogoMaestroRepository(self.session)
        return self._run(
            metadata=metadata, id_usuario=id_usuario,
            command_code="ADMIN.CONFIG.CATALOGO.CREATE", target_type=TARGET_CATALOGO,
            target_uid=None,
            target_key=payload["codigo_catalogo_maestro"].strip().upper(),
            payload=payload, status=201,
            execute=lambda: repo.create(payload, op_id=str(metadata.op_id)),
        )

    def change_catalogo(self, *, catalogo_id, payload, metadata, id_usuario, action):
        if metadata.expected_version is None:
            raise CatalogosCommandError(500, "TECHNICAL_INCONSISTENCY")
        repo = CatalogoMaestroRepository(self.session)
        target = repo.get_write(catalogo_id)
        if target is None:
            raise CatalogosCommandError(404, "NOT_FOUND")
        fp = {"id_catalogo_maestro": catalogo_id, **payload,
              "if_match_version": metadata.expected_version}
        command = "UPDATE" if action == "update" else "DELETE"
        execute = (
            lambda: repo.update(catalogo_id, payload, op_id=str(metadata.op_id),
                                if_match_version=metadata.expected_version)
            if action == "update" else
            lambda: repo.baja_logica(catalogo_id, op_id=str(metadata.op_id),
                                     if_match_version=metadata.expected_version)
        )
        return self._run(
            metadata=metadata, id_usuario=id_usuario,
            command_code=f"ADMIN.CONFIG.CATALOGO.{command}", target_type=TARGET_CATALOGO,
            target_uid=target["uid_global"], target_key=None, payload=fp,
            status=200, execute=execute,
        )

    def create_item(self, *, catalogo_id, payload, metadata, id_usuario):
        catalogo = CatalogoMaestroRepository(self.session).get_write(catalogo_id)
        if catalogo is None:
            raise CatalogosCommandError(404, "NOT_FOUND")
        repo = ItemCatalogoRepository(self.session)
        fp = {"id_catalogo_maestro": catalogo_id, **payload}
        key = f'{catalogo["uid_global"]}:{payload["codigo_item_catalogo"].strip().upper()}'
        return self._run(
            metadata=metadata, id_usuario=id_usuario,
            command_code="ADMIN.CONFIG.ITEM_CATALOGO.CREATE", target_type=TARGET_ITEM,
            target_uid=None, target_key=key, payload=fp, status=201,
            execute=lambda: repo.create(catalogo_id, payload, op_id=str(metadata.op_id)),
        )

    def change_item(self, *, catalogo_id, item_id, payload, metadata, id_usuario, action):
        if metadata.expected_version is None:
            raise CatalogosCommandError(500, "TECHNICAL_INCONSISTENCY")
        repo = ItemCatalogoRepository(self.session)
        target = repo.get(item_id)
        if target is None or target["id_catalogo_maestro"] != catalogo_id:
            raise CatalogosCommandError(404, "NOT_FOUND")
        fp = {"id_catalogo_maestro": catalogo_id, "id_item_catalogo": item_id,
              **payload, "if_match_version": metadata.expected_version}
        suffix = {"update": "UPDATE", "estado": "STATE", "baja": "DELETE"}[action]
        return self._run(
            metadata=metadata, id_usuario=id_usuario,
            command_code=f"ADMIN.CONFIG.ITEM_CATALOGO.{suffix}", target_type=TARGET_ITEM,
            target_uid=target["uid_global"], target_key=None, payload=fp, status=200,
            execute=lambda: repo.change(
                catalogo_id, item_id, payload, op_id=str(metadata.op_id),
                version=metadata.expected_version, action=action,
            ),
        )
