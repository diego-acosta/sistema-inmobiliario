from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    GeneratePlanPagoVentaV2PorBloquesCommand,
    PlanPagoVentaBloqueInput,
)
from app.application.comercial.services.build_plan_pago_venta_v2_por_bloques_preview_service import (
    BuildPlanPagoVentaV2PorBloquesPreviewService,
)
from app.application.common.commands import CommandContext

URL = "/api/v1/ventas/{id_venta}/plan-pago-v2/preview"


def _command(
    *,
    monto_total_plan: Decimal = Decimal("10000000.00"),
    bloques: list[PlanPagoVentaBloqueInput] | None = None,
) -> GeneratePlanPagoVentaV2PorBloquesCommand:
    return GeneratePlanPagoVentaV2PorBloquesCommand(
        context=CommandContext(),
        id_venta=1,
        tipo_pago="FINANCIADO",
        monto_total_plan=monto_total_plan,
        moneda="ARS",
        bloques=(
            bloques
            if bloques is not None
            else [
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                )
            ]
        ),
    )


def _count(db_session, table: str) -> int:
    return db_session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


def _payload_tramo_por_capital_total() -> dict:
    return {
        "tipo_pago": "FINANCIADO",
        "monto_total_plan": 10000000.00,
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "importe_total_bloque": 10000000.00,
                "cantidad_cuotas": 6,
                "fecha_primer_vencimiento": "2026-06-10",
                "periodicidad": "MENSUAL",
            }
        ],
    }


URL_SIN_VENTA = "/api/v1/ventas/plan-pago-v2/preview"


def _payload_contado() -> dict:
    return {
        "tipo_pago": "CONTADO",
        "monto_total_plan": "10000000.00",
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "CONTADO",
                "importe_total_bloque": "10000000.00",
                "fecha_vencimiento": "2026-07-10",
            }
        ],
        "observaciones": None,
    }


def _payload_financiado_sin_interes() -> dict:
    return {
        "tipo_pago": "FINANCIADO",
        "monto_total_plan": "10000000.00",
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "ANTICIPO",
                "importe_total_bloque": "3000000.00",
                "fecha_vencimiento": "2026-07-10",
            },
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "importe_total_bloque": "7000000.00",
                "cantidad_cuotas": 12,
                "fecha_primer_vencimiento": "2026-08-10",
                "periodicidad": "MENSUAL",
                "metodo_liquidacion": "SIN_INTERES",
            },
        ],
        "observaciones": None,
    }


def _preview_side_effect_tables(db_session) -> list[str]:
    tables = [
        "venta",
        "plan_pago_venta",
        "plan_pago_venta_bloque",
        "relacion_generadora",
        "obligacion_financiera",
        "composicion_obligacion",
        "obligacion_obligado",
    ]
    if db_session.execute(text("SELECT to_regclass('public.outbox_event')")).scalar():
        tables.append("outbox_event")
    return tables


def _counts(db_session, tables: list[str]) -> dict[str, int]:
    return {table: _count(db_session, table) for table in tables}


def test_endpoint_preview_sin_id_venta_contado_no_devuelve_id_venta_ni_persiste(
    db_session, client
) -> None:
    tables = _preview_side_effect_tables(db_session)
    before = _counts(db_session, tables)

    response = client.post(URL_SIN_VENTA, json=_payload_contado())

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert "id_venta" not in data
    assert data["metodo_plan_pago"] == "PLAN_POR_BLOQUES"
    assert data["tipo_pago"] == "CONTADO"
    assert data["total_calculado"] == "10000000.00"
    assert data["total_con_interes"] == "10000000.00"
    assert len(data["bloques"]) == 1
    assert len(data["obligaciones"]) == 1
    assert data["obligaciones"][0]["tipo_item_cronograma"] == "SALDO"
    assert data["obligaciones"][0]["fecha_vencimiento"] == "2026-07-10"
    assert data["obligaciones"][0]["importe_total"] == "10000000.00"
    assert _counts(db_session, tables) == before


def test_endpoint_preview_sin_id_venta_financiado_sin_interes_devuelve_cuotas(
    db_session, client
) -> None:
    tables = _preview_side_effect_tables(db_session)
    before = _counts(db_session, tables)

    response = client.post(URL_SIN_VENTA, json=_payload_financiado_sin_interes())

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert "id_venta" not in data
    assert data["tipo_pago"] == "FINANCIADO"
    assert data["total_calculado"] == "10000000.00"
    assert len(data["bloques"]) == 2
    assert len(data["obligaciones"]) == 13
    assert data["obligaciones"][0]["tipo_item_cronograma"] == "ANTICIPO"
    assert data["obligaciones"][0]["importe_total"] == "3000000.00"
    cuotas = data["obligaciones"][1:]
    assert all(cuota["tipo_item_cronograma"] == "CUOTA" for cuota in cuotas)
    assert sum(Decimal(cuota["importe_total"]) for cuota in cuotas) == Decimal(
        "7000000.00"
    )
    assert _counts(db_session, tables) == before


