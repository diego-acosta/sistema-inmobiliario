"""
Tests de integración para ConsumeRestitucionLocativaService.

Setup: contrato activo + ocupación ALQUILER abierta + disponibilidad NO_DISPONIBLE
(estado resultante tras procesar entrega_locativa_registrada) + outbox event
de restitucion_locativa_registrada insertado manualmente.
"""
import json

from sqlalchemy import text

from app.application.inmuebles.services.consume_restitucion_locativa_service import (
    ConsumeRestitucionLocativaService,
    PROCESSOR_NAME,
)
from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository
from app.infrastructure.persistence.repositories.inmueble_repository import InmuebleRepository
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository
from tests.test_contratos_alquiler_activate import _crear_contrato_borrador
from tests.test_disponibilidades_create import HEADERS
from tests.test_inmobiliario_entrega_locativa_consumer import (
    _build_service as _build_entrega_service,
    _insertar_outbox_entrega,
    _setup as _setup_entrega,
)
from tests.test_reservas_venta_create import _crear_disponibilidad


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_service(db_session) -> ConsumeRestitucionLocativaService:
    return ConsumeRestitucionLocativaService(
        db=db_session,
        inmueble_repository=InmuebleRepository(db_session),
        outbox_repository=OutboxRepository(db_session),
        inbox_repository=InboxRepository(db_session),
    )


