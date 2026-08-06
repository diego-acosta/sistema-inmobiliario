"""Persistencia interna de credenciales PASSWORD; nunca administra transacciones."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text


@dataclass(frozen=True, slots=True)
class _StoredCredential:
    id_credencial_usuario: int
    id_usuario: int
    hash_credencial: str
    estado_credencial: str
    es_credencial_principal: bool
    deleted_at: datetime | None


class CredencialUsuarioRepository:
    def __init__(self, session) -> None:
        self.db = session

    @staticmethod
    def _map(row) -> _StoredCredential:
        return _StoredCredential(**dict(row))

    def find_created_by_op_id(self, op_id: UUID) -> _StoredCredential | None:
        row = (
            self.db.execute(
                text("""
            SELECT id_credencial_usuario, id_usuario, hash_credencial,
                   estado_credencial, es_credencial_principal, deleted_at
            FROM credencial_usuario WHERE op_id_alta = :op_id
        """),
                {"op_id": str(op_id)},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row else None

    def list_password_credentials_for_update(
        self, id_usuario: int
    ) -> list[_StoredCredential]:
        rows = (
            self.db.execute(
                text("""
            SELECT id_credencial_usuario, id_usuario, hash_credencial,
                   estado_credencial, es_credencial_principal, deleted_at
            FROM credencial_usuario
            WHERE id_usuario = :id_usuario AND tipo_credencial = 'PASSWORD'
            ORDER BY id_credencial_usuario FOR UPDATE
        """),
                {"id_usuario": id_usuario},
            )
            .mappings()
            .all()
        )
        return [self._map(row) for row in rows]

    def get_transaction_timestamp(self) -> datetime:
        return self.db.execute(text("SELECT CURRENT_TIMESTAMP")).scalar_one()

    def revoke_password(
        self,
        credential_id: int,
        *,
        timestamp: datetime,
        installation_id: int,
        op_id: UUID,
    ) -> None:
        self.db.execute(
            text("""
            UPDATE credencial_usuario SET estado_credencial='REVOCADA',
              fecha_revocacion=:timestamp, motivo_revocacion='RESET_ADMINISTRATIVO_LOCAL',
              es_credencial_principal=false, id_instalacion_ultima_modificacion=:installation_id,
              op_id_ultima_modificacion=:op_id
            WHERE id_credencial_usuario=:credential_id
        """),
            {
                "timestamp": timestamp,
                "installation_id": installation_id,
                "op_id": str(op_id),
                "credential_id": credential_id,
            },
        )

    def insert_active_password(
        self,
        *,
        id_usuario: int,
        password_hash: str,
        algorithm: str,
        timestamp: datetime,
        installation_id: int,
        op_id: UUID,
    ) -> None:
        self.db.execute(
            text("""
            INSERT INTO credencial_usuario (
              id_usuario,tipo_credencial,identificador_credencial,hash_credencial,
              algoritmo_hash,estado_credencial,es_credencial_principal,fecha_alta,
              fecha_activacion,fecha_vencimiento,fecha_revocacion,motivo_revocacion,
              obliga_rotacion,ultimo_cambio_credencial,intentos_fallidos_acumulados,
              ultimo_intento_fallido,bloqueo_hasta,requiere_reset,observaciones,
              id_instalacion_origen,id_instalacion_ultima_modificacion,op_id_alta,
              op_id_ultima_modificacion,deleted_at)
            VALUES (:id_usuario,'PASSWORD',NULL,:password_hash,:algorithm,'ACTIVA',true,
              :timestamp,:timestamp,NULL,NULL,NULL,false,:timestamp,0,NULL,NULL,false,NULL,
              :installation_id,:installation_id,:op_id,:op_id,NULL)
        """),
            {
                "id_usuario": id_usuario,
                "password_hash": password_hash,
                "algorithm": algorithm,
                "timestamp": timestamp,
                "installation_id": installation_id,
                "op_id": str(op_id),
            },
        )
