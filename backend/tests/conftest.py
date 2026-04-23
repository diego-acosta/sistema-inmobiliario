import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


os.environ["ENV"] = "test"

from app.api.dependencies import get_db
from app.config.database import engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def validate_test_database_bootstrap() -> None:
    with engine.connect() as connection:
        outbox_table = connection.execute(
            text("SELECT to_regclass('public.outbox_event')")
        ).scalar()
        sucursal_base = connection.execute(
            text("SELECT COUNT(*) FROM sucursal WHERE id_sucursal = 1")
        ).scalar()
        instalacion_base = connection.execute(
            text("SELECT COUNT(*) FROM instalacion WHERE id_instalacion = 1")
        ).scalar()

    if outbox_table != "outbox_event" or sucursal_base != 1 or instalacion_base != 1:
        raise RuntimeError(
            "La base de test no esta bootstrappeada con el schema oficial y el "
            "baseline tecnico requerido. Ejecutar backend\\scripts\\reset_db.bat "
            "antes de correr pytest."
        )


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    testing_session_factory = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        class_=Session,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = testing_session_factory()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
