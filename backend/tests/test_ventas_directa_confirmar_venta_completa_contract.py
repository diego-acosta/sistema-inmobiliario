from typing import Any

from app.main import app
from tests.test_disponibilidades_create import HEADERS


ENDPOINT = "/api/v1/ventas/directa/confirmar-venta-completa"


def _payload_confirmar_venta_directa_completa() -> dict[str, object]:
    return {
        "generar_venta": {
            "codigo_venta": "VD-COMP-001",
            "fecha_venta": "2026-05-22T10:00:00",
            "monto_total": "150000.00",
            "observaciones": "Venta directa completa",
        },
        "objetos": [
            {
                "id_inmueble": 1,
                "id_unidad_funcional": None,
                "precio_asignado": "150000.00",
                "observaciones": None,
            }
        ],
        "compradores": [
            {
                "id_persona": 1,
                "id_rol_participacion": 1,
                "fecha_desde": "2026-05-22",
                "fecha_hasta": None,
                "observaciones": None,
            }
        ],
        "condiciones_comerciales": {
            "monto_total": "150000.00",
            "tipo_plan_financiero": "CUOTAS_FIJAS",
            "moneda": "ARS",
            "importe_anticipo": "50000.00",
            "fecha_vencimiento_anticipo": "2026-05-30",
            "importe_saldo": "100000.00",
            "fecha_vencimiento_saldo": "2026-06-30",
            "cuotas": [],
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
                    "fecha_vencimiento": "2026-05-30",
                },
                {
                    "tipo_bloque": "TRAMO_CUOTAS",
                    "etiqueta_bloque": "Saldo",
                    "importe_total_bloque": "100000.00",
                    "cantidad_cuotas": 2,
                    "fecha_primer_vencimiento": "2026-06-30",
                    "periodicidad": "MENSUAL",
                    "regla_redondeo": "ULTIMA_CUOTA",
                },
            ],
            "observaciones": "Plan directo placeholder",
        },
        "confirmacion": {
            "observaciones": "Confirmacion directa placeholder",
        },
    }


def _resolve_schema(openapi: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    name = ref.rsplit("/", 1)[-1]
    return openapi["components"]["schemas"][name]


def test_confirmar_venta_directa_completa_endpoint_existe_en_openapi() -> None:
    assert ENDPOINT in app.openapi()["paths"]


def test_confirmar_venta_directa_completa_no_expone_if_match_version() -> None:
    operation = app.openapi()["paths"][ENDPOINT]["post"]
    header_names = {
        parameter["name"]
        for parameter in operation.get("parameters", [])
        if parameter["in"] == "header"
    }

    assert "X-Op-Id" in header_names
    assert "X-Usuario-Id" in header_names
    assert "X-Sucursal-Id" in header_names
    assert "X-Instalacion-Id" in header_names
    assert "If-Match-Version" not in header_names


def test_confirmar_venta_directa_completa_objetos_van_en_nivel_superior() -> None:
    openapi = app.openapi()
    operation = openapi["paths"][ENDPOINT]["post"]
    body_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    request_schema = _resolve_schema(openapi, body_schema)
    properties = request_schema["properties"]
    condiciones_schema = _resolve_schema(
        openapi,
        properties["condiciones_comerciales"],
    )

    assert "objetos" in properties
    assert "compradores" in properties
    assert "objetos" not in condiciones_schema["properties"]


def test_confirmar_venta_directa_completa_request_invalido_falla_validacion(
    client,
) -> None:
    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json={"generar_venta": {}},
    )

    assert response.status_code == 422


def test_confirmar_venta_directa_completa_rechaza_objetos_duplicados_en_condiciones(
    client,
) -> None:
    payload = _payload_confirmar_venta_directa_completa()
    condiciones = payload["condiciones_comerciales"]
    assert isinstance(condiciones, dict)
    condiciones["objetos"] = [
        {
            "id_inmueble": 1,
            "id_unidad_funcional": None,
            "precio_asignado": "150000.00",
        }
    ]

    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=payload,
    )

    assert response.status_code == 422


def test_confirmar_venta_directa_completa_request_valido_devuelve_not_implemented(
    client,
) -> None:
    response = client.post(
        ENDPOINT,
        headers=HEADERS,
        json=_payload_confirmar_venta_directa_completa(),
    )

    assert response.status_code == 501
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_IMPLEMENTED"
    assert body["details"]["errors"] == ["NOT_IMPLEMENTED"]