def test_endpoint_preview_sin_id_venta_interes_directo_devuelve_total_raiz(
    db_session, client
) -> None:
    tables = _preview_side_effect_tables(db_session)
    before = _counts(db_session, tables)
    payload = _payload_tramo_por_capital_total()
    payload["monto_total_plan"] = "1000000.00"
    payload["bloques"][0].update(
        {
            "importe_total_bloque": "1000000.00",
            "cantidad_cuotas": 12,
            "metodo_liquidacion": "INTERES_DIRECTO",
            "tasa_interes_directo_periodica": "0.02",
            "cantidad_periodos": 12,
            "base_calculo_interes": "CAPITAL_INICIAL_BLOQUE",
        }
    )

    response = client.post(URL_SIN_VENTA, json=payload)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert "id_venta" not in data
    assert data["total_calculado"] == "1000000.00"
    assert data["total_con_interes"] == "1240000.00"
    assert len(data["obligaciones"]) == 12
    assert sum(
        Decimal(obligacion["importe_total"])
        for obligacion in data["obligaciones"]
    ) == Decimal("1240000.00")
    assert _counts(db_session, tables) == before


def test_endpoint_preview_sin_id_venta_indexacion_lee_indices_readonly_y_no_persiste(
    db_session, client
) -> None:
    id_indice = _crear_indice_preview(db_session, "IPC_PREVIEW_SIN_VENTA")
    id_valor = _crear_valor_indice_preview(
        db_session, id_indice, "2026-08-10", "110.00000000"
    )
    tables = _preview_side_effect_tables(db_session)
    before = _counts(db_session, tables)
    payload = _payload_tramo_por_capital_total()
    payload["monto_total_plan"] = "1000.00"
    payload["bloques"][0].update(
        {
            "importe_total_bloque": "1000.00",
            "cantidad_cuotas": 1,
            "fecha_primer_vencimiento": "2026-08-10",
            "metodo_liquidacion": "INDEXACION",
            "id_indice_financiero": id_indice,
            "fecha_base_indice": "2026-05-01",
            "valor_base_indice": "100.00000000",
            "modo_indexacion": "POR_COEFICIENTE",
            "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
            "tipo_generacion_indexada": "DEFINITIVA",
            "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
            "conserva_capital_original": True,
            "genera_ajuste_por_diferencia": True,
        }
    )

    response = client.post(URL_SIN_VENTA, json=payload)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert "id_venta" not in data
    assert data["total_calculado"] == "1000.00"
    assert data["total_ajuste_indexacion"] == "100.00"
    assert data["total_con_indexacion"] == "1100.00"
    obligacion = data["obligaciones"][0]
    assert obligacion["estado_preview_indexacion"] == "CON_INDICE_APLICADO"
    assert obligacion["id_indice_financiero"] == id_indice
    assert obligacion["id_indice_financiero_valor"] == id_valor
    assert obligacion["coeficiente_indexacion"] == "1.10000000"
    assert _counts(db_session, tables) == before


def test_endpoint_preview_sin_id_venta_cuotas_refuerzo_internas(
    client,
) -> None:
    payload = _payload_tramo_por_capital_total()
    payload["monto_total_plan"] = "24000000.00"
    payload["bloques"][0].update(
        {
            "importe_total_bloque": "24000000.00",
            "cantidad_cuotas": 24,
            "fecha_primer_vencimiento": "2026-01-10",
            "metodo_liquidacion": "SIN_INTERES",
            "cuotas_refuerzo": [
                {
                    "numero_cuota": 6,
                    "etiqueta": "Refuerzo cuota 6",
                    "unidades_refuerzo": "1.00",
                },
                {
                    "numero_cuota": 12,
                    "etiqueta": "Refuerzo cuota 12",
                    "unidades_refuerzo": "1.00",
                },
            ],
        }
    )

    response = client.post(URL_SIN_VENTA, json=payload)

    assert response.status_code == 200, response.text
    obligaciones = response.json()["data"]["obligaciones"]
    assert len(obligaciones) == 22
    assert all(ob["tipo_item_cronograma"] == "CUOTA" for ob in obligaciones)
    assert obligaciones[5]["numero_cuota_asociada"] == 6
    assert "incluye Refuerzo cuota 6" in obligaciones[5]["etiqueta_obligacion"]
    assert obligaciones[5]["importe_total"] == "2000000.00"
    assert obligaciones[11]["numero_cuota_asociada"] == 12
    assert "incluye Refuerzo cuota 12" in obligaciones[11]["etiqueta_obligacion"]
    assert obligaciones[11]["importe_total"] == "2000000.00"


def test_endpoint_preview_sin_id_venta_payload_invalido_devuelve_error(
    client,
) -> None:
    payload = _payload_financiado_sin_interes()
    payload["monto_total_plan"] = "9999999.99"

    response = client.post(URL_SIN_VENTA, json=payload)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["details"]["errors"] == ["SUMA_BLOQUES_INVALIDA"]


def test_endpoint_preview_con_id_venta_sigue_devolviendo_id_venta(client) -> None:
    response = client.post(URL.format(id_venta=1), json=_payload_contado())

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id_venta"] == 1
    assert data["total_calculado"] == "10000000.00"

def test_preview_tramo_por_capital_total_ajusta_ultima_cuota_y_suma_exacta() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(_command())

    assert result.success, result.errors
    obligaciones = result.data["obligaciones"]
    importes = [obligacion.importe_total for obligacion in obligaciones]
    assert len(importes) == 6
    assert importes[:5] == [Decimal("1666666.67")] * 5
    assert importes[-1] == Decimal("1666666.65")
    assert sum(importes, Decimal("0.00")) == Decimal("10000000.00")
    assert result.data["total_calculado"] == Decimal("10000000.00")
    assert result.data["diferencia"] == Decimal("0.00")


