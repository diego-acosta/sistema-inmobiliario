"""
Tests de integración para POST /api/v1/financiero/imputaciones.
"""
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_rel_gen_create import _crear_contrato, _crear_relacion_generadora

URL = "/api/v1/financiero/imputaciones"
URL_OBLIGACIONES = "/api/v1/financiero/obligaciones"


# ── helpers ───────────────────────────────────────────────────────────────────

def _crear_rg(client, *, codigo: str) -> dict:
    contrato = _crear_contrato(client, codigo=codigo)
    return _crear_relacion_generadora(client, id_origen=contrato["id_contrato_alquiler"])


def _crear_obligacion(client, *, id_relacion_generadora: int, composiciones: list) -> dict:
    response = client.post(
        URL_OBLIGACIONES,
        headers=HEADERS,
        json={
            "id_relacion_generadora": id_relacion_generadora,
            "fecha_vencimiento": "2026-12-31",
            "composiciones": composiciones,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def _imputar(client, *, id_obligacion_financiera: int, monto: float) -> dict:
    response = client.post(
        URL,
        headers=HEADERS,
        json={"id_obligacion_financiera": id_obligacion_financiera, "monto": monto},
    )
    assert response.status_code == 201
    return response.json()["data"]


# ── imputación parcial (1 composición) ───────────────────────────────────────

def test_imputacion_parcial_una_composicion(client, db_session) -> None:
    rg = _crear_rg(client, codigo="IMP-P-001")
    ob = _crear_obligacion(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        composiciones=[{"codigo_concepto_financiero": "CANON_LOCATIVO", "importe_componente": 1000.00}],
    )

    response = client.post(
        URL,
        headers=HEADERS,
        json={"id_obligacion_financiera": ob["id_obligacion_financiera"], "monto": 400.00},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["id_obligacion_financiera"] == ob["id_obligacion_financiera"]
    assert isinstance(data["id_movimiento_financiero"], int)
    assert data["monto_aplicado"] == 400.00
    assert len(data["aplicaciones"]) == 1
    aplic = data["aplicaciones"][0]
    assert aplic["importe_aplicado"] == 400.00
    assert aplic["id_composicion_obligacion"] == ob["composiciones"][0]["id_composicion_obligacion"]


# ── imputación distribuida (varias composiciones) ────────────────────────────

def test_imputacion_distribuida_varias_composiciones(client, db_session) -> None:
    rg = _crear_rg(client, codigo="IMP-D-001")
    ob = _crear_obligacion(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        composiciones=[
            {"codigo_concepto_financiero": "CANON_LOCATIVO", "importe_componente": 600.00},
            {"codigo_concepto_financiero": "EXPENSA_TRASLADADA", "importe_componente": 400.00},
        ],
    )

    # CANON_LOCATIVO (prioridad 7) < EXPENSA_TRASLADADA (prioridad 8): canon va primero
    response = client.post(
        URL,
        headers=HEADERS,
        json={"id_obligacion_financiera": ob["id_obligacion_financiera"], "monto": 800.00},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["monto_aplicado"] == 800.00
    assert len(data["aplicaciones"]) == 2

    id_canon = next(
        c["id_composicion_obligacion"]
        for c in ob["composiciones"]
        if c["codigo_concepto_financiero"] == "CANON_LOCATIVO"
    )
    id_expensa = next(
        c["id_composicion_obligacion"]
        for c in ob["composiciones"]
        if c["codigo_concepto_financiero"] == "EXPENSA_TRASLADADA"
    )

    aplicado_por_comp = {a["id_composicion_obligacion"]: a["importe_aplicado"] for a in data["aplicaciones"]}
    assert aplicado_por_comp[id_canon] == 600.00
    assert aplicado_por_comp[id_expensa] == 200.00


# ── respeta orden de prioridad ────────────────────────────────────────────────

def test_imputacion_respeta_orden_prioridad(client, db_session) -> None:
    rg = _crear_rg(client, codigo="IMP-ORD-001")
    # CANON_LOCATIVO en orden 1, INTERES_MORA en orden 2 — pero mora tiene prioridad más alta
    ob = _crear_obligacion(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        composiciones=[
            {"codigo_concepto_financiero": "CANON_LOCATIVO", "importe_componente": 1000.00},
            {"codigo_concepto_financiero": "INTERES_MORA", "importe_componente": 1000.00},
        ],
    )

    id_mora = next(
        c["id_composicion_obligacion"]
        for c in ob["composiciones"]
        if c["codigo_concepto_financiero"] == "INTERES_MORA"
    )

    # Monto menor que cualquier composición: debería ir íntegro a INTERES_MORA (prioridad 0)
    data = _imputar(client, id_obligacion_financiera=ob["id_obligacion_financiera"], monto=300.00)

    assert len(data["aplicaciones"]) == 1
    assert data["aplicaciones"][0]["id_composicion_obligacion"] == id_mora
    assert data["aplicaciones"][0]["importe_aplicado"] == 300.00


# ── error: monto excede saldo ─────────────────────────────────────────────────

def test_imputacion_falla_si_monto_excede_saldo(client, db_session) -> None:
    rg = _crear_rg(client, codigo="IMP-ERR-001")
    ob = _crear_obligacion(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        composiciones=[{"codigo_concepto_financiero": "CANON_LOCATIVO", "importe_componente": 500.00}],
    )

    response = client.post(
        URL,
        headers=HEADERS,
        json={"id_obligacion_financiera": ob["id_obligacion_financiera"], "monto": 600.00},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "MONTO_EXCEDE_SALDO"


# ── error: obligación inexistente ─────────────────────────────────────────────

def test_imputacion_falla_si_obligacion_inexistente(client) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json={"id_obligacion_financiera": 999999, "monto": 100.00},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
