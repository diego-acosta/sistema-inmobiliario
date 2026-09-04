from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class OperationalContextProjection:
    branch_exists: bool
    branch_eligible: bool
    installation_belongs_to_branch: bool
    principal_has_operational_scope: bool | None


class TechnicalContextRepository:
    """Validaciones de pertenencia para metadata técnica CORE-EF."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def installation_belongs_to_branch(
        self, *, id_sucursal: int, id_instalacion: int
    ) -> bool:
        return (
            self._session.execute(
                text(
                    """
                    SELECT 1
                    FROM public.instalacion
                    WHERE id_instalacion = :id_instalacion
                      AND id_sucursal = :id_sucursal
                    """
                ),
                {
                    "id_sucursal": id_sucursal,
                    "id_instalacion": id_instalacion,
                },
            ).scalar_one_or_none()
            is not None
        )

    def resolve_operational_context(
        self,
        *,
        id_sucursal: int,
        id_instalacion: int,
        id_usuario: int | None,
    ) -> OperationalContextProjection:
        """Proyecta elegibilidad y alcance sin locks ni efectos transaccionales."""
        row = self._session.execute(
            text(
                """
                WITH reloj AS MATERIALIZED (
                    SELECT clock_timestamp()::timestamp without time zone AS ahora
                )
                SELECT
                    EXISTS (
                        SELECT 1 FROM public.sucursal s
                        WHERE s.id_sucursal = :id_sucursal
                    ) AS branch_exists,
                    EXISTS (
                        SELECT 1 FROM public.sucursal s
                        WHERE s.id_sucursal = :id_sucursal
                          AND s.estado_sucursal = 'ACTIVA'
                          AND s.permite_operacion = true
                          AND s.deleted_at IS NULL
                          AND s.fecha_baja IS NULL
                    ) AS branch_eligible,
                    EXISTS (
                        SELECT 1 FROM public.instalacion i
                        WHERE i.id_instalacion = :id_instalacion
                          AND i.id_sucursal = :id_sucursal
                    ) AS installation_belongs_to_branch,
                    CASE WHEN CAST(:id_usuario AS bigint) IS NULL THEN NULL
                         ELSE EXISTS (
                            SELECT 1
                              FROM public.usuario_sucursal us, reloj
                             WHERE us.id_usuario = CAST(:id_usuario AS bigint)
                               AND us.id_sucursal = :id_sucursal
                               AND us.estado_vinculo = 'ACTIVO'
                               AND us.puede_operar = true
                               AND us.deleted_at IS NULL
                               AND us.fecha_desde <= reloj.ahora
                               AND (us.fecha_hasta IS NULL
                                    OR us.fecha_hasta > reloj.ahora)
                         )
                    END AS principal_has_operational_scope
                """
            ),
            {
                "id_sucursal": id_sucursal,
                "id_instalacion": id_instalacion,
                "id_usuario": id_usuario,
            },
        ).mappings().one()
        return OperationalContextProjection(**row)
