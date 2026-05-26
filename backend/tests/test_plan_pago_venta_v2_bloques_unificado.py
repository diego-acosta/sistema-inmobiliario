from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    GeneratePlanPagoVentaV2PorBloquesCommand,
    PlanPagoVentaBloqueInput,
)
from app.application.comercial.services.generate_plan_pago_venta_v2_por_bloques_service import (
    GeneratePlanPagoVentaV2PorBloquesService,
)
from app.application.common.commands import CommandContext
from app.infrastructure.persistence.repositories.plan_pago_venta_v2_repository import (
    PlanPagoVentaV2Repository,
)
from tests.test_fin_event_venta_confirmada import _vincular_comprador_venta
from tests.test_plan_pago_venta_v2_cuotas_iguales import (
    _bloques_plan_pago_venta_v2,
    _count_venta_plan_cuota,
    _insertar_venta_minima,
)
from tests.test_disponibilidades_create import HEADERS

URL = "/api/v1/ventas/{id_venta}/plan-pago-v2/generar"


def _service(db_session) -> GeneratePlanPagoVentaV2PorBloquesService:
    return GeneratePlanPagoVentaV2PorBloquesService(
        repository=PlanPagoVentaV2Repository(db_session)
    )


def _command(
    *,
    id_venta: int,
    tipo_pago: str = "FINANCIADO",
    monto_total_plan: Decimal = Decimal("12700000.00"),
    bloques: list[PlanPagoVentaBloqueInput] | None = None,
) -> GeneratePlanPagoVentaV2PorBloquesCommand:
    return GeneratePlanPagoVentaV2PorBloquesCommand(
        context=CommandContext(),
        id_venta=id_venta,
        tipo_pago=tipo_pago,
        monto_total_plan=monto_total_plan,
        moneda="ARS",
        bloques=bloques if bloques is not None else _bloques_financiado(),
    )


def _bloques_financiado() -> list[PlanPagoVentaBloqueInput]:
    return [
        PlanPagoVentaBloqueInput(
            tipo_bloque="ANTICIPO",
            importe_total_bloque=Decimal("2000000.00"),
            fecha_vencimiento=date(2026, 5, 10),
        ),
        PlanPagoVentaBloqueInput(
            tipo_bloque="TRAMO_CUOTAS",
            cantidad_cuotas=6,
            importe_cuota=Decimal("500000.00"),
            fecha_primer_vencimiento=date(2026, 6, 10),
            periodicidad="MENSUAL",
        ),
        PlanPagoVentaBloqueInput(
            tipo_bloque="TRAMO_CUOTAS",
            cantidad_cuotas=6,
            importe_cuota=Decimal("700000.00"),
            fecha_primer_vencimiento=date(2026, 12, 10),
            periodicidad="MENSUAL",
        ),
        PlanPagoVentaBloqueInput(
            tipo_bloque="REFUERZO",
            etiqueta_bloque="Refuerzo diciembre",
            importe_total_bloque=Decimal("1500000.00"),
            fecha_vencimiento=date(2026, 12, 20),
        ),
        PlanPagoVentaBloqueInput(
            tipo_bloque="SALDO",
            etiqueta_bloque="Saldo contra escritura",
            importe_total_bloque=Decimal("2000000.00"),
            fecha_vencimiento=date(2027, 3, 10),
        ),
    ]


def _payload_financiado() -> dict[str, object]:
    return {
        "tipo_pago": "FINANCIADO",
        "monto_total_plan": 12700000.00,
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "ANTICIPO",
                "etiqueta_bloque": "Anticipo",
                "importe_total_bloque": 2000000.00,
                "fecha_vencimiento": "2026-05-10",
            },
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "etiqueta_bloque": "Primer tramo",
                "cantidad_cuotas": 6,
                "importe_cuota": 500000.00,
                "fecha_primer_vencimiento": "2026-06-10",
                "periodicidad": "MENSUAL",
            },
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "etiqueta_bloque": "Segundo tramo",
                "cantidad_cuotas": 6,
                "importe_cuota": 700000.00,
                "fecha_primer_vencimiento": "2026-12-10",
                "periodicidad": "MENSUAL",
            },
            {
                "tipo_bloque": "REFUERZO",
                "etiqueta_bloque": "Refuerzo diciembre",
                "importe_total_bloque": 1500000.00,
                "fecha_vencimiento": "2026-12-20",
            },
            {
                "tipo_bloque": "SALDO",
                "etiqueta_bloque": "Saldo contra escritura",
                "importe_total_bloque": 2000000.00,
                "fecha_vencimiento": "2027-03-10",
            },
        ],
    }