def test_preview_no_persiste_plan_bloques_ni_obligaciones(db_session) -> None:
    before = {
        "plan_pago_venta": _count(db_session, "plan_pago_venta"),
        "plan_pago_venta_bloque": _count(db_session, "plan_pago_venta_bloque"),
        "obligacion_financiera": _count(db_session, "obligacion_financiera"),
    }

    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(_command())

    assert result.success, result.errors
    after = {
        "plan_pago_venta": _count(db_session, "plan_pago_venta"),
        "plan_pago_venta_bloque": _count(db_session, "plan_pago_venta_bloque"),
        "obligacion_financiera": _count(db_session, "obligacion_financiera"),
    }
    assert after == before


def test_preview_contrato_legacy_por_importe_cuota_sigue_funcionando() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            monto_total_plan=Decimal("3000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_cuota=Decimal("500000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                )
            ],
        )
    )

    assert result.success, result.errors
    obligaciones = result.data["obligaciones"]
    assert [obligacion.importe_total for obligacion in obligaciones] == [
        Decimal("500000.00")
    ] * 6
    assert result.data["total_calculado"] == Decimal("3000000.00")


def test_preview_tramo_prioriza_importe_total_bloque_si_importe_cuota_viene_presente() -> (
    None
):
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            monto_total_plan=Decimal("10000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    importe_cuota=Decimal("1.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                )
            ],
        )
    )

    assert result.success, result.errors
    bloque = result.data["bloques"][0]
    obligaciones = result.data["obligaciones"]
    assert bloque.importe_total_bloque == Decimal("10000000.00")
    assert bloque.importe_cuota == Decimal("1666666.67")
    assert [obligacion.importe_total for obligacion in obligaciones[:5]] == [
        Decimal("1666666.67")
    ] * 5
    assert obligaciones[-1].importe_total == Decimal("1666666.65")
    assert sum(
        (obligacion.importe_total for obligacion in obligaciones), Decimal("0.00")
    ) == Decimal("10000000.00")


def test_preview_valida_suma_general_con_tramo_por_capital_total() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(monto_total_plan=Decimal("10000000.01"))
    )

    assert not result.success
    assert result.errors == ["SUMA_BLOQUES_INVALIDA"]


def test_endpoint_preview_tramo_por_capital_total_devuelve_ultima_cuota_ajustada(
    client,
) -> None:
    response = client.post(
        URL.format(id_venta=1), json=_payload_tramo_por_capital_total()
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["metodo_plan_pago"] == "PLAN_POR_BLOQUES"
    assert data["total_calculado"] == "10000000.00"
    assert data["diferencia"] == "0.00"
    assert len(data["bloques"]) == 1
    assert data["bloques"][0]["importe_total_bloque"] == "10000000.00"
    assert data["bloques"][0]["importe_cuota"] == "1666666.67"

    importes = [obligacion["importe_total"] for obligacion in data["obligaciones"]]
    assert len(importes) == 6
    assert importes[:5] == ["1666666.67"] * 5
    assert importes[-1] == "1666666.65"


def test_endpoint_preview_no_persiste_filas(db_session, client) -> None:
    tables = [
        "plan_pago_venta",
        "plan_pago_venta_bloque",
        "generacion_cronograma_financiero",
        "obligacion_financiera",
        "composicion_obligacion",
        "obligacion_obligado",
    ]
    before = {table: _count(db_session, table) for table in tables}

    response = client.post(
        URL.format(id_venta=1), json=_payload_tramo_por_capital_total()
    )

    assert response.status_code == 200, response.text
    after = {table: _count(db_session, table) for table in tables}
    assert after == before


def test_endpoint_preview_legacy_por_importe_cuota_sigue_funcionando(client) -> None:
    payload = {
        "tipo_pago": "FINANCIADO",
        "monto_total_plan": 3000000.00,
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "importe_cuota": 500000.00,
                "cantidad_cuotas": 6,
                "fecha_primer_vencimiento": "2026-06-10",
                "periodicidad": "MENSUAL",
            }
        ],
    }

    response = client.post(URL.format(id_venta=1), json=payload)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total_calculado"] == "3000000.00"
    assert [obligacion["importe_total"] for obligacion in data["obligaciones"]] == [
        "500000.00"
    ] * 6


def test_endpoint_preview_rechaza_campos_extra_internos(client) -> None:
    payload = _payload_tramo_por_capital_total()
    payload["id_plan_pago_venta"] = 1
    payload["bloques"][0]["id_plan_pago_venta_bloque"] = 1
    payload["bloques"][0]["clave_bloque"] = "CLIENTE:NO:DEBE:ENVIAR"

    response = client.post(URL.format(id_venta=1), json=payload)

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    locations = {tuple(error["loc"]) for error in errors}
    assert ("body", "id_plan_pago_venta") in locations
    assert ("body", "bloques", 0, "id_plan_pago_venta_bloque") in locations
    assert ("body", "bloques", 0, "clave_bloque") in locations


def test_preview_interes_directo_requiere_tres_parametros() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                    metodo_liquidacion="INTERES_DIRECTO",
                )
            ]
        )
    )
    assert not result.success
    assert result.errors == ["VALIDATION_ERROR"]


def test_endpoint_preview_interes_directo_devuelve_campos_nuevos(client) -> None:
    payload = _payload_tramo_por_capital_total()
    payload["bloques"][0].update(
        {
            "metodo_liquidacion": "INTERES_DIRECTO",
            "tasa_interes_directo_periodica": 0.02,
            "cantidad_periodos": 6,
            "base_calculo_interes": "capital_inicial_bloque",
        }
    )
    response = client.post(URL.format(id_venta=1), json=payload)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total_con_interes"] == "11200000.00"
    bloque = data["bloques"][0]
    assert bloque["metodo_liquidacion"] == "INTERES_DIRECTO"
    assert bloque["tasa_interes_directo_periodica"] == "0.02"
    assert bloque["cantidad_periodos"] == 6
    assert bloque["base_calculo_interes"] == "CAPITAL_INICIAL_BLOQUE"


