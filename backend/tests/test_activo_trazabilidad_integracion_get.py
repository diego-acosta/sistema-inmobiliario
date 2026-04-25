from sqlalchemy import text

from app.application.inmuebles.services.consume_escrituracion_registrada_service import (
    ConsumeEscrituracionRegistradaService,
)
from app.application.inmuebles.services.consume_venta_confirmada_service import (
    ConsumeVentaConfirmadaService,
)
from app.infrastructure.persistence.repositories.inmueble_repository import (
    InmuebleRepository,
)
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)
from tests.test_disponibilidades_create import HEADERS
from tests.test_escrituraciones_create import (
    _confirmar_venta_publica,
    _payload_escrituracion,
)
from tests.test_reservas_venta_create import _crear_disponibilidad, _crear_inmueble
from tests.test_ventas_definir_condiciones_comerciales import (
    _insertar_venta_para_condiciones,
)


def _consume_venta_confirmada(db_session):
    return ConsumeVentaConfirmadaService(
        db=db_session,
        inmueble_repository=InmuebleRepository(db_session),
        outbox_repository=OutboxRepository(db_session),
    ).execute(limit=100)


def _consume_escrituracion_registrada(db_session):
    return ConsumeEscrituracionRegistradaService(
        db=db_session,
        inmueble_repository=InmuebleRepository(db_session),
        outbox_repository=OutboxRepository(db_session),
    ).execute(limit=100)


def _crear_unidad_funcional(client, id_inmueble: int, *, codigo: str) -> int:
    response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": codigo,
            "nombre_unidad": f"Unidad {codigo}",
            "superficie": "72.50",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": "unidad para trazabilidad",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_unidad_funcional"]


def _insertar_outbox_evento_venta(
    db_session,
    *,
    id_venta: int,
    event_type: str,
    payload: str,
    status: str = "PENDING",
    published_at_sql: str = "NULL",
) -> None:
    db_session.execute(
        text(
            f"""
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
                :event_type,
                'venta',
                :id_venta,
                CAST(:payload AS jsonb),
                TIMESTAMP '2026-04-24 11:00:00',
                {published_at_sql},
                :status
            )
            """
        ),
        {
            "event_type": event_type,
            "id_venta": id_venta,
            "payload": payload,
            "status": status,
        },
    )


def test_get_inmueble_trazabilidad_integracion_devuelve_lista_vacia_si_no_hay_venta(
    client,
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-TRACE-EMPTY-001")

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}/trazabilidad-integracion")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}


def test_get_inmueble_trazabilidad_integracion_devuelve_lista_vacia_si_inmueble_no_existe(
    client,
) -> None:
    response = client.get("/api/v1/inmuebles/999999/trazabilidad-integracion")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}


def test_get_inmueble_trazabilidad_integracion_devuelve_eventos_pendientes_y_efecto_operativo(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(numero_escritura="ESC-TRACE-INM-001"),
    )
    assert response.status_code == 201

    trace_response = client.get(
        f"/api/v1/inmuebles/{venta['id_inmueble']}/trazabilidad-integracion"
    )

    assert trace_response.status_code == 200
    body = trace_response.json()
    assert len(body["data"]) == 1

    venta_trace = body["data"][0]
    assert venta_trace["id_venta"] == venta["id_venta"]
    assert venta_trace["estado_venta"] == "confirmada"
    assert [evento["estado"] for evento in venta_trace["eventos"]] == [
        "PENDING",
        "PENDING",
    ]
    assert venta_trace["eventos"][0]["nombre_evento"] == "venta_confirmada"
    assert venta_trace["eventos"][0]["efecto_operativo_aplicado"] == {
        "disponibilidad": "SIN_CAMBIO",
        "ocupacion": "SIN_CAMBIO",
    }
    assert venta_trace["eventos"][1]["nombre_evento"] == "escrituracion_registrada"
    assert venta_trace["eventos"][1]["efecto_operativo_aplicado"] == {
        "disponibilidad": "PENDIENTE",
        "ocupacion": "SIN_CAMBIO",
    }


