# ruff: noqa: E402
from uuid import UUID
from unittest.mock import MagicMock

import pytest

from app.cli.admin_credentials import _read_password, build_parser, main


def test_parser_has_both_commands_and_uuid():
    value = "12345678-1234-5678-1234-567812345678"
    for operation in ("init", "reset"):
        args = build_parser().parse_args(
            [operation, "--usuario", "ADMIN", "--op-id", value]
        )
        assert args.operation == operation
        assert args.op_id == UUID(value)


def test_parser_rejects_invalid_uuid():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["init", "--usuario", "ADMIN", "--op-id", "bad"])


def test_tty_is_checked_before_database(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert main(["init", "--usuario", "ADMIN", "--op-id", str(UUID(int=1))]) == 2


def test_password_requires_exact_confirmation(monkeypatch):
    answers = iter(
        ["first password", "other password", "valid password 12", "valid password 12"]
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: next(answers))
    assert _read_password("ADMIN", "admin") == "valid password 12"


from types import SimpleNamespace
from uuid import uuid4

from app.application.administrativo.commands.bootstrap_credential import (
    ActiveCredentialAlreadyExists,
    ActiveCredentialNotFound,
    CredentialBootstrapTechnicalError,
    CredentialIdempotencyConflict,
    CredentialStateConflict,
    InvalidCredentialInput,
    UserNotEligible,
    UserNotFound,
)
from app.cli.admin_credentials import _error_code


@pytest.mark.parametrize(
    "argv",
    [[], ["init"], ["init", "--usuario", "U"], ["init", "--op-id", str(uuid4())]],
)
def test_required_parser_inputs(argv):
    with pytest.raises(SystemExit) as raised:
        build_parser().parse_args(argv)
    assert raised.value.code == 2


@pytest.mark.parametrize("usuario", ["", "   "])
def test_empty_user_is_input_error(monkeypatch, usuario):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    assert main(["init", "--usuario", usuario, "--op-id", str(uuid4())]) == 2


def test_three_mismatches_are_rejected(monkeypatch):
    monkeypatch.setattr("getpass.getpass", MagicMock(side_effect=["a", "b"] * 3))
    with pytest.raises(InvalidCredentialInput):
        _read_password("U", "login")


@pytest.mark.parametrize(
    "error,code",
    [
        (InvalidCredentialInput("x"), 2),
        (UserNotFound("x"), 3),
        (UserNotEligible("x"), 4),
        (ActiveCredentialNotFound("x"), 4),
        (ActiveCredentialAlreadyExists("x"), 5),
        (CredentialStateConflict("x"), 5),
        (CredentialIdempotencyConflict("x"), 5),
        (CredentialBootstrapTechnicalError("x"), 1),
    ],
)
def test_exit_code_mapping(error, code):
    assert _error_code(error) == code


def test_eof_and_keyboard_interrupt_password(monkeypatch):
    monkeypatch.setattr("getpass.getpass", MagicMock(side_effect=EOFError))
    with pytest.raises(EOFError):
        _read_password("U", "login")
    monkeypatch.setattr("getpass.getpass", MagicMock(side_effect=KeyboardInterrupt))
    with pytest.raises(KeyboardInterrupt):
        _read_password("U", "login")


@pytest.mark.parametrize("result", ["COMPLETADO", "REPLAY_IDEMPOTENTE"])
def test_sanitized_success_output(monkeypatch, capsys, result):
    class FakeCommand:
        def __init__(self, *args):
            pass

        def preflight(self, user):
            return SimpleNamespace(
                id_usuario=1,
                codigo_usuario=user,
                login="login",
                codigo_instalacion="INST",
                nombre_instalacion="Local",
            )

        def execute(self, *args):
            return SimpleNamespace(
                codigo_usuario="USER",
                codigo_instalacion="INST",
                nombre_instalacion="Local",
                result=result,
            )

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(
        "app.cli.admin_credentials.BootstrapCredentialCommand", FakeCommand
    )
    monkeypatch.setattr(
        "getpass.getpass", MagicMock(side_effect=["Secret-safe-123", "Secret-safe-123"])
    )
    assert main(["init", "--usuario", "USER", "--op-id", str(uuid4())]) == 0
    captured = capsys.readouterr()
    assert result in captured.out and captured.err == ""
    assert "Secret-safe-123" not in captured.out and "$argon2" not in captured.out
    assert (
        "postgresql://" not in captured.out
        and "SELECT" not in captured.out
        and "Traceback" not in captured.out
    )
