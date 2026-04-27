"""
Tests de integración para ConsumeEntregaLocativaService.

Setup: contrato activo + RESERVADA disponibilidad + outbox event manualmente insertado.
"""
import json

from sqlalchemy import text

from app.application.inmuebles.services.consume_entrega_locativa_service import (
    ConsumeEntregaLocativaService,
    PROCESSOR_NAME,
)
from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository
from app.infrastructure.persistence.repositories.inmueble_repository import InmuebleRepository
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository
from tests.test_contratos_alquiler_activate import _crear_contrato_borrador
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_disponibilidad


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_service(db_session) -> ConsumeEntregaLocativaService:
    return ConsumeEntregaLocativaService(
        db=db_session,
        inmueble_repository=InmuebleRepository(db_session),
        outbox_repository=OutboxRepository(db_session),
        inbox_repository=InboxRepository(db_session),
    )


def _activar_contrato(client, contrato: dict) -> dict:
    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/activar",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _insertar_outbox_entrega(
    db_session,
    *,
    id_contrato_alquiler: int,
    fecha_entrega: str,
    objetos: list[dict],
) -> dict:
    row = db_session.execute(
        text(
            """
            INSERT INTO outbox_event (
                event_type, aggregate_type, aggregate_id, payload,
                occurred_at, status
            )
            VALUES (
                'entrega_locativa_registrada',
                'contrato_alquiler',
                :id_contrato_alquiler,
                CAST(:payload AS jsonb),
                now(),
                'PENDING'
            )
            RETURNING id, event_id
            """
        ),
        {
            "id_contrato_alquiler": id_contrato_alquiler,
            "payload": json.dumps(
                {
                    "id_contrato_alquiler": id_contrato_alquiler,
                    "fecha_entrega": fecha_entrega,
                    "objetos": objetos,
                }
            ),
        },
    ).mappings().one()
    db_session.commit()
    return {"id": row["id"], "event_id": str(row["event_id"])}


