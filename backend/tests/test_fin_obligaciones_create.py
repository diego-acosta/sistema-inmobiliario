"""
Tests de integración para POST /api/v1/financiero/obligaciones.
"""
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_rel_gen_create import _crear_contrato, _crear_relacion_generadora


URL = "/api/v1/financiero/obligaciones"


def _payload(*, id_relacion_generadora: int, **kwargs) -> dict:
    base = {
        "id_relacion_generadora": id_relacion_generadora,
        "fecha_vencimiento": "2026-12-31",
        "composiciones": [
            {
                "codigo_concepto_financiero": "CANON_LOCATIVO",
                "importe_componente": 100000.00,
            }
        ],
    }
    base.update(kwargs)
    return base


# ── creación exitosa ──────────────────────────────────────────────────────────

def test_fin_obligacion_create_ok(client, db_session) -> None:
    contrato = _crear_contrato(client, codigo="OBL-C-001")
    rg = _crear_relacion_generadora(client, id_origen=contrato["id_contrato_alquiler"])

    response = client.post(
        URL,
        headers=HEADERS,
        json=_payload(id_relacion_generadora=rg["id_relacion_generadora"]),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert isinstance(data["id_obligacion_financiera"], int)
    assert data["id_relacion_generadora"] == rg["id_relacion_generadora"]
    assert data["estado_obligacion"] == "PROYECTADA"
    assert data["importe_total"] == 100000.00
    assert data["saldo_pendiente"] == 100000.00
    assert data["uid_global"] is not None
    assert len(data["composiciones"]) == 1
    comp = data["composiciones"][0]
    assert comp["codigo_concepto_financiero"] == "CANON_LOCATIVO"
    assert comp["importe_componente"] == 100000.00
    assert comp["saldo_componente"] == 100000.00
    assert comp["orden_composicion"] == 1
    assert comp["estado_composicion_obligacion"] == "ACTIVA"


# ── error: sin composiciones ──────────────────────────────────────────────────

def test_fin_obligacion_create_sin_composiciones_falla(client, db_session) -> None:
    contrato = _crear_contrato(client, codigo="OBL-C-002")
    rg = _crear_relacion_generadora(client, id_origen=contrato["id_contrato_alquiler"])

    response = client.post(
        URL,
        headers=HEADERS,
        json={
            "id_relacion_generadora": rg["id_relacion_generadora"],
            "fecha_vencimiento": "2026-12-31",
            "composiciones": [],
        },
    )

    assert response.status_code == 422


# ── error: concepto inexistente ───────────────────────────────────────────────

def test_fin_obligacion_create_concepto_inexistente_falla(client, db_session) -> None:
    contrato = _crear_contrato(client, codigo="OBL-C-003")
    rg = _crear_relacion_generadora(client, id_origen=contrato["id_contrato_alquiler"])

    response = client.post(
        URL,
        headers=HEADERS,
        json={
            "id_relacion_generadora": rg["id_relacion_generadora"],
            "fecha_vencimiento": "2026-12-31",
            "composiciones": [
                {
                    "codigo_concepto_financiero": "CONCEPTO_INEXISTENTE_XYZ",
                    "importe_componente": 100.00,
                }
            ],
        },
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


# ── error: relación inexistente ───────────────────────────────────────────────

def test_fin_obligacion_create_relacion_inexistente_falla(client) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json={
            "id_relacion_generadora": 999999,
            "fecha_vencimiento": "2026-12-31",
            "composiciones": [
                {
                    "codigo_concepto_financiero": "CANON_LOCATIVO",
                    "importe_componente": 100.00,
                }
            ],
        },
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