def test_preview_interes_directo_calcula_total_con_interes_y_ajuste_ultima() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            monto_total_plan=Decimal("1000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("1000000.00"),
                    cantidad_cuotas=12,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                    metodo_liquidacion="INTERES_DIRECTO",
                    tasa_interes_directo_periodica=Decimal("0.02"),
                    cantidad_periodos=12,
                    base_calculo_interes="CAPITAL_INICIAL_BLOQUE",
                )
            ],
        )
    )
    assert result.success, result.errors
    assert result.data["total_calculado"] == Decimal("1000000.00")
    assert result.data["total_con_interes"] == Decimal("1240000.00")
    cuotas = [ob.importe_total for ob in result.data["obligaciones"]]
    assert cuotas[0] == Decimal("103333.33")
    assert cuotas[-1] == Decimal("103333.37")


def test_preview_interes_directo_base_calculo_invalida_devuelve_validation_error() -> (
    None
):
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                    metodo_liquidacion="INTERES_DIRECTO",
                    tasa_interes_directo_periodica=Decimal("0.02"),
                    cantidad_periodos=6,
                    base_calculo_interes="SALDO",
                )
            ]
        )
    )
    assert not result.success
    assert result.errors == ["VALIDATION_ERROR"]


def _indexacion_kwargs() -> dict:
    return {
        "metodo_liquidacion": "indexacion",
        "id_indice_financiero": 1,
        "fecha_base_indice": date(2026, 5, 1),
        "valor_base_indice": Decimal("100.12345678"),
        "modo_indexacion": "por_coeficiente",
        "base_calculo_indexacion": "capital_inicial_bloque",
        "tipo_generacion_indexada": "definitiva",
        "politica_valor_no_disponible": "error_si_no_existe",
        "conserva_capital_original": True,
        "genera_ajuste_por_diferencia": True,
    }


def _tramo_indexado(**overrides) -> PlanPagoVentaBloqueInput:
    values = {
        "tipo_bloque": "TRAMO_CUOTAS",
        "importe_total_bloque": Decimal("10000000.00"),
        "cantidad_cuotas": 6,
        "fecha_primer_vencimiento": date(2026, 6, 10),
        "periodicidad": "MENSUAL",
        **_indexacion_kwargs(),
    }
    values.update(overrides)
    return PlanPagoVentaBloqueInput(**values)


def test_preview_acepta_indexacion_valida_y_propaga_campos_en_bloque() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(bloques=[_tramo_indexado()])
    )

    assert result.success, result.errors
    bloque = result.data["bloques"][0]
    assert bloque.input.metodo_liquidacion == "INDEXACION"
    assert bloque.input.id_indice_financiero == 1
    assert bloque.input.fecha_base_indice == date(2026, 5, 1)
    assert bloque.input.valor_base_indice == Decimal("100.12345678")
    assert bloque.input.modo_indexacion == "POR_COEFICIENTE"
    assert bloque.input.base_calculo_indexacion == "CAPITAL_INICIAL_BLOQUE"
    assert bloque.input.tipo_generacion_indexada == "DEFINITIVA"
    assert bloque.input.politica_valor_no_disponible == "ERROR_SI_NO_EXISTE"
    assert bloque.input.conserva_capital_original is True
    assert bloque.input.genera_ajuste_por_diferencia is True
    assert result.data["total_calculado"] == Decimal("10000000.00")
    assert result.data["total_con_interes"] == Decimal("10000000.00")
    assert sum(
        (obligacion.importe_total for obligacion in result.data["obligaciones"]),
        Decimal("0.00"),
    ) == Decimal("10000000.00")


def test_endpoint_preview_indexacion_valida_devuelve_campos_nuevos(client) -> None:
    payload = _payload_tramo_por_capital_total()
    payload["bloques"][0].update(
        {
            "metodo_liquidacion": "indexacion",
            "id_indice_financiero": 999999999,
            "fecha_base_indice": "2026-05-01",
            "valor_base_indice": "100.12345678",
            "modo_indexacion": "por_coeficiente",
            "base_calculo_indexacion": "capital_inicial_bloque",
            "tipo_generacion_indexada": "definitiva",
            "politica_valor_no_disponible": "error_si_no_existe",
            "conserva_capital_original": True,
            "genera_ajuste_por_diferencia": True,
        }
    )

    response = client.post(URL.format(id_venta=1), json=payload)

    assert response.status_code == 200, response.text
    bloque = response.json()["data"]["bloques"][0]
    assert bloque["metodo_liquidacion"] == "INDEXACION"
    assert bloque["id_indice_financiero"] == 999999999
    assert bloque["fecha_base_indice"] == "2026-05-01"
    assert bloque["valor_base_indice"] == "100.12345678"
    assert bloque["modo_indexacion"] == "POR_COEFICIENTE"
    assert bloque["base_calculo_indexacion"] == "CAPITAL_INICIAL_BLOQUE"
    assert bloque["tipo_generacion_indexada"] == "DEFINITIVA"
    assert bloque["politica_valor_no_disponible"] == "ERROR_SI_NO_EXISTE"
    assert bloque["conserva_capital_original"] is True
    assert bloque["genera_ajuste_por_diferencia"] is True
    data = response.json()["data"]
    assert data["total_calculado"] == "10000000.00"
    assert data["total_con_indexacion"] == "10000000.00"
    assert data["total_ajuste_indexacion"] == "0.00"
    assert bloque["total_con_indexacion"] == "10000000.00"
    assert bloque["total_ajuste_indexacion"] == "0.00"
    assert bloque["cantidad_cuotas_con_indice"] == 0
    assert bloque["cantidad_cuotas_proyectadas_sin_indice"] == 6
    assert {
        obligacion["estado_preview_indexacion"] for obligacion in data["obligaciones"]
    } == {"PROYECTADA_SIN_INDICE"}


