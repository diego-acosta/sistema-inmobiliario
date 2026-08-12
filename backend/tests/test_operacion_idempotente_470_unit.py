from dataclasses import FrozenInstanceError
from typing import ClassVar
from uuid import uuid4

from app.application.common import idempotency as runtime
from app.infrastructure.persistence.repositories.operacion_idempotente_repository import (
    StoredOperationReceipt,
    advisory_keys,
)
import pytest


class FakeRepository:
    stored = None
    calls: ClassVar[list[tuple[str, object]]] = []

    def __init__(self, session):
        self.session = session

    def lock_operation(self, op_id):
        self.calls.append(("lock", op_id))

    def find_by_op_id(self, op_id):
        self.calls.append(("lookup", op_id))
        return self.stored


@pytest.fixture(autouse=True)
def fake_repository(monkeypatch):
    FakeRepository.stored = None
    FakeRepository.calls = []
    monkeypatch.setattr(runtime, "OperacionIdempotenteRepository", FakeRepository)


def claim(**changes):
    values = {
        "op_id": uuid4(),
        "command_code": "TEST.CREATE",
        "target_type": "TEST",
        "target_uid": None,
        "target_key": None,
        "payload_hash": "a" * 64,
    }
    values.update(changes)
    return runtime.OperationClaim(**values)


def receipt(value):
    return StoredOperationReceipt(
        op_id=value.op_id, command_code=value.command_code,
        target_type=value.target_type, target_uid=value.target_uid,
        target_key=value.target_key, payload_hash=value.payload_hash,
        canonicalization_version=value.canonicalization_version,
        result_code="CREATED", result_http_status=201,
        result_target_uid=uuid4(), result_version=1,
        response_snapshot={"nested": {"value": 1}},
    )


def decide(value):
    return runtime.claim_operation(object(), value)


def test_execute_and_lock_precedes_lookup():
    value = claim()
    assert decide(value).decision is runtime.ClaimDecision.EXECUTE
    assert [call[0] for call in FakeRepository.calls] == ["lock", "lookup"]


def test_replay_is_durable_and_snapshot_is_defensive():
    value = claim()
    FakeRepository.stored = receipt(value)
    result = decide(value)
    assert result.decision is runtime.ClaimDecision.REPLAY
    first = result.replay.response_snapshot
    first["nested"]["value"] = 99
    assert result.replay.response_snapshot == {"nested": {"value": 1}}


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"command_code": "OTHER", "target_type": "other", "payload_hash": "b" * 64}, runtime.ConflictKind.COMMAND),
        ({"target_type": "other", "payload_hash": "b" * 64}, runtime.ConflictKind.TARGET),
        ({"payload_hash": "b" * 64}, runtime.ConflictKind.PAYLOAD),
        ({"canonicalization_version": 2}, runtime.ConflictKind.PAYLOAD),
    ],
)
def test_conflict_precedence(changes, expected):
    original = claim()
    FakeRepository.stored = receipt(original)
    attempted = runtime.OperationClaim(**{**{name: getattr(original, name) for name in original.__dataclass_fields__}, **changes})
    assert decide(attempted).conflict is expected


@pytest.mark.parametrize("target_key", ["", "Key", " key", "key "])
def test_target_comparison_is_exact(target_key):
    original = claim(target_key=None if target_key == "" else "key")
    FakeRepository.stored = receipt(original)
    attempted = claim(op_id=original.op_id, target_key=target_key)
    assert decide(attempted).conflict is runtime.ConflictKind.TARGET


def test_target_uid_and_key_are_both_compared():
    uid = uuid4()
    original = claim(target_uid=uid, target_key="key")
    FakeRepository.stored = receipt(original)
    assert decide(claim(op_id=original.op_id, target_uid=uid, target_key="other")).conflict is runtime.ConflictKind.TARGET


def test_dtos_are_immutable_and_have_no_fastapi_types():
    value = claim()
    with pytest.raises(FrozenInstanceError):
        value.command_code = "changed"
    assert "fastapi" not in runtime.__dict__


def test_advisory_keys_use_uuid_high_words_as_signed_int32():
    op_id = uuid4()
    expected = tuple(
        word if word < 2**31 else word - 2**32
        for word in ((op_id.int >> 96) & 0xFFFFFFFF, (op_id.int >> 64) & 0xFFFFFFFF)
    )
    assert advisory_keys(op_id) == expected


def test_technical_errors_are_not_semantic_conflicts():
    assert not issubclass(runtime.IdempotencyRuntimeError, runtime.ConflictClaim)