def test_get_inmueble_trazabilidad_integracion_devuelve_published_cuando_el_consumo_aplica(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )
    assert response.status_code == 201

    venta_result = _consume_venta_confirmada(db_session)
    assert venta_result.success is True

    escrituracion_result = _consume_escrituracion_registrada(db_session)
    assert escrituracion_result.success is True

    trace_response = client.get(
        f"/api/v1/inmuebles/{venta['id_inmueble']}/trazabilidad-integracion"
    )

    assert trace_response.status_code == 200
    venta_trace = trace_response.json()["data"][0]
    assert [evento["estado"] for evento in venta_trace["eventos"]] == [
        "PUBLISHED",
        "PUBLISHED",
    ]
    assert venta_trace["eventos"][1]["efecto_operativo_aplicado"] == {
        "disponibilidad": "NO_DISPONIBLE",
        "ocupacion": "SIN_CAMBIO",
    }


def test_get_inmueble_trazabilidad_integracion_devuelve_rejected_si_el_efecto_operativo_no_aplica(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(numero_escritura="ESC-TRACE-INM-REJ-001"),
    )
    assert response.status_code == 201

    venta_result = _consume_venta_confirmada(db_session)
    assert venta_result.success is True

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

    escrituracion_result = _consume_escrituracion_registrada(db_session)
    assert escrituracion_result.success is False
    assert escrituracion_result.errors == ["CURRENT_NOT_RESERVADA"]

    trace_response = client.get(
        f"/api/v1/inmuebles/{venta['id_inmueble']}/trazabilidad-integracion"
    )

    assert trace_response.status_code == 200
    venta_trace = trace_response.json()["data"][0]
    assert [evento["estado"] for evento in venta_trace["eventos"]] == [
        "PUBLISHED",
        "REJECTED",
    ]
    assert venta_trace["eventos"][1]["efecto_operativo_aplicado"] == {
        "disponibilidad": "NO_APLICADO",
        "ocupacion": "SIN_CAMBIO",
    }


def test_get_unidad_funcional_trazabilidad_integracion_devuelve_venta_asociada_y_eventos(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-TRACE-UF-001")
    id_unidad_funcional = _crear_unidad_funcional(
        client, id_inmueble, codigo="UF-TRACE-001"
    )
    _crear_disponibilidad(
        client,
        id_unidad_funcional=id_unidad_funcional,
        estado_disponibilidad="RESERVADA",
        fecha_desde="2026-04-20T09:00:00",
    )

    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-TRACE-UF-001",
        estado_venta="confirmada",
        monto_total=90000,
        objetos=[
            {
                "id_inmueble": None,
                "id_unidad_funcional": id_unidad_funcional,
                "precio_asignado": 90000,
                "observaciones": "UF asociada",
            }
        ],
    )

    _insertar_outbox_evento_venta(
        db_session,
        id_venta=venta["id_venta"],
        event_type="venta_confirmada",
        payload=(
            '{"id_venta": %d, "id_reserva_venta": null, "estado_venta": "confirmada", '
            '"objetos": [{"id_inmueble": null, "id_unidad_funcional": %d}]}'
            % (venta["id_venta"], id_unidad_funcional)
        ),
    )
    _insertar_outbox_evento_venta(
        db_session,
        id_venta=venta["id_venta"],
        event_type="escrituracion_registrada",
        payload=(
            '{"id_venta": %d, "id_escrituracion": 1, "fecha_escrituracion": "2026-04-24T11:00:00", '
            '"numero_escritura": "ESC-UF-001", '
            '"objetos": [{"id_inmueble": null, "id_unidad_funcional": %d}]}'
            % (venta["id_venta"], id_unidad_funcional)
        ),
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/trazabilidad-integracion"
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 1
    venta_trace = body["data"][0]
    assert venta_trace["id_venta"] == venta["id_venta"]
    assert venta_trace["codigo_venta"] == "V-TRACE-UF-001"
    assert [evento["nombre_evento"] for evento in venta_trace["eventos"]] == [
        "venta_confirmada",
        "escrituracion_registrada",
    ]
    assert venta_trace["eventos"][0]["efecto_operativo_aplicado"] == {
        "disponibilidad": "SIN_CAMBIO",
        "ocupacion": "SIN_CAMBIO",
    }
    assert venta_trace["eventos"][1]["efecto_operativo_aplicado"] == {
        "disponibilidad": "PENDIENTE",
        "ocupacion": "SIN_CAMBIO",
    }


def test_get_unidad_funcional_trazabilidad_integracion_devuelve_lista_vacia_si_no_existe(
    client,
) -> None:
    response = client.get(
        "/api/v1/unidades-funcionales/999999/trazabilidad-integracion"
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": []}
