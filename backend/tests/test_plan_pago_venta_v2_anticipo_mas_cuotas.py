from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import text

from app.application.comercial.commands.generate_plan_pago_venta_anticipo_mas_cuotas_iguales import (
    GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand,
)
from app.application.comercial.services.generate_plan_pago_venta_anticipo_mas_cuotas_iguales_service import (
    GeneratePlanPagoVentaAnticipoMasCuotasIgualesService,
)
from app.application.common.commands import CommandContext
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_event_venta_confirmada import (
    _crear_persona_minima,
    _vincular_comprador_venta,
)
from tests.test_plan_pago_venta_v2_cuotas_iguales import (
    _bloques_plan_pago_venta_v2,
    _count_venta_plan_cuota,
    _insertar_venta_minima,
)

URL = "/api/v1/ventas/{id_venta}/plan-pago-v2/anticipo-mas-cuotas-iguales"
URL_CUOTAS_IGUALES = "/api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple"


def _payload(
    *,
    monto_total_plan: float = 12000000.00,
    importe_anticipo: float = 2000000.00,
    fecha_vencimiento_anticipo: str = "2026-05-10",
    cantidad_cuotas: int = 10,
    fecha_primer_vencimiento: str = "2026-06-10",
) -> dict[str, object]:
    return {
        "monto_total_plan": monto_total_plan,
        "moneda": "ARS",
        "importe_anticipo": importe_anticipo,
        "fecha_vencimiento_anticipo": fecha_vencimiento_anticipo,
        "cantidad_cuotas": cantidad_cuotas,
        "fecha_primer_vencimiento": fecha_primer_vencimiento,
        "periodicidad": "MENSUAL",
        "regla_redondeo": "ULTIMA_CUOTA",
    }


