import pytest
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


class FailingObligacionFinancieraRepository(FinancieroRepository):
    def create_obligacion_financiera(self, obligacion, composiciones) -> dict:
        raise RuntimeError("forced obligation creation failure")


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


def _count_obligados_obligacion(db_session, *, id_obligacion_financiera: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM obligacion_obligado
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND deleted_at IS NULL
            """
        ),
        {"id_obligacion_financiera": id_obligacion_financiera},
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


def _asegurar_rol_comprador(db_session, *, id_rol_participacion: int = 9901) -> int:
    row = db_session.execute(
        text(
            """
            SELECT id_rol_participacion
            FROM rol_participacion
            WHERE codigo_rol = 'COMPRADOR'
              AND deleted_at IS NULL
            LIMIT 1
            """
        )
    ).mappings().one_or_none()
    if row is not None:
        return row["id_rol_participacion"]

    return db_session.execute(
        text(
            """
            INSERT INTO rol_participacion (
                id_rol_participacion,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                codigo_rol,
                nombre_rol,
                estado_rol
            )
            VALUES (
                :id_rol_participacion,
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                'COMPRADOR',
                'Comprador',
                'ACTIVO'
            )
            RETURNING id_rol_participacion
            """
        ),
        {"id_rol_participacion": id_rol_participacion},
    ).mappings().one()["id_rol_participacion"]


def _crear_persona_minima(db_session, *, codigo: str) -> int:
    return db_session.execute(
        text(
            """
            INSERT INTO persona (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                tipo_persona,
                codigo_persona,
                nombre,
                apellido,
                estado_persona
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                'FISICA',
                :codigo,
                'Comprador',
                :codigo,
                'ACTIVA'
            )
            RETURNING id_persona
            """
        ),
        {"codigo": codigo},
    ).mappings().one()["id_persona"]


def _vincular_comprador_venta(
    db_session,
    *,
    id_venta: int,
    id_persona: int | None = None,
    id_rol_participacion: int | None = None,
) -> int:
    id_rol = id_rol_participacion or _asegurar_rol_comprador(db_session)
    id_persona_final = id_persona or _crear_persona_minima(
        db_session, codigo=f"PER-COMP-VTA-{id_venta}"
    )
    db_session.execute(
        text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_persona,
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
                fecha_desde
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                :id_persona,
                :id_rol_participacion,
                'venta',
                :id_venta,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "id_persona": id_persona_final,
            "id_rol_participacion": id_rol,
            "id_venta": id_venta,
        },
    )
    db_session.commit()
    return id_persona_final


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
    obligado = db_session.execute(
        text(
            """
            SELECT id_persona, rol_obligado, porcentaje_responsabilidad
            FROM obligacion_obligado
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND deleted_at IS NULL
            """
        ),
        {"id_obligacion_financiera": result.data["id_obligacion_financiera"]},
    ).mappings().one()
    assert obligado["rol_obligado"] == "COMPRADOR"
    assert str(obligado["porcentaje_responsabilidad"]) == "100.00"


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
    assert (
        _count_obligados_obligacion(
            db_session,
            id_obligacion_financiera=first_result.data["id_obligacion_financiera"],
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


def test_fin_venta_confirmada_rollback_si_falla_creacion_obligacion(
    db_session,
) -> None:
    id_venta = _insertar_venta_confirmada_con_monto(db_session, monto_total=150000)
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=id_venta))
    service = HandleVentaConfirmadaEventService(
        repository=FailingObligacionFinancieraRepository(db_session),
    )

    with pytest.raises(RuntimeError, match="forced obligation creation failure"):
        service.execute(event)

    assert _count_relaciones_venta(db_session, id_venta=id_venta) == 0
    obligaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM obligacion_financiera")
    ).mappings().one()
    assert obligaciones["total"] == 0


def test_fin_venta_confirmada_sin_comprador_bloquea_sin_crear_deuda(
    db_session,
) -> None:
    id_venta = _insertar_venta_confirmada_con_monto(db_session, monto_total=150000)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=id_venta))

    result = _build_service(db_session).execute(event)

    assert result.success is False
    assert result.errors == ["COMPRADOR_VENTA_NO_RESUELTO"]
    assert _count_relaciones_venta(db_session, id_venta=id_venta) == 0
    assert db_session.execute(
        text("SELECT COUNT(*) AS total FROM obligacion_financiera")
    ).mappings().one()["total"] == 0


def test_fin_venta_confirmada_multiples_compradores_bloquea_v1(
    db_session,
) -> None:
    id_venta = _insertar_venta_confirmada_con_monto(db_session, monto_total=150000)
    _vincular_comprador_venta(
        db_session,
        id_venta=id_venta,
        id_persona=_crear_persona_minima(db_session, codigo="PER-COMP-MULTI-1"),
    )
    _vincular_comprador_venta(
        db_session,
        id_venta=id_venta,
        id_persona=_crear_persona_minima(db_session, codigo="PER-COMP-MULTI-2"),
    )
    event = dict(_get_venta_confirmada_event(db_session, id_venta=id_venta))

    result = _build_service(db_session).execute(event)

    assert result.success is False
    assert result.errors == ["COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO"]
    assert _count_relaciones_venta(db_session, id_venta=id_venta) == 0
    assert db_session.execute(
        text("SELECT COUNT(*) AS total FROM obligacion_financiera")
    ).mappings().one()["total"] == 0


def test_fin_venta_confirmada_reproceso_completa_obligado_faltante(
    client,
    db_session,
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=venta["id_venta"]))
    service = _build_service(db_session)

    first_result = service.execute(event)
    assert first_result.success is True
    id_obligacion = first_result.data["id_obligacion_financiera"]
    db_session.execute(
        text(
            """
            UPDATE obligacion_obligado
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_obligacion_financiera = :id_obligacion
            """
        ),
        {"id_obligacion": id_obligacion},
    )
    db_session.commit()

    second_result = service.execute(event)

    assert second_result.success is True
    assert second_result.data["obligacion_created"] is False
    assert second_result.data["obligado_created"] is True
    assert _count_obligados_obligacion(
        db_session, id_obligacion_financiera=id_obligacion
    ) == 1


def test_fin_venta_confirmada_anticipo_y_saldo_crea_dos_obligaciones(
    db_session,
) -> None:
    id_venta = _insertar_venta_confirmada_con_monto(db_session, monto_total=150000)
    db_session.execute(
        text(
            """
            UPDATE venta
            SET tipo_plan_financiero = 'ANTICIPO_Y_SALDO',
                moneda = 'ARS',
                importe_anticipo = 50000.00,
                fecha_vencimiento_anticipo = DATE '2026-05-10',
                importe_saldo = 100000.00,
                fecha_vencimiento_saldo = DATE '2026-06-10'
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": id_venta},
    )
    id_persona = _vincular_comprador_venta(db_session, id_venta=id_venta)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=id_venta))

    result = _build_service(db_session).execute(event)

    assert result.success is True
    assert result.data["obligacion_created"] is True
    assert len(result.data["id_obligaciones_financieras"]) == 2
    rows = db_session.execute(
        text(
            """
            SELECT
                o.id_obligacion_financiera,
                o.fecha_vencimiento,
                o.importe_total,
                o.moneda,
                cf.codigo_concepto_financiero,
                oo.id_persona,
                oo.rol_obligado,
                oo.porcentaje_responsabilidad
            FROM obligacion_financiera o
            JOIN composicion_obligacion co
              ON co.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
            JOIN obligacion_obligado oo
              ON oo.id_obligacion_financiera = o.id_obligacion_financiera
             AND oo.deleted_at IS NULL
            WHERE o.id_relacion_generadora = :id_relacion_generadora
              AND o.deleted_at IS NULL
            ORDER BY o.fecha_vencimiento ASC
            """
        ),
        {"id_relacion_generadora": result.data["id_relacion_generadora"]},
    ).mappings().all()

    assert len(rows) == 2
    assert rows[0]["codigo_concepto_financiero"] == "ANTICIPO_VENTA"
    assert str(rows[0]["importe_total"]) == "50000.00"
    assert str(rows[0]["fecha_vencimiento"]) == "2026-05-10"
    assert rows[1]["codigo_concepto_financiero"] == "CAPITAL_VENTA"
    assert str(rows[1]["importe_total"]) == "100000.00"
    assert str(rows[1]["fecha_vencimiento"]) == "2026-06-10"
    assert {row["id_persona"] for row in rows} == {id_persona}
    assert {row["rol_obligado"] for row in rows} == {"COMPRADOR"}
    assert {str(row["porcentaje_responsabilidad"]) for row in rows} == {"100.00"}

    second_result = _build_service(db_session).execute(event)
    assert second_result.success is True
    assert second_result.data["obligacion_created"] is False
    assert (
        _count_obligaciones_relacion(
            db_session,
            id_relacion_generadora=result.data["id_relacion_generadora"],
        )
        == 2
    )