def _payload_contado() -> dict[str, object]:
    return {
        "tipo_pago": "CONTADO",
        "monto_total_plan": 12000000.00,
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "CONTADO",
                "importe_total_bloque": 12000000.00,
                "fecha_vencimiento": "2026-05-10",
            }
        ],
    }


def _obligaciones_unificadas(db_session, *, id_venta: int) -> list[dict]:
    rows = (
        db_session.execute(
            text("""
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
            """),
            {"id_venta": id_venta},
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def test_endpoint_unificado_genera_contado_como_saldo_con_capital(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-HTTP-001")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    response = client.post(
        URL.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload_contado(),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["plan_pago_venta"]["metodo_plan_pago"] == "PLAN_POR_BLOQUES"
    assert data["plan_pago_venta"]["estado_plan_pago"] == "GENERADO"
    assert len(data["bloques"]) == 1
    assert data["bloques"][0]["numero_bloque"] == 1
    assert data["bloques"][0]["tipo_bloque"] == "CONTADO"
    assert data["bloques"][0]["clave_bloque"].endswith(":BLOQUE:CONTADO:1")
    assert len(data["obligaciones"]) == 1
    assert data["obligaciones"][0]["numero_obligacion"] == 1
    assert data["obligaciones"][0]["tipo_item_cronograma"] == "SALDO"
    assert data["obligaciones"][0]["clave_funcional_origen"].endswith(":SALDO:1")
    assert (
        data["obligaciones"][0]["id_plan_pago_venta_bloque"]
        == data["bloques"][0]["id_plan_pago_venta_bloque"]
    )
    assert _count_venta_plan_cuota(db_session, id_venta=id_venta) == 0


def test_endpoint_unificado_genera_financiado_con_bloques_y_obligaciones(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-HTTP-002")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    response = client.post(
        URL.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload_financiado(),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id_venta"] == id_venta
    assert data["plan_pago_venta"]["metodo_plan_pago"] == "PLAN_POR_BLOQUES"
    assert data["generacion_cronograma_financiero"]["tipo_generacion"] == (
        "PLAN_PAGO_VENTA_V2"
    )
    assert [bloque["numero_bloque"] for bloque in data["bloques"]] == [1, 2, 3, 4, 5]
    assert [bloque["tipo_bloque"] for bloque in data["bloques"]] == [
        "ANTICIPO",
        "TRAMO_CUOTAS",
        "TRAMO_CUOTAS",
        "REFUERZO",
        "SALDO",
    ]
    assert len(data["obligaciones"]) == 15
    assert [obligacion["numero_obligacion"] for obligacion in data["obligaciones"]] == (
        list(range(1, 16))
    )
    assert [
        obligacion["tipo_item_cronograma"] for obligacion in data["obligaciones"]
    ] == [
        "ANTICIPO",
        *["CUOTA"] * 6,
        *["CUOTA"] * 6,
        "REFUERZO",
        "SALDO",
    ]
    assert _count_venta_plan_cuota(db_session, id_venta=id_venta) == 0


def test_endpoint_unificado_rechaza_suma_invalida(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-HTTP-003")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    payload = {**_payload_financiado(), "monto_total_plan": 12700001.00}

    response = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=payload)

    assert response.status_code == 400, response.text
    assert response.json()["details"]["errors"] == ["SUMA_BLOQUES_INVALIDA"]


def test_endpoint_unificado_rechaza_contado_mezclado(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-HTTP-004")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    payload = _payload_contado()
    payload["bloques"] = [
        {
            "tipo_bloque": "CONTADO",
            "importe_total_bloque": 10000000.00,
            "fecha_vencimiento": "2026-05-10",
        },
        {
            "tipo_bloque": "SALDO",
            "importe_total_bloque": 2000000.00,
            "fecha_vencimiento": "2026-06-10",
        },
    ]

    response = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=payload)

    assert response.status_code == 400, response.text
    assert response.json()["details"]["errors"] == ["CONTADO_BLOQUES_INVALIDOS"]


def test_endpoint_unificado_reejecutar_mismo_payload_no_duplica(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-HTTP-005")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    payload = _payload_financiado()

    first = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=payload)
    second = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert len(_bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)) == 5
    assert len(_obligaciones_unificadas(db_session, id_venta=id_venta)) == 15
    assert _count_venta_plan_cuota(db_session, id_venta=id_venta) == 0


def test_endpoint_unificado_schema_rechaza_campos_internos_del_cliente(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-HTTP-006")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    payload = _payload_contado()
    payload["numero_obligacion"] = 1
    payload["clave_funcional_origen"] = "CLIENTE:NO:DEBE:ENVIAR"
    payload["bloques"][0]["numero_bloque"] = 1
    payload["bloques"][0]["clave_bloque"] = "CLIENTE:NO:DEBE:ENVIAR"

    response = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=payload)

    assert response.status_code == 422, response.text
    errors = response.json()["detail"]
    locations = {tuple(error["loc"]) for error in errors}
    assert ("body", "numero_obligacion") in locations
    assert ("body", "clave_funcional_origen") in locations
    assert ("body", "bloques", 0, "numero_bloque") in locations
    assert ("body", "bloques", 0, "clave_bloque") in locations
    assert _count_venta_plan_cuota(db_session, id_venta=id_venta) == 0


def test_servicio_unificado_genera_contado_como_saldo_con_capital(db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-001")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    result = _service(db_session).execute(
        _command(
            id_venta=id_venta,
            tipo_pago="CONTADO",
            monto_total_plan=Decimal("12000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="CONTADO",
                    importe_total_bloque=Decimal("12000000.00"),
                    fecha_vencimiento=date(2026, 5, 10),
                )
            ],
        )
    )

    assert result.success, result.errors
    assert result.data["plan_pago_venta"]["metodo_plan_pago"] == "PLAN_POR_BLOQUES"
    bloques = _bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)
    assert len(bloques) == 1
    assert bloques[0]["tipo_bloque"] == "CONTADO"
    obligaciones = _obligaciones_unificadas(db_session, id_venta=id_venta)
    assert len(obligaciones) == 1
    assert obligaciones[0]["tipo_item_cronograma"] == "SALDO"
    assert obligaciones[0]["codigo_concepto_financiero"] == "CAPITAL_VENTA"
    assert (
        obligaciones[0]["id_plan_pago_venta_bloque"]
        == bloques[0]["id_plan_pago_venta_bloque"]
    )
    assert _count_venta_plan_cuota(db_session, id_venta=id_venta) == 0


def test_servicio_unificado_execute_in_existing_transaction_no_abre_transaccion_propia(
    db_session,
    monkeypatch,
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-EXT-TX")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    service = _service(db_session)

    def fail_if_transaction_is_opened():
        raise AssertionError("execute_in_existing_transaction no debe abrir transaccion")

    monkeypatch.setattr(service, "_transaction", fail_if_transaction_is_opened)

    result = service.execute_in_existing_transaction(
        _command(
            id_venta=id_venta,
            tipo_pago="CONTADO",
            monto_total_plan=Decimal("12000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="CONTADO",
                    importe_total_bloque=Decimal("12000000.00"),
                    fecha_vencimiento=date(2026, 5, 10),
                )
            ],
        )
    )

    assert result.success, result.errors
    assert len(_obligaciones_unificadas(db_session, id_venta=id_venta)) == 1


def test_servicio_unificado_genera_financiado_con_bloques_y_trazabilidad(
    db_session,
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-002")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    result = _service(db_session).execute(_command(id_venta=id_venta))

    assert result.success, result.errors
    bloques = _bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)
    assert [bloque["numero_bloque"] for bloque in bloques] == [1, 2, 3, 4, 5]
    assert [bloque["tipo_bloque"] for bloque in bloques] == [
        "ANTICIPO",
        "TRAMO_CUOTAS",
        "TRAMO_CUOTAS",
        "REFUERZO",
        "SALDO",
    ]
    assert [bloque["clave_bloque"].split(":")[-2:] for bloque in bloques] == [
        ["ANTICIPO", "1"],
        ["TRAMO_CUOTAS", "1"],
        ["TRAMO_CUOTAS", "2"],
        ["REFUERZO", "1"],
        ["SALDO", "1"],
    ]

    obligaciones = _obligaciones_unificadas(db_session, id_venta=id_venta)
    assert len(obligaciones) == 15
    assert [ob["numero_obligacion"] for ob in obligaciones] == list(range(1, 16))
    assert [ob["tipo_item_cronograma"] for ob in obligaciones] == [
        "ANTICIPO",
        *["CUOTA"] * 6,
        *["CUOTA"] * 6,
        "REFUERZO",
        "SALDO",
    ]
    assert obligaciones[0]["codigo_concepto_financiero"] == "ANTICIPO_VENTA"
    assert {ob["codigo_concepto_financiero"] for ob in obligaciones[1:]} == {
        "CAPITAL_VENTA"
    }
    assert (
        obligaciones[0]["id_plan_pago_venta_bloque"]
        == bloques[0]["id_plan_pago_venta_bloque"]
    )
    assert {ob["id_plan_pago_venta_bloque"] for ob in obligaciones[1:7]} == {
        bloques[1]["id_plan_pago_venta_bloque"]
    }
    assert {ob["id_plan_pago_venta_bloque"] for ob in obligaciones[7:13]} == {
        bloques[2]["id_plan_pago_venta_bloque"]
    }
    assert (
        obligaciones[13]["id_plan_pago_venta_bloque"]
        == bloques[3]["id_plan_pago_venta_bloque"]
    )
    assert (
        obligaciones[14]["id_plan_pago_venta_bloque"]
        == bloques[4]["id_plan_pago_venta_bloque"]
    )
    assert sum((ob["importe_total"] for ob in obligaciones), Decimal("0")) == Decimal(
        "12700000.00"
    )
    assert {ob["rol_obligado"] for ob in obligaciones} == {"COMPRADOR"}
    assert _count_venta_plan_cuota(db_session, id_venta=id_venta) == 0


def test_servicio_unificado_genera_tramo_por_capital_total_con_ultima_cuota_ajustada(
    db_session,
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-007")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    result = _service(db_session).execute(
        _command(
            id_venta=id_venta,
            monto_total_plan=Decimal("10000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
                    cantidad_cuotas=6,
                    fecha_primer_vencimiento=date(2026, 6, 10),
                    periodicidad="MENSUAL",
                )
            ],
        )
    )

    assert result.success, result.errors
    bloques = _bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)
    assert len(bloques) == 1
    assert bloques[0]["tipo_bloque"] == "TRAMO_CUOTAS"
    assert bloques[0]["importe_total_bloque"] == Decimal("10000000.00")
    assert bloques[0]["importe_cuota"] == Decimal("1666666.67")

    obligaciones = _obligaciones_unificadas(db_session, id_venta=id_venta)
    importes = [ob["importe_total"] for ob in obligaciones]
    assert importes[:5] == [Decimal("1666666.67")] * 5
    assert importes[-1] == Decimal("1666666.65")
    assert sum(importes, Decimal("0.00")) == Decimal("10000000.00")
    assert _count_venta_plan_cuota(db_session, id_venta=id_venta) == 0


