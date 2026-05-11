from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _crear_persona,
)
from tests.test_ventas_confirm import _crear_venta_desde_reserva_publica
from tests.test_ventas_detalle_integral import (
    _confirmar_venta,
    _procesar_evento_financiero_venta,
)


def _contadores_no_mutacion(db_session) -> dict:
    return dict(
        db_session.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM relacion_generadora) AS relaciones,
                    (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones,
                    (SELECT COUNT(*) FROM movimiento_financiero) AS movimientos,
                    (SELECT COUNT(*) FROM outbox_event) AS outbox_events,
                    (SELECT COUNT(*) FROM inbox_event) AS inbox_events
                """
            )
        ).mappings().one()
    )


def test_list_ventas_ui_filtra_y_devuelve_resumenes_sin_mutar(
    client, db_session
) -> None:
    venta = _confirmar_venta(client, db_session)
    fin = _procesar_evento_financiero_venta(db_session, id_venta=venta["id_venta"])
    before = _contadores_no_mutacion(db_session)

    response = client.get(
        "/api/v1/ventas",
        params={
            "q": "V-CONF-001",
            "estado_venta": "confirmada",
            "id_inmueble": venta["id_inmueble"],
            "tipo_plan_financiero": "CONTADO",
            "con_saldo": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id_venta"] == venta["id_venta"]
    assert item["codigo_venta"] == "V-CONF-001"
    assert item["estado_venta"] == "confirmada"
    assert item["tipo_plan_financiero"] == "CONTADO"
    assert len(item["comprador_resumen"]) == 1
    assert item["comprador_resumen"][0]["codigo_rol"] == "COMPRADOR"
    assert len(item["objetos_resumen"]) == 1
    assert item["objetos_resumen"][0]["id_inmueble"] == venta["id_inmueble"]
    assert item["relacion_financiera"]["id_relacion_generadora"] == (
        fin["id_relacion_generadora"]
    )
    assert item["relacion_financiera"]["cantidad_obligaciones"] == 1
    assert float(item["relacion_financiera"]["saldo_pendiente_total"]) == 150000.00
    assert item["acciones_ui"]["puede_abrir_detalle"] is True
    assert _contadores_no_mutacion(db_session) == before


def test_list_ventas_filtra_por_comprador_unidad_plan_y_no_duplica(
    client, db_session
) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)
    id_unidad = db_session.execute(
        text(
            """
            INSERT INTO unidad_funcional (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_inmueble, codigo_unidad, nombre_unidad,
                superficie, estado_administrativo, estado_operativo, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_inmueble, 'UF-V-LIST-001', 'Unidad venta listado',
                40.00, 'ACTIVO', 'DISPONIBLE', NULL
            )
            RETURNING id_unidad_funcional
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "id_inmueble": venta["id_inmueble"]},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO venta_objeto_inmobiliario (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_venta, id_inmueble, id_unidad_funcional, precio_asignado, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_venta, NULL, :id_unidad, 1.00, 'Unidad adicional'
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_venta": venta["id_venta"],
            "id_unidad": id_unidad,
        },
    )
    id_comprador_2 = _crear_persona(client, nombre="Comprador", apellido="Secundario")
    id_rol_comprador = db_session.execute(
        text(
            """
            SELECT id_rol_participacion
            FROM rol_participacion
            WHERE codigo_rol = 'COMPRADOR'
              AND deleted_at IS NULL
            ORDER BY id_rol_participacion
            LIMIT 1
            """
        )
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_persona, id_rol_participacion,
                tipo_relacion, id_relacion, fecha_desde, fecha_hasta, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_persona, :id_rol,
                'venta', :id_venta, TIMESTAMP '2026-05-01 00:00:00', NULL, NULL
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_persona": id_comprador_2,
            "id_rol": id_rol_comprador,
            "id_venta": venta["id_venta"],
        },
    )

    response = client.get(
        "/api/v1/ventas",
        params={
            "id_persona": id_comprador_2,
            "rol_codigo": "COMPRADOR",
            "id_unidad_funcional": id_unidad,
            "tipo_plan_financiero": "CONTADO",
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id_venta"] == venta["id_venta"]
    assert len(item["comprador_resumen"]) == 2
    assert len(item["objetos_resumen"]) == 2


def test_list_ventas_excluye_deleted_y_pagina(client, db_session) -> None:
    venta_visible = _crear_venta_desde_reserva_publica(client, db_session)
    id_venta_baja = db_session.execute(
        text(
            """
            INSERT INTO venta (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_reserva_venta, codigo_venta, fecha_venta, estado_venta,
                monto_total, tipo_plan_financiero, moneda, observaciones,
                deleted_at
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                NULL, 'V-CONF-001-BAJA', TIMESTAMP '2026-04-22 11:00:00',
                'borrador', 1.00, 'CONTADO', 'ARS', NULL, CURRENT_TIMESTAMP
            )
            RETURNING id_venta
            """
        ),
        {"op_id": HEADERS["X-Op-Id"]},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO venta_objeto_inmobiliario (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_venta, id_inmueble, id_unidad_funcional, precio_asignado, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_venta, :id_inmueble, NULL, 1.00, NULL
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_venta": id_venta_baja,
            "id_inmueble": venta_visible["id_inmueble"],
        },
    )

    response = client.get(
        "/api/v1/ventas",
        params={"limit": 1, "offset": 0, "q": "V-CONF-001"},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    ids = {item["id_venta"] for item in body["items"]}
    assert venta_visible["id_venta"] in ids
    assert id_venta_baja not in ids
    assert len(body["items"]) <= 1


def test_list_ventas_filtra_tipos_plan_financiero(client, db_session) -> None:
    for plan in ("CONTADO", "ANTICIPO_Y_SALDO", "CUOTAS_FIJAS"):
        db_session.execute(
            text(
                """
                INSERT INTO venta (
                    uid_global, version_registro, created_at, updated_at,
                    id_instalacion_origen, id_instalacion_ultima_modificacion,
                    op_id_alta, op_id_ultima_modificacion,
                    id_reserva_venta, codigo_venta, fecha_venta, estado_venta,
                    monto_total, tipo_plan_financiero, moneda,
                    importe_anticipo, fecha_vencimiento_anticipo,
                    importe_saldo, fecha_vencimiento_saldo, observaciones
                )
                VALUES (
                    gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                    1, 1, :op_id, :op_id,
                    NULL, :codigo, TIMESTAMP '2026-04-22 11:00:00',
                    'borrador', 100.00, CAST(:plan AS varchar), 'ARS',
                    CASE WHEN CAST(:plan AS varchar) = 'ANTICIPO_Y_SALDO' THEN 40.00 ELSE NULL END,
                    CASE WHEN CAST(:plan AS varchar) = 'ANTICIPO_Y_SALDO' THEN DATE '2026-05-10' ELSE NULL END,
                    CASE WHEN CAST(:plan AS varchar) = 'ANTICIPO_Y_SALDO' THEN 60.00 ELSE NULL END,
                    CASE WHEN CAST(:plan AS varchar) = 'ANTICIPO_Y_SALDO' THEN DATE '2026-06-10' ELSE NULL END,
                    NULL
                )
                """
            ),
            {
                "op_id": HEADERS["X-Op-Id"],
                "codigo": f"V-LIST-PLAN-{plan}",
                "plan": plan,
            },
        )

    for plan in ("CONTADO", "ANTICIPO_Y_SALDO", "CUOTAS_FIJAS"):
        response = client.get(
            "/api/v1/ventas",
            params={"tipo_plan_financiero": plan, "q": f"V-LIST-PLAN-{plan}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["tipo_plan_financiero"] == plan
