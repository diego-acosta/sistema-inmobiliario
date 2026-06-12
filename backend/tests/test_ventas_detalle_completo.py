from decimal import Decimal

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_confirmar_venta_completa import _usar_plan_refuerzo_interno
from tests.test_ventas_directa_confirmar_venta_completa import (
    _crear_base_directa,
    _obligaciones_items_by_venta,
    _payload,
    _venta_by_codigo,
)


ENDPOINT_CONFIRMAR_DIRECTA = "/api/v1/ventas/directa/confirmar-venta-completa"


def _detalle_completo(client, id_venta: int):
    return client.get(f"/api/v1/ventas/{id_venta}/detalle-completo")


def test_detalle_completo_venta_confirmada_incluye_plan_obligaciones_obligados_e_impacto(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="DET-COMP")
    payload = _payload(codigo_venta="VD-DET-COMP", **base)

    confirm = client.post(ENDPOINT_CONFIRMAR_DIRECTA, headers=HEADERS, json=payload)

    assert confirm.status_code == 200, confirm.text
    id_venta = confirm.json()["data"]["venta"]["id_venta"]

    response = _detalle_completo(client, id_venta)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["venta"]["id_venta"] == id_venta
    assert data["venta"]["estado_venta"] == "confirmada"
    assert data["objetos_vendidos"][0]["id_inmueble"] == base["id_inmueble"]
    assert data["objetos_vendidos"][0]["precio_asignado"] == "150000.00"
    assert data["compradores"][0]["persona"]["id_persona"] == base["id_persona"]
    assert data["compradores"][0]["rol_participacion"]["codigo_rol"] == "COMPRADOR"
    assert data["compradores"][0]["porcentaje_responsabilidad"] == "100.00"
    assert data["impacto_activo"]["objetos"][0]["id_inmueble"] == base["id_inmueble"]

    plan = data["plan_pago_v2"]
    assert plan["cabecera"]["id_plan_pago_venta"] == plan["id_plan_pago_venta"]
    obligaciones_plan = [
        obligacion
        for bloque in plan["bloques"]
        for obligacion in bloque["obligaciones"]
    ]
    assert len(obligaciones_plan) == confirm.json()["data"]["obligaciones"]["cantidad"]
    assert len(data["obligaciones_financieras"]) == len(obligaciones_plan)
    assert sum(Decimal(ob["importe_total"]) for ob in obligaciones_plan) == Decimal(
        plan["monto_total_plan"]
    )
    assert sum(Decimal(ob["importe_total"]) for ob in data["obligaciones_financieras"]) == Decimal(
        data["resumen_financiero"]["saldo_total"]
    )
    assert plan["resumen_financiero"]["cantidad_obligaciones"] == len(
        obligaciones_plan
    )
    assert all(ob["composiciones"] for ob in obligaciones_plan)
    assert all(ob["obligados"] for ob in obligaciones_plan)


def test_detalle_completo_refuerzos_integrados_son_cuotas_de_mayor_importe(
    client, db_session
) -> None:
    base = _crear_base_directa(client, db_session, codigo="DET-REF")
    payload = _payload(codigo_venta="VD-DET-REF", **base)
    _usar_plan_refuerzo_interno(payload)

    confirm = client.post(ENDPOINT_CONFIRMAR_DIRECTA, headers=HEADERS, json=payload)

    assert confirm.status_code == 200, confirm.text
    id_venta = _venta_by_codigo(db_session, "VD-DET-REF")["id_venta"]
    persisted = _obligaciones_items_by_venta(db_session, id_venta)
    assert [ob["importe_total"] for ob in persisted] == [
        Decimal("37500.00"),
        Decimal("75000.00"),
        Decimal("37500.00"),
    ]

    response = _detalle_completo(client, id_venta)

    assert response.status_code == 200, response.text
    plan = response.json()["data"]["plan_pago_v2"]
    obligaciones = [
        obligacion
        for bloque in plan["bloques"]
        for obligacion in bloque["obligaciones"]
    ]
    assert len(obligaciones) == 3
    assert {ob["tipo_item_cronograma"] for ob in obligaciones} == {"CUOTA"}
    assert [Decimal(ob["importe_total"]) for ob in obligaciones] == [
        Decimal("37500.00"),
        Decimal("75000.00"),
        Decimal("37500.00"),
    ]
    assert sum(Decimal(ob["importe_total"]) for ob in obligaciones) == Decimal(
        "150000.00"
    )


def test_detalle_completo_404_si_venta_no_existe(client) -> None:
    response = _detalle_completo(client, 999999)

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
