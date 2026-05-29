from datetime import date
from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy import text

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    GeneratePlanPagoVentaV2PorBloquesCommand,
    PlanPagoVentaBloqueInput,
)
from app.application.comercial.services.generate_plan_pago_venta_v2_por_bloques_service import (
    GeneratePlanPagoVentaV2PorBloquesService,
)
from app.application.comercial.services.generate_plan_pago_venta_cuotas_iguales_simple_service import (
    PlanPagoVentaBloqueUpsertPayload,
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


def _insertar_plan_pago_venta_minimo(db_session, *, codigo_venta: str) -> int:
    id_venta = _insertar_venta_minima(db_session, codigo_venta=codigo_venta)
    return db_session.execute(
        text(
            """
            INSERT INTO plan_pago_venta (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_venta,
                metodo_plan_pago,
                estado_plan_pago,
                moneda,
                monto_total_plan
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
                :id_venta,
                'PLAN_POR_BLOQUES',
                'BORRADOR',
                'ARS',
                10000000.00
            )
            RETURNING id_plan_pago_venta
            """
        ),
        {"id_venta": id_venta, "op_id": HEADERS["X-Op-Id"]},
    ).scalar_one()


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

def test_generate_interes_directo_genera_obligaciones_y_composicion(db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-ID-001")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    result = _service(db_session).execute(
        _command(
            id_venta=id_venta,
            monto_total_plan=Decimal("10000000.00"),
            bloques=[
                PlanPagoVentaBloqueInput(
                    tipo_bloque="TRAMO_CUOTAS",
                    importe_total_bloque=Decimal("10000000.00"),
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
    assert len(result.data["obligaciones"]) == 12
    total_obligaciones = sum(
        Decimal(str(ob["importe_total"])) for ob in result.data["obligaciones"]
    )
    assert total_obligaciones == Decimal("12400000.00")
    composiciones = db_session.execute(
        text(
            """
            SELECT co.importe_componente, cf.codigo_concepto_financiero
            FROM composicion_obligacion co
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = co.id_obligacion_financiera
            WHERE o.id_relacion_generadora = :id_relacion_generadora
            ORDER BY o.numero_obligacion, co.orden_composicion
            """
        ),
        {"id_relacion_generadora": result.data["id_relacion_generadora"]},
    ).mappings().all()
    assert len(composiciones) == 24
    capital = sum(
        Decimal(str(row["importe_componente"]))
        for row in composiciones
        if row["codigo_concepto_financiero"] == "CAPITAL_VENTA"
    )
    interes = sum(
        Decimal(str(row["importe_componente"]))
        for row in composiciones
        if row["codigo_concepto_financiero"] == "INTERES_FINANCIERO"
    )
    assert capital == Decimal("10000000.00")
    assert interes == Decimal("2400000.00")


def test_generate_interes_directo_metodo_invalido_devuelve_validation_error(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-ID-002")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    payload = _payload_financiado()
    payload["bloques"][1]["metodo_liquidacion"] = "NOPE"
    response = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=payload)
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert "VALIDATION_ERROR" in body["details"]["errors"]


def test_generate_interes_directo_base_calculo_invalida_devuelve_validation_error(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-ID-003")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    payload = _payload_financiado()
    payload["bloques"][1].update(
        {
            "metodo_liquidacion": "INTERES_DIRECTO",
            "tasa_interes_directo_periodica": 0.02,
            "cantidad_periodos": 6,
            "base_calculo_interes": "SALDO",
        }
    )
    response = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=payload)
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert "VALIDATION_ERROR" in body["details"]["errors"]


def test_repository_bloque_interes_directo_tasa_distinta_es_incompatible(db_session) -> None:
    repository = PlanPagoVentaV2Repository(db_session)
    now = datetime.now(UTC)
    id_plan_pago_venta = _insertar_plan_pago_venta_minimo(
        db_session, codigo_venta="V-PPV2-BLQ-REPO-ID-001"
    )
    payload = PlanPagoVentaBloqueUpsertPayload(
        id_plan_pago_venta=id_plan_pago_venta,
        numero_bloque=1,
        tipo_bloque="TRAMO_CUOTAS",
        etiqueta_bloque="Tramo 1",
        clave_bloque="PLAN_PAGO_VENTA:1:BLOQUE:TRAMO_CUOTAS:1",
        cantidad_cuotas=6,
        importe_total_bloque=None,
        importe_cuota=Decimal("1666666.67"),
        fecha_vencimiento=None,
        fecha_primer_vencimiento=date(2026, 6, 10),
        periodicidad="MENSUAL",
        regla_redondeo="ULTIMA_CUOTA",
        metodo_liquidacion="INTERES_DIRECTO",
        tasa_interes_directo_periodica=Decimal("0.021"),
        cantidad_periodos=6,
        base_calculo_interes="CAPITAL_INICIAL_BLOQUE",
        concepto_financiero_codigo="CAPITAL_VENTA",
        observaciones=None,
        created_at=now,
        updated_at=now,
        id_instalacion_origen=1,
        id_instalacion_ultima_modificacion=1,
        op_id_alta=None,
        op_id_ultima_modificacion=None,
    )
    repository.get_or_create_plan_pago_venta_bloque(payload)
    payload.tasa_interes_directo_periodica = Decimal("0.024")

    try:
        repository.get_or_create_plan_pago_venta_bloque(payload)
        assert False, "expected incompatibility"
    except ValueError as exc:
        assert str(exc).startswith("PLAN_PAGO_VENTA_BLOQUE_INCOMPATIBLE")
        assert "tasa_interes_directo_periodica" in str(exc)


def test_repository_bloque_interes_directo_tasa_equivalente_por_escala_es_compatible(db_session) -> None:
    repository = PlanPagoVentaV2Repository(db_session)
    now = datetime.now(UTC)
    id_plan_pago_venta = _insertar_plan_pago_venta_minimo(
        db_session, codigo_venta="V-PPV2-BLQ-REPO-ID-002"
    )
    payload = PlanPagoVentaBloqueUpsertPayload(
        id_plan_pago_venta=id_plan_pago_venta,
        numero_bloque=1,
        tipo_bloque="TRAMO_CUOTAS",
        etiqueta_bloque="Tramo 1",
        clave_bloque="PLAN_PAGO_VENTA:1:BLOQUE:TRAMO_CUOTAS:1",
        cantidad_cuotas=6,
        importe_total_bloque=None,
        importe_cuota=Decimal("1666666.67"),
        fecha_vencimiento=None,
        fecha_primer_vencimiento=date(2026, 6, 10),
        periodicidad="MENSUAL",
        regla_redondeo="ULTIMA_CUOTA",
        metodo_liquidacion="INTERES_DIRECTO",
        tasa_interes_directo_periodica=Decimal("0.021"),
        cantidad_periodos=6,
        base_calculo_interes="CAPITAL_INICIAL_BLOQUE",
        concepto_financiero_codigo="CAPITAL_VENTA",
        observaciones=None,
        created_at=now,
        updated_at=now,
        id_instalacion_origen=1,
        id_instalacion_ultima_modificacion=1,
        op_id_alta=None,
        op_id_ultima_modificacion=None,
    )
    first = repository.get_or_create_plan_pago_venta_bloque(payload)
    payload.tasa_interes_directo_periodica = Decimal("0.02100000")
    second = repository.get_or_create_plan_pago_venta_bloque(payload)
    assert first["id_plan_pago_venta_bloque"] == second["id_plan_pago_venta_bloque"]


def _insertar_indice_financiero_minimo(db_session, *, codigo: str) -> int:
    return db_session.execute(
        text(
            """
            INSERT INTO indice_financiero (
                codigo_indice_financiero,
                nombre_indice_financiero,
                tipo_indice,
                unidad_medida,
                frecuencia_publicacion,
                fuente_indice,
                estado_indice_financiero
            )
            VALUES (:codigo, :codigo, 'INDICE', 'PUNTOS', 'MENSUAL', 'TEST', 'ACTIVO')
            RETURNING id_indice_financiero
            """
        ),
        {"codigo": codigo},
    ).scalar_one()


def _indexacion_payload_kwargs(id_indice_financiero: int = 1) -> dict:
    return {
        "metodo_liquidacion": "INDEXACION",
        "id_indice_financiero": id_indice_financiero,
        "fecha_base_indice": date(2026, 5, 1),
        "valor_base_indice": Decimal("100.12345678"),
        "modo_indexacion": "POR_COEFICIENTE",
        "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
        "tipo_generacion_indexada": "DEFINITIVA",
        "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
        "conserva_capital_original": True,
        "genera_ajuste_por_diferencia": True,
    }


def _indexacion_repo_payload(
    *,
    id_plan_pago_venta_bloque: int,
    id_indice_financiero: int,
    fecha_base_indice: date = date(2026, 5, 1),
    valor_base_indice: Decimal = Decimal("100.12345678"),
    politica_valor_no_disponible: str = "ERROR_SI_NO_EXISTE",
) -> object:
    from app.application.comercial.services.generate_plan_pago_venta_cuotas_iguales_simple_service import (
        PlanPagoVentaBloqueIndexacionUpsertPayload,
    )

    now = datetime.now(UTC)
    return PlanPagoVentaBloqueIndexacionUpsertPayload(
        id_plan_pago_venta_bloque=id_plan_pago_venta_bloque,
        id_indice_financiero=id_indice_financiero,
        fecha_base_indice=fecha_base_indice,
        valor_base_indice=valor_base_indice,
        modo_indexacion="POR_COEFICIENTE",
        base_calculo_indexacion="CAPITAL_INICIAL_BLOQUE",
        tipo_generacion_indexada="DEFINITIVA",
        politica_valor_no_disponible=politica_valor_no_disponible,
        conserva_capital_original=True,
        genera_ajuste_por_diferencia=True,
        observaciones=None,
        created_at=now,
        updated_at=now,
        id_instalacion_origen=1,
        id_instalacion_ultima_modificacion=1,
        op_id_alta=None,
        op_id_ultima_modificacion=None,
    )


def test_generate_indexacion_devuelve_error_controlado_y_no_persiste(client, db_session) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-BLQ-IX-001")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    id_indice = _insertar_indice_financiero_minimo(db_session, codigo="RIPTE-IX-GEN-001")
    payload = _payload_financiado()
    payload["bloques"][1].update(
        {
            "importe_total_bloque": 3000000.00,
            "metodo_liquidacion": "INDEXACION",
            "id_indice_financiero": id_indice,
            "fecha_base_indice": "2026-05-01",
            "valor_base_indice": "100.12345678",
            "modo_indexacion": "POR_COEFICIENTE",
            "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
            "tipo_generacion_indexada": "DEFINITIVA",
            "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
            "conserva_capital_original": True,
            "genera_ajuste_por_diferencia": True,
        }
    )

    response = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=payload)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["details"]["errors"] == ["INDEXACION_GENERATE_NO_IMPLEMENTADO"]
    assert (
        db_session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM plan_pago_venta
                WHERE id_venta = :id_venta
                  AND deleted_at IS NULL
                """
            ),
            {"id_venta": id_venta},
        ).scalar_one()
        == 0
    )
    assert len(_bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)) == 0
    assert len(_obligaciones_unificadas(db_session, id_venta=id_venta)) == 0
    assert (
        db_session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM plan_pago_venta_bloque_indexacion ppvbi
                JOIN plan_pago_venta_bloque ppvb
                  ON ppvb.id_plan_pago_venta_bloque = ppvbi.id_plan_pago_venta_bloque
                JOIN plan_pago_venta ppv
                  ON ppv.id_plan_pago_venta = ppvb.id_plan_pago_venta
                WHERE ppv.id_venta = :id_venta
                  AND ppvbi.deleted_at IS NULL
                """
            ),
            {"id_venta": id_venta},
        ).scalar_one()
        == 0
    )


def test_repository_persiste_y_lee_plan_pago_venta_bloque_indexacion(db_session) -> None:
    repository = PlanPagoVentaV2Repository(db_session)
    id_indice = _insertar_indice_financiero_minimo(db_session, codigo="RIPTE-IX-001")
    id_plan_pago_venta = _insertar_plan_pago_venta_minimo(
        db_session, codigo_venta="V-PPV2-BLQ-REPO-IX-001"
    )
    bloque = repository.get_or_create_plan_pago_venta_bloque(
        PlanPagoVentaBloqueUpsertPayload(
            id_plan_pago_venta=id_plan_pago_venta,
            numero_bloque=1,
            tipo_bloque="TRAMO_CUOTAS",
            etiqueta_bloque="Tramo indexado",
            clave_bloque="PLAN_PAGO_VENTA:1:BLOQUE:TRAMO_CUOTAS:1",
            cantidad_cuotas=6,
            importe_total_bloque=Decimal("10000000.00"),
            importe_cuota=Decimal("1666666.67"),
            fecha_vencimiento=None,
            fecha_primer_vencimiento=date(2026, 6, 10),
            periodicidad="MENSUAL",
            regla_redondeo="ULTIMA_CUOTA",
            metodo_liquidacion="INDEXACION",
            tasa_interes_directo_periodica=None,
            cantidad_periodos=None,
            base_calculo_interes=None,
            concepto_financiero_codigo="CAPITAL_VENTA",
            observaciones=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            id_instalacion_origen=1,
            id_instalacion_ultima_modificacion=1,
            op_id_alta=None,
            op_id_ultima_modificacion=None,
        )
    )
    payload = _indexacion_repo_payload(
        id_plan_pago_venta_bloque=bloque["id_plan_pago_venta_bloque"],
        id_indice_financiero=id_indice,
    )

    created = repository.get_or_create_plan_pago_venta_bloque_indexacion(payload)
    found = repository.get_plan_pago_venta_bloque_indexacion(
        bloque["id_plan_pago_venta_bloque"]
    )

    assert found == created
    assert created["id_indice_financiero"] == id_indice
    assert created["valor_base_indice"] == Decimal("100.12345678")


def test_repository_indexacion_detecta_incompatibilidad(db_session) -> None:
    repository = PlanPagoVentaV2Repository(db_session)
    id_indice = _insertar_indice_financiero_minimo(db_session, codigo="RIPTE-IX-002")
    id_indice_otro = _insertar_indice_financiero_minimo(db_session, codigo="CAC-IX-002")
    id_plan_pago_venta = _insertar_plan_pago_venta_minimo(
        db_session, codigo_venta="V-PPV2-BLQ-REPO-IX-002"
    )
    bloque = repository.get_or_create_plan_pago_venta_bloque(
        PlanPagoVentaBloqueUpsertPayload(
            id_plan_pago_venta=id_plan_pago_venta,
            numero_bloque=1,
            tipo_bloque="TRAMO_CUOTAS",
            etiqueta_bloque="Tramo indexado",
            clave_bloque="PLAN_PAGO_VENTA:2:BLOQUE:TRAMO_CUOTAS:1",
            cantidad_cuotas=6,
            importe_total_bloque=Decimal("10000000.00"),
            importe_cuota=Decimal("1666666.67"),
            fecha_vencimiento=None,
            fecha_primer_vencimiento=date(2026, 6, 10),
            periodicidad="MENSUAL",
            regla_redondeo="ULTIMA_CUOTA",
            metodo_liquidacion="INDEXACION",
            tasa_interes_directo_periodica=None,
            cantidad_periodos=None,
            base_calculo_interes=None,
            concepto_financiero_codigo="CAPITAL_VENTA",
            observaciones=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            id_instalacion_origen=1,
            id_instalacion_ultima_modificacion=1,
            op_id_alta=None,
            op_id_ultima_modificacion=None,
        )
    )
    id_bloque = bloque["id_plan_pago_venta_bloque"]
    repository.get_or_create_plan_pago_venta_bloque_indexacion(
        _indexacion_repo_payload(
            id_plan_pago_venta_bloque=id_bloque,
            id_indice_financiero=id_indice,
        )
    )

    incompatible_payloads = [
        _indexacion_repo_payload(
            id_plan_pago_venta_bloque=id_bloque,
            id_indice_financiero=id_indice_otro,
        ),
        _indexacion_repo_payload(
            id_plan_pago_venta_bloque=id_bloque,
            id_indice_financiero=id_indice,
            valor_base_indice=Decimal("100.12345679"),
        ),
        _indexacion_repo_payload(
            id_plan_pago_venta_bloque=id_bloque,
            id_indice_financiero=id_indice,
            fecha_base_indice=date(2026, 5, 2),
        ),
    ]

    for payload in incompatible_payloads:
        try:
            repository.get_or_create_plan_pago_venta_bloque_indexacion(payload)
            assert False, "expected incompatibility"
        except ValueError as exc:
            assert str(exc).startswith(
                "PLAN_PAGO_VENTA_BLOQUE_INDEXACION_INCOMPATIBLE"
            )


def test_repository_indexacion_compara_valor_base_indice_a_ocho_decimales(db_session) -> None:
    repository = PlanPagoVentaV2Repository(db_session)
    id_indice = _insertar_indice_financiero_minimo(db_session, codigo="RIPTE-IX-003")
    id_plan_pago_venta = _insertar_plan_pago_venta_minimo(
        db_session, codigo_venta="V-PPV2-BLQ-REPO-IX-003"
    )
    bloque = repository.get_or_create_plan_pago_venta_bloque(
        PlanPagoVentaBloqueUpsertPayload(
            id_plan_pago_venta=id_plan_pago_venta,
            numero_bloque=1,
            tipo_bloque="TRAMO_CUOTAS",
            etiqueta_bloque="Tramo indexado",
            clave_bloque="PLAN_PAGO_VENTA:3:BLOQUE:TRAMO_CUOTAS:1",
            cantidad_cuotas=6,
            importe_total_bloque=Decimal("10000000.00"),
            importe_cuota=Decimal("1666666.67"),
            fecha_vencimiento=None,
            fecha_primer_vencimiento=date(2026, 6, 10),
            periodicidad="MENSUAL",
            regla_redondeo="ULTIMA_CUOTA",
            metodo_liquidacion="INDEXACION",
            tasa_interes_directo_periodica=None,
            cantidad_periodos=None,
            base_calculo_interes=None,
            concepto_financiero_codigo="CAPITAL_VENTA",
            observaciones=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            id_instalacion_origen=1,
            id_instalacion_ultima_modificacion=1,
            op_id_alta=None,
            op_id_ultima_modificacion=None,
        )
    )
    id_bloque = bloque["id_plan_pago_venta_bloque"]
    first = repository.get_or_create_plan_pago_venta_bloque_indexacion(
        _indexacion_repo_payload(
            id_plan_pago_venta_bloque=id_bloque,
            id_indice_financiero=id_indice,
            valor_base_indice=Decimal("100.12"),
        )
    )
    second = repository.get_or_create_plan_pago_venta_bloque_indexacion(
        _indexacion_repo_payload(
            id_plan_pago_venta_bloque=id_bloque,
            id_indice_financiero=id_indice,
            valor_base_indice=Decimal("100.12000000"),
        )
    )
    assert first["id_plan_pago_venta_bloque_indexacion"] == second[
        "id_plan_pago_venta_bloque_indexacion"
    ]

    try:
        repository.get_or_create_plan_pago_venta_bloque_indexacion(
            _indexacion_repo_payload(
                id_plan_pago_venta_bloque=id_bloque,
                id_indice_financiero=id_indice,
                valor_base_indice=Decimal("100.12000001"),
            )
        )
        assert False, "expected incompatibility"
    except ValueError as exc:
        assert "valor_base_indice" in str(exc)
