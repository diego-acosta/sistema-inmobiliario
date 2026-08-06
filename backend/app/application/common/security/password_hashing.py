"""Primitivas internas Argon2id para credenciales de usuario.

#449 no crea ni persiste credenciales. Los futuros consumidores deberán
persistir ``hash_credencial`` como PHC string y ``algoritmo_hash`` como
``argon2id:v1``.
"""

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

PASSWORD_HASH_ALGORITHM = "argon2id:v1"
PASSWORD_MAX_LENGTH = 1024

_ARGON2ID_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


class PasswordHashingError(Exception):
    pass


class InvalidPasswordInput(PasswordHashingError):
    pass


class InvalidPasswordHash(PasswordHashingError):
    pass


class PasswordHashingTechnicalError(PasswordHashingError):
    pass


def _validate_secret(secret: str) -> None:
    if not isinstance(secret, str):
        raise InvalidPasswordInput("Invalid password input.")
    if secret == "" or secret.strip() == "":
        raise InvalidPasswordInput("Invalid password input.")
    if len(secret) > PASSWORD_MAX_LENGTH:
        raise InvalidPasswordInput("Invalid password input.")


def _validate_hash_type(encoded_hash: str) -> None:
    if not isinstance(encoded_hash, str):
        raise InvalidPasswordHash("Invalid password hash.")


def _is_argon2id_phc(encoded_hash: str) -> bool:
    return encoded_hash.startswith("$argon2id$")


def hash_password(secret: str) -> str:
    _validate_secret(secret)
    try:
        return _ARGON2ID_HASHER.hash(secret)
    except HashingError as exc:
        raise PasswordHashingTechnicalError("Password hashing failed.") from exc


def verify_password(secret: str, encoded_hash: str) -> bool:
    _validate_secret(secret)
    if not isinstance(encoded_hash, str):
        return False
    if encoded_hash == "" or encoded_hash.strip() == "":
        return False
    if not _is_argon2id_phc(encoded_hash):
        return False
    try:
        return bool(_ARGON2ID_HASHER.verify(encoded_hash, secret))
    except (VerifyMismatchError, InvalidHashError):
        return False
    except VerificationError as exc:
        raise PasswordHashingTechnicalError("Password verification failed.") from exc


def needs_rehash(encoded_hash: str) -> bool:
    _validate_hash_type(encoded_hash)
    if encoded_hash == "" or encoded_hash.strip() == "" or not _is_argon2id_phc(encoded_hash):
        raise InvalidPasswordHash("Invalid password hash.")
    try:
        return bool(_ARGON2ID_HASHER.check_needs_rehash(encoded_hash))
    except InvalidHashError as exc:
        raise InvalidPasswordHash("Invalid password hash.") from exc
    except VerificationError as exc:
        raise PasswordHashingTechnicalError("Password rehash check failed.") from exc
