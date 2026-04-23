from datetime import UTC, datetime

from sqlalchemy import text

from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)
from tests.test_disponibilidades_create import HEADERS
from tests.test_escrituraciones_create import (
    _confirmar_venta_publica as _confirmar_venta_para_escrituracion,
)
from tests.test_escrituraciones_create import (
    _crear_trigger_falla_escrituracion,
    _payload_escrituracion,
)
from tests.test_ventas_confirm import (
    _crear_trigger_falla_confirmacion_venta,
    _crear_venta_desde_reserva_publica,
    _payload_confirmar_venta,
)


def _table_lock_modes(db_session, *, table_name: str) -> set[str]:
    pid = db_session.execute(text("SELECT pg_backend_pid()")).scalar_one()
    rows = db_session.execute(
        text(
            """
            SELECT lock.mode
            FROM pg_locks AS lock
            JOIN pg_class AS class ON class.oid = lock.relation
            WHERE lock.pid = :pid
              AND lock.granted = TRUE
              AND class.relname = :table_name
            """
        ),
        {"pid": pid, "table_name": table_name},
    ).mappings().all()
    return {row["mode"] for row in rows}


def test_failpoint_confirmacion_no_toma_lock_ddl_en_venta(db_session) -> None:
    _crear_trigger_falla_confirmacion_venta(db_session, id_venta=9202)
    db_session.commit()

    assert "ShareRowExclusiveLock" not in _table_lock_modes(
        db_session, table_name="venta"
    )


def test_failpoint_escrituracion_no_toma_lock_ddl_en_tabla_escrituracion(
    db_session,
) -> None:
    _crear_trigger_falla_escrituracion(db_session, id_venta=9203)
    db_session.commit()

    assert "ShareRowExclusiveLock" not in _table_lock_modes(
        db_session, table_name="escrituracion"
    )


def test_confirm_venta_crea_evento_outbox(client, db_session) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)

    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )

    assert response.status_code == 200
    body = response.json()["data"]

    event_row = db_session.execute(
        text(
            """
            SELECT
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                status,
                published_at,
                processing_reason,
                processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :aggregate_id
              AND event_type = 'venta_confirmada'
            """
        ),
        {"aggregate_id": venta["id_venta"]},
    ).mappings().one()

    assert event_row["event_type"] == "venta_confirmada"
    assert event_row["aggregate_type"] == "venta"
    assert event_row["aggregate_id"] == venta["id_venta"]
    assert event_row["payload"]["id_venta"] == venta["id_venta"]
    assert event_row["payload"]["estado_venta"] == "confirmada"
    assert event_row["status"] == "PENDING"
    assert event_row["published_at"] is None
    assert event_row["processing_reason"] is None
    assert event_row["processing_metadata"] is None
    assert body["estado_venta"] == "confirmada"


def test_confirm_venta_no_crea_evento_outbox_si_falla_la_transaccion(
    client, db_session
) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)
    _crear_trigger_falla_confirmacion_venta(db_session, id_venta=venta["id_venta"])
    db_session.commit()

    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"

    event_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :aggregate_id
              AND event_type = 'venta_confirmada'
            """
        ),
        {"aggregate_id": venta["id_venta"]},
    ).mappings().one()
    assert event_count["total"] == 0

    venta_row = db_session.execute(
        text(
            """
            SELECT estado_venta
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert venta_row["estado_venta"] == "borrador"


def test_create_escrituracion_crea_evento_outbox(client, db_session) -> None:
    venta = _confirmar_venta_para_escrituracion(client, db_session)

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )

    assert response.status_code == 201
    body = response.json()["data"]

    event_row = db_session.execute(
        text(
            """
            SELECT
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                status,
                published_at,
                processing_reason,
                processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :aggregate_id
              AND event_type = 'escrituracion_registrada'
            """
        ),
        {"aggregate_id": venta["id_venta"]},
    ).mappings().one()

    assert event_row["event_type"] == "escrituracion_registrada"
    assert event_row["aggregate_type"] == "venta"
    assert event_row["aggregate_id"] == venta["id_venta"]
    assert event_row["payload"]["id_venta"] == venta["id_venta"]
    assert event_row["payload"]["id_escrituracion"] == body["id_escrituracion"]
    assert event_row["status"] == "PENDING"
    assert event_row["published_at"] is None
    assert event_row["processing_reason"] is None
    assert event_row["processing_metadata"] is None


def test_create_escrituracion_hace_rollback_y_no_deja_evento_outbox(
    client, db_session
) -> None:
    venta = _confirmar_venta_para_escrituracion(client, db_session)
    _crear_trigger_falla_escrituracion(db_session, id_venta=venta["id_venta"])
    db_session.commit()

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"

    event_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :aggregate_id
              AND event_type = 'escrituracion_registrada'
            """
        ),
        {"aggregate_id": venta["id_venta"]},
    ).mappings().one()
    assert event_count["total"] == 0

    escrituraciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM escrituracion
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert escrituraciones["total"] == 0


def test_outbox_mark_as_published_persiste_razon_y_metadata(db_session) -> None:
    repository = OutboxRepository(db_session)
    event = repository.add_event(
        event_type="venta_confirmada",
        aggregate_type="venta",
        aggregate_id=9201,
        payload={"id_venta": 9201, "estado_venta": "confirmada", "objetos": []},
        occurred_at=datetime(2026, 4, 24, 11, 0, 0, tzinfo=UTC),
    )

    processed_at = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)
    published = repository.mark_as_published(
        event["id"],
        published_at=processed_at,
        processing_reason={
            "code": "PUBLISHED_BY_TEST",
            "category": "PUBLISHER_RESULT",
            "detail": "test_publisher_path",
        },
        processing_metadata={
            "processor": "tests.outbox",
            "mode": "publisher",
            "processed_at": processed_at.isoformat(),
            "object_count": 0,
        },
    )
    db_session.commit()

    assert published is not None
    assert published["status"] == "PUBLISHED"
    assert published["processing_reason"] == {
        "code": "PUBLISHED_BY_TEST",
        "category": "PUBLISHER_RESULT",
        "detail": "test_publisher_path",
    }
    assert published["processing_metadata"] == {
        "processor": "tests.outbox",
        "mode": "publisher",
        "processed_at": "2026-04-24T12:00:00+00:00",
        "object_count": 0,
    }

    event_row = db_session.execute(
        text(
            """
            SELECT status, published_at, processing_reason, processing_metadata
            FROM outbox_event
            WHERE id = :id
            """
        ),
        {"id": event["id"]},
    ).mappings().one()

    assert event_row["status"] == "PUBLISHED"
    assert event_row["published_at"] is not None
    assert event_row["processing_reason"] == published["processing_reason"]
    assert event_row["processing_metadata"] == published["processing_metadata"]
