"""Lecturas y locks de usuario/credencial para autenticación; sin transacciones."""

from sqlalchemy import text

_USER_COLUMNS = "id_usuario, estado_usuario, fecha_baja, deleted_at"
_CREDENTIAL_COLUMNS = """id_credencial_usuario, id_usuario, tipo_credencial,
hash_credencial, algoritmo_hash, estado_credencial, es_credencial_principal,
fecha_activacion, fecha_vencimiento, bloqueo_hasta, requiere_reset,
obliga_rotacion, deleted_at"""


class AuthenticationRepository:
    def __init__(self, session) -> None:
        self.db = session

    def get_user_by_login_exact(self, login: str) -> dict | None:
        row = self.db.execute(text(f"SELECT {_USER_COLUMNS} FROM usuario WHERE login = :login"), {"login": login}).mappings().one_or_none()
        return dict(row) if row else None

    def list_password_credentials(self, id_usuario: int) -> list[dict]:
        rows = self.db.execute(text(f"SELECT {_CREDENTIAL_COLUMNS} FROM credencial_usuario WHERE id_usuario=:id_usuario AND tipo_credencial='PASSWORD' ORDER BY id_credencial_usuario"), {"id_usuario": id_usuario}).mappings().all()
        return [dict(row) for row in rows]

    def get_user_for_update(self, id_usuario: int) -> dict | None:
        row = self.db.execute(text(f"SELECT {_USER_COLUMNS} FROM usuario WHERE id_usuario=:id FOR UPDATE"), {"id": id_usuario}).mappings().one_or_none()
        return dict(row) if row else None

    def get_credential_for_update(self, credential_id: int) -> dict | None:
        row = self.db.execute(text(f"SELECT {_CREDENTIAL_COLUMNS} FROM credencial_usuario WHERE id_credencial_usuario=:id FOR UPDATE"), {"id": credential_id}).mappings().one_or_none()
        return dict(row) if row else None