def _setup(client, db_session, *, codigo: str) -> dict:
    """Crea contrato activo + RESERVADA disponibilidad + outbox event."""
    borrador = _crear_contrato_borrador(client, codigo=codigo)
    activo = _activar_contrato(client, borrador)
    id_contrato = activo["id_contrato_alquiler"]
    id_inmueble = activo["objetos"][0]["id_inmueble"]

    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
        fecha_desde="2026-08-01T00:00:00",
    )

    event = _insertar_outbox_entrega(
        db_session,
        id_contrato_alquiler=id_contrato,
        fecha_entrega="2026-08-01",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    return {
        "id_contrato_alquiler": id_contrato,
        "id_inmueble": id_inmueble,
        "event": event,
    }


# ── tests exitosos ────────────────────────────────────────────────────────────

def test_consume_entrega_locativa_procesa_correctamente(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CENT-OK-001")

    result = _build_service(db_session).execute(limit=100)

    assert result.success is True
    assert result.data["processed_events"] == 1
    event_result = result.data["events"][0]
    assert event_result["id_contrato_alquiler"] == data["id_contrato_alquiler"]
    assert event_result["objects"][0]["status"] == "OK"


def test_consume_entrega_crea_entrega_restitucion_inmueble(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CENT-ENT-001")

    _build_service(db_session).execute(limit=100)

    row = db_session.execute(
        text(
            """
            SELECT id_entrega_restitucion, id_contrato_alquiler, fecha_entrega
            FROM entrega_restitucion_inmueble
            WHERE id_contrato_alquiler = :id AND deleted_at IS NULL
            """
        ),
        {"id": data["id_contrato_alquiler"]},
    ).mappings().one_or_none()

    assert row is not None
    assert row["id_contrato_alquiler"] == data["id_contrato_alquiler"]


def test_consume_entrega_crea_ocupacion_alquiler(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CENT-OCP-001")

    _build_service(db_session).execute(limit=100)

    row = db_session.execute(
        text(
            """
            SELECT tipo_ocupacion, fecha_hasta
            FROM ocupacion
            WHERE id_inmueble = :id AND deleted_at IS NULL
            """
        ),
        {"id": data["id_inmueble"]},
    ).mappings().one_or_none()

    assert row is not None
    assert row["tipo_ocupacion"] == "ALQUILER"
    assert row["fecha_hasta"] is None  # ocupación abierta


def test_consume_entrega_marca_disponibilidad_no_disponible(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CENT-DISP-001")

    _build_service(db_session).execute(limit=100)

    abierta = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad
            FROM disponibilidad
            WHERE id_inmueble = :id
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id": data["id_inmueble"]},
    ).mappings().one()

    assert abierta["estado_disponibilidad"] == "NO_DISPONIBLE"


def test_consume_entrega_marca_outbox_published(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CENT-OBX-001")

    _build_service(db_session).execute(limit=100)

    outbox = db_session.execute(
        text(
            "SELECT status, processing_reason, processing_metadata FROM outbox_event WHERE id = :id"
        ),
        {"id": data["event"]["id"]},
    ).mappings().one()

    assert outbox["status"] == "PUBLISHED"
    assert outbox["processing_reason"]["code"] == "CONSUMED_APPLIED"
    assert outbox["processing_reason"]["category"] == "CONSUMER_RESULT"
    assert outbox["processing_metadata"]["processor"] == PROCESSOR_NAME
    assert outbox["processing_metadata"]["object_count"] == 1


def test_consume_entrega_marca_inbox_processed(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CENT-INB-001")

    _build_service(db_session).execute(limit=100)

    inbox = db_session.execute(
        text(
            """
            SELECT status, processed_at
            FROM inbox_event
            WHERE event_id = CAST(:eid AS uuid) AND consumer = :consumer
            """
        ),
        {"eid": data["event"]["event_id"], "consumer": PROCESSOR_NAME},
    ).mappings().one_or_none()

    assert inbox is not None
    assert inbox["status"] == "PROCESSED"
    assert inbox["processed_at"] is not None


# ── idempotencia ──────────────────────────────────────────────────────────────

def test_consume_entrega_doble_procesamiento_no_duplica(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CENT-IDEMP-001")
    service = _build_service(db_session)

    first = service.execute(limit=100)
    assert first.success is True

    # Resetear outbox a PENDING para simular reentrada del publisher
    db_session.execute(
        text(
            """
            UPDATE outbox_event
            SET status = 'PENDING', published_at = NULL
            WHERE id = :id
            """
        ),
        {"id": data["event"]["id"]},
    )
    db_session.commit()

    second = service.execute(limit=100)

    assert second.success is True

    # No duplicación
    entrega_count = db_session.execute(
        text(
            "SELECT COUNT(*) AS total FROM entrega_restitucion_inmueble WHERE id_contrato_alquiler = :id AND deleted_at IS NULL"
        ),
        {"id": data["id_contrato_alquiler"]},
    ).mappings().one()["total"]
    assert entrega_count == 1

    ocupacion_count = db_session.execute(
        text(
            "SELECT COUNT(*) AS total FROM ocupacion WHERE id_inmueble = :id AND deleted_at IS NULL"
        ),
        {"id": data["id_inmueble"]},
    ).mappings().one()["total"]
    assert ocupacion_count == 1

    no_disp_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total FROM disponibilidad
            WHERE id_inmueble = :id AND estado_disponibilidad = 'NO_DISPONIBLE' AND deleted_at IS NULL
            """
        ),
        {"id": data["id_inmueble"]},
    ).mappings().one()["total"]
    assert no_disp_count == 1


# ── tests de error ────────────────────────────────────────────────────────────

def test_consume_entrega_falla_si_disponibilidad_no_es_reservada(
    client, db_session
) -> None:
    data = _setup(client, db_session, codigo="CA-CENT-NOREV-001")

    # Forzar estado distinto de RESERVADA
    db_session.execute(
        text(
            """
            UPDATE disponibilidad
            SET estado_disponibilidad = 'DISPONIBLE'
            WHERE id_inmueble = :id
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id": data["id_inmueble"]},
    )
    db_session.commit()

    result = _build_service(db_session).execute(limit=100)

    assert result.success is False
    assert result.errors == ["CURRENT_NOT_RESERVADA"]

    outbox = db_session.execute(
        text("SELECT status FROM outbox_event WHERE id = :id"),
        {"id": data["event"]["id"]},
    ).mappings().one()
    assert outbox["status"] == "REJECTED"

    # Sin efectos secundarios
    assert (
        db_session.execute(
            text("SELECT COUNT(*) AS t FROM ocupacion WHERE id_inmueble = :id AND deleted_at IS NULL"),
            {"id": data["id_inmueble"]},
        ).mappings().one()["t"]
        == 0
    )
    assert (
        db_session.execute(
            text("SELECT COUNT(*) AS t FROM entrega_restitucion_inmueble WHERE id_contrato_alquiler = :id AND deleted_at IS NULL"),
            {"id": data["id_contrato_alquiler"]},
        ).mappings().one()["t"]
        == 0
    )


def test_consume_entrega_rechaza_payload_invalido(db_session) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO outbox_event (
                event_type, aggregate_type, aggregate_id, payload, occurred_at, status
            )
            VALUES (
                'entrega_locativa_registrada', 'contrato_alquiler', 9999,
                '{"id_contrato_alquiler": 9999, "fecha_entrega": "2026-08-01", "objetos": []}'::jsonb,
                now(), 'PENDING'
            )
            """
        )
    )
    db_session.commit()

    result = _build_service(db_session).execute(limit=100)

    assert result.success is False
    assert result.errors == ["INVALID_EVENT_OBJECTS"]

    outbox = db_session.execute(
        text(
            """
            SELECT status FROM outbox_event
            WHERE aggregate_type = 'contrato_alquiler'
              AND aggregate_id = 9999
              AND event_type = 'entrega_locativa_registrada'
            """
        )
    ).mappings().one()
    assert outbox["status"] == "REJECTED"
