from app.infrastructure.persistence.repositories.credencial_usuario_repository import CredencialUsuarioRepository


def test_repository_uses_postgresql_transaction_timestamp(db_session):
    first = CredencialUsuarioRepository(db_session).get_transaction_timestamp()
    second = CredencialUsuarioRepository(db_session).get_transaction_timestamp()
    assert first == second
