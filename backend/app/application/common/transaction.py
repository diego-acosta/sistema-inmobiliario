from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


@contextmanager
def committed_command(session: Any) -> Generator[None, None, None]:
    """Own the transaction for a complete application command.

    SQLAlchemy may already have autobegun a transaction because the command ran
    validation queries.  A nested transaction would only release a savepoint and
    would leave that outer transaction pending.  Completing the context therefore
    commits the session transaction explicitly; every exception, including a
    commit failure, rolls the whole command back.
    """

    transaction = (
        session.begin_nested() if session.in_transaction() else session.begin()
    )
    with transaction:
        yield

    # Exiting a nested transaction only releases its savepoint.  The explicit
    # commit is what makes an autobegun outer transaction durable.
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
