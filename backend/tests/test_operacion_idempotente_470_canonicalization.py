import builtins
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.common.idempotency import (
    NonCanonicalizablePayload,
    UnsupportedCanonicalizationVersion,
    canonical_payload_hash,
)


def test_key_order_nested_unicode_escaping_and_arrays_are_canonical():
    # RFC 8785/JCS object-property sorting; library conformance belongs upstream.
    left = {"z": [None, True, 7, "\n"], "é": {"b": "€", "a": "😀"}}
    right = {"é": {"a": "😀", "b": "€"}, "z": [None, True, 7, "\n"]}
    assert canonical_payload_hash(left) == canonical_payload_hash(right)


@pytest.mark.parametrize("payload", [{}, [], None, True, False, 0, -1, "text"])
def test_supported_roots_are_deterministic_lowercase_sha256(payload):
    first = canonical_payload_hash(payload)
    assert first == canonical_payload_hash(payload)
    assert re.fullmatch(r"[0-9a-f]{64}", first)


def test_absent_null_and_distinct_payloads_differ():
    assert canonical_payload_hash({}) != canonical_payload_hash({"value": None})
    assert canonical_payload_hash({"value": 1}) != canonical_payload_hash({"value": 2})


def test_version_one_and_unsupported_version():
    assert canonical_payload_hash({}, canonicalization_version=1)
    with pytest.raises(UnsupportedCanonicalizationVersion):
        canonical_payload_hash({}, canonicalization_version=2)


@dataclass
class Arbitrary:
    value: int


@pytest.mark.parametrize(
    "payload",
    [1.0, float("nan"), float("inf"), Decimal("1"), uuid4(), date.today(),
     datetime.now(), set(), frozenset(), b"x", Arbitrary(1), object(), {1: "x"}],
)
def test_non_json_ready_types_are_rejected(payload):
    with pytest.raises(NonCanonicalizablePayload):
        canonical_payload_hash(payload)


def test_python_hash_is_not_used(monkeypatch):
    monkeypatch.setattr(builtins, "hash", lambda value: (_ for _ in ()).throw(AssertionError()))
    assert canonical_payload_hash({"ok": True})
