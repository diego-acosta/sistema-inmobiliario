from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_event_venta_confirmada import _vincular_comprador_venta
from tests.test_reservas_venta_create import _crear_inmueble
from tests.test_ventas_definir_condiciones_comerciales import (
    _insertar_venta_para_condiciones,
    _payload_condiciones,
)


URL = "/api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple"


def _insertar_venta_minima(db_session, *, codigo_venta: str) -> int:
    return db_session.execute(
        text(
            """
            INSERT INTO venta (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_venta,
                fecha_venta,
                estado_venta,
                monto_total,
                moneda,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                CAST(:op_id AS uuid),
                CAST(:op_id AS uuid),
                :codigo_venta,
                TIMESTAMP '2026-05-14 10:00:00',
                'borrador',
                12000000.00,
                'ARS',
                'Venta para plan pago V2'
            )
            RETURNING id_venta
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "codigo_venta": codigo_venta},
    ).scalar_one()


def _payload(
    *,
    monto_total_plan: float = 12000000.00,
    cantidad_cuotas: int = 12,
    fecha_primer_vencimiento: str = "2026-06-10",
) -> dict[str, object]:
    return {
        "monto_total_plan": monto_total_plan,
        "moneda": "ARS",
        "cantidad_cuotas": cantidad_cuotas,
        "fecha_primer_vencimiento": fecha_primer_vencimiento,
        "periodicidad": "MENSUAL",
        "regla_redondeo": "ULTIMA_CUOTA",
    }


def _count_venta_plan_cuota(db_session, *, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM venta_plan_cuota
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).scalar_one()


def _obligaciones_v2(db_session, *, id_venta: int) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT
                o.id_obligacion_financiera,
                o.id_plan_pago_venta_bloque,
                o.numero_obligacion,
                o.tipo_item_cronograma,
                o.etiqueta_obligacion,
                o.clave_funcional_origen,
                o.fecha_vencimiento,
                o.importe_total,
                o.saldo_pendiente,
                o.moneda,
                o.estado_obligacion,
                cf.codigo_concepto_financiero,
                oo.rol_obligado,
                oo.porcentaje_responsabilidad
            FROM relacion_generadora rg
            JOIN obligacion_financiera o
              ON o.id_relacion_generadora = rg.id_relacion_generadora
             AND o.deleted_at IS NULL
            JOIN composicion_obligacion co
              ON co.id_obligacion_financiera = o.id_obligacion_financiera
             AND co.deleted_at IS NULL
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
            JOIN obligacion_obligado oo
              ON oo.id_obligacion_financiera = o.id_obligacion_financiera
             AND oo.deleted_at IS NULL
            WHERE rg.tipo_origen = 'venta'
              AND rg.id_origen = :id_venta
              AND rg.deleted_at IS NULL
            ORDER BY o.numero_obligacion ASC
            """
        ),
        {"id_venta": id_venta},
    ).mappings().all()
    return [dict(row) for row in rows]