def _payload_cuotas_iguales(
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


def _obligaciones_v2(db_session, *, id_venta: int) -> list[dict]:
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
                o.fecha_emision,
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


def _count_generaciones(db_session, *, id_venta: int) -> int:
    return db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM generacion_cronograma_financiero gcf
            JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = gcf.id_relacion_generadora
            WHERE rg.tipo_origen = 'venta'
              AND rg.id_origen = :id_venta
              AND gcf.deleted_at IS NULL
            """),
        {"id_venta": id_venta},
    ).scalar_one()


def _command(
    *,
    monto_total_plan: Decimal = Decimal("12000000.00"),
    importe_anticipo: Decimal = Decimal("2000000.00"),
    fecha_vencimiento_anticipo: date | None = date(2026, 5, 10),
    cantidad_cuotas: int = 10,
    fecha_primer_vencimiento: date | None = date(2026, 6, 10),
) -> GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand:
    return GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand(
        context=CommandContext(),
        id_venta=1,
        monto_total_plan=monto_total_plan,
        moneda="ARS",
        importe_anticipo=importe_anticipo,
        fecha_vencimiento_anticipo=fecha_vencimiento_anticipo,
        cantidad_cuotas=cantidad_cuotas,
        fecha_primer_vencimiento=fecha_primer_vencimiento,
        periodicidad="MENSUAL",
        regla_redondeo="ULTIMA_CUOTA",
    )


def test_anticipo_mas_cuotas_v2_valida_fechas_obligatorias_en_servicio() -> None:
    service = GeneratePlanPagoVentaAnticipoMasCuotasIgualesService(
        repository=SimpleNamespace(db=None)
    )

    assert (
        service._validate(_command(fecha_vencimiento_anticipo=None))
        == "INVALID_FECHA_VENCIMIENTO_ANTICIPO"
    )
    assert (
        service._validate(_command(fecha_primer_vencimiento=None))
        == "INVALID_FECHA_PRIMER_VENCIMIENTO"
    )


def test_anticipo_mas_cuotas_v2_rechaza_importes_con_mas_de_dos_decimales() -> None:
    service = GeneratePlanPagoVentaAnticipoMasCuotasIgualesService(
        repository=SimpleNamespace(db=None)
    )

    assert (
        service._validate(_command(monto_total_plan=Decimal("12000000.001")))
        == "INVALID_MONTO_TOTAL_PLAN"
    )
    assert (
        service._validate(_command(importe_anticipo=Decimal("2000000.001")))
        == "INVALID_IMPORTE_ANTICIPO"
    )


def test_anticipo_mas_cuotas_v2_crea_plan_generacion_anticipo_y_cuotas(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-AMCI-001")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    response = client.post(
        URL.format(id_venta=id_venta), headers=HEADERS, json=_payload()
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["plan_pago_venta"]["metodo_plan_pago"] == "ANTICIPO_MAS_CUOTAS_IGUALES"
    assert data["plan_pago_venta"]["estado_plan_pago"] == "GENERADO"
    assert Decimal(str(data["plan_pago_venta"]["importe_anticipo"])) == Decimal(
        "2000000.00"
    )
    assert data["plan_pago_venta"]["fecha_vencimiento_anticipo"] == "2026-05-10"
    assert data["plan_pago_venta"]["cantidad_cuotas"] == 10
    assert (
        data["generacion_cronograma_financiero"]["tipo_generacion"]
        == "PLAN_PAGO_VENTA_V2"
    )
    assert data["generacion_cronograma_financiero"]["clave_generacion"].endswith(
        ":ANTICIPO_MAS_CUOTAS_IGUALES"
    )
    assert len(data["obligaciones"]) == 11
    assert _count_venta_plan_cuota(db_session, id_venta=id_venta) == 0

    bloques = _bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)
    assert len(bloques) == 2
    bloque_anticipo = bloques[0]
    bloque_cuotas = bloques[1]
    assert bloque_anticipo["numero_bloque"] == 1
    assert bloque_anticipo["tipo_bloque"] == "ANTICIPO"
    assert bloque_anticipo["etiqueta_bloque"] == "Anticipo"
    assert bloque_anticipo["clave_bloque"].endswith(":BLOQUE:ANTICIPO:1")
    assert bloque_anticipo["importe_total_bloque"] == Decimal("2000000.00")
    assert bloque_anticipo["fecha_vencimiento"].isoformat() == "2026-05-10"
    assert bloque_anticipo["concepto_financiero_codigo"] == "ANTICIPO_VENTA"
    assert bloque_cuotas["numero_bloque"] == 2
    assert bloque_cuotas["tipo_bloque"] == "TRAMO_CUOTAS"
    assert bloque_cuotas["etiqueta_bloque"] == "Cuotas saldo"
    assert bloque_cuotas["clave_bloque"].endswith(":BLOQUE:TRAMO_CUOTAS:1")
    assert bloque_cuotas["cantidad_cuotas"] == 10
    assert bloque_cuotas["importe_cuota"] == Decimal("1000000.00")
    assert bloque_cuotas["fecha_primer_vencimiento"].isoformat() == "2026-06-10"
    assert bloque_cuotas["periodicidad"] == "MENSUAL"
    assert bloque_cuotas["regla_redondeo"] == "ULTIMA_CUOTA"
    assert bloque_cuotas["concepto_financiero_codigo"] == "CAPITAL_VENTA"

    obligaciones = _obligaciones_v2(db_session, id_venta=id_venta)
    assert len(obligaciones) == 11
    assert [ob["numero_obligacion"] for ob in obligaciones] == list(range(1, 12))
    assert obligaciones[0]["tipo_item_cronograma"] == "ANTICIPO"
    assert obligaciones[0]["id_plan_pago_venta_bloque"] == bloque_anticipo[
        "id_plan_pago_venta_bloque"
    ]
    assert obligaciones[0]["etiqueta_obligacion"] == "Anticipo"
    assert obligaciones[0]["clave_funcional_origen"].endswith(":ANTICIPO:1")
    assert obligaciones[0]["fecha_emision"].isoformat() == "2026-05-10"
    assert obligaciones[0]["fecha_vencimiento"].isoformat() == "2026-05-10"
    assert obligaciones[0]["importe_total"] == Decimal("2000000.00")
    assert obligaciones[0]["saldo_pendiente"] == Decimal("2000000.00")
    assert obligaciones[0]["codigo_concepto_financiero"] == "ANTICIPO_VENTA"

    cuotas = obligaciones[1:]
    assert {ob["id_plan_pago_venta_bloque"] for ob in cuotas} == {
        bloque_cuotas["id_plan_pago_venta_bloque"]
    }
    assert {ob["tipo_item_cronograma"] for ob in cuotas} == {"CUOTA"}
    assert [ob["etiqueta_obligacion"] for ob in cuotas[:2]] == ["Cuota 1", "Cuota 2"]
    assert cuotas[0]["clave_funcional_origen"].endswith(":CUOTA:1")
    assert cuotas[-1]["clave_funcional_origen"].endswith(":CUOTA:10")
    assert {ob["codigo_concepto_financiero"] for ob in cuotas} == {"CAPITAL_VENTA"}
    assert {ob["estado_obligacion"] for ob in obligaciones} == {"PROYECTADA"}
    assert {ob["rol_obligado"] for ob in obligaciones} == {"COMPRADOR"}
    assert {str(ob["porcentaje_responsabilidad"]) for ob in obligaciones} == {"100.00"}
    assert sum(
        (ob["importe_total"] for ob in obligaciones),
        start=Decimal("0"),
    ) == Decimal("12000000.00")


def test_anticipo_mas_cuotas_v2_redondea_ultima_cuota_y_suma_total(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-AMCI-002")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    response = client.post(
        URL.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload(
            monto_total_plan=100.00, importe_anticipo=10.00, cantidad_cuotas=4
        ),
    )

    assert response.status_code == 200, response.text
    obligaciones = _obligaciones_v2(db_session, id_venta=id_venta)
    assert [ob["importe_total"] for ob in obligaciones] == [
        Decimal("10.00"),
        Decimal("22.50"),
        Decimal("22.50"),
        Decimal("22.50"),
        Decimal("22.50"),
    ]
    assert sum((ob["importe_total"] for ob in obligaciones), Decimal("0")) == Decimal(
        "100.00"
    )


def test_anticipo_mas_cuotas_v2_reejecutar_mismo_payload_no_duplica(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-AMCI-003")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    first = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())
    second = client.post(
        URL.format(id_venta=id_venta), headers=HEADERS, json=_payload()
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert len(_obligaciones_v2(db_session, id_venta=id_venta)) == 11
    assert len(_bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)) == 2
    assert _count_generaciones(db_session, id_venta=id_venta) == 1


def test_anticipo_mas_cuotas_v2_no_oculta_bloque_existente_incompatible(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-AMCI-006")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    first = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())
    assert first.status_code == 200, first.text

    db_session.execute(
        text(
            """
            UPDATE plan_pago_venta_bloque b
            SET importe_cuota = 999999.99
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
    assert len(_obligaciones_v2(db_session, id_venta=id_venta)) == 11
    assert len(_bloques_plan_pago_venta_v2(db_session, id_venta=id_venta)) == 2


def test_anticipo_mas_cuotas_v2_payload_distinto_con_plan_vivo_devuelve_409(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-AMCI-004")
    _vincular_comprador_venta(db_session, id_venta=id_venta)
    first = client.post(URL.format(id_venta=id_venta), headers=HEADERS, json=_payload())
    second = client.post(
        URL.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload(importe_anticipo=3000000.00),
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 409


def test_anticipo_mas_cuotas_v2_comprador_unico_requerido(client, db_session) -> None:
    id_venta_sin_comprador = _insertar_venta_minima(
        db_session, codigo_venta="V-PPV2-AMCI-005"
    )

    sin_comprador = client.post(
        URL.format(id_venta=id_venta_sin_comprador),
        headers=HEADERS,
        json=_payload(),
    )

    assert sin_comprador.status_code == 400
    assert sin_comprador.json()["error_code"] == "APPLICATION_ERROR"

    id_venta_multi = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-AMCI-006")
    _vincular_comprador_venta(db_session, id_venta=id_venta_multi)
    segundo_comprador = _crear_persona_minima(
        db_session, codigo=f"PER-COMP-VTA-{id_venta_multi}-B"
    )
    _vincular_comprador_venta(
        db_session, id_venta=id_venta_multi, id_persona=segundo_comprador
    )

    multi = client.post(
        URL.format(id_venta=id_venta_multi),
        headers=HEADERS,
        json=_payload(),
    )

    assert multi.status_code == 400
    assert multi.json()["error_code"] == "APPLICATION_ERROR"


def test_anticipo_mas_cuotas_v2_rechaza_importe_anticipo_invalido(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-AMCI-007")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    igual_total = client.post(
        URL.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload(importe_anticipo=12000000.00),
    )

    assert igual_total.status_code == 400
    assert igual_total.json()["error_code"] == "APPLICATION_ERROR"


def test_cuotas_iguales_simple_sigue_funcionando_con_endpoint_existente(
    client, db_session
) -> None:
    id_venta = _insertar_venta_minima(db_session, codigo_venta="V-PPV2-AMCI-008")
    _vincular_comprador_venta(db_session, id_venta=id_venta)

    response = client.post(
        URL_CUOTAS_IGUALES.format(id_venta=id_venta),
        headers=HEADERS,
        json=_payload_cuotas_iguales(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["plan_pago_venta"]["metodo_plan_pago"] == (
        "CUOTAS_IGUALES_SIMPLE"
    )
    assert len(_obligaciones_v2(db_session, id_venta=id_venta)) == 12
