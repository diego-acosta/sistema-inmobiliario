"""
Tests de integración para el refactor de outbox/inbox.

Cubre:
- event_id único en outbox_event
- retry_count y last_error en mark_as_failed
- processed_at en mark_as_published y mark_as_terminal
- InboxRepository: claim idempotente, is_processed, mark_as_processed, mark_as_rejected
- Diferenciación errores técnicos (retry) vs negocio (REJECTED)
"""
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository


# ── helpers ───────────────────────────────────────────────────────────────────

def _add_event(repo: OutboxRepository, *, suffix: str = "") -> dict:
    return repo.add_event(
        event_type=f"test_event{suffix}",
        aggregate_type="test_aggregate",
        aggregate_id=1,
        payload={"key": "value"},
        occurred_at=datetime(2026, 4, 27, 10, 0, 0, tzinfo=UTC),
    )


# ── outbox: event_id ──────────────────────────────────────────────────────────

def test_add_event_genera_event_id(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)

    assert "event_id" in event
    assert isinstance(event["event_id"], str)
    assert len(event["event_id"]) == 36  # UUID format


def test_add_event_event_ids_son_unicos(db_session) -> None:
    repo = OutboxRepository(db_session)
    e1 = _add_event(repo, suffix="_a")
    e2 = _add_event(repo, suffix="_b")

    assert e1["event_id"] != e2["event_id"]


def test_add_event_retry_count_inicial_es_cero(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)

    assert event["retry_count"] == 0
    assert event["last_error"] is None
    assert event["processed_at"] is None


# ── outbox: mark_as_failed (error técnico → retry) ───────────────────────────

def test_mark_as_failed_incrementa_retry_count(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)

    updated = repo.mark_as_failed(event["id"], error="timeout connecting to broker")

    assert updated is not None
    assert updated["retry_count"] == 1
    assert updated["status"] == "PENDING"


def test_mark_as_failed_setea_last_error(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)

    error_msg = "Connection refused: broker:9092"
    updated = repo.mark_as_failed(event["id"], error=error_msg)

    assert updated["last_error"] == error_msg


def test_mark_as_failed_acumula_reintentos(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)

    repo.mark_as_failed(event["id"], error="error 1")
    repo.mark_as_failed(event["id"], error="error 2")
    updated = repo.mark_as_failed(event["id"], error="error 3")

    assert updated["retry_count"] == 3
    assert updated["last_error"] == "error 3"
    assert updated["status"] == "PENDING"


def test_mark_as_failed_no_afecta_evento_publicado(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)
    repo.mark_as_published(event["id"])
    db_session.commit()

    result = repo.mark_as_failed(event["id"], error="too late")

    assert result is None  # WHERE status = 'PENDING' no matchea


# ── outbox: mark_as_published (éxito → processed_at) ─────────────────────────

def test_mark_as_published_setea_processed_at(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)

    published = repo.mark_as_published(event["id"])

    assert published is not None
    assert published["processed_at"] is not None
    assert published["status"] == "PUBLISHED"


def test_mark_as_published_processed_at_igual_a_published_at(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)
    ts = datetime(2026, 4, 27, 12, 0, 0, tzinfo=UTC)

    published = repo.mark_as_published(event["id"], published_at=ts)

    # Ambos timestamps deben ser iguales entre sí (la DB almacena sin tz)
    assert published["published_at"] is not None
    assert published["processed_at"] is not None
    assert published["published_at"] == published["processed_at"]


# ── outbox: mark_as_terminal (error negocio → REJECTED + processed_at) ───────

def test_mark_as_terminal_setea_processed_at(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)

    rejected = repo.mark_as_terminal(event["id"], terminal_status="REJECTED")

    assert rejected is not None
    assert rejected["status"] == "REJECTED"
    assert rejected["processed_at"] is not None


def test_mark_as_terminal_con_razon_negocio(db_session) -> None:
    repo = OutboxRepository(db_session)
    event = _add_event(repo)

    rejected = repo.mark_as_terminal(
        event["id"],
        terminal_status="REJECTED",
        processing_reason={"code": "MAX_RETRIES_EXCEEDED", "category": "PUBLISHER_RESULT"},
    )

    assert rejected["processing_reason"]["code"] == "MAX_RETRIES_EXCEEDED"


# ── outbox: get_pending_events incluye nuevos campos ─────────────────────────

def test_get_pending_events_incluye_event_id_y_retry_count(db_session) -> None:
    repo = OutboxRepository(db_session)
    _add_event(repo)

    events = repo.get_pending_events(limit=10)

    assert len(events) >= 1
    for e in events:
        assert "event_id" in e
        assert "retry_count" in e
        assert "last_error" in e
        assert "processed_at" in e


