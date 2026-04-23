from collections.abc import Iterable
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session


def install_statement_failpoint_once(
    db_session: Session,
    *,
    statement_prefix: str,
    parameter_name: str,
    parameter_value: Any,
    error_message: str,
) -> None:
    connection = db_session.connection()
    normalized_prefix = _normalize_sql(statement_prefix)
    state = {"fired": False}

    def _listener(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        if state["fired"]:
            return
        if not _normalize_sql(statement).startswith(normalized_prefix):
            return

        for parameter_set in _iter_parameter_sets(parameters, executemany=executemany):
            if parameter_set.get(parameter_name) == parameter_value:
                state["fired"] = True
                raise Exception(error_message)

    event.listen(connection, "before_cursor_execute", _listener)


def _iter_parameter_sets(parameters: Any, *, executemany: bool) -> Iterable[dict[str, Any]]:
    if executemany:
        if isinstance(parameters, list):
            for parameter_set in parameters:
                if isinstance(parameter_set, dict):
                    yield parameter_set
        return

    if isinstance(parameters, dict):
        yield parameters


def _normalize_sql(statement: str) -> str:
    return " ".join(statement.lower().split())
