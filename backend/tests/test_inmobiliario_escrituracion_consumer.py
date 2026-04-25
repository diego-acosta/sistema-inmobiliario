from datetime import datetime

from sqlalchemy import text

from app.application.inmuebles.services.consume_escrituracion_registrada_service import (
    ConsumeEscrituracionRegistradaService,
)
from app.infrastructure.persistence.repositories.inmueble_repository import (
    InmuebleRepository,
)
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)
from tests.test_escrituraciones_create import (
    _confirmar_venta_publica,
    _payload_escrituracion,
)
from tests.test_reservas_venta_create import _crear_disponibilidad, _crear_inmueble
from tests.test_ventas_definir_condiciones_comerciales import (
    _insertar_venta_para_condiciones,
)


def _build_service(db_session) -> ConsumeEscrituracionRegistradaService:
    return ConsumeEscrituracionRegistradaService(
        db=db_session,
        inmueble_repository=InmuebleRepository(db_session),
        outbox_repository=OutboxRepository(db_session),
    )


def _crear_venta_multiobjeto_confirmada_para_consumidor(client, db_session) -> dict[str, int]:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-CONS-ESC-001")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-CONS-ESC-002")

    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble_1,
        estado_disponibilidad="RESERVADA",
        fecha_desde="2026-04-20T09:00:00",
    )
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble_2,
        estado_disponibilidad="RESERVADA",
        fecha_desde="2026-04-20T09:00:00",
    )

    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-CONS-ESC-001",
        estado_venta="confirmada",
        monto_total=300000,
        objetos=[
            {
                "id_inmueble": id_inmueble_1,
                "id_unidad_funcional": None,
                "precio_asignado": 200000,
                "observaciones": "Objeto A",
            },
            {
                "id_inmueble": id_inmueble_2,
                "id_unidad_funcional": None,
                "precio_asignado": 100000,
                "observaciones": "Objeto B",
            },
        ],
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        json=_payload_escrituracion(numero_escritura="ESC-CONS-001"),
        headers={
            "X-Instalacion-Id": "1",
            "X-Op-Id": "00000000-0000-0000-0000-000000000101",
        },
    )
    assert response.status_code == 201

    return {
        "id_venta": venta["id_venta"],
        "id_inmueble_1": id_inmueble_1,
        "id_inmueble_2": id_inmueble_2,
    }


