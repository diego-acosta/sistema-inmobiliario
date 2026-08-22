from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.infrastructure.persistence.repositories.usuario_sistema_repository import (
    UsuarioSistemaRepository,
)


def test_usuario_uid_global_tiene_contrato_fisico(db_session):
    column = db_session.execute(
        text(
            """
            SELECT data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'usuario'
              AND column_name = 'uid_global'
            """
        )
    ).mappings().one()
    assert column["data_type"] == "uuid"
    assert column["is_nullable"] == "NO"
    assert "gen_random_uuid" in column["column_default"]

    constraint = db_session.execute(
        text(
            """
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'public.usuario'::regclass
              AND conname = 'uq_usuario_uid_global'
            """
        )
    ).scalar_one()
    assert constraint == "UNIQUE (uid_global)"
    assert db_session.execute(
        text("SELECT count(*) FROM usuario WHERE uid_global IS NULL")
    ).scalar_one() == 0
    assert db_session.execute(
        text(
            "SELECT count(*) - count(DISTINCT uid_global) FROM usuario"
        )
    ).scalar_one() == 0


def test_uid_global_es_inmutable_y_se_conserva_en_baja(db_session):
    row = db_session.execute(
        text("SELECT id_usuario, uid_global FROM usuario ORDER BY id_usuario LIMIT 1")
    ).mappings().one()

    with pytest.raises(DBAPIError, match="usuario.uid_global es inmutable"):
        db_session.execute(
            text("UPDATE usuario SET uid_global=:new_uid WHERE id_usuario=:id"),
            {"new_uid": str(uuid4()), "id": row["id_usuario"]},
        )
    db_session.rollback()

    db_session.execute(
        text("UPDATE usuario SET deleted_at=CURRENT_TIMESTAMP WHERE id_usuario=:id"),
        {"id": row["id_usuario"]},
    )
    preserved = db_session.execute(
        text("SELECT uid_global FROM usuario WHERE id_usuario=:id"),
        {"id": row["id_usuario"]},
    ).scalar_one()
    assert preserved == row["uid_global"]

    with pytest.raises(DBAPIError):
        db_session.execute(
            text(
                """
                INSERT INTO usuario
                    (codigo_usuario, login, estado_usuario, uid_global)
                VALUES ('UID-REUSE', 'uid.reuse', 'ACTIVO', :uid)
                """
            ),
            {"uid": str(row["uid_global"])},
        )


def test_resolver_uid_global_devuelve_usuario_local_sin_fallback(db_session):
    expected = db_session.execute(
        text("SELECT id_usuario, uid_global FROM usuario ORDER BY id_usuario LIMIT 1")
    ).mappings().one()
    repository = UsuarioSistemaRepository(db_session)

    resolved = repository.get_by_uid_global(str(expected["uid_global"]))
    assert resolved is not None
    assert resolved["id_usuario"] == expected["id_usuario"]
    assert resolved["uid_global"] == expected["uid_global"]
    assert repository.get_by_uid_global(str(uuid4())) is None

    # Una identidad con forma de login, email o PK remota no activa fallback alguno.
    for non_uid in ("admin", "admin@example.com", str(expected["id_usuario"])):
        with pytest.raises((DBAPIError, ValueError)):
            repository.get_by_uid_global(non_uid)
        db_session.rollback()


def test_usuarios_nuevos_reciben_uid_independiente(db_session):
    uid = db_session.execute(
        text(
            """
            INSERT INTO usuario (codigo_usuario, login, email, estado_usuario)
            VALUES ('UID-NEW', 'uid.new', 'uid.new@example.com', 'ACTIVO')
            RETURNING uid_global
            """
        )
    ).scalar_one()
    assert isinstance(uid, UUID)
    assert str(uid) not in {"UID-NEW", "uid.new", "uid.new@example.com"}
