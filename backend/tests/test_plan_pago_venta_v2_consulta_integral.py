from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    CuotaRefuerzoInput,
    PlanPagoVentaBloqueInput,
)
from app.infrastructure.persistence.repositories.plan_pago_venta_v2_repository import (
    PlanPagoVentaV2Repository,
)
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_event_venta_confirmada import (
    _crear_persona_minima,
    _vincular_comprador_venta,
)
from tests.test_plan_pago_venta_v2_bloques_unificado import (
    _bloque_indexado_generate,
    _command,
    _insertar_indice_financiero_minimo,
    _insertar_indice_financiero_valor,
    _service,
)
from tests.test_plan_pago_venta_v2_cuotas_iguales import _insertar_venta_minima

URL_GET = "/api/v1/ventas/{id_venta}/plan-pago-v2"
URL_CUOTAS_IGUALES = "/api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple"


def _payload_cuotas_iguales() -> dict[str, object]:
    return {
        "monto_total_plan": 12000000.00,
        "moneda": "ARS",
        "cantidad_cuotas": 3,
        "fecha_primer_vencimiento": "2026-06-10",
        "periodicidad": "MENSUAL",
        "regla_redondeo": "ULTIMA_CUOTA",
    }


def _count_plan_rows(db_session, *, id_venta: int) -> dict[str, int]:
    return {
        "obligaciones": db_session.execute(
            text("""
                SELECT COUNT(*)
                FROM obligacion_financiera o
                JOIN relacion_generadora rg
                  ON rg.id_relacion_generadora = o.id_relacion_generadora
                WHERE rg.tipo_origen = 'venta'
                  AND rg.id_origen = :id_venta
                  AND rg.deleted_at IS NULL
                  AND o.deleted_at IS NULL
                """),
            {"id_venta": id_venta},
        ).scalar_one(),
        "composiciones": db_session.execute(
            text("""
                SELECT COUNT(*)
                FROM composicion_obligacion co
                JOIN obligacion_financiera o
                  ON o.id_obligacion_financiera = co.id_obligacion_financiera
                JOIN relacion_generadora rg
                  ON rg.id_relacion_generadora = o.id_relacion_generadora
                WHERE rg.tipo_origen = 'venta'
                  AND rg.id_origen = :id_venta
                  AND rg.deleted_at IS NULL
                  AND o.deleted_at IS NULL
                  AND co.deleted_at IS NULL
                """),
            {"id_venta": id_venta},
        ).scalar_one(),
        "obligados": db_session.execute(
            text("""
                SELECT COUNT(*)
                FROM obligacion_obligado oo
                JOIN obligacion_financiera o
                  ON o.id_obligacion_financiera = oo.id_obligacion_financiera
                JOIN relacion_generadora rg
                  ON rg.id_relacion_generadora = o.id_relacion_generadora
                WHERE rg.tipo_origen = 'venta'
                  AND rg.id_origen = :id_venta
                  AND rg.deleted_at IS NULL
                  AND o.deleted_at IS NULL
                  AND oo.deleted_at IS NULL
                """),
            {"id_venta": id_venta},
        ).scalar_one(),
        "indexaciones": db_session.execute(
            text("""
                SELECT COUNT(*)
                FROM obligacion_financiera_indexacion ofi
                JOIN obligacion_financiera o
                  ON o.id_obligacion_financiera = ofi.id_obligacion_financiera
                JOIN relacion_generadora rg
                  ON rg.id_relacion_generadora = o.id_relacion_generadora
                WHERE rg.tipo_origen = 'venta'
                  AND rg.id_origen = :id_venta
                  AND rg.deleted_at IS NULL
                  AND o.deleted_at IS NULL
                  AND ofi.deleted_at IS NULL
                """),
            {"id_venta": id_venta},
        ).scalar_one(),
    }


def test_consulta_plan_por_bloques_legacy_sin_indexacion(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-GET-LEGACY")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    generated = client.post(
        URL_CUOTAS_IGUALES.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload_cuotas_iguales(),
    )
    assert generated.status_code == 200, generated.text

    response = client.get(URL_GET.format(id_venta=id_venta))

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id_venta"] == id_venta
    assert data["plan_pago_venta"]["metodo_plan_pago"] == "CUOTAS_IGUALES_SIMPLE"
    assert len(data["bloques"]) == 1
    bloque = data["bloques"][0]
    assert bloque["indexacion"] is None
    assert len(bloque["obligaciones"]) == 3
    assert all(
        obligacion["indexacion"] is None for obligacion in bloque["obligaciones"]
    )
    assert all(
        len(obligacion["obligados"]) == 1 for obligacion in bloque["obligaciones"]
    )
    assert all(
        Decimal(str(obligacion["obligados"][0]["porcentaje_responsabilidad"]))
        == Decimal("100.00")
        for obligacion in bloque["obligaciones"]
    )
    assert all(
        Decimal(str(obligacion["obligados"][0]["importe_responsabilidad_informativo"]))
        == Decimal(str(obligacion["importe_total"]))
        for obligacion in bloque["obligaciones"]
    )
    assert all(
        [
            composicion["codigo_concepto_financiero"]
            for composicion in obligacion["composiciones"]
        ]
        == ["CAPITAL_VENTA"]
        for obligacion in bloque["obligaciones"]
    )
    assert data["resumen"]["cantidad_bloques"] == 1
    assert data["resumen"]["cantidad_obligaciones"] == 3
    assert data["resumen"]["cantidad_obligados_total"] == 3
    assert data["resumen"]["cantidad_obligaciones_con_multiples_obligados"] == 0
    assert Decimal(str(data["resumen"]["total_capital"])) == Decimal("12000000.00")
    assert Decimal(str(data["resumen"]["total_interes"])) == Decimal("0")
    assert Decimal(str(data["resumen"]["total_ajuste_indexacion"])) == Decimal("0")


