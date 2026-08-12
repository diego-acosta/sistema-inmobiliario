"""Persistence primitives for the immutable operation receipt ledger.

Transaction ownership deliberately remains with the caller.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class StoredOperationReceipt:
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
    response_snapshot: Any


class OperationReceiptIntegrityError(RuntimeError):
    """An insert collided with, or violated, the physical ledger contract."""


_RECEIPT_COLUMNS = """
op_id, command_code, target_type, target_uid, target_key, payload_hash,
canonicalization_version, result_code, result_http_status, result_target_uid,
result_version, response_snapshot
"""


def advisory_keys(op_id: UUID) -> tuple[int, int]:
    """Derive the stable signed int32 pair used by PostgreSQL advisory locks."""
    value = op_id.int
    unsigned_1 = (value >> 96) & 0xFFFFFFFF
    unsigned_2 = (value >> 64) & 0xFFFFFFFF
    key_1 = unsigned_1 if unsigned_1 < 2**31 else unsigned_1 - 2**32
    key_2 = unsigned_2 if unsigned_2 < 2**31 else unsigned_2 - 2**32
    return key_1, key_2


class OperacionIdempotenteRepository:
    """Ledger access without transaction-boundary side effects."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_operation(self, op_id: UUID) -> None:
        key_1, key_2 = advisory_keys(op_id)
        self._session.execute(
            text(
                "SELECT pg_catalog.pg_advisory_xact_lock(:key1, :key2)"
            ),
            {"key1": key_1, "key2": key_2},
        )

    def find_by_op_id(self, op_id: UUID) -> StoredOperationReceipt | None:
        row = self._session.execute(
            text(
                f"""
                SELECT {_RECEIPT_COLUMNS}
                  FROM public.OPERACION_IDEMPOTENTE
                 WHERE op_id = :op_id
                """
            ),
            {"op_id": op_id},
        ).mappings().one_or_none()
        return StoredOperationReceipt(**row) if row is not None else None

    def insert(self, completion: Any) -> StoredOperationReceipt:
        try:
            row = self._session.execute(
                text(
                    f"""
                    INSERT INTO public.OPERACION_IDEMPOTENTE (
                        op_id, command_code, target_type, target_uid, target_key,
                        payload_hash, canonicalization_version, result_code,
                        result_http_status, result_target_uid, result_version,
                        response_snapshot, id_usuario, id_sucursal, id_instalacion
                    ) VALUES (
                        :op_id, :command_code, :target_type, :target_uid, :target_key,
                        :payload_hash, :canonicalization_version, :result_code,
                        :result_http_status, :result_target_uid, :result_version,
                        CAST(:response_snapshot AS jsonb), :id_usuario, :id_sucursal,
                        :id_instalacion
                    )
                    RETURNING {_RECEIPT_COLUMNS}
                    """
                ),
                {
                    "op_id": completion.op_id,
                    "command_code": completion.command_code,
                    "target_type": completion.target_type,
                    "target_uid": completion.target_uid,
                    "target_key": completion.target_key,
                    "payload_hash": completion.payload_hash,
                    "canonicalization_version": completion.canonicalization_version,
                    "result_code": completion.result_code,
                    "result_http_status": completion.result_http_status,
                    "result_target_uid": completion.result_target_uid,
                    "result_version": completion.result_version,
                    "response_snapshot": completion.snapshot_json,
                    "id_usuario": completion.id_usuario,
                    "id_sucursal": completion.id_sucursal,
                    "id_instalacion": completion.id_instalacion,
                },
            ).mappings().one()
        except DBAPIError as exc:
            raise OperationReceiptIntegrityError(
                "The operation receipt could not be persisted."
            ) from exc
        return StoredOperationReceipt(**row)
