from app.main import app
from tests.test_disponibilidades_create import HEADERS


ENDPOINT = "/api/v1/reservas-venta/1/confirmar-venta-completa"


def _payload_confirmar_venta_completa() -> dict[str, object]:
    return {
        "generar_venta": {
            "codigo_venta": "VTA-COMP-001",
            "fecha_venta": "2026-04-22T11:00:00",
            "monto_total": "150000.00",
            "observaciones": "Venta completa desde reserva",
        },
        "condiciones_comerciales": {
            "monto_total": "150000.00",
            "tipo_plan_financiero": "CUOTAS_FIJAS",
            "moneda": "ARS",
            "importe_anticipo": "50000.00",
            "fecha_vencimiento_anticipo": "2026-04-30",
            "importe_saldo": "100000.00",
            "fecha_vencimiento_saldo": "2026-05-30",
            "cuotas": [],
            "objetos": [
                {
                    "id_inmueble": 1,
                    "id_unidad_funcional": None,
                    "precio_asignado": "150000.00",
                }
            ],
        },
        "plan_pago_v2": {
            "tipo_pago": "FINANCIADO",
            "monto_total_plan": "150000.00",
            "moneda": "ARS",
            "bloques": [
                {
                    "tipo_bloque": "ANTICIPO",
                    "etiqueta_bloque": "Anticipo",
                    "importe_total_bloque": "50000.00",
                    "fecha_vencimiento": "2026-04-30",
                },
                {
                    "tipo_bloque": "TRAMO_CUOTAS",
                    "etiqueta_bloque": "Saldo",
                    "importe_total_bloque": "100000.00",
                    "cantidad_cuotas": 2,
                    "fecha_primer_vencimiento": "2026-05-30",
                    "periodicidad": "MENSUAL",
                    "regla_redondeo": "ULTIMA_CUOTA",
                },
            ],
            "observaciones": "Plan placeholder",
        },
        "confirmacion": {
            "observaciones": "Confirmacion placeholder",
        },
    }


def test_confirmar_venta_completa_desde_reserva_endpoint_existe_en_openapi() -> None:
    assert (
        "/api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa"
        in app.openapi()["paths"]
    )


def test_confirmar_venta_completa_desde_reserva_request_invalido_falla_validacion(
    client,
) -> None:
    response = client.post(
        ENDPOINT,
        headers={**HEADERS, "If-Match-Version": "1"},
        json={"generar_venta": {}},
    )

    assert response.status_code == 422


def test_confirmar_venta_completa_desde_reserva_request_valido_devuelve_skeleton(
    client,
) -> None:
    response = client.post(
        ENDPOINT,
        headers={**HEADERS, "If-Match-Version": "1"},
        json=_payload_confirmar_venta_completa(),
    )

    assert response.status_code == 501
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_IMPLEMENTED"
    assert body["details"]["errors"] == ["NOT_IMPLEMENTED"]
