from sqlalchemy import text

from app.application.financiero.services.handle_venta_confirmada_event_service import (
    HandleVentaConfirmadaEventService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from tests.test_disponibilidades_create import HEADERS
from tests.test_ventas_confirm import (
    _crear_venta_desde_reserva_publica,
    _payload_confirmar_venta,
)


URL_DEUDA = "/api/v1/financiero/deuda"
URL_ESTADO_CUENTA = "/api/v1/financiero/estado-cuenta"


def _get_venta_confirmada_event(db_session, *, id_venta: int) -> dict:
    return db_session.execute(
        text(
            """
            SELECT id, event_type, aggregate_type, aggregate_id, payload
            FROM outbox_event
            WHERE event_type = 'venta_confirmada'
              AND aggregate_type = 'venta'
              AND aggregate_id = :id_venta
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()


def _get_venta_minima(db_session, *, id_venta: int) -> dict:
    return db_session.execute(
        text(
            """
            SELECT monto_total, fecha_venta::date AS fecha_venta
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()


def test_venta_confirmada_materializa_deuda_y_estado_cuenta_v1_contado(
    client,
    db_session,
) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)

    confirm_response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )
    assert confirm_response.status_code == 200
    id_venta = confirm_response.json()["data"]["id_venta"]

    event = dict(_get_venta_confirmada_event(db_session, id_venta=id_venta))
    result = HandleVentaConfirmadaEventService(
        repository=FinancieroRepository(db_session),
    ).execute(event)

    assert result.success is True
    assert result.data is not None
    assert result.data["obligacion_created"] is True
    id_relacion_generadora = result.data["id_relacion_generadora"]
    id_obligacion_financiera = result.data["id_obligacion_financiera"]

    venta_row = _get_venta_minima(db_session, id_venta=id_venta)
    monto_total = venta_row["monto_total"]
    fecha_venta = venta_row["fecha_venta"]

    relacion = db_session.execute(
        text(
            """
            SELECT tipo_origen, id_origen
            FROM relacion_generadora
            WHERE id_relacion_generadora = :id_relacion_generadora
              AND deleted_at IS NULL
            """
        ),
        {"id_relacion_generadora": id_relacion_generadora},
    ).mappings().one()
    assert relacion["tipo_origen"] == "venta"
    assert relacion["id_origen"] == id_venta

    obligacion = db_session.execute(
        text(
            """
            SELECT
                o.id_obligacion_financiera,
                o.id_relacion_generadora,
                o.fecha_vencimiento,
                o.importe_total,
                o.saldo_pendiente,
                c.moneda_componente,
                cf.codigo_concepto_financiero
            FROM obligacion_financiera o
            JOIN composicion_obligacion c
              ON c.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE o.id_relacion_generadora = :id_relacion_generadora
              AND o.deleted_at IS NULL
            """
        ),
        {"id_relacion_generadora": id_relacion_generadora},
    ).mappings().one()
    assert obligacion["id_obligacion_financiera"] == id_obligacion_financiera
    assert obligacion["id_relacion_generadora"] == id_relacion_generadora
    assert obligacion["codigo_concepto_financiero"] == "CAPITAL_VENTA"
    assert obligacion["importe_total"] == monto_total
    assert obligacion["saldo_pendiente"] == monto_total
    assert obligacion["fecha_vencimiento"] == fecha_venta
    assert obligacion["moneda_componente"] == "ARS"

    deuda_response = client.get(
        URL_DEUDA,
        headers=HEADERS,
        params={"id_relacion_generadora": id_relacion_generadora},
    )
    assert deuda_response.status_code == 200
    deuda_data = deuda_response.json()["data"]
    assert deuda_data["total"] == 1
    deuda_item = deuda_data["items"][0]
    assert deuda_item["id_obligacion_financiera"] == id_obligacion_financiera
    assert deuda_item["id_relacion_generadora"] == id_relacion_generadora
    assert deuda_item["importe_total"] == float(monto_total)
    assert deuda_item["saldo_pendiente"] == float(monto_total)
    assert deuda_item["composiciones"][0]["codigo_concepto_financiero"] == "CAPITAL_VENTA"

    estado_response = client.get(
        URL_ESTADO_CUENTA,
        headers=HEADERS,
        params={"id_relacion_generadora": id_relacion_generadora},
    )
    assert estado_response.status_code == 200
    estado_data = estado_response.json()["data"]
    assert estado_data["id_relacion_generadora"] == id_relacion_generadora
    assert estado_data["resumen"]["importe_total"] == float(monto_total)
    assert estado_data["resumen"]["saldo_pendiente"] == float(monto_total)
    assert estado_data["resumen"]["cantidad_obligaciones"] == 1
    assert len(estado_data["obligaciones"]) == 1
    estado_obligacion = estado_data["obligaciones"][0]
    assert estado_obligacion["id_obligacion_financiera"] == id_obligacion_financiera
    assert (
        estado_obligacion["composiciones"][0]["codigo_concepto_financiero"]
        == "CAPITAL_VENTA"
    )