def _crear_indice_preview(db_session, codigo: str) -> int:
    row = db_session.execute(
        text("""
            INSERT INTO indice_financiero (
                codigo_indice_financiero,
                nombre_indice_financiero,
                tipo_indice,
                unidad_medida,
                frecuencia_publicacion,
                estado_indice_financiero
            )
            VALUES (
                :codigo,
                :nombre,
                'IPC',
                'PUNTOS',
                'MENSUAL',
                'ACTIVO'
            )
            RETURNING id_indice_financiero
            """),
        {"codigo": codigo, "nombre": f"Indice {codigo}"},
    ).one()
    return row[0]


def _crear_valor_indice_preview(
    db_session,
    id_indice_financiero: int,
    fecha_valor: str,
    valor_indice: str,
) -> int:
    row = db_session.execute(
        text("""
            INSERT INTO indice_financiero_valor (
                id_indice_financiero,
                fecha_valor,
                valor_indice,
                fecha_publicacion,
                fuente_valor,
                estado_valor_indice
            )
            VALUES (
                :id_indice_financiero,
                :fecha_valor,
                :valor_indice,
                :fecha_valor,
                'TEST',
                'PUBLICADO'
            )
            RETURNING id_indice_financiero_valor
            """),
        {
            "id_indice_financiero": id_indice_financiero,
            "fecha_valor": fecha_valor,
            "valor_indice": valor_indice,
        },
    ).one()
    return row[0]


def test_endpoint_preview_indexacion_calcula_cuotas_con_indice_disponible(
    db_session, client
) -> None:
    id_indice = _crear_indice_preview(db_session, "IPC_PREVIEW_ALL")
    valores = [
        _crear_valor_indice_preview(
            db_session, id_indice, "2026-06-10", "110.00000000"
        ),
        _crear_valor_indice_preview(
            db_session, id_indice, "2026-07-10", "120.00000000"
        ),
        _crear_valor_indice_preview(
            db_session, id_indice, "2026-08-10", "130.00000000"
        ),
    ]
    payload = _payload_tramo_por_capital_total()
    payload["monto_total_plan"] = "3000.00"
    payload["bloques"][0].update(
        {
            "importe_total_bloque": "3000.00",
            "cantidad_cuotas": 3,
            "metodo_liquidacion": "INDEXACION",
            "id_indice_financiero": id_indice,
            "fecha_base_indice": "2026-05-01",
            "valor_base_indice": "100.00000000",
            "modo_indexacion": "POR_COEFICIENTE",
            "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
            "tipo_generacion_indexada": "DEFINITIVA",
            "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
            "conserva_capital_original": True,
            "genera_ajuste_por_diferencia": True,
        }
    )

    response = client.post(URL.format(id_venta=1), json=payload)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total_calculado"] == "3000.00"
    assert data["total_con_interes"] == "3000.00"
    assert data["total_ajuste_indexacion"] == "600.00"
    assert data["total_con_indexacion"] == "3600.00"
    bloque = data["bloques"][0]
    assert bloque["total_ajuste_indexacion"] == "600.00"
    assert bloque["total_con_indexacion"] == "3600.00"
    assert bloque["cantidad_cuotas_con_indice"] == 3
    assert bloque["cantidad_cuotas_proyectadas_sin_indice"] == 0
    obligaciones = data["obligaciones"]
    assert [obligacion["capital_cuota"] for obligacion in obligaciones] == [
        "1000.00",
        "1000.00",
        "1000.00",
    ]
    assert [obligacion["ajuste_indexacion_cuota"] for obligacion in obligaciones] == [
        "100.00",
        "200.00",
        "300.00",
    ]
    assert [obligacion["importe_total"] for obligacion in obligaciones] == [
        "1100.00",
        "1200.00",
        "1300.00",
    ]
    assert [
        obligacion["id_indice_financiero_valor"] for obligacion in obligaciones
    ] == valores


def test_preview_rechaza_indexacion_si_tipo_bloque_no_es_tramo_cuotas() -> None:
    bloque = PlanPagoVentaBloqueInput(
        tipo_bloque="ANTICIPO",
        importe_total_bloque=Decimal("10000000.00"),
        fecha_vencimiento=date(2026, 6, 10),
        **_indexacion_kwargs(),
    )

    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(bloques=[bloque])
    )

    assert not result.success
    assert result.errors == ["VALIDATION_ERROR"]


def test_preview_rechaza_indexacion_si_faltan_parametros_obligatorios() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(bloques=[_tramo_indexado(id_indice_financiero=None)])
    )

    assert not result.success
    assert result.errors == ["VALIDATION_ERROR"]