def test_servicio_unificado_rechaza_suma_de_bloques_invalida(db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-003")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    result = _service(db_session).execute(
        _command(id_venta=id_venta, monto_total_plan=Decimal("12700001.00"))
    )

    assert not result.success
    assert result.errors == ["SUMA_BLOQUES_INVALIDA"]


def test_servicio_unificado_rechaza_contado_mezclado(db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-004")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    result = _service(db_session).execute(
        _command(
            id_venta=id_venta,
            tipo_pago="CONTADO",
            monto_total_plan=Decimal("12000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="CONTADO",
                    importe_total_bloque=Decimal("10000000.00"),
                    fecha_vencimiento=date(2026, 5, 10),
                ),
                PlanPagoVentaBloqueInput(
                    tipo_bloque="SALDO",
                    importe_total_bloque=Decimal("2000000.00"),
                    fecha_vencimiento=date(2026, 6, 10),
                ),
            ],
        )
    )

    assert not result.success
    assert result.errors == ["CONTADO_BLOQUES_INVALIDOS"]


def test_servicio_unificado_reejecutar_mismo_payload_no_duplica(db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-005")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    first = _service(db_session).execute(_command(id_venta=id_venta))
    second = _service(db_session).execute(_command(id_venta=id_venta))

    assert first.success, first.errors
    assert second.success, second.errors
    assert len(_bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)) == 5
    assert len(_obligaciones_unificadas(db_session, id_venta=id_venta)) == 15


