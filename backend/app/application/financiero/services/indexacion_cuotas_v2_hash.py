from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

Q2 = Decimal("0.01")
Q8 = Decimal("0.00000001")

DETALLE_HASH_KEYS = [
    "id_obligacion_financiera",
    "id_composicion_capital_venta",
    "version_esperada",
    "capital_base",
    "ajuste_anterior",
    "ajuste_nuevo",
    "diferencia_neta",
    "importe_anterior",
    "importe_nuevo",
    "saldo_anterior",
    "saldo_nuevo",
    "estado_elegibilidad",
    "motivo_exclusion",
    "advertencias",
    "snapshot_antes",
    "snapshot_despues",
]


def build_indexacion_cuotas_v2_hash(
    *,
    snapshot_alcance: dict[str, Any],
    valor_base_indice: Decimal,
    valor_aplicado_indice: Decimal,
    coeficiente_indexacion: Decimal,
    detalles: list[dict[str, Any]],
) -> str:
    canonical = build_indexacion_cuotas_v2_canonical(
        snapshot_alcance=snapshot_alcance,
        valor_base_indice=valor_base_indice,
        valor_aplicado_indice=valor_aplicado_indice,
        coeficiente_indexacion=coeficiente_indexacion,
        detalles=detalles,
    )
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_indexacion_cuotas_v2_canonical(
    *,
    snapshot_alcance: dict[str, Any],
    valor_base_indice: Decimal,
    valor_aplicado_indice: Decimal,
    coeficiente_indexacion: Decimal,
    detalles: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "alcance": _canon(snapshot_alcance),
        "valor_base_indice": _canon_decimal(_dec(valor_base_indice), Q8),
        "valor_aplicado_indice": _canon_decimal(_dec(valor_aplicado_indice), Q8),
        "coeficiente_indexacion": _canon_decimal(_dec(coeficiente_indexacion), Q8),
        "detalles": [
            canonical_detalle_indexacion_cuotas_v2(d)
            for d in sorted(detalles, key=lambda r: r["id_obligacion_financiera"])
        ],
    }


def canonical_detalle_indexacion_cuotas_v2(detalle: dict[str, Any]) -> dict[str, Any]:
    return {key: _canon(detalle[key]) for key in DETALLE_HASH_KEYS}


def _dec(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _canon_decimal(value: Decimal, quantum: Decimal) -> str:
    return str(value.quantize(quantum))


def _canon(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _canon(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canon(v) for v in value]
    return value
