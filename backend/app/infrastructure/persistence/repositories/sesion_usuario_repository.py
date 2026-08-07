"""Persistencia local de sesiones administrativas; sin commit ni rollback."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import text


class SesionUsuarioRepository:
    def __init__(self, session) -> None:
        self.db = session

    def get_wall_clock_timestamp(self) -> datetime:
        """Instante PostgreSQL real, aun dentro de una transacción ya iniciada."""
        # clock_timestamp avanza durante la transacción; el cast conserva la
        # convención física timestamp without time zone del schema existente.
        return self.db.execute(
            text("SELECT clock_timestamp()::timestamp without time zone")
        ).scalar_one()

    def insert(self, *, id_usuario: int, id_credencial_usuario: int, id_instalacion_origen: int, token_digest: str, started_at: datetime, expires_at: datetime) -> UUID:
        return UUID(str(self.db.execute(text("""
            INSERT INTO sesion_usuario (id_usuario,id_credencial_usuario,id_sucursal_operativa,
              id_instalacion_origen,token_sesion,fecha_hora_inicio,fecha_hora_ultima_actividad,
              fecha_hora_cierre,estado_sesion,motivo_cierre,origen_autenticacion,ip_origen,
              nombre_equipo_origen,version_cliente,requiere_reautenticacion,expira_en,observaciones)
            VALUES (:user_id,:credential_id,NULL,:installation_id,:digest,:started,:started,NULL,
              'ACTIVA',NULL,'PASSWORD',NULL,NULL,NULL,false,:expires,NULL)
            RETURNING uid_global
        """), {"user_id": id_usuario, "credential_id": id_credencial_usuario, "installation_id": id_instalacion_origen, "digest": token_digest, "started": started_at, "expires": expires_at}).scalar_one()))

    def get_by_digest(self, digest: str) -> dict | None:
        row = self.db.execute(text("SELECT * FROM sesion_usuario WHERE token_sesion=:digest"), {"digest": digest}).mappings().one_or_none()
        return dict(row) if row else None

    def get_by_digest_for_update(self, digest: str) -> dict | None:
        row = self.db.execute(text("SELECT * FROM sesion_usuario WHERE token_sesion=:digest FOR UPDATE"), {"digest": digest}).mappings().one_or_none()
        return dict(row) if row else None

    def finish(self, session_id: int, timestamp: datetime, state: str, reason: str) -> None:
        self.db.execute(text("UPDATE sesion_usuario SET estado_sesion=:state, fecha_hora_cierre=:closed, motivo_cierre=:reason WHERE id_sesion_usuario=:id AND estado_sesion='ACTIVA'"), {"state": state, "closed": timestamp, "reason": reason, "id": session_id})
