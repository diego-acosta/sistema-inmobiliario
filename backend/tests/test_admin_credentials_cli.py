from uuid import UUID

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
