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


def test_consulta_plan_expone_corridas_y_resultados_persistidos_por_obligacion(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-GET-CORRIDAS")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    id_indice = _insertar_indice_financiero_minimo(db_session, codigo="RIPTE-GET-CORRIDAS")
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
    plan = result.data["plan_pago_venta"]
    bloque = result.data["bloques"][0]
    obligaciones = result.data["obligaciones"]
    configuracion = db_session.execute(
        text("""
            SELECT id_plan_pago_venta_bloque_indexacion
            FROM plan_pago_venta_bloque_indexacion
            WHERE id_plan_pago_venta_bloque = :bloque
              AND deleted_at IS NULL
        """),
        {"bloque": bloque["id_plan_pago_venta_bloque"]},
    ).scalar_one()
    id_obligacion_repetida = obligaciones[1]["id_obligacion_financiera"]
    for codigo_concepto, importe in (
        ("CAPITAL_VENTA", Decimal("50.00")),
        ("AJUSTE_INDEXACION", Decimal("20.00")),
    ):
        db_session.execute(
            text("""
                INSERT INTO composicion_obligacion (
                    id_obligacion_financiera, id_concepto_financiero,
                    orden_composicion, estado_composicion_obligacion,
                    importe_componente, saldo_componente, moneda_componente
                )
                SELECT :obligacion, cf.id_concepto_financiero,
                       COALESCE((
                           SELECT MAX(co.orden_composicion) + 1
                           FROM composicion_obligacion co
                           WHERE co.id_obligacion_financiera = :obligacion
                             AND co.deleted_at IS NULL
                       ), 1),
                       'ACTIVA', :importe, :importe, 'ARS'
                FROM concepto_financiero cf
                WHERE cf.codigo_concepto_financiero = :codigo_concepto
                  AND cf.deleted_at IS NULL
            """),
            {
                "obligacion": id_obligacion_repetida,
                "codigo_concepto": codigo_concepto,
                "importe": importe,
            },
        )
    corrida = db_session.execute(
        text("""
            INSERT INTO corrida_indexacion_financiera (
                id_plan_pago_venta, id_plan_pago_venta_bloque,
                id_plan_pago_venta_bloque_indexacion, id_indice_financiero,
                id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte,
                origen_corrida, estado_corrida, op_id, hash_corrida,
                cantidad_analizada, cantidad_elegible, cantidad_excluida,
                importe_total_nuevo, ajuste_nuevo_total
            ) VALUES (
                :plan, :bloque, :configuracion, :indice, :valor, DATE '2026-07-10',
                DATE '2026-07-10', 'PUBLICACION_INDICE', 'PENDIENTE_APLICACION',
                '550e8400-e29b-41d4-a716-446655441100', 'a' || repeat('0', 63),
                2, 1, 1, 2000000, 100000
            ) RETURNING id_corrida_indexacion_financiera
        """), {
            "plan": plan["id_plan_pago_venta"],
            "bloque": bloque["id_plan_pago_venta_bloque"],
            "configuracion": configuracion,
            "indice": id_indice,
            "valor": id_valor,
        },
    ).scalar_one()
    for obligacion, estado, motivo, error in (
        (obligaciones[1], "ELEGIBLE", None, None),
        (obligaciones[2], "EXCLUIDA", "ESTADO_OBLIGACION_NO_ELEGIBLE", "ERROR_CONTROLADO"),
    ):
        db_session.execute(
            text("""
                INSERT INTO corrida_indexacion_financiera_detalle (
                    id_corrida_indexacion_financiera, id_obligacion_financiera,
                    version_esperada, capital_base, valor_indice_base,
                    valor_indice_aplicado, coeficiente_indexacion,
                    estado_elegibilidad, motivo_exclusion, codigo_error
                ) VALUES (
                    :corrida, :obligacion, 1, 1000000, 100, 110, 1.1,
                    :estado, :motivo, :error
                )
            """), {
                "corrida": corrida,
                "obligacion": obligacion["id_obligacion_financiera"],
                "estado": estado,
                "motivo": motivo,
                "error": error,
            },
        )
    corrida_fallida = db_session.execute(
        text("""
            INSERT INTO corrida_indexacion_financiera (
                id_plan_pago_venta, id_plan_pago_venta_bloque,
                id_plan_pago_venta_bloque_indexacion, id_indice_financiero,
                id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte,
                origen_corrida, estado_corrida, op_id, hash_corrida,
                codigo_error, etapa_error, diagnostico_tecnico
            ) VALUES (
                :plan, :bloque, :configuracion, :indice, :valor, DATE '2026-07-10',
                DATE '2026-07-10', 'REINDEXACION_MANUAL', 'FALLIDA',
                '550e8400-e29b-41d4-a716-446655441101', 'b' || repeat('0', 63),
                'VERSION_OBLIGACION_INCOMPATIBLE', 'APLICACION', 'Fallo sin detalles'
            ) RETURNING id_corrida_indexacion_financiera
        """), {
            "plan": plan["id_plan_pago_venta"],
            "bloque": bloque["id_plan_pago_venta_bloque"],
            "configuracion": configuracion,
            "indice": id_indice,
            "valor": id_valor,
        },
    ).scalar_one()
    db_session.commit()

    response = client.get(URL_GET.format(id_venta=id_venta))

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data["corridas_indexacion"]) == 2
    corrida_data = data["corridas_indexacion"][0]
    assert corrida_data["id_corrida_indexacion_financiera"] == corrida
    assert corrida_data["estado_corrida"] == "PENDIENTE_APLICACION"
    assert corrida_data["cantidad_error"] == 1
    assert Decimal(str(corrida_data["capital_analizado_total"])) == Decimal(
        "2000000.00"
    )
    assert Decimal(str(corrida_data["ajuste_total"])) == Decimal("100000.00")
    assert len(corrida_data["exclusiones"]) == 1
    assert len(corrida_data["errores"]) == 1
    corrida_fallida_data = data["corridas_indexacion"][1]
    assert corrida_fallida_data["id_corrida_indexacion_financiera"] == corrida_fallida
    assert corrida_fallida_data["cantidad_error"] == 1
    assert corrida_fallida_data["codigo_error"] == "VERSION_OBLIGACION_INCOMPATIBLE"
    assert corrida_fallida_data["etapa_error"] == "APLICACION"
    assert corrida_fallida_data["diagnostico_tecnico"] == "Fallo sin detalles"
    assert corrida_fallida_data["errores"] == []
    cuotas = data["bloques"][0]["obligaciones"]
    assert Decimal(str(cuotas[1]["capital_original"])) == Decimal("1000050.00")
    assert Decimal(str(cuotas[1]["ajuste_indexacion"])) == Decimal("98663.65")
    assert cuotas[1]["estado_indexacion_presentacion"] == "CON_INDICE_APLICADO"
    assert cuotas[1]["origen_indexacion"] == "AL_NACIMIENTO"
    assert cuotas[2]["estado_indexacion_presentacion"] == "CON_ERROR"
    assert cuotas[2]["corrida_relacionada"]["id_corrida_indexacion_financiera"] == corrida


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
