from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.application.common.synchronization_policy import SynchronizationPolicyError
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository


@pytest.mark.parametrize(
    ("event_type", "aggregate_type", "payload"),
    [
        ("credencial_creada", "credencial_usuario", {}),
        ("sesion_iniciada", "sesion_usuario", {}),
        ("venta_confirmada", "venta", {"id_venta": 1, "data": [{"hash_credencial": "DO_NOT_LOG_PHC_455"}]}),
        ("venta_confirmada", "venta", {"id_venta": 1, "context": {"token_sesion": "DO_NOT_LOG_TOKEN_455"}}),
    ],
)
def test_rechazo_previo_no_inserta_ni_expone_sentinelas(
    db_session, capsys, caplog, event_type, aggregate_type, payload
) -> None:
    before = db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one()
    with pytest.raises(SynchronizationPolicyError):
        OutboxRepository(db_session).add_event(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=1,
            payload=payload,
            occurred_at=datetime.now(UTC),
        )
    assert db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one() == before
    db_session.execute(text("SELECT 1")).scalar_one()  # transacción sigue utilizable
    captured = capsys.readouterr()
    for sentinel in ("DO_NOT_LOG_PHC_455", "DO_NOT_LOG_TOKEN_455"):
        assert sentinel not in captured.out
        assert sentinel not in captured.err
        assert sentinel not in caplog.text


def test_error_crudo_de_publisher_se_persiste_sanitizado(db_session, capsys, caplog) -> None:
    repo = OutboxRepository(db_session)
    event = repo.add_event(
        event_type="sucursal_creada",
        aggregate_type="sucursal",
        aggregate_id=1,
        payload={"nombre": "payload no renderizable"},
        occurred_at=datetime.now(UTC),
    )
    raw = (
        "postgresql://usuario:password@host/db DO_NOT_LOG_PASSWORD_455 "
        "DO_NOT_LOG_PHC_455 DO_NOT_LOG_TOKEN_455 SELECT"
    )
    updated = repo.mark_as_failed(event["id"], error=raw)
    assert updated is not None
    assert updated["last_error"] == "SYNC_PUBLISH_FAILED"
    persisted = db_session.execute(
        text("SELECT last_error FROM outbox_event WHERE id=:id"), {"id": event["id"]}
    ).scalar_one()
    assert persisted == "SYNC_PUBLISH_FAILED"
    captured = capsys.readouterr()
    assert raw not in captured.out
    assert raw not in captured.err
    assert raw not in caplog.text
