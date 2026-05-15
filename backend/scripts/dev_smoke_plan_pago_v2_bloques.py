"""Smoke test local para POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar.

Uso:
    python scripts/dev_smoke_plan_pago_v2_bloques.py --id-venta 1 --modo CONTADO
    python scripts/dev_smoke_plan_pago_v2_bloques.py --id-venta 2 --modo FINANCIADO

Requisitos:
    - Backend corriendo en http://127.0.0.1:8000
    - La venta debe existir y tener un comprador financiero resoluble.
    - Si falta requests: python -m pip install requests
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from uuid import uuid4

try:
    import requests
except ImportError as exc:
    raise SystemExit(
        "Falta instalar requests. Ejecutar: python -m pip install requests"
    ) from exc


BASE_URL = "http://127.0.0.1:8000"


def build_payload(modo: str) -> dict[str, object]:
    if modo == "CONTADO":
        return {
            "tipo_pago": "CONTADO",
            "monto_total_plan": 12000000.00,
            "moneda": "ARS",
            "bloques": [
                {
                    "tipo_bloque": "CONTADO",
                    "etiqueta_bloque": "Pago contado",
                    "importe_total_bloque": 12000000.00,
                    "fecha_vencimiento": "2026-06-10",
                }
            ],
        }

    return {
        "tipo_pago": "FINANCIADO",
        "monto_total_plan": 12700000.00,
        "moneda": "ARS",
        "bloques": [
            {
                "tipo_bloque": "ANTICIPO",
                "etiqueta_bloque": "Anticipo",
                "importe_total_bloque": 2000000.00,
                "fecha_vencimiento": "2026-06-10",
            },
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "etiqueta_bloque": "Primer tramo",
                "cantidad_cuotas": 6,
                "importe_cuota": 500000.00,
                "fecha_primer_vencimiento": "2026-07-10",
                "periodicidad": "MENSUAL",
            },
            {
                "tipo_bloque": "TRAMO_CUOTAS",
                "etiqueta_bloque": "Segundo tramo",
                "cantidad_cuotas": 6,
                "importe_cuota": 700000.00,
                "fecha_primer_vencimiento": "2027-01-10",
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
                "fecha_vencimiento": "2027-06-10",
            },
        ],
    }


def build_headers() -> dict[str, str]:
    return {
        "X-Op-Id": str(uuid4()),
        "X-Usuario-Id": "dev-smoke",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
    }


def as_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def print_summary(data: dict[str, object]) -> None:
    plan = data.get("plan_pago_venta") or {}
    bloques = data.get("bloques") or []
    obligaciones = data.get("obligaciones") or []

    if not isinstance(plan, dict) or not isinstance(bloques, list):
        return
    if not isinstance(obligaciones, list):
        return

    total_obligaciones = sum(
        (
            as_decimal(obligacion.get("importe_total"))
            for obligacion in obligaciones
            if isinstance(obligacion, dict)
        ),
        Decimal("0"),
    )
    tipos_bloque = [
        bloque.get("tipo_bloque")
        for bloque in bloques
        if isinstance(bloque, dict)
    ]
    tipos_obligacion = [
        obligacion.get("tipo_item_cronograma")
        for obligacion in obligaciones
        if isinstance(obligacion, dict)
    ]

    print("\nResumen:")
    print(f"  metodo_plan_pago: {plan.get('metodo_plan_pago')}")
    print(f"  cantidad de bloques: {len(bloques)}")
    print(f"  cantidad de obligaciones: {len(obligaciones)}")
    print(f"  total de obligaciones: {total_obligaciones}")
    print(f"  tipos de bloque: {tipos_bloque}")
    print(f"  tipos de obligacion: {tipos_obligacion}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test local para plan de pago V2 por bloques."
    )
    parser.add_argument("--id-venta", type=int, required=True)
    parser.add_argument("--modo", choices=("CONTADO", "FINANCIADO"), required=True)
    args = parser.parse_args()

    url = f"{BASE_URL}/api/v1/ventas/{args.id_venta}/plan-pago-v2/generar"
    response = requests.post(
        url,
        headers=build_headers(),
        json=build_payload(args.modo),
        timeout=30,
    )

    print(f"POST {url}")
    print(f"Status code: {response.status_code}")

    try:
        body = response.json()
    except ValueError:
        print(response.text)
        return 1

    print(json.dumps(body, indent=2, ensure_ascii=False))

    if response.status_code == 200 and isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, dict):
            print_summary(data)

    return 0 if response.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
