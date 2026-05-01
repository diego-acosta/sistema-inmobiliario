"""
Tests de integración para GET /api/v1/financiero/deuda/consolidado.
"""
import pytest

from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_imputaciones_create import _crear_rg

URL = "/api/v1/financiero/deuda/consolidado"
URL_OBLIGACIONES = "/api/v1/financiero/obligaciones"


# ── helpers ───────────────────────────────────────────────────────────────────

def _crear_ob(client, *, id_relacion_generadora: int, importe: float,
              fecha_vencimiento: str = "2026-12-31") -> dict:
    resp = client.post(
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
    assert resp.status_code == 201
    return resp.json()["data"]


# ── tests ─────────────────────────────────────────────────────────────────────

def test_consolidado_vacio_sin_deuda(client, db_session) -> None:
    """Sin obligaciones con saldo → resumen en cero."""
    resp = client.get(URL, headers=HEADERS)
    # puede haber deuda de otros tests, pero la respuesta es siempre 200
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    data = body["data"]
    assert "fecha_corte" in data
    assert "resumen" in data
    assert "por_tipo_origen" in data
    assert "relaciones" in data


def test_consolidado_resumen_correcto(client, db_session) -> None:
    """Una relacion con dos obligaciones → resumen suma correctamente."""
    rg = _crear_rg(client, codigo="DC-SUM-001")
    id_rg = rg["id_relacion_generadora"]
    _crear_ob(client, id_relacion_generadora=id_rg, importe=30000.00)
    _crear_ob(client, id_relacion_generadora=id_rg, importe=20000.00)

    resp = client.get(URL, headers=HEADERS, params={"fecha_corte": "2026-12-01"})

    assert resp.status_code == 200
    data = resp.json()["data"]
    # La relacion debe aparecer con saldo 50000
    match = next(
        (r for r in data["relaciones"] if r["id_relacion_generadora"] == id_rg), None
    )
    assert match is not None
    assert match["saldo_pendiente"] == pytest.approx(50000.00)
    assert match["cantidad_obligaciones"] == 2
    # resumen incluye esta relacion
    assert data["resumen"]["saldo_pendiente_total"] >= 50000.00


def test_consolidado_separacion_vencida_futura(client, db_session) -> None:
    """
    Dos obligaciones con vencimientos futuros distintos.
    fecha_corte=2026-06-01: mayo (2026-05-15) es vencida, diciembre (2026-12-31) es futura.
    """
    rg = _crear_rg(client, codigo="DC-VF-001")
    id_rg = rg["id_relacion_generadora"]
    _crear_ob(client, id_relacion_generadora=id_rg, importe=10000.00,
              fecha_vencimiento="2026-05-15")
    _crear_ob(client, id_relacion_generadora=id_rg, importe=20000.00,
              fecha_vencimiento="2026-12-31")

    resp = client.get(URL, headers=HEADERS, params={"fecha_corte": "2026-06-01"})

    assert resp.status_code == 200
    data = resp.json()["data"]
    match = next(
        (r for r in data["relaciones"] if r["id_relacion_generadora"] == id_rg), None
    )
    assert match is not None
    assert match["saldo_vencido"] == pytest.approx(10000.00)
    assert match["saldo_futuro"] == pytest.approx(20000.00)


def test_consolidado_mora_calculada(client, db_session) -> None:
    """
    Obligación con vencimiento 2026-05-10, saldo 50000.
    fecha_corte=2026-05-20 → 10 días → mora = 50000 * 0.001 * 10 = 500.
    """
    rg = _crear_rg(client, codigo="DC-MORA-001")
    id_rg = rg["id_relacion_generadora"]
    _crear_ob(client, id_relacion_generadora=id_rg, importe=50000.00,
              fecha_vencimiento="2026-05-10")

    resp = client.get(URL, headers=HEADERS, params={"fecha_corte": "2026-05-20"})

    assert resp.status_code == 200
    data = resp.json()["data"]
    match = next(
        (r for r in data["relaciones"] if r["id_relacion_generadora"] == id_rg), None
    )
    assert match is not None
    assert match["mora_calculada"] == pytest.approx(500.00)
    assert match["total_con_mora"] == pytest.approx(50500.00)


def test_consolidado_agrupacion_por_relacion(client, db_session) -> None:
    """Dos relaciones distintas aparecen como ítems separados en 'relaciones'."""
    rg1 = _crear_rg(client, codigo="DC-GRP-001")
    rg2 = _crear_rg(client, codigo="DC-GRP-002")
    _crear_ob(client, id_relacion_generadora=rg1["id_relacion_generadora"], importe=10000.00)
    _crear_ob(client, id_relacion_generadora=rg2["id_relacion_generadora"], importe=15000.00)

    resp = client.get(URL, headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    ids_rg = {r["id_relacion_generadora"] for r in data["relaciones"]}
    assert rg1["id_relacion_generadora"] in ids_rg
    assert rg2["id_relacion_generadora"] in ids_rg
    # cada uno tiene su saldo propio
    r1 = next(r for r in data["relaciones"]
              if r["id_relacion_generadora"] == rg1["id_relacion_generadora"])
    r2 = next(r for r in data["relaciones"]
              if r["id_relacion_generadora"] == rg2["id_relacion_generadora"])
    assert r1["saldo_pendiente"] == pytest.approx(10000.00)
    assert r2["saldo_pendiente"] == pytest.approx(15000.00)


def test_consolidado_por_tipo_origen_contrato_alquiler(client, db_session) -> None:
    """Obligaciones de tipo CONTRATO_ALQUILER aparecen en por_tipo_origen."""
    rg = _crear_rg(client, codigo="DC-TIP-001")
    _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"], importe=25000.00)

    resp = client.get(URL, headers=HEADERS, params={"tipo_origen": "CONTRATO_ALQUILER"})

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "CONTRATO_ALQUILER" in data["por_tipo_origen"]
    resumen_tipo = data["por_tipo_origen"]["CONTRATO_ALQUILER"]
    assert resumen_tipo["saldo_pendiente_total"] >= 25000.00
    assert resumen_tipo["cantidad_relaciones"] >= 1
    # filtro: no aparecen otras tipos
    for r in data["relaciones"]:
        assert r["tipo_origen"] == "CONTRATO_ALQUILER"


def test_consolidado_filtro_tipo_origen_inexistente_devuelve_vacio(client, db_session) -> None:
    """tipo_origen=SERVICIO (no existe) → relaciones vacías, resumen en cero."""
    resp = client.get(URL, headers=HEADERS, params={"tipo_origen": "SERVICIO_INEXISTENTE"})

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["relaciones"] == []
    assert data["por_tipo_origen"] == {}
    assert data["resumen"]["saldo_pendiente_total"] == pytest.approx(0.0)


def test_consolidado_mora_cero_sin_vencidas(client, db_session) -> None:
    """Con fecha_corte antes de todos los vencimientos → mora = 0."""
    rg = _crear_rg(client, codigo="DC-MOCERO-001")
    _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"], importe=10000.00,
              fecha_vencimiento="2026-12-31")

    resp = client.get(URL, headers=HEADERS, params={"fecha_corte": "2026-01-01"})

    assert resp.status_code == 200
    data = resp.json()["data"]
    match = next(
        (r for r in data["relaciones"]
         if r["id_relacion_generadora"] == rg["id_relacion_generadora"]), None
    )
    assert match is not None
    assert match["mora_calculada"] == pytest.approx(0.0)
    assert match["saldo_vencido"] == pytest.approx(0.0)
    assert match["saldo_futuro"] == pytest.approx(10000.00)


def test_consolidado_fecha_corte_en_respuesta(client, db_session) -> None:
    """fecha_corte enviada aparece en la respuesta; sin ella usa today."""
    rg = _crear_rg(client, codigo="DC-FC-001")
    _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"], importe=5000.00)

    resp_con = client.get(URL, headers=HEADERS, params={"fecha_corte": "2026-06-15"})
    resp_sin = client.get(URL, headers=HEADERS)

    assert resp_con.status_code == 200
    assert resp_sin.status_code == 200
    assert resp_con.json()["data"]["fecha_corte"] == "2026-06-15"

    from datetime import date
    assert resp_sin.json()["data"]["fecha_corte"] == str(date.today())