def test_preview_rechaza_indexacion_con_valores_invalidos() -> None:
    invalid_overrides = [
        {"modo_indexacion": "POR_INDICE"},
        {"base_calculo_indexacion": "SALDO"},
        {"tipo_generacion_indexada": "PROVISORIA"},
        {"politica_valor_no_disponible": "USAR_ULTIMO"},
        {"valor_base_indice": Decimal("0.00000000")},
        {"id_indice_financiero": 0},
        {"tasa_interes_directo_periodica": Decimal("0.02")},
        {"conserva_capital_original": False},
        {"genera_ajuste_por_diferencia": False},
    ]

    for overrides in invalid_overrides:
        result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
            _command(bloques=[_tramo_indexado(**overrides)])
        )
        assert not result.success, overrides
        assert result.errors == ["VALIDATION_ERROR"]


def test_preview_rechaza_interes_directo_con_configuracion_indexacion() -> None:
    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                    metodo_liquidacion="INTERES_DIRECTO",
                    tasa_interes_directo_periodica=Decimal("0.02"),
                    cantidad_periodos=6,
                    base_calculo_interes="CAPITAL_INICIAL_BLOQUE",
                    id_indice_financiero=1,
                )
            ]
        )
    )

    assert not result.success
    assert result.errors == ["VALIDATION_ERROR"]


class _IndicePreviewFake:
    def __init__(self, valores: dict[date, dict]) -> None:
        self.valores = valores

    def get_valor_publicado_por_id_y_fecha(
        self, id_indice_financiero: int, fecha_objetivo: date
    ) -> dict | None:
        fechas = [fecha for fecha in self.valores if fecha <= fecha_objetivo]
        if not fechas:
            return None
        return self.valores[max(fechas)]


def _valor_indice(
    *,
    id_indice_financiero: int = 1,
    id_indice_financiero_valor: int,
    fecha_valor: date,
    valor_indice: str,
) -> dict:
    return {
        "id_indice_financiero": id_indice_financiero,
        "codigo_indice_financiero": "IPC_TEST",
        "nombre_indice_financiero": "Indice test",
        "id_indice_financiero_valor": id_indice_financiero_valor,
        "fecha_valor": fecha_valor,
        "valor_indice": Decimal(valor_indice),
        "fecha_publicacion": fecha_valor,
        "fuente_valor": "TEST",
    }


def test_preview_indexacion_calcula_todas_las_cuotas_con_indice_disponible() -> None:
    bloque = _tramo_indexado(
        importe_total_bloque=Decimal("3000.00"),
        cantidad_cuotas=3,
        fecha_primer_vencimiento=date(2026, 6, 10),
        valor_base_indice=Decimal("100.00000000"),
    )
    query = _IndicePreviewFake(
        {
            date(2026, 6, 10): _valor_indice(
                id_indice_financiero_valor=10,
                fecha_valor=date(2026, 6, 10),
                valor_indice="110.00000000",
            ),
            date(2026, 7, 10): _valor_indice(
                id_indice_financiero_valor=11,
                fecha_valor=date(2026, 7, 10),
                valor_indice="120.00000000",
            ),
            date(2026, 8, 10): _valor_indice(
                id_indice_financiero_valor=12,
                fecha_valor=date(2026, 8, 10),
                valor_indice="130.00000000",
            ),
        }
    )

    result = BuildPlanPagoVentaV2PorBloquesPreviewService(query).execute(
        _command(monto_total_plan=Decimal("3000.00"), bloques=[bloque])
    )

    assert result.success, result.errors
    assert result.data["total_calculado"] == Decimal("3000.00")
    assert result.data["total_con_interes"] == Decimal("3000.00")
    assert result.data["total_ajuste_indexacion"] == Decimal("600.00")
    assert result.data["total_con_indexacion"] == Decimal("3600.00")
    preview_bloque = result.data["bloques"][0]
    assert preview_bloque.total_ajuste_indexacion == Decimal("600.00")
    assert preview_bloque.total_con_indexacion == Decimal("3600.00")
    assert preview_bloque.cantidad_cuotas_con_indice == 3
    assert preview_bloque.cantidad_cuotas_proyectadas_sin_indice == 0
    obligaciones = result.data["obligaciones"]
    assert [ob.capital_cuota for ob in obligaciones] == [Decimal("1000.00")] * 3
    assert [ob.ajuste_indexacion_cuota for ob in obligaciones] == [
        Decimal("100.00"),
        Decimal("200.00"),
        Decimal("300.00"),
    ]
    assert [ob.importe_total for ob in obligaciones] == [
        Decimal("1100.00"),
        Decimal("1200.00"),
        Decimal("1300.00"),
    ]
    assert all(
        ob.estado_preview_indexacion == "CON_INDICE_APLICADO" for ob in obligaciones
    )
    assert obligaciones[0].id_indice_financiero_valor == 10
    assert obligaciones[0].fecha_valor_indice == date(2026, 6, 10)
    assert obligaciones[0].valor_base_indice == Decimal("100.00000000")
    assert obligaciones[0].valor_aplicado_indice == Decimal("110.00000000")
    assert obligaciones[0].coeficiente_indexacion == Decimal("1.10000000")