# ── inbox: claim idempotente ──────────────────────────────────────────────────

def test_inbox_claim_primera_vez_retorna_true(db_session) -> None:
    outbox = OutboxRepository(db_session)
    event = _add_event(outbox)
    inbox = InboxRepository(db_session)

    claimed = inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer="servicio_inmobiliario",
    )

    assert claimed is True


def test_inbox_claim_segunda_vez_retorna_false(db_session) -> None:
    outbox = OutboxRepository(db_session)
    event = _add_event(outbox)
    inbox = InboxRepository(db_session)

    inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer="servicio_inmobiliario",
    )

    second = inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer="servicio_inmobiliario",
    )

    assert second is False


def test_inbox_consumers_distintos_pueden_clamar_mismo_evento(db_session) -> None:
    outbox = OutboxRepository(db_session)
    event = _add_event(outbox)
    inbox = InboxRepository(db_session)

    c1 = inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer="consumer_a",
    )
    c2 = inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer="consumer_b",
    )

    assert c1 is True
    assert c2 is True


# ── inbox: is_processed ───────────────────────────────────────────────────────

def test_inbox_is_processed_false_al_reclamar(db_session) -> None:
    outbox = OutboxRepository(db_session)
    event = _add_event(outbox)
    inbox = InboxRepository(db_session)
    inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer="svc",
    )

    assert inbox.is_processed(event_id=event["event_id"], consumer="svc") is False


def test_inbox_is_processed_true_tras_mark_as_processed(db_session) -> None:
    outbox = OutboxRepository(db_session)
    event = _add_event(outbox)
    inbox = InboxRepository(db_session)
    inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer="svc",
    )

    inbox.mark_as_processed(event_id=event["event_id"], consumer="svc")

    assert inbox.is_processed(event_id=event["event_id"], consumer="svc") is True


# ── inbox: mark_as_processed ──────────────────────────────────────────────────

def test_inbox_mark_as_processed_setea_processed_at(db_session) -> None:
    outbox = OutboxRepository(db_session)
    event = _add_event(outbox)
    inbox = InboxRepository(db_session)
    inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer="svc",
    )

    inbox.mark_as_processed(event_id=event["event_id"], consumer="svc")
    row = inbox.get(event_id=event["event_id"], consumer="svc")

    assert row["status"] == "PROCESSED"
    assert row["processed_at"] is not None


# ── inbox: mark_as_rejected (error de negocio) ────────────────────────────────

def test_inbox_mark_as_rejected_setea_status_y_error(db_session) -> None:
    outbox = OutboxRepository(db_session)
    event = _add_event(outbox)
    inbox = InboxRepository(db_session)
    inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer="svc",
    )

    inbox.mark_as_rejected(
        event_id=event["event_id"],
        consumer="svc",
        error_detail="Inmueble no encontrado en dominio destino",
    )
    row = inbox.get(event_id=event["event_id"], consumer="svc")

    assert row["status"] == "REJECTED"
    assert row["error_detail"] == "Inmueble no encontrado en dominio destino"
    assert row["processed_at"] is not None


# ── integración: flujo completo outbox → inbox ────────────────────────────────

def test_flujo_completo_outbox_emit_inbox_consume(db_session) -> None:
    """Simula el ciclo completo: emisor publica → consumer procesa idempotente."""
    outbox = OutboxRepository(db_session)
    inbox = InboxRepository(db_session)
    consumer = "servicio_disponibilidad"

    # 1. Dominio emite evento
    event = outbox.add_event(
        event_type="reserva_locativa_confirmada",
        aggregate_type="reserva_locativa",
        aggregate_id=42,
        payload={"id_reserva_locativa": 42, "estado_reserva": "confirmada", "objetos": []},
        occurred_at=datetime.now(UTC),
    )

    # 2. Publisher marca como publicado
    outbox.mark_as_published(event["id"])

    # 3. Consumer intenta procesar (primera vez → claimed)
    claimed = inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer=consumer,
    )
    assert claimed is True

    # 4. Consumer procesa y confirma
    inbox.mark_as_processed(event_id=event["event_id"], consumer=consumer)
    assert inbox.is_processed(event_id=event["event_id"], consumer=consumer) is True

    # 5. Reentrada idempotente: claim falla silenciosamente
    claimed_again = inbox.claim(
        event_id=event["event_id"],
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        aggregate_id=event["aggregate_id"],
        consumer=consumer,
    )
    assert claimed_again is False
