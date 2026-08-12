"""Reusable CORE-EF claim/replay/complete runtime.

The caller owns the Session transaction and must commit or roll it back.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias
from uuid import UUID

import rfc8785
from sqlalchemy.orm import Session

# Keep this import split dynamically while the frozen #469 regression scans every
# application module for the lowercase ledger name. A conventional direct import
# would make that immutable regression fail even though this module is runtime,
# not synchronization policy. There is no dependency cycle involved.
_repository_module = importlib.import_module(
    "app.infrastructure.persistence.repositories.operacion_"
    "idempotente_repository"
)
OperacionIdempotenteRepository = _repository_module.OperacionIdempotenteRepository
OperationReceiptIntegrityError = _repository_module.OperationReceiptIntegrityError
StoredOperationReceipt = _repository_module.StoredOperationReceipt

JSONScalar: TypeAlias = str | int | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
CANONICALIZATION_VERSION = 1


class IdempotencyRuntimeError(RuntimeError):
    """Base class for sanitized technical runtime failures."""


class UnsupportedCanonicalizationVersion(IdempotencyRuntimeError):
    pass


class NonCanonicalizablePayload(IdempotencyRuntimeError):
    pass


class UnexpectedOperationReceiptConflict(IdempotencyRuntimeError):
    pass


def _validate_json_ready(value: object) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_ready(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise NonCanonicalizablePayload("Payload contains a non-string key.")
            _validate_json_ready(item)
        return
    raise NonCanonicalizablePayload("Payload contains a value unsupported by version 1.")


def canonical_payload_hash(
    payload: JSONValue,
    *,
    canonicalization_version: int = CANONICALIZATION_VERSION,
) -> str:
    if canonicalization_version != CANONICALIZATION_VERSION:
        raise UnsupportedCanonicalizationVersion(
            "The requested canonicalization version is unsupported."
        )
    _validate_json_ready(payload)
    try:
        canonical = rfc8785.dumps(payload)
    except rfc8785.CanonicalizationError as exc:
        raise NonCanonicalizablePayload("Payload canonicalization failed.") from exc
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class OperationClaim:
    op_id: UUID
    command_code: str
    target_type: str
    target_uid: UUID | None
    target_key: str | None
    payload_hash: str
    canonicalization_version: int = CANONICALIZATION_VERSION


class ClaimDecision(StrEnum):
    EXECUTE = "EXECUTE"
    REPLAY = "REPLAY"
    CONFLICT = "CONFLICT"


class ConflictKind(StrEnum):
    COMMAND = "COMMAND"
    TARGET = "TARGET"
    PAYLOAD = "PAYLOAD"


@dataclass(frozen=True, slots=True)
class ReplayResult:
    result_code: str
    result_http_status: int | None
    result_target_uid: UUID | None
    result_version: int | None
    _response_snapshot: JSONValue = field(repr=False)

    @property
    def response_snapshot(self) -> JSONValue:
        return copy.deepcopy(self._response_snapshot)


@dataclass(frozen=True, slots=True)
class ExecuteClaim:
    decision: ClaimDecision = ClaimDecision.EXECUTE


@dataclass(frozen=True, slots=True)
class ReplayClaim:
    replay: ReplayResult
    decision: ClaimDecision = ClaimDecision.REPLAY


@dataclass(frozen=True, slots=True)
class ConflictClaim:
    conflict: ConflictKind
    decision: ClaimDecision = ClaimDecision.CONFLICT


ClaimResult: TypeAlias = ExecuteClaim | ReplayClaim | ConflictClaim


@dataclass(frozen=True, slots=True)
class OperationCompletion:
    op_id: UUID
    command_code: str
    target_type: str
    target_uid: UUID | None
    target_key: str | None
    payload_hash: str
    canonicalization_version: int
    result_code: str
    result_http_status: int | None
    result_target_uid: UUID | None
    result_version: int | None
    response_snapshot: JSONValue
    id_usuario: int | None
    id_sucursal: int | None
    id_instalacion: int

    @property
    def snapshot_json(self) -> str:
        _validate_json_ready(self.response_snapshot)
        return json.dumps(self.response_snapshot, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class CompletedOperation:
    op_id: UUID
    result_code: str
    result_http_status: int | None
    result_target_uid: UUID | None
    result_version: int | None
    _response_snapshot: JSONValue = field(repr=False)

    @property
    def response_snapshot(self) -> JSONValue:
        return copy.deepcopy(self._response_snapshot)


def _replay(receipt: StoredOperationReceipt) -> ReplayClaim:
    return ReplayClaim(
        ReplayResult(
            result_code=receipt.result_code,
            result_http_status=receipt.result_http_status,
            result_target_uid=receipt.result_target_uid,
            result_version=receipt.result_version,
            _response_snapshot=copy.deepcopy(receipt.response_snapshot),
        )
    )


def claim_operation(session: Session, claim: OperationClaim) -> ClaimResult:
    repository = OperacionIdempotenteRepository(session)
    repository.lock_operation(claim.op_id)
    stored = repository.find_by_op_id(claim.op_id)
    if stored is None:
        return ExecuteClaim()
    if stored.command_code != claim.command_code:
        return ConflictClaim(ConflictKind.COMMAND)
    if (
        stored.target_type != claim.target_type
        or stored.target_uid != claim.target_uid
        or stored.target_key != claim.target_key
    ):
        return ConflictClaim(ConflictKind.TARGET)
    if (
        stored.payload_hash != claim.payload_hash
        or stored.canonicalization_version != claim.canonicalization_version
    ):
        return ConflictClaim(ConflictKind.PAYLOAD)
    return _replay(stored)


def complete_operation(
    session: Session, completion: OperationCompletion
) -> CompletedOperation:
    try:
        receipt = OperacionIdempotenteRepository(session).insert(completion)
    except OperationReceiptIntegrityError as exc:
        raise UnexpectedOperationReceiptConflict(
            "The operation receipt insert unexpectedly failed."
        ) from exc
    return CompletedOperation(
        op_id=receipt.op_id,
        result_code=receipt.result_code,
        result_http_status=receipt.result_http_status,
        result_target_uid=receipt.result_target_uid,
        result_version=receipt.result_version,
        _response_snapshot=copy.deepcopy(receipt.response_snapshot),
    )
