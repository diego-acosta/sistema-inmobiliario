from typing import Any

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository

_ROL_SEGURIDAD_COLUMNS = """
    id_rol_seguridad,
    codigo_rol,
    nombre_rol,
    descripcion,
    estado_rol
"""

_PERMISO_COLUMNS = """
    id_permiso,
    codigo_permiso,
    nombre_permiso,
    descripcion,
    estado_permiso
"""


class RolSeguridadRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        return dict(row)

    def list_roles_seguridad(self) -> list[dict[str, Any]]:
        statement = text(f"""
            SELECT {_ROL_SEGURIDAD_COLUMNS}
            FROM rol_seguridad
            ORDER BY codigo_rol, id_rol_seguridad
            """)
        return [self._map(row) for row in self.db.execute(statement).mappings().all()]

    def get_rol_seguridad(self, id_rol_seguridad: int) -> dict[str, Any] | None:
        statement = text(f"""
            SELECT {_ROL_SEGURIDAD_COLUMNS}
            FROM rol_seguridad
            WHERE id_rol_seguridad = :id_rol_seguridad
            """)
        row = (
            self.db.execute(statement, {"id_rol_seguridad": id_rol_seguridad})
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def list_permisos(self) -> list[dict[str, Any]]:
        statement = text(f"""
            SELECT {_PERMISO_COLUMNS}
            FROM permiso
            ORDER BY codigo_permiso, id_permiso
            """)
        return [self._map(row) for row in self.db.execute(statement).mappings().all()]

    def list_permisos_by_rol_seguridad(
        self, id_rol_seguridad: int
    ) -> list[dict[str, Any]] | None:
        if self.get_rol_seguridad(id_rol_seguridad) is None:
            return None

        statement = text(f"""
            SELECT p.id_permiso,
                   p.codigo_permiso,
                   p.nombre_permiso,
                   p.descripcion,
                   p.estado_permiso
            FROM rol_seguridad_permiso rsp
            JOIN permiso p ON p.id_permiso = rsp.id_permiso
            WHERE rsp.id_rol_seguridad = :id_rol_seguridad
            ORDER BY p.codigo_permiso, p.id_permiso
            """)
        return [
            self._map(row)
            for row in self.db.execute(
                statement, {"id_rol_seguridad": id_rol_seguridad}
            )
            .mappings()
            .all()
        ]