def _activar_contrato(client, contrato: dict) -> dict:
    client.post(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/condiciones-economicas-alquiler",
        headers=HEADERS,
        json={"monto_base": "150000.00", "fecha_desde": "2026-05-01"},
    )
    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/activar",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _insertar_outbox_restitucion(
    db_session,
    *,
    id_contrato_alquiler: int,
    fecha_restitucion: str,
    objetos: list[dict],
    uid_restitucion_locativa: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
) -> dict:
    row = db_session.execute(
        text(
            """
            INSERT INTO outbox_event (
                event_type, aggregate_type, aggregate_id, payload,
                occurred_at, status
            )
            VALUES (
                'restitucion_locativa_registrada',
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
                    "uid_restitucion_locativa": uid_restitucion_locativa,
                    "id_contrato_alquiler": id_contrato_alquiler,
                    "fecha_restitucion": fecha_restitucion,
                    "objetos": objetos,
                }
            ),
        },
    ).mappings().one()
    db_session.commit()
    return {"id": row["id"], "event_id": str(row["event_id"])}


def _setup(client, db_session, *, codigo: str) -> dict:
    """
    Construye el estado previo a una restitución:
    contrato activo + ocupación ALQUILER abierta + disponibilidad NO_DISPONIBLE.

    Reutiliza el consumer de entrega para establecer el estado correcto.
    """
    entrega_data = _setup_entrega(client, db_session, codigo=codigo)
    _build_entrega_service(db_session).execute(limit=100)

    id_contrato = entrega_data["id_contrato_alquiler"]
    id_inmueble = entrega_data["id_inmueble"]

    event = _insertar_outbox_restitucion(
        db_session,
        id_contrato_alquiler=id_contrato,
        fecha_restitucion="2026-09-01",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    return {
        "id_contrato_alquiler": id_contrato,
        "id_inmueble": id_inmueble,
        "event": event,
    }


# ── tests exitosos ────────────────────────────────────────────────────────────

def test_consume_restitucion_procesa_correctamente(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CREST-OK-001")

    result = _build_service(db_session).execute(limit=100)

    assert result.success is True
    assert result.data["processed_events"] == 1
    event_result = result.data["events"][0]
    assert event_result["id_contrato_alquiler"] == data["id_contrato_alquiler"]
    assert event_result["objects"][0]["status"] == "OK"


def test_consume_restitucion_cierra_ocupacion_alquiler(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CREST-OCP-001")

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
    assert row["fecha_hasta"] is not None  # ocupación cerrada


def test_consume_restitucion_marca_disponibilidad_disponible(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CREST-DISP-001")

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

    assert abierta["estado_disponibilidad"] == "DISPONIBLE"


def test_consume_restitucion_crea_entrega_restitucion_inmueble(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CREST-ERI-001")

    _build_service(db_session).execute(limit=100)

    row = db_session.execute(
        text(
            """
            SELECT id_entrega_restitucion, id_contrato_alquiler, fecha_entrega
            FROM entrega_restitucion_inmueble
            WHERE id_contrato_alquiler = :id AND deleted_at IS NULL
            ORDER BY id_entrega_restitucion DESC
            LIMIT 1
            """
        ),
        {"id": data["id_contrato_alquiler"]},
    ).mappings().one_or_none()

    assert row is not None
    assert row["id_contrato_alquiler"] == data["id_contrato_alquiler"]
    assert str(row["fecha_entrega"]) == "2026-09-01"


def test_consume_restitucion_marca_outbox_published(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CREST-OBX-001")

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


def test_consume_restitucion_marca_inbox_processed(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CREST-INB-001")

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

def test_consume_restitucion_doble_procesamiento_no_duplica(client, db_session) -> None:
    data = _setup(client, db_session, codigo="CA-CREST-IDEMP-001")
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

    # Ocupación cerrada exactamente una vez
    ocupacion_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total FROM ocupacion
            WHERE id_inmueble = :id
              AND tipo_ocupacion = 'ALQUILER'
              AND fecha_hasta IS NOT NULL
              AND deleted_at IS NULL
            """
        ),
        {"id": data["id_inmueble"]},
    ).mappings().one()["total"]
    assert ocupacion_count == 1

    # Disponibilidad DISPONIBLE exactamente una vez (la abierta)
    disp_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total FROM disponibilidad
            WHERE id_inmueble = :id
              AND estado_disponibilidad = 'DISPONIBLE'
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id": data["id_inmueble"]},
    ).mappings().one()["total"]
    assert disp_count == 1

    # Fila de restitución creada exactamente una vez.
    # El setup ya materializa la entrega locativa inicial en la misma tabla.
    eri_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM entrega_restitucion_inmueble
            WHERE id_contrato_alquiler = :id
              AND fecha_entrega = DATE '2026-09-01'
              AND deleted_at IS NULL
            """
        ),
        {"id": data["id_contrato_alquiler"]},
    ).mappings().one()["total"]
    assert eri_count == 1


# ── tests de error ────────────────────────────────────────────────────────────

def test_consume_restitucion_sin_ocupacion_activa_rechaza(client, db_session) -> None:
    """Sin ocupación ALQUILER abierta → REJECTED con NO_OPEN_OCUPACION_ALQUILER."""
    borrador = _crear_contrato_borrador(client, codigo="CA-CREST-NOOCP-001")
    activo = _activar_contrato(client, borrador)
    id_contrato = activo["id_contrato_alquiler"]
    id_inmueble = activo["objetos"][0]["id_inmueble"]

    # Estado post-entrega simulado: NO_DISPONIBLE, pero sin ocupación
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="NO_DISPONIBLE",
        fecha_desde="2026-08-01T00:00:00",
    )

    event = _insertar_outbox_restitucion(
        db_session,
        id_contrato_alquiler=id_contrato,
        fecha_restitucion="2026-09-01",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    result = _build_service(db_session).execute(limit=100)

    assert result.success is False
    assert result.errors == ["NO_OPEN_OCUPACION_ALQUILER"]

    outbox = db_session.execute(
        text("SELECT status FROM outbox_event WHERE id = :id"),
        {"id": event["id"]},
    ).mappings().one()
    assert outbox["status"] == "REJECTED"

    # Sin efectos secundarios
    assert (
        db_session.execute(
            text(
                "SELECT COUNT(*) AS t FROM entrega_restitucion_inmueble WHERE id_contrato_alquiler = :id AND deleted_at IS NULL"
            ),
            {"id": id_contrato},
        ).mappings().one()["t"]
        == 0
    )


def test_consume_restitucion_disponibilidad_invalida_rechaza(client, db_session) -> None:
    """Disponibilidad en estado inesperado → REJECTED con CURRENT_NOT_RESERVADA."""
    data = _setup(client, db_session, codigo="CA-CREST-NODISP-001")

    # Forzar disponibilidad a un estado que no es NO_DISPONIBLE sin solapar
    # otro tramo histórico del mismo estado.
    db_session.execute(
        text(
            """
            UPDATE disponibilidad
            SET estado_disponibilidad = 'BLOQUEADA'
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

    # Sin entrega_restitucion_inmueble creada para la restitución
    eri_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS t FROM entrega_restitucion_inmueble
            WHERE id_contrato_alquiler = :id
              AND deleted_at IS NULL
            """
        ),
        {"id": data["id_contrato_alquiler"]},
    ).mappings().one()["t"]
    # La entrega consumer ya creó una fila; la restitución no debe haber creado otra
    assert eri_count == 1


def test_consume_restitucion_rechaza_payload_invalido(db_session) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO outbox_event (
                event_type, aggregate_type, aggregate_id, payload, occurred_at, status
            )
            VALUES (
                'restitucion_locativa_registrada', 'contrato_alquiler', 9999,
                '{"id_contrato_alquiler": 9999, "fecha_restitucion": "2026-09-01", "objetos": []}'::jsonb,
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
              AND event_type = 'restitucion_locativa_registrada'
            """
        )
    ).mappings().one()
    assert outbox["status"] == "REJECTED"
