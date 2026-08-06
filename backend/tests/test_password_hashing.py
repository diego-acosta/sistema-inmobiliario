import importlib
import inspect
import re
import sys

import pytest
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from argon2.low_level import Type

from app.application.common.security import password_hashing as ph


SECRET = "Clave ficticia de test 449 con espacios internos"
WRONG_SECRET = "Clave ficticia alternativa 449"
OTHER_ALGORITHM_HASH = "$argon2i$v=19$m=8,t=1,p=1$YWJjZGVmZ2hpamtsbW5vcA$YWJjZGVmZ2hpamtsbW5vcA"


def test_policy_constants_and_phc_parameters():
    assert ph.PASSWORD_HASH_ALGORITHM == "argon2id:v1"
    assert ph.PASSWORD_MAX_LENGTH == 1024
    encoded = ph.hash_password(SECRET)
    assert encoded.startswith("$argon2id$")
    assert "$v=19$" in encoded
    assert "$m=65536,t=3,p=2$" in encoded


def test_hash_generates_distinct_argon2id_phc_and_verifies():
    first = ph.hash_password(SECRET)
    second = ph.hash_password(SECRET)
    assert isinstance(first, str)
    assert isinstance(second, str)
    assert first != second
    assert first.startswith("$argon2id$")
    assert ph.verify_password(SECRET, first) is True


@pytest.mark.parametrize("secret", ["", "   ", "\t\n", "x" * 1025, None, b"bytes", 123, object()])
def test_hash_rejects_invalid_secret(secret):
    with pytest.raises(ph.InvalidPasswordInput):
        ph.hash_password(secret)


def test_verify_correct_and_incorrect_passwords():
    encoded = ph.hash_password(SECRET)
    assert ph.verify_password(SECRET, encoded) is True
    assert ph.verify_password(WRONG_SECRET, encoded) is False


@pytest.mark.parametrize("encoded", ["", "   ", "hash-corrupto", "no-phc", OTHER_ALGORITHM_HASH])
def test_verify_returns_false_for_invalid_hashes(encoded):
    assert ph.verify_password(SECRET, encoded) is False


def test_verify_invalid_secret_raises_invalid_password_input():
    encoded = ph.hash_password(SECRET)
    with pytest.raises(ph.InvalidPasswordInput):
        ph.verify_password("", encoded)


def test_verify_converts_unexpected_argon2_verification_error(monkeypatch):
    encoded = ph.hash_password(SECRET)

    class FailingHasher:
        def verify(self, encoded_hash, secret):
            raise VerificationError("detalle tecnico no sensible")

    monkeypatch.setattr(ph, "_ARGON2ID_HASHER", FailingHasher())
    with pytest.raises(ph.PasswordHashingTechnicalError):
        ph.verify_password(SECRET, encoded)


def test_needs_rehash_current_policy_false_and_weaker_policy_true():
    current = ph.hash_password(SECRET)
    weaker = PasswordHasher(
        time_cost=1,
        memory_cost=8192,
        parallelism=1,
        hash_len=16,
        salt_len=16,
        type=Type.ID,
    ).hash(SECRET)
    assert ph.needs_rehash(current) is False
    assert ph.needs_rehash(weaker) is True


@pytest.mark.parametrize("encoded", ["", "   ", "hash-corrupto", "no-phc", OTHER_ALGORITHM_HASH])
def test_needs_rehash_rejects_invalid_hashes(encoded):
    with pytest.raises(ph.InvalidPasswordHash):
        ph.needs_rehash(encoded)


def test_needs_rehash_validates_hash_type():
    with pytest.raises(ph.InvalidPasswordHash):
        ph.needs_rehash(None)


def test_needs_rehash_does_not_hash_or_persist(monkeypatch):
    encoded = ph.hash_password(SECRET)

    class RehashOnlyHasher:
        def hash(self, secret):
            raise AssertionError("needs_rehash must not generate hashes")

        def check_needs_rehash(self, encoded_hash):
            return False

    monkeypatch.setattr(ph, "_ARGON2ID_HASHER", RehashOnlyHasher())
    assert ph.needs_rehash(encoded) is False


def test_portability_after_module_reload():
    encoded = ph.hash_password(SECRET)
    sys.modules.pop("app.application.common.security.password_hashing")
    reloaded = importlib.import_module("app.application.common.security.password_hashing")
    assert reloaded.verify_password(SECRET, encoded) is True
    assert re.search(r"\$m=65536,t=3,p=2\$", encoded)


def test_module_has_no_infrastructure_or_http_imports():
    source = inspect.getsource(ph)
    forbidden = ["fastapi", "sqlalchemy", "repositories", "routers", "Session", "outbox"]
    lowered = source.lower()
    for name in forbidden:
        assert name.lower() not in lowered


def test_no_weak_or_reversible_security_primitives_in_module():
    source = inspect.getsource(ph).lower()
    for forbidden in ["sha", "md5", "hmac", "encrypt", "decrypt"]:
        assert forbidden not in source


def test_sanitized_exceptions_do_not_include_secret_or_hash():
    encoded = ph.hash_password(SECRET)
    for call in [lambda: ph.hash_password(""), lambda: ph.needs_rehash("no-phc")]:
        with pytest.raises(ph.PasswordHashingError) as exc_info:
            call()
        message = str(exc_info.value)
        assert SECRET not in message
        assert encoded not in message
        assert "PHC" not in message
        assert "salt" not in message.lower()
