from sqlalchemy import text

from app.application.inmuebles.services.consume_venta_confirmada_service import (
    ConsumeVentaConfirmadaService,
)
from app.infrastructure.persistence.repositories.inmueble_repository import (
    InmuebleRepository,
)
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)
from tests.test_escrituraciones_create import _confirmar_venta_publica


def _build_service(db_session) -> ConsumeVentaConfirmadaService:
    return ConsumeVentaConfirmadaService(
        db=db_session,
        inmueble_repository=InmuebleRepository(db_session),
        outbox_repository=OutboxRepository(db_session),
    )


def test_consume_venta_confirmada_es_no_op_explicito_y_publica_evento(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    disponibilidades_antes = db_session.execute(
        text(
            """
            SELECT id_disponibilidad, estado_disponibilidad, fecha_desde, fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().all()

    result = _build_service(db_session).execute(limit=100)

    assert result.success is True
    assert result.data is not None
    assert result.data["processed_events"] == 1
    assert result.data["events"][0]["id_venta"] == venta["id_venta"]
    assert result.data["events"][0]["effect"] == "NO_OP"
    assert result.data["events"][0]["objects"] == [
        {
            "id_inmueble": venta["id_inmueble"],
            "id_unidad_funcional": None,
            "status": "NO_OP",
        }
    ]

    event_row = db_session.execute(
        text(
            """
            SELECT status, published_at, processing_reason, processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :id_venta
              AND event_type = 'venta_confirmada'
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert event_row["status"] == "PUBLISHED"
    assert event_row["published_at"] is not None
    assert event_row["processing_reason"] == {
        "code": "CONSUMED_NO_OP",
        "category": "CONSUMER_RESULT",
        "detail": "venta_confirmada_no_mutates_operational_state",
    }
    assert event_row["processing_metadata"]["processor"] == (
        "inmobiliario.consume_venta_confirmada"
    )
    assert event_row["processing_metadata"]["mode"] == "consumer"
    assert event_row["processing_metadata"]["object_count"] == 1
    assert event_row["processing_metadata"]["processed_at"] is not None

    disponibilidades_despues = db_session.execute(
        text(
            """
            SELECT id_disponibilidad, estado_disponibilidad, fecha_desde, fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().all()
    assert disponibilidades_despues == disponibilidades_antes

    abiertas = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().all()
    assert abiertas == [{"estado_disponibilidad": "RESERVADA"}]

    ocupaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM ocupacion
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().one()
    assert ocupaciones["total"] == 0


def test_consume_venta_confirmada_es_idempotente_sin_generar_writes(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    service = _build_service(db_session)

    first_result = service.execute(limit=100)
    assert first_result.success is True

    before_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().one()["total"]

    db_session.execute(
        text(
            """
            UPDATE outbox_event
            SET status = 'PENDING',
                published_at = NULL
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :id_venta
              AND event_type = 'venta_confirmada'
            """
        ),
        {"id_venta": venta["id_venta"]},
    )
    db_session.commit()

    second_result = service.execute(limit=100)

    assert second_result.success is True
    assert second_result.data is not None
    assert second_result.data["processed_events"] == 1
    assert second_result.data["events"][0]["effect"] == "NO_OP"
    assert second_result.data["events"][0]["objects"] == [
        {
            "id_inmueble": venta["id_inmueble"],
            "id_unidad_funcional": None,
            "status": "NO_OP",
        }
    ]

    after_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().one()["total"]
    assert after_count == before_count

    abiertas = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().all()
    assert abiertas == [{"estado_disponibilidad": "RESERVADA"}]

    ocupaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM ocupacion
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().one()
    assert ocupaciones["total"] == 0


def test_consume_venta_confirmada_rechaza_objeto_inexistente_con_estado_terminal(
    db_session,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO outbox_event (
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                occurred_at,
                published_at,
                status
            )
            VALUES (
                'venta_confirmada',
                'venta',
                9101,
                '{
                    "id_venta": 9101,
                    "id_reserva_venta": 9100,
                    "estado_venta": "confirmada",
                    "objetos": [{"id_inmueble": 999999, "id_unidad_funcional": null}]
                }'::jsonb,
                TIMESTAMP '2026-04-24 11:00:00',
                NULL,
                'PENDING'
            )
            """
        )
    )
    db_session.commit()

    result = _build_service(db_session).execute(limit=100)

    assert result.success is False
    assert result.errors == ["NOT_FOUND_INMUEBLE"]

    event_row = db_session.execute(
        text(
            """
            SELECT status, published_at, processing_reason, processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = 9101
              AND event_type = 'venta_confirmada'
            """
        )
    ).mappings().one()
    assert event_row["status"] == "REJECTED"
    assert event_row["published_at"] is None
    assert event_row["processing_reason"] == {
        "code": "NOT_FOUND_INMUEBLE",
        "category": "CONSUMER_REJECTION",
        "detail": "venta_confirmada_rejected_due_to_permanent_inconsistency",
    }
    assert event_row["processing_metadata"]["processor"] == (
        "inmobiliario.consume_venta_confirmada"
    )
    assert event_row["processing_metadata"]["mode"] == "consumer"
    assert event_row["processing_metadata"]["object_count"] == 0
    assert event_row["processing_metadata"]["processed_at"] is not None


def test_consume_venta_confirmada_rechaza_payload_invalido_con_estado_terminal(
    db_session,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO outbox_event (
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                occurred_at,
                published_at,
                status
            )
            VALUES (
                'venta_confirmada',
                'venta',
                9102,
                '{"id_venta": 9102, "estado_venta": "borrador", "objetos": []}'::jsonb,
                TIMESTAMP '2026-04-24 11:00:00',
                NULL,
                'PENDING'
            )
            """
        )
    )
    db_session.commit()

    result = _build_service(db_session).execute(limit=100)

    assert result.success is False
    assert result.errors == ["INVALID_EVENT_STATE"]

    event_row = db_session.execute(
        text(
            """
            SELECT status, published_at, processing_reason, processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = 9102
              AND event_type = 'venta_confirmada'
            """
        )
    ).mappings().one()
    assert event_row["status"] == "REJECTED"
    assert event_row["published_at"] is None
    assert event_row["processing_reason"] == {
        "code": "INVALID_EVENT_STATE",
        "category": "CONSUMER_REJECTION",
        "detail": "venta_confirmada_rejected_due_to_permanent_inconsistency",
    }
    assert event_row["processing_metadata"]["processor"] == (
        "inmobiliario.consume_venta_confirmada"
    )
    assert event_row["processing_metadata"]["mode"] == "consumer"
    assert event_row["processing_metadata"]["object_count"] == 0
    assert event_row["processing_metadata"]["processed_at"] is not None
