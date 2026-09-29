from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session


def lock_usuarios_ordered(
    session: Session,
    id_usuarios: Iterable[int],
) -> dict[int, dict[str, Any]]:
    usuarios: dict[int, dict[str, Any]] = {}
    for id_usuario in sorted(set(id_usuarios)):
        row = session.execute(
            text(
                """
                SELECT id_usuario, estado_usuario, fecha_baja, deleted_at
                FROM usuario
                WHERE id_usuario = :id_usuario
                FOR UPDATE
                """
            ),
            {"id_usuario": id_usuario},
        ).mappings().one_or_none()
        if row is not None:
            usuarios[id_usuario] = dict(row)
    return usuarios