def test_servicio_unificado_payload_distinto_con_plan_vivo_devuelve_conflicto(
    db_session,
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-006")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    first = _service(db_session).execute(_command(id_venta=id_venta))
    changed = _bloques_financiado()
    changed[-1] = PlanPagoVentaBloqueInput(
        tipo_bloque="SALDO",
        etiqueta_bloque="Saldo contra escritura",
        importe_total_bloque=Decimal("2100000.00"),
        fecha_vencimiento=date(2027, 3, 10),
    )

    second = _service(db_session).execute(
        _command(
            id_venta=id_venta,
            monto_total_plan=Decimal("12800000.00"),
            bloques=changed,
        )
    )

    assert first.success, first.errors
    assert not second.success
    assert second.errors == ["PLAN_PAGO_VENTA_VIVO_INCOMPATIBLE"]


def test_plan_pago_v2_generar_requiere_x_op_id_valido(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-HTTP-HDR-001")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    headers = {k: v for k, v in HEADERS.items() if k != "X-Op-Id"}
    response = client.post(URL.format(id_venta=id_venta), headers=headers, json=_payload_contado())

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": "X-Op-Id"}

    headers = {**HEADERS, "X-Op-Id": "no-es-uuid"}
    response = client.post(URL.format(id_venta=id_venta), headers=headers, json=_payload_contado())

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": "X-Op-Id"}