def test_preview_indexacion_representa_cuotas_mixtas_sin_inventar_indice() -> None:
    bloque = _tramo_indexado(
        importe_total_bloque=Decimal("3000.00"),
        cantidad_cuotas=3,
        fecha_primer_vencimiento=date(2026, 6, 10),
        valor_base_indice=Decimal("100.00000000"),
    )
    query = _IndicePreviewFake(
        {
            date(2026, 7, 10): _valor_indice(
                id_indice_financiero_valor=20,
                fecha_valor=date(2026, 7, 10),
                valor_indice="125.00000000",
            )
        }
    )

    result = BuildPlanPagoVentaV2PorBloquesPreviewService(query).execute(
        _command(monto_total_plan=Decimal("3000.00"), bloques=[bloque])
    )

    assert result.success, result.errors
    obligaciones = result.data["obligaciones"]
    assert obligaciones[0].estado_preview_indexacion == "PROYECTADA_SIN_INDICE"
    assert obligaciones[0].importe_total == Decimal("1000.00")
    assert obligaciones[0].id_indice_financiero_valor is None
    assert obligaciones[0].valor_aplicado_indice is None
    assert obligaciones[0].ajuste_indexacion_cuota is None
    assert [ob.estado_preview_indexacion for ob in obligaciones[1:]] == [
        "CON_INDICE_APLICADO",
        "CON_INDICE_APLICADO",
    ]
    assert [ob.id_indice_financiero_valor for ob in obligaciones[1:]] == [20, 20]
    assert [ob.ajuste_indexacion_cuota for ob in obligaciones[1:]] == [
        Decimal("250.00"),
        Decimal("250.00"),
    ]
    assert result.data["total_ajuste_indexacion"] == Decimal("500.00")
    assert result.data["total_con_indexacion"] == Decimal("3500.00")
    assert result.data["bloques"][0].cantidad_cuotas_con_indice == 2
    assert result.data["bloques"][0].cantidad_cuotas_proyectadas_sin_indice == 1


def test_preview_plan_mixto_interes_directo_e_indexacion_en_bloques_distintos() -> None:
    bloque_interes = PlanPagoVentaBloqueInput(
        tipo_bloque="TRAMO_CUOTAS",
        importe_total_bloque=Decimal("1000.00"),
        cantidad_cuotas=2,
        fecha_primer_vencimiento=date(2026, 6, 10),
        periodicidad="MENSUAL",
        metodo_liquidacion="INTERES_DIRECTO",
        tasa_interes_directo_periodica=Decimal("0.10"),
        cantidad_periodos=2,
        base_calculo_interes="CAPITAL_INICIAL_BLOQUE",
    )
    bloque_indexacion = _tramo_indexado(
        importe_total_bloque=Decimal("3000.00"),
        cantidad_cuotas=3,
        fecha_primer_vencimiento=date(2026, 8, 10),
        valor_base_indice=Decimal("100.00000000"),
    )
    query = _IndicePreviewFake(
        {
            date(2026, 8, 10): _valor_indice(
                id_indice_financiero_valor=30,
                fecha_valor=date(2026, 8, 10),
                valor_indice="110.00000000",
            ),
            date(2026, 9, 10): _valor_indice(
                id_indice_financiero_valor=31,
                fecha_valor=date(2026, 9, 10),
                valor_indice="120.00000000",
            ),
            date(2026, 10, 10): _valor_indice(
                id_indice_financiero_valor=32,
                fecha_valor=date(2026, 10, 10),
                valor_indice="130.00000000",
            ),
        }
    )

    result = BuildPlanPagoVentaV2PorBloquesPreviewService(query).execute(
        _command(
            monto_total_plan=Decimal("4000.00"),
            bloques=[bloque_interes, bloque_indexacion],
        )
    )

    assert result.success, result.errors
    bloques = result.data["bloques"]
    assert [bloque.input.metodo_liquidacion for bloque in bloques] == [
        "INTERES_DIRECTO",
        "INDEXACION",
    ]
    assert bloques[0].input.id_indice_financiero is None
    assert bloques[0].input.valor_base_indice is None
    assert bloques[1].input.tasa_interes_directo_periodica is None
    assert bloques[1].input.cantidad_periodos is None
    assert bloques[1].input.base_calculo_interes is None
    obligaciones = result.data["obligaciones"]
    suma_obligaciones = sum(
        (obligacion.importe_total for obligacion in obligaciones), Decimal("0.00")
    )
    assert result.data["total_calculado"] == Decimal("4000.00")
    assert result.data["total_con_interes"] == Decimal("4200.00")
    assert result.data["total_ajuste_indexacion"] == Decimal("600.00")
    assert result.data["total_con_indexacion"] == suma_obligaciones
    assert result.data["total_con_indexacion"] == Decimal("4800.00")
    assert [ob.importe_total for ob in obligaciones[:2]] == [
        Decimal("600.00"),
        Decimal("600.00"),
    ]
    assert [ob.ajuste_indexacion_cuota for ob in obligaciones[:2]] == [None, None]
    assert [ob.ajuste_indexacion_cuota for ob in obligaciones[2:]] == [
        Decimal("100.00"),
        Decimal("200.00"),
        Decimal("300.00"),
    ]


def test_preview_indexacion_sin_valores_devuelve_cuotas_proyectadas_sin_indice() -> (
    None
):
    bloque = _tramo_indexado(
        importe_total_bloque=Decimal("3000.00"),
        cantidad_cuotas=3,
        fecha_primer_vencimiento=date(2026, 6, 10),
        valor_base_indice=Decimal("100.00000000"),
    )

    result = BuildPlanPagoVentaV2PorBloquesPreviewService(
        _IndicePreviewFake({})
    ).execute(_command(monto_total_plan=Decimal("3000.00"), bloques=[bloque]))

    assert result.success, result.errors
    obligaciones = result.data["obligaciones"]
    assert [ob.estado_preview_indexacion for ob in obligaciones] == [
        "PROYECTADA_SIN_INDICE"
    ] * 3
    assert [ob.importe_total for ob in obligaciones] == [Decimal("1000.00")] * 3
    assert all(ob.ajuste_indexacion_cuota is None for ob in obligaciones)
    assert all(ob.valor_aplicado_indice is None for ob in obligaciones)
    assert result.data["total_ajuste_indexacion"] == Decimal("0.00")
    assert result.data["total_con_indexacion"] == Decimal("3000.00")
    assert result.data["bloques"][0].cantidad_cuotas_con_indice == 0
    assert result.data["bloques"][0].cantidad_cuotas_proyectadas_sin_indice == 3


