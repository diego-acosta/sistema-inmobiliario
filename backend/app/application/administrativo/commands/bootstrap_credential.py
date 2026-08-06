"""Caso de uso local y no sincronizable para bootstrap de credenciales."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.application.common.local_installation import resolve_local_installation
from app.application.common.security.password_hashing import (
    PASSWORD_HASH_ALGORITHM,
    InvalidPasswordInput,
    PasswordHashingTechnicalError,
    hash_password,
    verify_password,
)
from app.infrastructure.persistence.repositories.credencial_usuario_repository import (
    CredencialUsuarioRepository,
)
from app.infrastructure.persistence.repositories.usuario_sistema_repository import (
    UsuarioSistemaRepository,
)


class CredentialBootstrapError(RuntimeError):
    pass


class InvalidCredentialInput(CredentialBootstrapError):
    pass


class UserNotFound(CredentialBootstrapError):
    pass


class UserNotEligible(CredentialBootstrapError):
    pass


class ActiveCredentialAlreadyExists(CredentialBootstrapError):
    pass


class ActiveCredentialNotFound(CredentialBootstrapError):
    pass


class CredentialStateConflict(CredentialBootstrapError):
    pass


class CredentialIdempotencyConflict(CredentialBootstrapError):
    pass


class CredentialBootstrapTechnicalError(CredentialBootstrapError):
    pass


@dataclass(frozen=True, slots=True)
class CredentialBootstrapPreview:
    id_usuario: int
    codigo_usuario: str
    login: str
    codigo_instalacion: str
    nombre_instalacion: str


@dataclass(frozen=True, slots=True)
class CredentialBootstrapResult:
    codigo_usuario: str
    codigo_instalacion: str
    nombre_instalacion: str
    result: str


def validate_password_policy(secret: str, *, codigo_usuario: str, login: str) -> None:
    if (
        not isinstance(secret, str)
        or not 12 <= len(secret) <= 1024
        or not secret.strip()
    ):
        raise InvalidCredentialInput("La contraseña no cumple la política requerida.")
    if secret == codigo_usuario or secret == login:
        raise InvalidCredentialInput("La contraseña no cumple la política requerida.")


def _eligible(user) -> None:
    if (
        user["estado_usuario"] != "ACTIVO"
        or user["deleted_at"] is not None
        or user["fecha_baja"] is not None
    ):
        raise UserNotEligible("El usuario no es elegible para esta operación.")


class BootstrapCredentialCommand:
    def __init__(self, session_factory, settings) -> None:
        self.session_factory = session_factory
        self.settings = settings

    def preflight(self, codigo_usuario: str) -> CredentialBootstrapPreview:
        with self.session_factory() as session:
            try:
                identity = resolve_local_installation(session, self.settings)
                user = UsuarioSistemaRepository(session).get_by_codigo_exact(
                    codigo_usuario
                )
                if user is None:
                    raise UserNotFound("El usuario indicado no existe.")
                _eligible(user)
                return CredentialBootstrapPreview(
                    user["id_usuario"],
                    user["codigo_usuario"],
                    user["login"],
                    identity.codigo_instalacion,
                    identity.nombre_instalacion,
                )
            finally:
                session.rollback()

    def execute(
        self,
        operation: str,
        preview: CredentialBootstrapPreview,
        secret: str,
        op_id: UUID,
    ) -> CredentialBootstrapResult:
        if operation not in {"init", "reset"}:
            raise InvalidCredentialInput("La operación indicada no es válida.")
        validate_password_policy(
            secret, codigo_usuario=preview.codigo_usuario, login=preview.login
        )
        try:
            password_hash = hash_password(secret)
        except InvalidPasswordInput as exc:
            raise InvalidCredentialInput("La contraseña no es válida.") from exc
        except PasswordHashingTechnicalError as exc:
            raise CredentialBootstrapTechnicalError(
                "No fue posible procesar la contraseña."
            ) from exc

        try:
            with self.session_factory() as session, session.begin():
                identity = resolve_local_installation(session, self.settings)
                user = UsuarioSistemaRepository(session).get_by_codigo_exact_for_update(
                    preview.codigo_usuario
                )
                if user is None:
                    raise UserNotFound("El usuario indicado no existe.")
                _eligible(user)
                if user["id_usuario"] != preview.id_usuario:
                    raise CredentialStateConflict(
                        "El usuario cambió durante la operación."
                    )
                repo = CredencialUsuarioRepository(session)
                replay = repo.find_created_by_op_id(op_id)
                if replay is not None:
                    if replay.id_usuario != user["id_usuario"] or not verify_password(
                        secret, replay.hash_credencial
                    ):
                        raise CredentialIdempotencyConflict(
                            "El identificador de operación ya fue utilizado."
                        )
                    return CredentialBootstrapResult(
                        user["codigo_usuario"],
                        identity.codigo_instalacion,
                        identity.nombre_instalacion,
                        "REPLAY_IDEMPOTENTE",
                    )
                credentials = repo.list_password_credentials_for_update(
                    user["id_usuario"]
                )
                active = [
                    row
                    for row in credentials
                    if row.deleted_at is None and row.estado_credencial == "ACTIVA"
                ]
                if len(active) > 1 or (
                    len(active) == 1 and not active[0].es_credencial_principal
                ):
                    raise CredentialStateConflict(
                        "El estado de credenciales es inconsistente."
                    )
                if operation == "init" and active:
                    raise ActiveCredentialAlreadyExists(
                        "El usuario ya posee una credencial activa."
                    )
                if operation == "reset" and not active:
                    raise ActiveCredentialNotFound(
                        "El usuario no posee una credencial activa."
                    )
                timestamp = repo.get_transaction_timestamp()
                if operation == "reset":
                    repo.revoke_password(
                        active[0].id_credencial_usuario,
                        timestamp=timestamp,
                        installation_id=identity.id_instalacion,
                        op_id=op_id,
                    )
                repo.insert_active_password(
                    id_usuario=user["id_usuario"],
                    password_hash=password_hash,
                    algorithm=PASSWORD_HASH_ALGORITHM,
                    timestamp=timestamp,
                    installation_id=identity.id_instalacion,
                    op_id=op_id,
                )
                session.flush()
                result = CredentialBootstrapResult(
                    user["codigo_usuario"],
                    identity.codigo_instalacion,
                    identity.nombre_instalacion,
                    "COMPLETADO",
                )
            return result
        except CredentialBootstrapError:
            raise
        except PasswordHashingTechnicalError as exc:
            raise CredentialBootstrapTechnicalError(
                "No fue posible verificar la operación."
            ) from exc
        except IntegrityError as exc:
            name = getattr(
                getattr(getattr(exc, "orig", None), "diag", None),
                "constraint_name",
                None,
            )
            if name in {
                "ux_credencial_usuario_op_id_alta",
                "ux_credencial_usuario_password_activa",
                "ux_credencial_usuario_principal_activa",
            }:
                raise CredentialStateConflict(
                    "La operación entra en conflicto con el estado actual."
                ) from exc
            raise CredentialBootstrapTechnicalError(
                "No fue posible completar la operación."
            ) from exc
        except DBAPIError as exc:
            raise CredentialBootstrapTechnicalError(
                "No fue posible completar la operación."
            ) from exc
