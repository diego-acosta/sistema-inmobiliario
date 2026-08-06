"""CLI segura para inicializar o resetear credenciales administrativas."""

import argparse
import getpass
import sys
from uuid import UUID

from app.application.administrativo.commands.bootstrap_credential import (
    ActiveCredentialAlreadyExists,
    ActiveCredentialNotFound,
    BootstrapCredentialCommand,
    CredentialBootstrapTechnicalError,
    CredentialIdempotencyConflict,
    CredentialStateConflict,
    InvalidCredentialInput,
    UserNotEligible,
    UserNotFound,
    validate_password_policy,
)
from app.application.common.local_installation import (
    InvalidLocalInstallationCode,
    LocalInstallationNotConfigured,
    LocalInstallationNotEligible,
    LocalInstallationNotFound,
    LocalInstallationStateConflict,
    LocalInstallationTechnicalError,
)


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("debe ser un UUID válido") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bootstrap local de credenciales administrativas"
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for name in ("init", "reset"):
        command = subparsers.add_parser(name)
        command.add_argument("--usuario", required=True)
        command.add_argument("--op-id", required=True, type=_uuid)
    return parser


def _read_password(codigo_usuario: str, login: str) -> str:
    for _ in range(3):
        first = getpass.getpass("Contraseña: ")
        second = getpass.getpass("Confirmación: ")
        if first != second:
            continue
        validate_password_policy(first, codigo_usuario=codigo_usuario, login=login)
        return first
    raise InvalidCredentialInput("No fue posible confirmar la contraseña.")


def _error_code(exc: Exception) -> int:
    if isinstance(exc, UserNotFound):
        return 3
    if isinstance(
        exc,
        (
            UserNotEligible,
            LocalInstallationNotFound,
            LocalInstallationNotEligible,
            LocalInstallationStateConflict,
            ActiveCredentialNotFound,
        ),
    ):
        return 4
    if isinstance(
        exc,
        (
            ActiveCredentialAlreadyExists,
            CredentialStateConflict,
            CredentialIdempotencyConflict,
        ),
    ):
        return 5
    if isinstance(
        exc,
        (
            InvalidCredentialInput,
            LocalInstallationNotConfigured,
            InvalidLocalInstallationCode,
            EOFError,
        ),
    ):
        return 2
    return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.usuario or not args.usuario.strip():
        print("El código de usuario no es válido.", file=sys.stderr)
        return 2
    if not sys.stdin.isatty():
        print("Se requiere una terminal interactiva.", file=sys.stderr)
        return 2
    try:
        from app.config.database import SessionLocal
        from app.config.settings import Settings

        command = BootstrapCredentialCommand(SessionLocal, Settings())
        preview = command.preflight(args.usuario)
        print(
            f"Operación: {args.operation}\nInstalación: {preview.codigo_instalacion} — {preview.nombre_instalacion}\nUsuario: {preview.codigo_usuario}\nLogin: {preview.login}"
        )
        secret = _read_password(preview.codigo_usuario, preview.login)
        result = command.execute(args.operation, preview, secret, args.op_id)
        print(
            f"Operación: {args.operation}\nUsuario: {result.codigo_usuario}\nInstalación: {result.codigo_instalacion} — {result.nombre_instalacion}\nResultado: {result.result}\nOp ID: {args.op_id}"
        )
        return 0
    except KeyboardInterrupt:
        print("Operación cancelada.", file=sys.stderr)
        return 130
    except (
        InvalidCredentialInput,
        UserNotFound,
        UserNotEligible,
        ActiveCredentialAlreadyExists,
        ActiveCredentialNotFound,
        CredentialStateConflict,
        CredentialIdempotencyConflict,
        CredentialBootstrapTechnicalError,
        LocalInstallationNotConfigured,
        InvalidLocalInstallationCode,
        LocalInstallationNotFound,
        LocalInstallationNotEligible,
        LocalInstallationStateConflict,
        LocalInstallationTechnicalError,
        EOFError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return _error_code(exc)


if __name__ == "__main__":
    raise SystemExit(main())
