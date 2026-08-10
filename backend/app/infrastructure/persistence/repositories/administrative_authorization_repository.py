"""Proyección mínima para autorización administrativa global read-only."""

from dataclasses import dataclass

from sqlalchemy import text


@dataclass(frozen=True, slots=True)
class AdministrativeAuthorizationProjection:
    permission_defined: bool
    granted: bool


class AdministrativeAuthorizationRepository:
    def __init__(self, session) -> None:
        self.db = session

    def resolve_global_permission(
        self, id_usuario: int, permission_code: str
    ) -> AdministrativeAuthorizationProjection:
        """Evalúa una concesión GLOBAL usando el reloj de PostgreSQL."""
        statement = text("""
            WITH reloj AS MATERIALIZED (
                SELECT clock_timestamp()::timestamp without time zone AS ahora
            )
            SELECT
                EXISTS (
                    SELECT 1
                    FROM permiso p
                    WHERE p.codigo_permiso = :permission_code
                ) AS permission_defined,
                EXISTS (
                    SELECT 1
                    FROM usuario u
                    JOIN usuario_rol_seguridad urs
                      ON urs.id_usuario = u.id_usuario
                    JOIN rol_seguridad r
                      ON r.id_rol_seguridad = urs.id_rol_seguridad
                    JOIN rol_seguridad_permiso rsp
                      ON rsp.id_rol_seguridad = r.id_rol_seguridad
                    JOIN permiso p
                      ON p.id_permiso = rsp.id_permiso
                    CROSS JOIN reloj
                    WHERE u.id_usuario = :id_usuario
                      AND u.estado_usuario = 'ACTIVO'
                      AND u.deleted_at IS NULL
                      AND u.fecha_baja IS NULL
                      AND urs.deleted_at IS NULL
                      AND urs.fecha_desde <= reloj.ahora
                      AND (
                          urs.fecha_hasta IS NULL
                          OR urs.fecha_hasta > reloj.ahora
                      )
                      AND r.estado_rol = 'ACTIVO'
                      AND p.codigo_permiso = :permission_code
                      AND p.estado_permiso = 'ACTIVO'
                ) AS granted
        """)
        row = self.db.execute(
            statement,
            {"id_usuario": id_usuario, "permission_code": permission_code},
        ).mappings().one()
        return AdministrativeAuthorizationProjection(
            permission_defined=row["permission_defined"],
            granted=row["granted"],
        )
