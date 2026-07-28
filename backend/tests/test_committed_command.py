from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.application.common.transaction import committed_command


def test_committed_command_commits_before_returning_success() -> None:
    session = MagicMock()
    session.in_transaction.return_value = False

    with committed_command(session):
        session.execute("write complete sale")

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_committed_command_rolls_back_all_stages_on_command_error() -> None:
    session = MagicMock()
    session.in_transaction.return_value = False

    with pytest.raises(RuntimeError, match="outbox failure"):
        with committed_command(session):
            raise RuntimeError("outbox failure")

    session.commit.assert_not_called()
    session.begin.return_value.__exit__.assert_called_once()


def test_committed_command_exposes_commit_failure_and_rolls_back() -> None:
    session = MagicMock()
    session.in_transaction.return_value = False
    session.commit.side_effect = RuntimeError("commit failure")

    with pytest.raises(RuntimeError, match="commit failure"):
        with committed_command(session):
            session.execute("write complete sale")

    session.commit.assert_called_once_with()
    session.rollback.assert_called_once_with()


def test_committed_command_commits_outer_transaction_after_releasing_savepoint() -> None:
    session = MagicMock()
    session.in_transaction.return_value = True

    with committed_command(session):
        session.execute("write after validation query")

    session.begin_nested.assert_called_once_with()
    session.commit.assert_called_once_with()


def test_committed_command_persists_after_request_session_closes() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE venta (id_venta INTEGER PRIMARY KEY)"))

    request_session = Session(engine)
    request_session.execute(text("SELECT COUNT(*) FROM venta"))  # autobegin
    with committed_command(request_session):
        request_session.execute(text("INSERT INTO venta (id_venta) VALUES (3)"))
    request_session.close()

    with Session(engine) as second_session:
        assert second_session.execute(
            text("SELECT id_venta FROM venta WHERE id_venta = 3")
        ).scalar_one() == 3
