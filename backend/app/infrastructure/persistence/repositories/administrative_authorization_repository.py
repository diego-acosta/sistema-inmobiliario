"""Persistencia read-only para la autorización administrativa D1."""

from dataclasses import dataclass

from sqlalchemy import bindparam, text


@dataclass(frozen=True, slots=True)
class AdministrativeAuthorizationProjection:
    permission_defined: bool
    permission_active: bool
    principal_active: bool
    global_granted: bool
    contextual_granted: bool
    denied: bool
    scope_identifiable: bool
    branch_active: bool
    branch_allows_operation: bool
    has_current_assignment: bool
    assignment_capabilities_satisfied: bool


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationProjection:
    permission_defined: bool
    permission_active: bool
    principal_active: bool
    global_granted: bool
    denied: bool
    contextual_scope_ids: frozenset[int]


class AdministrativeAuthorizationRepository:
    def __init__(self, session) -> None:
        self.db = session

    def resolve_permission(
        self,
        id_usuario: int,
        permission_code: str,
        *,
        id_sucursal: int | None = None,
        require_can_query: bool = False,
        require_can_operate: bool = False,
        require_can_administer: bool = False,
    ) -> AdministrativeAuthorizationProjection:
        """Resuelve P/E/G/C/D y carriers H con un único instante UTC."""
        statement = text("""
            WITH reloj AS MATERIALIZED (
                SELECT clock_timestamp() AT TIME ZONE 'UTC' AS ahora
            ), permiso_objetivo AS MATERIALIZED (
                SELECT p.id_permiso, p.estado_permiso
                FROM permiso p
                WHERE p.codigo_permiso = :permission_code
            ), principal AS MATERIALIZED (
                SELECT EXISTS (
                    SELECT 1
                    FROM usuario u
                    WHERE u.id_usuario = :id_usuario
                      AND u.estado_usuario = 'ACTIVO'
                      AND u.deleted_at IS NULL
                      AND u.fecha_baja IS NULL
                ) AS activo
            )
            SELECT
                EXISTS (SELECT 1 FROM permiso_objetivo) AS permission_defined,
                EXISTS (
                    SELECT 1 FROM permiso_objetivo
                    WHERE estado_permiso = 'ACTIVO'
                ) AS permission_active,
                (SELECT activo FROM principal) AS principal_active,
                EXISTS (
                    SELECT 1
                    FROM usuario_rol_seguridad urs
                    JOIN rol_seguridad r
                      ON r.id_rol_seguridad = urs.id_rol_seguridad
                    JOIN rol_seguridad_permiso rsp
                      ON rsp.id_rol_seguridad = r.id_rol_seguridad
                    JOIN permiso_objetivo p
                      ON p.id_permiso = rsp.id_permiso
                    CROSS JOIN reloj
                    WHERE urs.id_usuario = :id_usuario
                      AND urs.deleted_at IS NULL
                      AND urs.fecha_desde <= reloj.ahora
                      AND (urs.fecha_hasta IS NULL OR urs.fecha_hasta > reloj.ahora)
                      AND r.estado_rol = 'ACTIVO'
                      AND p.estado_permiso = 'ACTIVO'
                ) AS global_granted,
                CASE WHEN CAST(:id_sucursal AS bigint) IS NULL THEN FALSE ELSE EXISTS (
                    SELECT 1
                    FROM usuario_rol_sucursal urc
                    JOIN rol_seguridad r
                      ON r.id_rol_seguridad = urc.id_rol_seguridad
                    JOIN rol_seguridad_permiso rsp
                      ON rsp.id_rol_seguridad = r.id_rol_seguridad
                    JOIN permiso_objetivo p
                      ON p.id_permiso = rsp.id_permiso
                    CROSS JOIN reloj
                    WHERE urc.id_usuario = :id_usuario
                      AND urc.id_sucursal = CAST(:id_sucursal AS bigint)
                      AND urc.fecha_desde <= reloj.ahora
                      AND (urc.fecha_hasta IS NULL OR urc.fecha_hasta > reloj.ahora)
                      AND r.estado_rol = 'ACTIVO'
                      AND p.estado_permiso = 'ACTIVO'
                ) END AS contextual_granted,
                EXISTS (
                    SELECT 1
                    FROM denegacion_explicita d
                    JOIN permiso_objetivo p ON p.id_permiso = d.id_permiso
                    WHERE d.id_usuario = :id_usuario
                ) AS denied,
                CASE WHEN CAST(:id_sucursal AS bigint) IS NULL THEN FALSE ELSE EXISTS (
                    SELECT 1 FROM sucursal s
                    WHERE s.id_sucursal = CAST(:id_sucursal AS bigint)
                ) END AS scope_identifiable,
                CASE WHEN CAST(:id_sucursal AS bigint) IS NULL THEN FALSE ELSE EXISTS (
                    SELECT 1 FROM sucursal s
                    WHERE s.id_sucursal = CAST(:id_sucursal AS bigint)
                      AND s.estado_sucursal = 'ACTIVA'
                      AND s.deleted_at IS NULL
                      AND s.fecha_baja IS NULL
                ) END AS branch_active,
                CASE WHEN CAST(:id_sucursal AS bigint) IS NULL THEN FALSE ELSE EXISTS (
                    SELECT 1 FROM sucursal s
                    WHERE s.id_sucursal = CAST(:id_sucursal AS bigint)
                      AND s.permite_operacion IS TRUE
                ) END AS branch_allows_operation,
                CASE WHEN CAST(:id_sucursal AS bigint) IS NULL THEN FALSE ELSE EXISTS (
                    SELECT 1
                    FROM usuario_sucursal us
                    CROSS JOIN reloj
                    WHERE us.id_usuario = :id_usuario
                      AND us.id_sucursal = CAST(:id_sucursal AS bigint)
                      AND us.estado_vinculo = 'ACTIVO'
                      AND us.deleted_at IS NULL
                      AND us.fecha_desde <= reloj.ahora
                      AND (us.fecha_hasta IS NULL OR us.fecha_hasta > reloj.ahora)
                ) END AS has_current_assignment,
                CASE WHEN CAST(:id_sucursal AS bigint) IS NULL THEN FALSE ELSE EXISTS (
                    SELECT 1 FROM usuario_sucursal us CROSS JOIN reloj
                    WHERE us.id_usuario = :id_usuario
                      AND us.id_sucursal = CAST(:id_sucursal AS bigint)
                      AND us.estado_vinculo = 'ACTIVO' AND us.deleted_at IS NULL
                      AND us.fecha_desde <= reloj.ahora
                      AND (us.fecha_hasta IS NULL OR us.fecha_hasta > reloj.ahora)
                      AND (
                          :require_can_query IS FALSE
                          OR us.puede_consultar IS TRUE
                      )
                      AND (
                          :require_can_operate IS FALSE
                          OR us.puede_operar IS TRUE
                      )
                      AND (
                          :require_can_administer IS FALSE
                          OR us.puede_administrar IS TRUE
                      )
                ) END AS assignment_capabilities_satisfied
        """)
        row = self.db.execute(
            statement,
            {
                "id_usuario": id_usuario,
                "permission_code": permission_code,
                "id_sucursal": id_sucursal,
                "require_can_query": require_can_query,
                "require_can_operate": require_can_operate,
                "require_can_administer": require_can_administer,
            },
        ).mappings().one()
        return AdministrativeAuthorizationProjection(**dict(row))

    def resolve_global_permission(
        self, id_usuario: int, permission_code: str
    ) -> AdministrativeAuthorizationProjection:
        """Alias compatible; GLOBAL se resuelve en el mismo evaluator D1."""
        return self.resolve_permission(id_usuario, permission_code)

    def resolve_resource_permission(
        self,
        id_usuario: int,
        permission_code: str,
        scope_ids: set[int],
    ) -> ResourceAuthorizationProjection:
        """Resuelve evidencia común y C(s) para filtrado resource-derived."""
        statement = text("""
            WITH reloj AS MATERIALIZED (
                SELECT clock_timestamp() AT TIME ZONE 'UTC' AS ahora
            ), permiso_objetivo AS MATERIALIZED (
                SELECT p.id_permiso, p.estado_permiso
                FROM permiso p
                WHERE p.codigo_permiso = :permission_code
            )
            SELECT
                EXISTS (SELECT 1 FROM permiso_objetivo) AS permission_defined,
                EXISTS (SELECT 1 FROM permiso_objetivo WHERE estado_permiso = 'ACTIVO')
                    AS permission_active,
                EXISTS (
                    SELECT 1 FROM usuario u
                    WHERE u.id_usuario = :id_usuario
                      AND u.estado_usuario = 'ACTIVO'
                      AND u.deleted_at IS NULL AND u.fecha_baja IS NULL
                ) AS principal_active,
                EXISTS (
                    SELECT 1
                    FROM usuario_rol_seguridad urs
                    JOIN rol_seguridad r ON r.id_rol_seguridad = urs.id_rol_seguridad
                    JOIN rol_seguridad_permiso rsp ON rsp.id_rol_seguridad = r.id_rol_seguridad
                    JOIN permiso_objetivo p ON p.id_permiso = rsp.id_permiso
                    CROSS JOIN reloj
                    WHERE urs.id_usuario = :id_usuario
                      AND urs.deleted_at IS NULL
                      AND urs.fecha_desde <= reloj.ahora
                      AND (urs.fecha_hasta IS NULL OR urs.fecha_hasta > reloj.ahora)
                      AND r.estado_rol = 'ACTIVO' AND p.estado_permiso = 'ACTIVO'
                ) AS global_granted,
                EXISTS (
                    SELECT 1 FROM denegacion_explicita d
                    JOIN permiso_objetivo p ON p.id_permiso = d.id_permiso
                    WHERE d.id_usuario = :id_usuario
                ) AS denied,
                COALESCE(array_agg(DISTINCT urc.id_sucursal)
                    FILTER (WHERE urc.id_sucursal IS NOT NULL), ARRAY[]::bigint[])
                    AS contextual_scope_ids
            FROM (SELECT 1) seed
            LEFT JOIN usuario_rol_sucursal urc
              ON urc.id_usuario = :id_usuario
             AND urc.id_sucursal IN :scope_ids
             AND urc.fecha_desde <= (SELECT ahora FROM reloj)
             AND (urc.fecha_hasta IS NULL OR urc.fecha_hasta > (SELECT ahora FROM reloj))
            LEFT JOIN rol_seguridad r ON r.id_rol_seguridad = urc.id_rol_seguridad
                                     AND r.estado_rol = 'ACTIVO'
            LEFT JOIN rol_seguridad_permiso rsp ON rsp.id_rol_seguridad = r.id_rol_seguridad
            LEFT JOIN permiso_objetivo p ON p.id_permiso = rsp.id_permiso
                                        AND p.estado_permiso = 'ACTIVO'
            WHERE urc.id_sucursal IS NULL OR p.id_permiso IS NOT NULL
        """).bindparams(bindparam("scope_ids", expanding=True))
        row = self.db.execute(
            statement,
            {
                "id_usuario": id_usuario,
                "permission_code": permission_code,
                "scope_ids": sorted(scope_ids) or [-1],
            },
        ).mappings().one()
        return ResourceAuthorizationProjection(
            permission_defined=row["permission_defined"],
            permission_active=row["permission_active"],
            principal_active=row["principal_active"],
            global_granted=row["global_granted"],
            denied=row["denied"],
            contextual_scope_ids=frozenset(row["contextual_scope_ids"]),
        )
