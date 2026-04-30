"""
Tests de integración para GET /api/v1/financiero/deuda.
"""
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_imputaciones_create import _crear_obligacion, _crear_rg, _imputar

URL = "/api/v1/financiero/deuda"
URL_OBLIGACIONES = "/api/v1/financiero/obligaciones"


# ── helpers locales ───────────────────────────────────────────────────────────

def _crear_ob(client, *, id_relacion_generadora: int, fecha_vencimiento: str = "2026-12-31", importe: float = 1000.00) -> dict:
    response = client.post(
        URL_OBLIGACIONES,
        headers=HEADERS,
        json={
            "id_relacion_generadora": id_relacion_generadora,
            "fecha_vencimiento": fecha_vencimiento,
            "composiciones": [
                {"codigo_concepto_financiero": "CANON_LOCATIVO", "importe_componente": importe}
            ],
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


# ── sin filtros → devuelve resultados ────────────────────────────────────────

def test_deuda_sin_filtros_devuelve_resultados(client, db_session) -> None:
    rg = _crear_rg(client, codigo="DEUDA-SF-001")
    _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])

    response = client.get(URL, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["total"] >= 1
    items = body["data"]["items"]
    assert len(items) >= 1
    # Verificar shape del item
    item = items[0]
    assert "id_obligacion_financiera" in item
    assert "id_relacion_generadora" in item
    assert "estado_obligacion" in item
    assert "importe_total" in item
    assert "saldo_pendiente" in item
    assert "composiciones" in item
    assert len(item["composiciones"]) >= 1
    comp = item["composiciones"][0]
    assert "id_composicion_obligacion" in comp
    assert "codigo_concepto_financiero" in comp
    assert "importe_componente" in comp
    assert "saldo_componente" in comp


# ── filtro por id_relacion_generadora ─────────────────────────────────────────

def test_deuda_filtra_por_relacion_generadora(client, db_session) -> None:
    rg1 = _crear_rg(client, codigo="DEUDA-RG-001")
    rg2 = _crear_rg(client, codigo="DEUDA-RG-002")
    ob1 = _crear_ob(client, id_relacion_generadora=rg1["id_relacion_generadora"])
    _crear_ob(client, id_relacion_generadora=rg2["id_relacion_generadora"])

    response = client.get(
        URL,
        params={"id_relacion_generadora": rg1["id_relacion_generadora"]},
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["id_relacion_generadora"] == rg1["id_relacion_generadora"]
    assert data["items"][0]["id_obligacion_financiera"] == ob1["id_obligacion_financiera"]


# ── filtro por con_saldo=true ─────────────────────────────────────────────────

def test_deuda_filtra_con_saldo(client, db_session) -> None:
    rg = _crear_rg(client, codigo="DEUDA-CS-001")
    ob_con_saldo = _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])
    ob_sin_saldo = _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])

    # Cancelar completamente ob_sin_saldo
    _imputar(client, id_obligacion_financiera=ob_sin_saldo["id_obligacion_financiera"], monto=1000.00)

    response = client.get(
        URL,
        params={"id_relacion_generadora": rg["id_relacion_generadora"], "con_saldo": True},
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["id_obligacion_financiera"] == ob_con_saldo["id_obligacion_financiera"]
    assert data["items"][0]["saldo_pendiente"] > 0


# ── filtro por rango de fechas ────────────────────────────────────────────────

def test_deuda_filtra_por_rango_fechas(client, db_session) -> None:
    rg = _crear_rg(client, codigo="DEUDA-FEC-001")
    ob_2026 = _crear_ob(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        fecha_vencimiento="2026-06-30",
    )
    _crear_ob(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        fecha_vencimiento="2027-06-30",
    )

    response = client.get(
        URL,
        params={
            "id_relacion_generadora": rg["id_relacion_generadora"],
            "fecha_vencimiento_hasta": "2026-12-31",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["id_obligacion_financiera"] == ob_2026["id_obligacion_financiera"]


# ── filtro por estado ─────────────────────────────────────────────────────────

def test_deuda_filtra_por_estado(client, db_session) -> None:
    rg = _crear_rg(client, codigo="DEUDA-EST-001")
    ob_proyectada = _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])
    ob_cancelada = _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])

    _imputar(client, id_obligacion_financiera=ob_cancelada["id_obligacion_financiera"], monto=1000.00)

    response = client.get(
        URL,
        params={
            "id_relacion_generadora": rg["id_relacion_generadora"],
            "estado_obligacion": "PROYECTADA",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["id_obligacion_financiera"] == ob_proyectada["id_obligacion_financiera"]
    assert data["items"][0]["estado_obligacion"] == "PROYECTADA"


# ── combinación de filtros ────────────────────────────────────────────────────

def test_deuda_combina_filtros(client, db_session) -> None:
    rg1 = _crear_rg(client, codigo="DEUDA-COMB-001")
    rg2 = _crear_rg(client, codigo="DEUDA-COMB-002")

    ob_rg1_activa = _crear_ob(client, id_relacion_generadora=rg1["id_relacion_generadora"])
    ob_rg1_cancelada = _crear_ob(client, id_relacion_generadora=rg1["id_relacion_generadora"])
    _crear_ob(client, id_relacion_generadora=rg2["id_relacion_generadora"])

    _imputar(client, id_obligacion_financiera=ob_rg1_cancelada["id_obligacion_financiera"], monto=1000.00)

    response = client.get(
        URL,
        params={
            "id_relacion_generadora": rg1["id_relacion_generadora"],
            "con_saldo": True,
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["id_obligacion_financiera"] == ob_rg1_activa["id_obligacion_financiera"]
    assert data["items"][0]["saldo_pendiente"] > 0
