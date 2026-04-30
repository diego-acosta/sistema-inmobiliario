from sqlalchemy import text

from app.application.financiero.services.handle_venta_confirmada_event_service import (
    HandleVentaConfirmadaEventService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from tests.test_escrituraciones_create import _confirmar_venta_publica


def _build_service(db_session) -> HandleVentaConfirmadaEventService:
    return HandleVentaConfirmadaEventService(
        repository=FinancieroRepository(db_session),
    )


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


def _count_relaciones_venta(db_session, *, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM relacion_generadora
            WHERE tipo_origen = 'venta'
              AND id_origen = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()["total"]


def _count_obligaciones_relacion(db_session, *, id_relacion_generadora: int) -> int:
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


def _get_fecha_venta(db_session, *, id_venta: int) -> str:
    return str(
        db_session.execute(
            text("SELECT fecha_venta::date AS fecha_venta FROM venta WHERE id_venta = :id_venta"),
            {"id_venta": id_venta},
        ).mappings().one()["fecha_venta"]
    )


def _insertar_venta_confirmada_con_monto(db_session, *, monto_total) -> int:
    id_venta = db_session.execute(
        text(
            """
            INSERT INTO venta (
                codigo_venta,
                fecha_venta,
                estado_venta,
                monto_total
            )
            VALUES (
                'V-FIN-EVT-MONTO-INVALIDO',
                TIMESTAMP '2026-04-30 10:00:00',
                'confirmada',
                :monto_total
            )
            RETURNING id_venta
            """
        ),
        {"monto_total": monto_total},
    ).mappings().one()["id_venta"]
    db_session.execute(
        text(
            """
            INSERT INTO outbox_event (
                event_type,
                aggregate_type,
                aggregate_id,
                payload,
                occurred_at,
                status
            )
            VALUES (
                'venta_confirmada',
                'venta',
                :id_venta,
                jsonb_build_object(
                    'id_venta', :id_venta,
                    'estado_venta', 'confirmada',
                    'objetos', '[]'::jsonb
                ),
                TIMESTAMP '2026-04-30 10:00:00',
                'PENDING'
            )
            """
        ),
        {"id_venta": id_venta},
    )
    db_session.commit()
    return id_venta


def test_fin_venta_confirmada_crea_relacion_generadora_y_obligacion_capital_venta(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=venta["id_venta"]))

    result = _build_service(db_session).execute(event)

    assert result.success is True
    assert result.data is not None
    assert result.data["id_venta"] == venta["id_venta"]
    assert result.data["created"] is True
    assert result.data["relacion_generadora_created"] is True
    assert result.data["obligacion_created"] is True
    assert isinstance(result.data["id_relacion_generadora"], int)
    assert isinstance(result.data["id_obligacion_financiera"], int)

    row = db_session.execute(
        text(
            """
            SELECT tipo_origen, id_origen, descripcion, estado_relacion_generadora
            FROM relacion_generadora
            WHERE id_relacion_generadora = :id_relacion_generadora
            """
        ),
        {"id_relacion_generadora": result.data["id_relacion_generadora"]},
    ).mappings().one()
    assert row["tipo_origen"] == "venta"
    assert row["id_origen"] == venta["id_venta"]
    assert row["descripcion"] == "Relacion generadora creada desde venta_confirmada"
    assert row["estado_relacion_generadora"] == "BORRADOR"

    obligacion = db_session.execute(
        text(
            """
            SELECT
                o.id_relacion_generadora,
                o.fecha_vencimiento,
                o.importe_total,
                o.saldo_pendiente,
                o.estado_obligacion,
                c.importe_componente,
                c.saldo_componente,
                c.moneda_componente,
                cf.codigo_concepto_financiero
            FROM obligacion_financiera o
            JOIN composicion_obligacion c
              ON c.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE o.id_obligacion_financiera = :id_obligacion_financiera
            """
        ),
        {"id_obligacion_financiera": result.data["id_obligacion_financiera"]},
    ).mappings().one()
    assert obligacion["id_relacion_generadora"] == result.data["id_relacion_generadora"]
    assert str(obligacion["fecha_vencimiento"]) == _get_fecha_venta(
        db_session,
        id_venta=venta["id_venta"],
    )
    assert str(obligacion["importe_total"]) == "150000.00"
    assert str(obligacion["saldo_pendiente"]) == "150000.00"
    assert obligacion["estado_obligacion"] == "PROYECTADA"
    assert obligacion["codigo_concepto_financiero"] == "CAPITAL_VENTA"
    assert str(obligacion["importe_componente"]) == "150000.00"
    assert str(obligacion["saldo_componente"]) == "150000.00"
    assert obligacion["moneda_componente"] == "ARS"


def test_fin_venta_confirmada_no_duplica_si_ya_existe(client, db_session) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=venta["id_venta"]))
    service = _build_service(db_session)

    first_result = service.execute(event)
    second_result = service.execute(event)

    assert first_result.success is True
    assert first_result.data is not None
    assert first_result.data["created"] is True
    assert first_result.data["obligacion_created"] is True
    assert second_result.success is True
    assert second_result.data is not None
    assert second_result.data["created"] is False
    assert second_result.data["obligacion_created"] is False
    assert (
        second_result.data["id_relacion_generadora"]
        == first_result.data["id_relacion_generadora"]
    )
    assert _count_relaciones_venta(db_session, id_venta=venta["id_venta"]) == 1
    assert (
        _count_obligaciones_relacion(
            db_session,
            id_relacion_generadora=first_result.data["id_relacion_generadora"],
        )
        == 1
    )


def test_fin_venta_confirmada_ignora_eventos_repetidos_idempotente(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=venta["id_venta"]))
    service = _build_service(db_session)

    results = [service.execute(event) for _ in range(3)]

    assert all(result.success for result in results)
    assert results[0].data is not None
    assert results[0].data["created"] is True
    assert results[0].data["obligacion_created"] is True
    assert [result.data["created"] for result in results[1:]] == [False, False]
    assert [result.data["obligacion_created"] for result in results[1:]] == [
        False,
        False,
    ]
    assert _count_relaciones_venta(db_session, id_venta=venta["id_venta"]) == 1
    assert (
        _count_obligaciones_relacion(
            db_session,
            id_relacion_generadora=results[0].data["id_relacion_generadora"],
        )
        == 1
    )


def test_fin_venta_confirmada_con_monto_no_positivo_no_crea_obligacion(
    db_session,
) -> None:
    id_venta = _insertar_venta_confirmada_con_monto(db_session, monto_total=0)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=id_venta))

    result = _build_service(db_session).execute(event)

    assert result.success is False
    assert result.errors == ["INVALID_MONTO_TOTAL"]
    assert _count_relaciones_venta(db_session, id_venta=id_venta) == 0
    obligaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM obligacion_financiera")
    ).mappings().one()
    assert obligaciones["total"] == 0


def test_fin_venta_confirmada_si_ya_existe_obligacion_no_crea_otra(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=venta["id_venta"]))
    service = _build_service(db_session)

    first_result = service.execute(event)
    assert first_result.success is True
    assert first_result.data is not None
    id_relacion_generadora = first_result.data["id_relacion_generadora"]

    second_result = service.execute(event)

    assert second_result.success is True
    assert second_result.data is not None
    assert second_result.data["obligacion_created"] is False
    assert (
        second_result.data["id_relacion_generadora"]
        == id_relacion_generadora
    )
    assert (
        _count_obligaciones_relacion(
            db_session,
            id_relacion_generadora=id_relacion_generadora,
        )
        == 1
    )
