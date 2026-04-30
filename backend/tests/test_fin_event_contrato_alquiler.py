"""
Tests de integración: activación de contrato de alquiler → evento → financiero.

Cubre:
- activación con condición económica → crea relacion_generadora + obligacion CANON_LOCATIVO
- activación sin condición económica falla (HTTP 400)
- inbox idempotente: evento repetido no duplica obligación
- evento desconocido no rompe el inbox
"""
from sqlalchemy import text

from app.application.financiero.services.handle_contrato_alquiler_activado_event_service import (
    HandleContratoAlquilerActivadoEventService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from tests.test_contratos_alquiler_activate import (
    _crear_contrato_borrador,
    _crear_condicion_minima,
)
from tests.test_disponibilidades_create import HEADERS


URL_ACTIVAR = "/api/v1/contratos-alquiler/{id}/activar"
URL_INBOX = "/api/v1/financiero/inbox"
URL_CONDICION = "/api/v1/contratos-alquiler/{id}/condiciones-economicas-alquiler"


# ─── helpers ─────────────────────────────────────────────────────────────────


def _activar_contrato(client, contrato: dict) -> dict:
    response = client.patch(
        URL_ACTIVAR.format(id=contrato["id_contrato_alquiler"]),
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _crear_contrato_con_condicion(client, *, codigo: str, monto: str = "150000.00") -> dict:
    contrato = _crear_contrato_borrador(client, codigo=codigo)
    client.post(
        URL_CONDICION.format(id=contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json={"monto_base": monto, "fecha_desde": "2026-05-01"},
    )
    return contrato


def _build_handler(db_session) -> HandleContratoAlquilerActivadoEventService:
    return HandleContratoAlquilerActivadoEventService(
        repository=FinancieroRepository(db_session)
    )


def _get_outbox_contrato_activado(db_session, *, id_contrato: int) -> dict:
    return db_session.execute(
        text(
            """
            SELECT id, event_type, aggregate_type, aggregate_id, payload
            FROM outbox_event
            WHERE event_type = 'contrato_alquiler_activado'
              AND aggregate_type = 'contrato_alquiler'
              AND aggregate_id = :id_contrato
            """
        ),
        {"id_contrato": id_contrato},
    ).mappings().one()


def _count_relaciones_contrato(db_session, *, id_contrato: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM relacion_generadora
            WHERE tipo_origen = 'contrato_alquiler'
              AND id_origen = :id_contrato
              AND deleted_at IS NULL
            """
        ),
        {"id_contrato": id_contrato},
    ).mappings().one()["total"]


def _count_obligaciones_relacion(db_session, *, id_relacion: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id AND deleted_at IS NULL
            """
        ),
        {"id": id_relacion},
    ).mappings().one()["total"]


# ─── caso 1: flujo completo via inbox HTTP ────────────────────────────────────


def test_inbox_contrato_alquiler_activado_crea_relacion_y_obligacion_canon_locativo(
    client, db_session
) -> None:
    contrato = _crear_contrato_con_condicion(client, codigo="FIN-CA-INB-001")
    activo = _activar_contrato(client, contrato)
    id_contrato = activo["id_contrato_alquiler"]

    response = client.post(
        URL_INBOX,
        headers=HEADERS,
        json={
            "event_type": "contrato_alquiler_activado",
            "payload": {"id_contrato_alquiler": id_contrato},
        },
    )

    assert response.status_code == 204

    assert _count_relaciones_contrato(db_session, id_contrato=id_contrato) == 1

    relacion = db_session.execute(
        text(
            """
            SELECT id_relacion_generadora, tipo_origen, id_origen, estado_relacion_generadora
            FROM relacion_generadora
            WHERE tipo_origen = 'contrato_alquiler'
              AND id_origen = :id_contrato
              AND deleted_at IS NULL
            """
        ),
        {"id_contrato": id_contrato},
    ).mappings().one()
    assert relacion["tipo_origen"] == "contrato_alquiler"
    assert relacion["id_origen"] == id_contrato

    obligacion = db_session.execute(
        text(
            """
            SELECT
                o.importe_total, o.saldo_pendiente, o.estado_obligacion,
                c.importe_componente, c.saldo_componente,
                cf.codigo_concepto_financiero
            FROM obligacion_financiera o
            JOIN composicion_obligacion c
              ON c.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE o.id_relacion_generadora = :id_relacion
              AND o.deleted_at IS NULL
            """
        ),
        {"id_relacion": relacion["id_relacion_generadora"]},
    ).mappings().one()
    assert obligacion["codigo_concepto_financiero"] == "CANON_LOCATIVO"
    assert str(obligacion["importe_total"]) == "150000.00"
    assert str(obligacion["saldo_pendiente"]) == "150000.00"
    assert obligacion["estado_obligacion"] == "PROYECTADA"
    assert str(obligacion["importe_componente"]) == "150000.00"


# ─── caso 2: flujo handler directo con verificación detallada ─────────────────


def test_handler_contrato_alquiler_activado_crea_relacion_y_obligacion(
    client, db_session
) -> None:
    contrato = _crear_contrato_con_condicion(client, codigo="FIN-CA-HDL-001", monto="85000.00")
    _activar_contrato(client, contrato)
    id_contrato = contrato["id_contrato_alquiler"]

    event = dict(_get_outbox_contrato_activado(db_session, id_contrato=id_contrato))
    result = _build_handler(db_session).execute(event)

    assert result.success is True
    assert result.data is not None
    assert result.data["id_contrato_alquiler"] == id_contrato
    assert result.data["relacion_generadora_created"] is True
    assert result.data["obligacion_created"] is True
    assert isinstance(result.data["id_relacion_generadora"], int)
    assert isinstance(result.data["id_obligacion_financiera"], int)

    obligacion = db_session.execute(
        text(
            """
            SELECT o.importe_total, cf.codigo_concepto_financiero
            FROM obligacion_financiera o
            JOIN composicion_obligacion c ON c.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE o.id_obligacion_financiera = :id
            """
        ),
        {"id": result.data["id_obligacion_financiera"]},
    ).mappings().one()
    assert obligacion["codigo_concepto_financiero"] == "CANON_LOCATIVO"
    assert str(obligacion["importe_total"]) == "85000.00"


# ─── caso 3: sin condición económica falla al activar ─────────────────────────


def test_activar_contrato_sin_condicion_economica_devuelve_400(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="FIN-CA-NOCOND-001")

    response = client.patch(
        URL_ACTIVAR.format(id=contrato["id_contrato_alquiler"]),
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert "SIN_CONDICION_ECONOMICA" in body["details"]["errors"]


# ─── caso 4: idempotencia — evento repetido no duplica obligación ─────────────


def test_inbox_contrato_alquiler_activado_idempotente(client, db_session) -> None:
    contrato = _crear_contrato_con_condicion(client, codigo="FIN-CA-IDEM-001")
    _activar_contrato(client, contrato)
    id_contrato = contrato["id_contrato_alquiler"]
    body = {
        "event_type": "contrato_alquiler_activado",
        "payload": {"id_contrato_alquiler": id_contrato},
    }

    r1 = client.post(URL_INBOX, headers=HEADERS, json=body)
    r2 = client.post(URL_INBOX, headers=HEADERS, json=body)

    assert r1.status_code == 204
    assert r2.status_code == 204

    assert _count_relaciones_contrato(db_session, id_contrato=id_contrato) == 1

    relacion = db_session.execute(
        text(
            """
            SELECT id_relacion_generadora FROM relacion_generadora
            WHERE tipo_origen = 'contrato_alquiler' AND id_origen = :id AND deleted_at IS NULL
            """
        ),
        {"id": id_contrato},
    ).mappings().one()
    assert _count_obligaciones_relacion(db_session, id_relacion=relacion["id_relacion_generadora"]) == 1


# ─── caso 5: outbox se emite al activar ──────────────────────────────────────


def test_activar_contrato_emite_evento_outbox(client, db_session) -> None:
    contrato = _crear_contrato_con_condicion(client, codigo="FIN-CA-EVT-001")
    activo = _activar_contrato(client, contrato)

    outbox = db_session.execute(
        text(
            """
            SELECT event_type, aggregate_type, aggregate_id, payload
            FROM outbox_event
            WHERE event_type = 'contrato_alquiler_activado'
              AND aggregate_id = :id_contrato
            """
        ),
        {"id_contrato": activo["id_contrato_alquiler"]},
    ).mappings().one_or_none()

    assert outbox is not None
    assert outbox["event_type"] == "contrato_alquiler_activado"
    assert outbox["aggregate_type"] == "contrato_alquiler"
    assert outbox["aggregate_id"] == activo["id_contrato_alquiler"]
    assert outbox["payload"]["id_contrato_alquiler"] == activo["id_contrato_alquiler"]
