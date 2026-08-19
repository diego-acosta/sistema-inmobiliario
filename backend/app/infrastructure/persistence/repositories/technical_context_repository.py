from sqlalchemy import text
from sqlalchemy.orm import Session


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
