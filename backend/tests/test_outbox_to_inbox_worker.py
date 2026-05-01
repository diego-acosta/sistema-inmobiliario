from sqlalchemy import text

from app.application.integration.outbox_to_inbox_worker import (
    run_outbox_worker_once,
)
from tests.test_contratos_alquiler_activate import (
    _crear_condicion_minima,
    _crear_contrato_borrador,
)
from tests.test_disponibilidades_create import HEADERS
from tests.test_escrituraciones_create import _confirmar_venta_publica


def _insert_outbox_event(
    db_session,
    *,
    event_type: str,
    aggregate_type: str = "test",
    aggregate_id: int = 1,
    payload_sql: str = "jsonb_build_object('ok', true)",
) -> int:
    event_id = db_session.execute(
        text(
            f"""
            INSERT INTO outbox_event (
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                occurred_at,
                status
            )
            VALUES (
                :event_type,
                :aggregate_type,
                :aggregate_id,
                {payload_sql},
                TIMESTAMP '2026-04-30 10:00:00',
                'PENDING'
            )
            RETURNING id
            """
        ),
        {
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
        },
    ).scalar_one()
    db_session.commit()
    return event_id


def _get_outbox_event(db_session, *, event_id: int) -> dict:
    return db_session.execute(
        text(
            """
            SELECT status, published_at, processed_at
            FROM outbox_event
            WHERE id = :id
            """
        ),
        {"id": event_id},
    ).mappings().one()


def _get_venta_confirmada_event_id(db_session, *, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT id
            FROM outbox_event
            WHERE event_type = 'venta_confirmada'
              AND aggregate_type = 'venta'
              AND aggregate_id = :id_venta
            """
        ),
        {"id_venta": id_venta},
    ).scalar_one()


def _get_contrato_activado_event_id(db_session, *, id_contrato: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT id
            FROM outbox_event
            WHERE event_type = 'contrato_alquiler_activado'
              AND aggregate_type = 'contrato_alquiler'
              AND aggregate_id = :id_contrato
            """
        ),
        {"id_contrato": id_contrato},
    ).scalar_one()


def _count_relaciones(db_session, *, tipo_origen: str, id_origen: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM relacion_generadora
            WHERE tipo_origen = :tipo_origen
              AND id_origen = :id_origen
              AND deleted_at IS NULL
            """
        ),
        {"tipo_origen": tipo_origen, "id_origen": id_origen},
    ).mappings().one()["total"]


def _get_relacion(db_session, *, tipo_origen: str, id_origen: int) -> dict:
    return db_session.execute(
        text(
            """
            SELECT id_relacion_generadora, tipo_origen, id_origen
            FROM relacion_generadora
            WHERE tipo_origen = :tipo_origen
              AND id_origen = :id_origen
              AND deleted_at IS NULL
            """
        ),
        {"tipo_origen": tipo_origen, "id_origen": id_origen},
    ).mappings().one()


def _count_obligaciones(db_session, *, id_relacion_generadora: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id_relacion_generadora
              AND deleted_at IS NULL
            """
        ),
        {"id_relacion_generadora": id_relacion_generadora},
    ).mappings().one()["total"]