def test_consume_escrituracion_registrada_reemplaza_reservada_y_no_crea_ocupacion(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    escrituracion_payload = _payload_escrituracion()
    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        json=escrituracion_payload,
        headers={
            "X-Instalacion-Id": "1",
            "X-Op-Id": "00000000-0000-0000-0000-000000000102",
        },
    )
    assert response.status_code == 201

    result = _build_service(db_session).execute(limit=100)

    assert result.success is True
    assert result.data is not None
    assert result.data["processed_events"] == 1
    assert result.data["events"][0]["id_venta"] == venta["id_venta"]
    assert result.data["events"][0]["objects"] == [
        {
            "id_inmueble": venta["id_inmueble"],
            "id_unidad_funcional": None,
            "status": "OK",
        }
    ]

    outbox_rows = db_session.execute(
        text(
            """
            SELECT event_type, status, published_at, processing_reason, processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :id_venta
            ORDER BY id
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().all()

    assert len(outbox_rows) == 2
    assert outbox_rows[0]["event_type"] == "venta_confirmada"
    assert outbox_rows[0]["status"] == "PENDING"
    assert outbox_rows[0]["published_at"] is None
    assert outbox_rows[0]["processing_reason"] is None
    assert outbox_rows[0]["processing_metadata"] is None
    assert outbox_rows[1]["event_type"] == "escrituracion_registrada"
    assert outbox_rows[1]["status"] == "PUBLISHED"
    assert outbox_rows[1]["published_at"] is not None
    assert outbox_rows[1]["processing_reason"] == {
        "code": "CONSUMED_APPLIED",
        "category": "CONSUMER_RESULT",
        "detail": "escrituracion_registrada_applied_operationally",
    }
    assert outbox_rows[1]["processing_metadata"]["processor"] == (
        "inmobiliario.consume_escrituracion_registrada"
    )
    assert outbox_rows[1]["processing_metadata"]["mode"] == "consumer"
    assert outbox_rows[1]["processing_metadata"]["object_count"] == 1
    assert outbox_rows[1]["processing_metadata"]["processed_at"] is not None

    disponibilidades = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad, fecha_desde, fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().all()

    assert len(disponibilidades) == 3
    assert disponibilidades[0]["estado_disponibilidad"] == "DISPONIBLE"
    assert disponibilidades[0]["fecha_hasta"] is not None
    fecha_esperada = datetime.fromisoformat(escrituracion_payload["fecha_escrituracion"])
    assert disponibilidades[1]["estado_disponibilidad"] == "RESERVADA"
    assert disponibilidades[1]["fecha_hasta"] == fecha_esperada
    assert disponibilidades[2]["estado_disponibilidad"] == "NO_DISPONIBLE"
    assert disponibilidades[2]["fecha_desde"] == fecha_esperada
    assert disponibilidades[2]["fecha_hasta"] is None

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


def test_consume_escrituracion_registrada_es_idempotente_si_ya_fue_aplicado(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        json=_payload_escrituracion(numero_escritura="ESC-IDEMP-001"),
        headers={
            "X-Instalacion-Id": "1",
            "X-Op-Id": "00000000-0000-0000-0000-000000000103",
        },
    )
    assert response.status_code == 201

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
              AND event_type = 'escrituracion_registrada'
            """
        ),
        {"id_venta": venta["id_venta"]},
    )
    db_session.commit()

    second_result = service.execute(limit=100)

    assert second_result.success is True
    assert second_result.data is not None
    assert second_result.data["processed_events"] == 1
    assert second_result.data["events"][0]["objects"] == [
        {
            "id_inmueble": venta["id_inmueble"],
            "id_unidad_funcional": None,
            "status": "ALREADY_APPLIED",
        }
    ]

    event_row = db_session.execute(
        text(
            """
            SELECT status, published_at, processing_reason, processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :id_venta
              AND event_type = 'escrituracion_registrada'
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert event_row["status"] == "PUBLISHED"
    assert event_row["published_at"] is not None
    assert event_row["processing_reason"] == {
        "code": "CONSUMED_ALREADY_APPLIED",
        "category": "CONSUMER_RESULT",
        "detail": "escrituracion_registrada_was_already_applied",
    }
    assert event_row["processing_metadata"]["processor"] == (
        "inmobiliario.consume_escrituracion_registrada"
    )
    assert event_row["processing_metadata"]["mode"] == "consumer"
    assert event_row["processing_metadata"]["object_count"] == 1
    assert event_row["processing_metadata"]["processed_at"] is not None

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
    assert abiertas == [{"estado_disponibilidad": "NO_DISPONIBLE"}]


def test_consume_escrituracion_registrada_falla_si_la_vigente_no_es_reservada(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        json=_payload_escrituracion(numero_escritura="ESC-FAIL-001"),
        headers={
            "X-Instalacion-Id": "1",
            "X-Op-Id": "00000000-0000-0000-0000-000000000104",
        },
    )
    assert response.status_code == 201

    db_session.execute(
        text(
            """
            UPDATE disponibilidad
            SET estado_disponibilidad = 'BLOQUEADA'
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    )
    db_session.commit()

    result = _build_service(db_session).execute(limit=100)

    assert result.success is False
    assert result.errors == ["CURRENT_NOT_RESERVADA"]

    event_row = db_session.execute(
        text(
            """
            SELECT status, published_at, processing_reason, processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :id_venta
              AND event_type = 'escrituracion_registrada'
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert event_row["status"] == "REJECTED"
    assert event_row["published_at"] is None
    assert event_row["processing_reason"] == {
        "code": "CURRENT_NOT_RESERVADA",
        "category": "CONSUMER_REJECTION",
        "detail": "escrituracion_registrada_rejected_due_to_permanent_inconsistency",
    }
    assert event_row["processing_metadata"]["processor"] == (
        "inmobiliario.consume_escrituracion_registrada"
    )
    assert event_row["processing_metadata"]["mode"] == "consumer"
    assert event_row["processing_metadata"]["object_count"] == 0
    assert event_row["processing_metadata"]["processed_at"] is not None

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
    assert abiertas == [{"estado_disponibilidad": "BLOQUEADA"}]

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


def test_consume_escrituracion_registrada_es_atomico_en_multiobjeto(
    client, db_session
) -> None:
    venta = _crear_venta_multiobjeto_confirmada_para_consumidor(client, db_session)

    db_session.execute(
        text(
            """
            UPDATE disponibilidad
            SET estado_disponibilidad = 'DISPONIBLE'
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble_2"]},
    )
    db_session.commit()

    result = _build_service(db_session).execute(limit=100)

    assert result.success is False
    assert result.errors == ["CURRENT_NOT_RESERVADA"]

    abiertas_1 = db_session.execute(
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
        {"id_inmueble": venta["id_inmueble_1"]},
    ).mappings().all()
    abiertas_2 = db_session.execute(
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
        {"id_inmueble": venta["id_inmueble_2"]},
    ).mappings().all()

    assert abiertas_1 == [{"estado_disponibilidad": "RESERVADA"}]
    assert abiertas_2 == [{"estado_disponibilidad": "DISPONIBLE"}]

    event_row = db_session.execute(
        text(
            """
            SELECT status, published_at, processing_reason, processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :id_venta
              AND event_type = 'escrituracion_registrada'
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert event_row["status"] == "REJECTED"
    assert event_row["published_at"] is None
    assert event_row["processing_reason"] == {
        "code": "CURRENT_NOT_RESERVADA",
        "category": "CONSUMER_REJECTION",
        "detail": "escrituracion_registrada_rejected_due_to_permanent_inconsistency",
    }
    assert event_row["processing_metadata"]["processor"] == (
        "inmobiliario.consume_escrituracion_registrada"
    )
    assert event_row["processing_metadata"]["mode"] == "consumer"
    assert event_row["processing_metadata"]["object_count"] == 0
    assert event_row["processing_metadata"]["processed_at"] is not None

    no_disponibles = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM disponibilidad
            WHERE estado_disponibilidad = 'NO_DISPONIBLE'
              AND deleted_at IS NULL
              AND (
                id_inmueble = :id_inmueble_1
                OR id_inmueble = :id_inmueble_2
              )
            """
        ),
        {
            "id_inmueble_1": venta["id_inmueble_1"],
            "id_inmueble_2": venta["id_inmueble_2"],
        },
    ).mappings().one()
    assert no_disponibles["total"] == 0


def test_consume_escrituracion_registrada_rechaza_payload_invalido_con_estado_terminal(
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
                'escrituracion_registrada',
                'venta',
                9001,
                '{"id_venta": 9001, "fecha_escrituracion": "2026-04-24T11:00:00", "objetos": []}'::jsonb,
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
    assert result.errors == ["INVALID_EVENT_OBJECTS"]

    event_row = db_session.execute(
        text(
            """
            SELECT status, published_at, processing_reason, processing_metadata
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = 9001
              AND event_type = 'escrituracion_registrada'
            """
        )
    ).mappings().one()
    assert event_row["status"] == "REJECTED"
    assert event_row["published_at"] is None
    assert event_row["processing_reason"] == {
        "code": "INVALID_EVENT_OBJECTS",
        "category": "CONSUMER_REJECTION",
        "detail": "escrituracion_registrada_rejected_due_to_permanent_inconsistency",
    }
    assert event_row["processing_metadata"]["processor"] == (
        "inmobiliario.consume_escrituracion_registrada"
    )
    assert event_row["processing_metadata"]["mode"] == "consumer"
    assert event_row["processing_metadata"]["object_count"] == 0
    assert event_row["processing_metadata"]["processed_at"] is not None
