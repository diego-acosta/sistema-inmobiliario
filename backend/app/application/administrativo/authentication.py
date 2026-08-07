"""Autenticación administrativa local y sesiones opacas revocables (#446)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import re
import secrets
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.application.common.local_installation import LocalInstallationError, resolve_local_installation
from app.application.common.security.password_hashing import InvalidPasswordInput, verify_password
from app.infrastructure.persistence.repositories.authentication_repository import AuthenticationRepository
from app.infrastructure.persistence.repositories.sesion_usuario_repository import SesionUsuarioRepository

SESSION_ABSOLUTE_TTL = timedelta(hours=8)
TOKEN_RANDOM_BYTES = 32
ACCESS_TOKEN_LENGTH = 43
TOKEN_COLLISION_MAX_ATTEMPTS = 3
_ACCESS_TOKEN_PATTERN = re.compile(rf"[A-Za-z0-9_-]{{{ACCESS_TOKEN_LENGTH}}}")

# PHC técnico generado exclusivamente para igualar el trabajo Argon2id cuando no
# hay una credencial real utilizable. No corresponde a ninguna credencial real.
AUTHENTICATION_DUMMY_ARGON2ID_PHC = (
    "$argon2id$v=19$m=65536,t=3,p=2$9+01rIcJgEpjmBWIPdX5kw$"
    "fXuBLw9/fNySEpzuzfuyghLQtmJGr5waVjDdicJW+oY"
)


class AuthenticationError(RuntimeError):
    pass


class InvalidCredentials(AuthenticationError):
    pass


class AuthenticationUnavailable(AuthenticationError):
    pass


class AuthenticationTechnicalError(AuthenticationError):
    pass


class SessionError(RuntimeError):
    pass


class InvalidSession(SessionError):
    pass


class SessionTechnicalError(SessionError):
    pass


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    expires_at: datetime
    session_id: UUID


def generate_access_token() -> str:
    return secrets.token_urlsafe(TOKEN_RANDOM_BYTES)


def digest_access_token(access_token: str) -> str:
    return sha256(access_token.encode("utf-8")).hexdigest()


def parse_bearer_header(value: str | None) -> str:
    if value is None or not value.startswith("Bearer "):
        raise InvalidSession("La sesión no es válida.")
    parts = value.split(" ")
    if (
        len(parts) != 2
        or not parts[1]
        # token_urlsafe(32) emite 43 caracteres Base64 URL-safe sin padding.
        or _ACCESS_TOKEN_PATTERN.fullmatch(parts[1]) is None
    ):
        raise InvalidSession("La sesión no es válida.")
    return parts[1]


def _eligible_user(user: dict | None) -> bool:
    return bool(
        user
        and user["estado_usuario"] == "ACTIVO"
        and user["deleted_at"] is None
        and user["fecha_baja"] is None
    )


def _usable_credential(credential: dict | None, now: datetime) -> bool:
    return bool(
        credential
        and credential["tipo_credencial"] == "PASSWORD"
        and credential["estado_credencial"] == "ACTIVA"
        and credential["deleted_at"] is None
        and credential["es_credencial_principal"] is True
        and credential["algoritmo_hash"] == "argon2id:v1"
        and (credential["fecha_activacion"] is None or credential["fecha_activacion"] <= now)
        and (credential["fecha_vencimiento"] is None or credential["fecha_vencimiento"] > now)
        and (credential["bloqueo_hasta"] is None or credential["bloqueo_hasta"] <= now)
        and credential["requiere_reset"] is False
        and credential["obliga_rotacion"] is False
    )


class AuthenticationService:
    def __init__(self, session, settings) -> None:
        self.db = session
        self.settings = settings

    def login(self, login: str, password: str) -> LoginResult:
        auth = AuthenticationRepository(self.db)
        sessions = SesionUsuarioRepository(self.db)
        try:
            try:
                installation = resolve_local_installation(self.db, self.settings)
            except LocalInstallationError as exc:
                raise AuthenticationUnavailable("Autenticación temporalmente no disponible.") from exc

            now = sessions.get_wall_clock_timestamp()
            user = auth.get_user_by_login_exact(login)
            credentials = auth.list_password_credentials(user["id_usuario"]) if user else []
            usable = [row for row in credentials if _usable_credential(row, now)]
            if len(usable) > 1:
                raise AuthenticationTechnicalError("Estado de autenticación inconsistente.")
            credential = usable[0] if _eligible_user(user) and len(usable) == 1 else None
            phc = credential["hash_credencial"] if credential else AUTHENTICATION_DUMMY_ARGON2ID_PHC
            try:
                verified = verify_password(password, phc)
            except InvalidPasswordInput:
                verified = False
            if not verified or credential is None:
                raise InvalidCredentials("Las credenciales no son válidas.")

            locked_user = auth.get_user_for_update(user["id_usuario"])
            locked_credential = auth.get_credential_for_update(credential["id_credencial_usuario"])
            locked_now = sessions.get_wall_clock_timestamp()
            if (
                not _eligible_user(locked_user)
                or not _usable_credential(locked_credential, locked_now)
                or locked_credential["id_usuario"] != locked_user["id_usuario"]
                or locked_credential["hash_credencial"] != phc
            ):
                raise InvalidCredentials("Las credenciales no son válidas.")

            expires_at = locked_now + SESSION_ABSOLUTE_TTL
            for _ in range(TOKEN_COLLISION_MAX_ATTEMPTS):
                token = generate_access_token()
                try:
                    with self.db.begin_nested():
                        session_id = sessions.insert(
                            id_usuario=locked_user["id_usuario"],
                            id_credencial_usuario=locked_credential["id_credencial_usuario"],
                            id_instalacion_origen=installation.id_instalacion,
                            token_digest=digest_access_token(token),
                            started_at=locked_now,
                            expires_at=expires_at,
                        )
                        self.db.flush()
                    self.db.commit()
                    return LoginResult(token, expires_at, session_id)
                except IntegrityError as exc:
                    if getattr(getattr(exc, "orig", None), "diag", None) is None or exc.orig.diag.constraint_name != "uq_sesion_token":
                        raise
            raise AuthenticationTechnicalError("No fue posible crear la sesión.")
        except (InvalidCredentials, AuthenticationUnavailable, AuthenticationTechnicalError):
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise AuthenticationTechnicalError("No fue posible completar la autenticación.") from exc

    def logout(self, access_token: str) -> None:
        sessions = SesionUsuarioRepository(self.db)
        try:
            row = sessions.get_by_digest_for_update(digest_access_token(access_token))
            if row is not None and row["estado_sesion"] == "ACTIVA":
                now = sessions.get_wall_clock_timestamp()
                if row["expira_en"] <= now:
                    sessions.finish(row["id_sesion_usuario"], now, "EXPIRADA", "EXPIRACION_ABSOLUTA")
                else:
                    sessions.finish(row["id_sesion_usuario"], now, "CERRADA", "LOGOUT_USUARIO")
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise SessionTechnicalError("No fue posible cerrar la sesión.") from exc