def _get_obligaciones_concepto(db_session, *, id_relacion_generadora: int) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT
                o.importe_total,
                o.saldo_pendiente,
                o.periodo_desde,
                o.periodo_hasta,
                cf.codigo_concepto_financiero
            FROM obligacion_financiera o
            JOIN composicion_obligacion c
              ON c.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE o.id_relacion_generadora = :id_relacion_generadora
              AND o.deleted_at IS NULL
            ORDER BY o.periodo_desde NULLS FIRST, o.id_obligacion_financiera
            """
        ),
        {"id_relacion_generadora": id_relacion_generadora},
    ).mappings().all()
    return [dict(row) for row in rows]


def _get_obligacion_concepto(db_session, *, id_relacion_generadora: int) -> dict:
    obligaciones = _get_obligaciones_concepto(
        db_session,
        id_relacion_generadora=id_relacion_generadora,
    )
    assert len(obligaciones) == 1
    return obligaciones[0]


def _activar_contrato_con_condicion(client, *, codigo: str) -> dict:
    contrato = _crear_contrato_borrador(client, codigo=codigo)
    _crear_condicion_minima(client, id_contrato=contrato["id_contrato_alquiler"])
    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/activar",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_worker_procesa_venta_confirmada_crea_relacion_y_obligacion(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    event_id = _get_venta_confirmada_event_id(db_session, id_venta=venta["id_venta"])

    run_outbox_worker_once(db_session)

    relacion = _get_relacion(db_session, tipo_origen="venta", id_origen=venta["id_venta"])
    obligacion = _get_obligacion_concepto(
        db_session,
        id_relacion_generadora=relacion["id_relacion_generadora"],
    )
    outbox = _get_outbox_event(db_session, event_id=event_id)

    assert obligacion["codigo_concepto_financiero"] == "CAPITAL_VENTA"
    assert str(obligacion["importe_total"]) == "150000.00"
    assert str(obligacion["saldo_pendiente"]) == "150000.00"
    assert outbox["status"] == "PUBLISHED"
    assert outbox["published_at"] is not None
    assert outbox["processed_at"] == outbox["published_at"]


def test_worker_procesa_contrato_alquiler_activado_crea_obligacion_canon_locativo(
    client, db_session
) -> None:
    contrato = _activar_contrato_con_condicion(client, codigo="OW-CA-001")
    id_contrato = contrato["id_contrato_alquiler"]
    event_id = _get_contrato_activado_event_id(db_session, id_contrato=id_contrato)

    run_outbox_worker_once(db_session)

    relacion = _get_relacion(
        db_session,
        tipo_origen="contrato_alquiler",
        id_origen=id_contrato,
    )
    obligaciones = _get_obligaciones_concepto(
        db_session,
        id_relacion_generadora=relacion["id_relacion_generadora"],
    )
    outbox = _get_outbox_event(db_session, event_id=event_id)

    assert len(obligaciones) == 6
    assert {ob["codigo_concepto_financiero"] for ob in obligaciones} == {"CANON_LOCATIVO"}
    assert {str(ob["importe_total"]) for ob in obligaciones} == {"150000.00"}
    assert {str(ob["saldo_pendiente"]) for ob in obligaciones} == {"150000.00"}
    assert outbox["status"] == "PUBLISHED"


def test_worker_ignora_evento_desconocido_sin_romper(db_session) -> None:
    event_id = _insert_outbox_event(
        db_session,
        event_type="evento_desconocido",
        payload_sql="jsonb_build_object('id', 1)",
    )

    run_outbox_worker_once(db_session)

    outbox = _get_outbox_event(db_session, event_id=event_id)
    assert outbox["status"] == "PUBLISHED"
    assert outbox["published_at"] is not None


def test_worker_no_marca_procesado_si_payload_es_invalido(db_session) -> None:
    event_id = _insert_outbox_event(
        db_session,
        event_type="venta_confirmada",
        aggregate_type="venta",
        aggregate_id=999999,
        payload_sql="jsonb_build_object('estado_venta', 'confirmada')",
    )

    run_outbox_worker_once(db_session)

    outbox = _get_outbox_event(db_session, event_id=event_id)
    assert outbox["status"] == "PENDING"
    assert outbox["published_at"] is None
    assert outbox["processed_at"] is None


def test_worker_es_idempotente_al_ejecutarse_dos_veces(client, db_session) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    run_outbox_worker_once(db_session)
    run_outbox_worker_once(db_session)

    assert _count_relaciones(db_session, tipo_origen="venta", id_origen=venta["id_venta"]) == 1
    relacion = _get_relacion(db_session, tipo_origen="venta", id_origen=venta["id_venta"])
    assert (
        _count_obligaciones(
            db_session,
            id_relacion_generadora=relacion["id_relacion_generadora"],
        )
        == 1
    )