def test_preview_tramo_cuotas_con_refuerzos_internos_no_agrega_obligaciones() -> None:
    from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
        CuotaRefuerzoInput,
    )

    result = BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
        _command(
            monto_total_plan=Decimal("24000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("24000000.00"),
                    cantidad_cuotas=24,
                    fecha_primer_vencimiento=date(2026, 1, 10),
                    periodicidad="MENSUAL",
                    metodo_liquidacion="SIN_INTERES",
                    cuotas_refuerzo=[
                        CuotaRefuerzoInput(
                            numero_cuota=6,
                            unidades_refuerzo=Decimal("1.00"),
                            etiqueta="Refuerzo cuota 6",
                        ),
                        CuotaRefuerzoInput(
                            numero_cuota=12,
                            unidades_refuerzo=Decimal("1.00"),
                            etiqueta="Refuerzo cuota 12",
                        ),
                    ],
                )
            ],
        )
    )

    assert result.success, result.errors
    obligaciones = result.data["obligaciones"]
    assert len(obligaciones) == 22
    assert all(ob.tipo_item_cronograma == "CUOTA" for ob in obligaciones)
    assert sum((ob.importe_total for ob in obligaciones), Decimal("0.00")) == Decimal(
        "24000000.00"
    )
    assert obligaciones[5].item_numero == 6
    assert obligaciones[5].importe_total == Decimal("2000000.00")
    assert obligaciones[5].fecha_vencimiento == date(2026, 6, 10)
    assert "incluye Refuerzo cuota 6" in obligaciones[5].etiqueta_obligacion
    assert obligaciones[11].item_numero == 12
    assert obligaciones[11].importe_total == Decimal("2000000.00")
    assert obligaciones[11].fecha_vencimiento == date(2026, 12, 10)
    assert "incluye Refuerzo cuota 12" in obligaciones[11].etiqueta_obligacion


def test_preview_valida_cuotas_refuerzo_internas() -> None:
    from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
        CuotaRefuerzoInput,
    )

    def _result(cuotas_refuerzo, *, tipo_bloque="TRAMO_CUOTAS"):
        return BuildPlanPagoVentaV2PorBloquesPreviewService().execute(
            _command(
                monto_total_plan=Decimal("1000000.00"),
                bloques=[
                    PlanPagoVentaBloqueInput(
                        tipo_bloque=tipo_bloque,
                        importe_total_bloque=Decimal("1000000.00"),
                        cantidad_cuotas=4 if tipo_bloque == "TRAMO_CUOTAS" else None,
                        fecha_primer_vencimiento=(
                            date(2026, 1, 10) if tipo_bloque == "TRAMO_CUOTAS" else None
                        ),
                        fecha_vencimiento=(
                            date(2026, 1, 10) if tipo_bloque != "TRAMO_CUOTAS" else None
                        ),
                        periodicidad=(
                            "MENSUAL" if tipo_bloque == "TRAMO_CUOTAS" else None
                        ),
                        cuotas_refuerzo=cuotas_refuerzo,
                    )
                ],
            )
        )

    cases = [
        ([CuotaRefuerzoInput(numero_cuota=0)], "CUOTA_REFUERZO_NUMERO_INVALIDO"),
        (
            [CuotaRefuerzoInput(numero_cuota=1), CuotaRefuerzoInput(numero_cuota=4)],
            "CUOTA_REFUERZO_NUMERO_INVALIDO",
        ),
        (
            [CuotaRefuerzoInput(numero_cuota=2), CuotaRefuerzoInput(numero_cuota=2)],
            "CUOTA_REFUERZO_DUPLICADA",
        ),
        (
            [CuotaRefuerzoInput(numero_cuota=1, unidades_refuerzo=Decimal("0.00"))],
            "CUOTA_REFUERZO_UNIDADES_INVALIDAS",
        ),
        (
            [CuotaRefuerzoInput(numero_cuota=1, unidades_refuerzo=Decimal("2.00"))],
            "CUOTA_REFUERZO_UNIDADES_NO_SOPORTADAS",
        ),
    ]
    for cuotas_refuerzo, expected_error in cases:
        result = _result(cuotas_refuerzo)
        assert not result.success
        assert result.errors == [expected_error]

    result = _result([CuotaRefuerzoInput(numero_cuota=1, unidades_refuerzo=None)])
    assert result.success, result.errors
    assert result.data["obligaciones"][0].tipo_item_cronograma == "CUOTA"
    assert "incluye Refuerzo" in result.data["obligaciones"][0].etiqueta_obligacion

    result = _result(
        [CuotaRefuerzoInput(numero_cuota=1, unidades_refuerzo=Decimal("1.00"))]
    )
    assert result.success, result.errors
    assert result.data["obligaciones"][0].tipo_item_cronograma == "CUOTA"
    assert "incluye Refuerzo" in result.data["obligaciones"][0].etiqueta_obligacion

    result = _result([CuotaRefuerzoInput(numero_cuota=1)], tipo_bloque="REFUERZO")
    assert not result.success
    assert result.errors == ["CUOTA_REFUERZO_NO_COMPATIBLE_CON_TIPO_BLOQUE"]