def _bloques_plan_pago_venta_v2(db_session, *, id_venta: int) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT
                b.id_plan_pago_venta_bloque,
                b.id_plan_pago_venta,
                b.numero_bloque,
                b.tipo_bloque,
                b.etiqueta_bloque,
                b.clave_bloque,
                b.cantidad_cuotas,
                b.importe_total_bloque,
                b.importe_cuota,
                b.fecha_vencimiento,
                b.fecha_primer_vencimiento,
                b.periodicidad,
                b.regla_redondeo,
                b.concepto_financiero_codigo
            FROM plan_pago_venta ppv
            JOIN plan_pago_venta_bloque b
              ON b.id_plan_pago_venta = ppv.id_plan_pago_venta
             AND b.deleted_at IS NULL
            WHERE ppv.id_venta = :id_venta
              AND ppv.deleted_at IS NULL
            ORDER BY b.numero_bloque ASC
            """
        ),
        {"id_venta": id_venta},
    ).mappings().all()
    return [dict(row) for row in rows]


def test_cuotas_iguales_v2_crea_plan_generacion_obligaciones_y_no_usa_venta_plan_cuota(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-CIS-001")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    response = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["plan_pago_venta"]["metodo_plan_pago"] == "CUOTAS_IGUALES_SIMPLE"
    assert data["plan_pago_venta"]["estado_plan_pago"] == "GENERADO"
    assert data["generacion_cronograma_financiero"]["tipo_generacion"] == "PLAN_PAGO_VENTA_V2"
    assert len(data["obligaciones"]) == 12
    assert _count_venta_plan_cuota(db_session, id_venta=id_venta) == 0

    bloques = _bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)
    assert len(bloques) == 1
    bloque = bloques[0]
    assert bloque["numero_bloque"] == 1
    assert bloque["tipo_bloque"] == "TRAMO_CUOTAS"
    assert bloque["etiqueta_bloque"] == "Cuotas iguales"
    assert bloque["clave_bloque"].endswith(":BLOQUE:TRAMO_CUOTAS:1")
    assert bloque["cantidad_cuotas"] == 12
    assert bloque["importe_cuota"] == Decimal("1000000.00")
    assert bloque["fecha_primer_vencimiento"].isoformat() == "2026-06-10"
    assert bloque["periodicidad"] == "MENSUAL"
    assert bloque["regla_redondeo"] == "ULTIMA_CUOTA"
    assert bloque["concepto_financiero_codigo"] == "CAPITAL_VENTA"

    obligaciones = _obligaciones_v2(db_session, id_venta=id_venta)
    assert len(obligaciones) == 12
    assert {ob["id_plan_pago_venta_bloque"] for ob in obligaciones} == {
        bloque["id_plan_pago_venta_bloque"]
    }
    assert sum(
        (obligacion["importe_total"] for obligacion in obligaciones),
        start=Decimal("0"),
    ) == Decimal("12000000.00")
    assert [obligacion["numero_obligacion"] for obligacion in obligaciones] == list(
        range(1, 13)
    )
    assert {obligacion["tipo_item_cronograma"] for obligacion in obligaciones} == {
        "CUOTA"
    }
    assert obligaciones[0]["etiqueta_obligacion"] == "Cuota 1"
    assert obligaciones[-1]["etiqueta_obligacion"] == "Cuota 12"
    assert obligaciones[0]["clave_funcional_origen"].endswith(":CUOTA:1")
    assert obligaciones[-1]["clave_funcional_origen"].endswith(":CUOTA:12")
    assert {obligacion["estado_obligacion"] for obligacion in obligaciones} == {
        "PROYECTADA"
    }
    assert {obligacion["codigo_concepto_financiero"] for obligacion in obligaciones} == {
        "CAPITAL_VENTA"
    }
    assert {obligacion["rol_obligado"] for obligacion in obligaciones} == {
        "COMPRADOR"
    }
    assert {str(obligacion["porcentaje_responsabilidad"]) for obligacion in obligaciones} == {
        "100.00"
    }


def test_cuotas_iguales_v2_redondea_ultima_cuota_y_suma_total(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-CIS-002")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    response = client.post(
        URL.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload(monto_total_plan=100.00, cantidad_cuotas=3),
    )

    assert response.status_code == 200, response.text
    obligaciones = _obligaciones_v2(db_session, id_venta=id_venta)
    assert [obligacion["importe_total"] for obligacion in obligaciones] == [
        Decimal("33.33"),
        Decimal("33.33"),
        Decimal("33.34"),
    ]


def test_cuotas_iguales_v2_fechas_mensuales_usan_ultimo_dia_si_no_existe(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-CIS-003")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    response = client.post(
        URL.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload(
            monto_total_plan=300.00,
            cantidad_cuotas=3,
            fecha_primer_vencimiento="2026-01-31",
        ),
    )

    assert response.status_code == 200, response.text
    obligaciones = _obligaciones_v2(db_session, id_venta=id_venta)
    assert [str(obligacion["fecha_vencimiento"]) for obligacion in obligaciones] == [
        "2026-01-31",
        "2026-02-28",
        "2026-03-31",
    ]


def test_cuotas_iguales_v2_reejecutar_no_duplica_obligaciones(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-CIS-004")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    first = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())
    second = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert len(_bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)) == 1
    obligaciones = _obligaciones_v2(db_session, id_venta=id_venta)
    assert len(obligaciones) == 12
    assert db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM generacion_cronograma_financiero gcf
            JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = gcf.id_relacion_generadora
            WHERE rg.tipo_origen = 'venta'
              AND rg.id_origen = :id_venta
              AND gcf.deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).scalar_one() == 1


def test_cuotas_iguales_v2_no_oculta_bloque_existente_incompatible(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-CIS-006")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    first = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())
    assert first.status_code == 200, first.text

    db_session.execute(
        text(
            """
            UPDATE plan_pago_venta_bloque b
            SET etiqueta_bloque = 'Bloque incompatible'
            FROM plan_pago_venta ppv
            WHERE ppv.id_plan_pago_venta = b.id_plan_pago_venta
              AND ppv.id_venta = :id_venta
              AND b.tipo_bloque = 'TRAMO_CUOTAS'
              AND b.deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    )

    second = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())

    assert second.status_code == 400, second.text
    assert any(
        error.startswith("PLAN_PAGO_VENTA_BLOQUE_INCOMPATIBLE")
        for error in second.json()["details"]["errors"]
    )
    assert len(_obligaciones_v2(db_session, id_venta=id_venta)) == 12
    assert len(_bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)) == 1


def test_cuotas_iguales_v2_respeta_unique_de_un_plan_vivo_por_venta(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-CIS-005")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    response = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())
    assert response.status_code == 200, response.text

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO plan_pago_venta (
                    id_venta,
                    metodo_plan_pago,
                    estado_plan_pago,
                    moneda,
                    monto_total_plan
                )
                VALUES (
                    :id_venta,
                    'CUOTAS_IGUALES_SIMPLE',
                    'BORRADOR',
                    'ARS',
                    12000000.00
                )
                """
            ),
            {"id_venta": id_venta},
        )


def test_cuotas_iguales_v2_rechaza_plan_vivo_incompatible(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-CIS-006")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    first = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())
    second = client.post(
        URL.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload(monto_total_plan=13000000.00),
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 409


def test_cuotas_fijas_v1_sigue_usando_venta_plan_cuota(client, db_session) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-PPV2-V1-CUOTAS")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-PPV2-V1-CUOTAS",
        estado_venta="borrador",
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": None,
            }
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json={
            **_payload_condiciones(
                monto_total=120000.00,
                objetos=[
                    {
                        "id_inmueble": id_inmueble,
                        "id_unidad_funcional": None,
                        "precio_asignado": 120000.00,
                    }
                ],
            ),
            "tipo_plan_financiero": "CUOTAS_FIJAS",
            "moneda": "ARS",
            "cuotas": [
                {
                    "numero_cuota": 1,
                    "importe_cuota": 60000.00,
                    "fecha_vencimiento": "2026-06-10",
                },
                {
                    "numero_cuota": 2,
                    "importe_cuota": 60000.00,
                    "fecha_vencimiento": "2026-07-10",
                },
            ],
        },
    )

    assert response.status_code == 200, response.text
    assert _count_venta_plan_cuota(db_session, id_venta=venta["id_venta"]) == 2