def test_consulta_plan_con_interes_directo_incluye_composiciones_y_resumen(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-GET-INT")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    result = _service(db_session).execute(
        _command(
            id_venta=id_venta,
            monto_total_plan=Decimal("3000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("3000000.00"),
                    cantidad_cuotas=3,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                    metodo_liquidacion="INTERES_DIRECTO",
                    tasa_interes_directo_periodica=Decimal("0.02"),
                    cantidad_periodos=1,
                    base_calculo_interes="CAPITAL_INICIAL_BLOQUE",
                )
            ],
        )
    )
    assert result.success, result.errors

    response = client.get(URL_GET.format(id_venta=id_venta))

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    obligaciones = data["bloques"][0]["obligaciones"]
    composiciones = obligaciones[0]["composiciones"]
    assert [c["codigo_concepto_financiero"] for c in composiciones] == [
        "CAPITAL_VENTA",
        "INTERES_FINANCIERO",
    ]
    assert Decimal(str(data["resumen"]["total_interes"])) == Decimal("60000.00")
    assert Decimal(str(data["resumen"]["total_capital"])) == Decimal("3000000.00")
    assert all(len(obligacion["obligados"]) == 1 for obligacion in obligaciones)


def test_consulta_plan_con_indexacion_distingue_cuotas_aplicadas_y_proyectadas(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-GET-IX")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    id_indice = _insertar_indice_financiero_minimo(db_session, codigo="RIPTE-GET-IX")
    id_valor = _insertar_indice_financiero_valor(
        db_session,
        id_indice_financiero=id_indice,
        fecha_valor=date(2026, 7, 10),
        valor_indice=Decimal("110.00000000"),
    )
    result = _service(db_session).execute(
        _command(
            id_venta=id_venta,
            monto_total_plan=Decimal("3000000.00"),
            bloques=[_bloque_indexado_generate(id_indice)],
        )
    )
    assert result.success, result.errors
    before = _count_plan_rows(db_session, id_venta=id_venta)

    response = client.get(URL_GET.format(id_venta=id_venta))

    assert response.status_code == 200, response.text
    after = _count_plan_rows(db_session, id_venta=id_venta)
    assert after == before
    data = response.json()["data"]
    bloque = data["bloques"][0]
    assert bloque["metodo_liquidacion"] == "INDEXACION"
    assert bloque["indexacion"]["id_indice_financiero"] == id_indice
    assert bloque["indexacion"]["codigo_indice_financiero"] == "RIPTE-GET-IX"
    obligaciones = bloque["obligaciones"]
    assert [ob["indexacion"] is None for ob in obligaciones] == [True, False, False]
    assert all(len(obligacion["obligados"]) == 1 for obligacion in obligaciones)
    assert {
        ob["indexacion"]["id_indice_financiero_valor"] for ob in obligaciones[1:]
    } == {id_valor}
    assert [
        [
            composicion["codigo_concepto_financiero"]
            for composicion in ob["composiciones"]
        ]
        for ob in obligaciones
    ] == [
        ["CAPITAL_VENTA"],
        ["CAPITAL_VENTA", "AJUSTE_INDEXACION"],
        ["CAPITAL_VENTA", "AJUSTE_INDEXACION"],
    ]
    assert Decimal(str(data["resumen"]["total_ajuste_indexacion"])) == Decimal(
        "197287.30"
    )
    assert data["resumen"]["cantidad_obligaciones_con_indexacion"] == 2
    assert data["resumen"]["cantidad_obligaciones_proyectadas_sin_indexacion"] == 1


def test_consulta_plan_con_dos_compradores_expone_obligados_sin_duplicar(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-GET-OBL-2")
    id_persona_1 = _crear_persona_minima(db_session, codigo="PER-PPV2-GET-OBL-2-A")
    id_persona_2 = _crear_persona_minima(db_session, codigo="PER-PPV2-GET-OBL-2-B")
    _vincular_comprador_venta(db_session, id_venta=id_venta, id_persona=id_persona_1)
    _vincular_comprador_venta(db_session, id_venta=id_venta, id_persona=id_persona_2)
    db_session.execute(
        text("""
            UPDATE relacion_persona_rol
            SET porcentaje_responsabilidad = 50.00
            WHERE tipo_relacion = 'venta'
              AND id_relacion = :id_venta
              AND id_persona IN (:id_persona_1, :id_persona_2)
            """),
        {
            "id_venta": id_venta,
            "id_persona_1": id_persona_1,
            "id_persona_2": id_persona_2,
        },
    )
    result = _service(db_session).execute(
        _command(
            id_venta=id_venta,
            monto_total_plan=Decimal("1000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("1000000.00"),
                    cantidad_cuotas=1,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                    regla_redondeo="ULTIMA_CUOTA",
                    metodo_liquidacion=None,
                )
            ],
        )
    )
    assert result.success, result.errors

    response = client.get(URL_GET.format(id_venta=id_venta))

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    obligaciones = data["bloques"][0]["obligaciones"]
    assert len(obligaciones) == 1
    assert data["resumen"]["cantidad_obligaciones"] == 1
    assert Decimal(str(data["resumen"]["total_obligaciones"])) == Decimal("1000000.00")
    assert data["resumen"]["cantidad_obligados_total"] == 2
    assert data["resumen"]["cantidad_obligaciones_con_multiples_obligados"] == 1

    obligacion = obligaciones[0]
    assert len(obligacion["obligados"]) == 2
    assert {obligado["id_persona"] for obligado in obligacion["obligados"]} == {
        id_persona_1,
        id_persona_2,
    }
    assert {
        Decimal(str(obligado["porcentaje_responsabilidad"]))
        for obligado in obligacion["obligados"]
    } == {Decimal("50.00")}
    assert {
        Decimal(str(obligado["importe_responsabilidad_informativo"]))
        for obligado in obligacion["obligados"]
    } == {Decimal("500000.00")}
    assert sum(
        Decimal(str(obligado["importe_responsabilidad_informativo"]))
        for obligado in obligacion["obligados"]
    ) == Decimal(str(obligacion["importe_total"]))


def test_consulta_venta_sin_plan_devuelve_error_controlado(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-GET-NOPLAN")

    response = client.get(URL_GET.format(id_venta=id_venta))

    assert response.status_code == 404, response.text
    assert response.json()["error_code"] == "NOT_FOUND_PLAN_PAGO_V2"


def test_consulta_integral_muestra_refuerzos_internos_en_tramo_cuotas(
    db_session,
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-GET-REF-INT")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    result = _service(db_session).execute(
        _command(
            id_venta=id_venta,
            monto_total_plan=Decimal("6000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("6000000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 1, 10),
                    periodicidad="MENSUAL",
                    cuotas_refuerzo=[
                        CuotaRefuerzoInput(numero_cuota=3, etiqueta="Refuerzo cuota 3"),
                        CuotaRefuerzoInput(numero_cuota=4, etiqueta="Refuerzo cuota 4"),
                    ],
                )
            ],
        )
    )
    assert result.success, result.errors

    integral = PlanPagoVentaV2Repository(db_session).get_plan_pago_venta_v2_integral(
        id_venta
    )

    assert integral is not None
    assert len(integral["bloques"]) == 1
    bloque = integral["bloques"][0]
    assert bloque["tipo_bloque"] == "TRAMO_CUOTAS"
    assert bloque["cantidad_cuotas"] == 6
    obligaciones = bloque["obligaciones"]
    assert len(obligaciones) == 4
    assert all(
        obligacion["tipo_item_cronograma"] == "CUOTA" for obligacion in obligaciones
    )
    assert [obligacion["numero_cuota_asociada"] for obligacion in obligaciones] == [
        1,
        2,
        3,
        4,
    ]
    assert not any(
        obligacion["numero_cuota_asociada"] in {5, 6} for obligacion in obligaciones
    )
    cuota_3 = next(
        obligacion
        for obligacion in obligaciones
        if obligacion["numero_cuota_asociada"] == 3
    )
    cuota_4 = next(
        obligacion
        for obligacion in obligaciones
        if obligacion["numero_cuota_asociada"] == 4
    )
    assert cuota_3["importe_total"] == Decimal("2000000.00")
    assert cuota_4["importe_total"] == Decimal("2000000.00")
    assert "Refuerzo cuota 3" in cuota_3["etiqueta_obligacion"]
    assert "Refuerzo cuota 4" in cuota_4["etiqueta_obligacion"]
    assert sum(
        (obligacion["importe_total"] for obligacion in obligaciones), Decimal("0.00")
    ) == Decimal("6000000.00")
