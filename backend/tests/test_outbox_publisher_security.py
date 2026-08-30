from __future__ import annotations

import sys

from scripts import outbox_publisher


def test_publisher_real_no_imprime_payload_ni_error_crudo(monkeypatch, capsys, caplog) -> None:
    sentinels = (
        "DO_NOT_LOG_PASSWORD_455",
        "DO_NOT_LOG_PHC_455",
        "DO_NOT_LOG_TOKEN_455",
    )
    raw_error = RuntimeError(
        "postgresql://user:password@host/db DO_NOT_LOG_PHC_455 SELECT ..."
    )

    class FakeDb:
        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakeRepository:
        failed_error = None
        requested_event_types = None

        def __init__(self, db) -> None:
            pass

        def get_pending_events(self, *, limit, event_types=None):
            type(self).requested_event_types = set(event_types or ())
            return [{
                "id": 455,
                "event_id": "00000000-0000-0000-0000-000000000455",
                "event_type": "sucursal_creada",
                "aggregate_type": "sucursal",
                "aggregate_id": 1,
                "retry_count": 0,
                "payload": {"secrets": list(sentinels)},
            }]

        def mark_as_published(self, *args, **kwargs):
            raise raw_error

        def mark_as_failed(self, event_id, *, error):
            type(self).failed_error = error

    import app.config.database
    import app.infrastructure.persistence.repositories.outbox_repository

    monkeypatch.setattr(app.config.database, "SessionLocal", FakeDb)
    monkeypatch.setattr(
        app.infrastructure.persistence.repositories.outbox_repository,
        "OutboxRepository",
        FakeRepository,
    )
    monkeypatch.setattr(sys, "argv", ["outbox_publisher.py", "--env", "test"])

    assert outbox_publisher.main() == 0
    captured = capsys.readouterr()
    for sentinel in sentinels:
        assert sentinel not in captured.out
        assert sentinel not in captured.err
        assert sentinel not in caplog.text
    assert "postgresql://" not in captured.out
    assert FakeRepository.failed_error is raw_error
    assert "sucursal_creada" in FakeRepository.requested_event_types
    assert "escrituracion_registrada" not in FakeRepository.requested_event_types
    assert "usuario_creado" not in FakeRepository.requested_event_types
    assert "usuario_desactivado" not in FakeRepository.requested_event_types
    assert "SYNC_PUBLISH_FAILED" in captured.out
