"""
Tests de integracion para GET /api/v1/financiero/estado-cuenta.
"""
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_imputaciones_create import _crear_rg, _imputar


URL = "/api/v1/financiero/estado-cuenta"
URL_OBLIGACIONES = "/api/v1/financiero/obligaciones"


def _crear_ob(
    client,
    *,
    id_relacion_generadora: int,
    fecha_vencimiento: str = "2026-12-31",
    importe: float = 1000.00,
) -> dict:
    response = client.post(
        URL_OBLIGACIONES,
        headers=HEADERS,
        json={
            "id_relacion_generadora": id_relacion_generadora,
            "fecha_vencimiento": fecha_vencimiento,
            "composiciones": [
                {
                    "codigo_concepto_financiero": "CANON_LOCATIVO",
                    "importe_componente": importe,
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_estado_cuenta_con_obligacion_pendiente(client, db_session) -> None:
    rg = _crear_rg(client, codigo="EC-PEND-001")
    ob = _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])

    response = client.get(
        URL,
        headers=HEADERS,
        params={"id_relacion_generadora": rg["id_relacion_generadora"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["id_relacion_generadora"] == rg["id_relacion_generadora"]
    assert data["resumen"]["importe_total"] == 1000.00
    assert data["resumen"]["saldo_pendiente"] == 1000.00
    assert data["resumen"]["importe_cancelado"] == 0.00
    assert data["resumen"]["cantidad_obligaciones"] == 1
    assert len(data["obligaciones"]) == 1

    item = data["obligaciones"][0]
    assert item["id_obligacion_financiera"] == ob["id_obligacion_financiera"]
    assert item["estado_obligacion"] == "PROYECTADA"
    assert item["importe_total"] == 1000.00
    assert item["saldo_pendiente"] == 1000.00
    assert len(item["composiciones"]) == 1
    assert item["composiciones"][0]["codigo_concepto_financiero"] == "CANON_LOCATIVO"
    assert item["aplicaciones"] == []


def test_estado_cuenta_con_obligacion_parcialmente_imputada(client, db_session) -> None:
    rg = _crear_rg(client, codigo="EC-PARC-001")
    ob = _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])
    _imputar(client, id_obligacion_financiera=ob["id_obligacion_financiera"], monto=400.00)

    response = client.get(
        URL,
        headers=HEADERS,
        params={"id_relacion_generadora": rg["id_relacion_generadora"]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resumen"]["importe_total"] == 1000.00
    assert data["resumen"]["saldo_pendiente"] == 600.00
    assert data["resumen"]["importe_cancelado"] == 400.00
    assert data["resumen"]["cantidad_obligaciones"] == 1

    item = data["obligaciones"][0]
    assert item["estado_obligacion"] == "PARCIALMENTE_CANCELADA"
    assert item["saldo_pendiente"] == 600.00
    assert len(item["aplicaciones"]) == 1
    aplic = item["aplicaciones"][0]
    assert aplic["importe_aplicado"] == 400.00
    assert aplic["orden_aplicacion"] == 1
    assert aplic["id_movimiento_financiero"] is not None


def test_estado_cuenta_excluye_canceladas_por_default(client, db_session) -> None:
    rg = _crear_rg(client, codigo="EC-EXC-001")
    ob_activa = _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])
    ob_cancelada = _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])
    _imputar(
        client,
        id_obligacion_financiera=ob_cancelada["id_obligacion_financiera"],
        monto=1000.00,
    )

    response = client.get(
        URL,
        headers=HEADERS,
        params={"id_relacion_generadora": rg["id_relacion_generadora"]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resumen"]["cantidad_obligaciones"] == 1
    assert data["obligaciones"][0]["id_obligacion_financiera"] == ob_activa["id_obligacion_financiera"]


def test_estado_cuenta_incluye_canceladas_si_se_solicita(client, db_session) -> None:
    rg = _crear_rg(client, codigo="EC-INC-001")
    _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])
    ob_cancelada = _crear_ob(client, id_relacion_generadora=rg["id_relacion_generadora"])
    _imputar(
        client,
        id_obligacion_financiera=ob_cancelada["id_obligacion_financiera"],
        monto=1000.00,
    )

    response = client.get(
        URL,
        headers=HEADERS,
        params={
            "id_relacion_generadora": rg["id_relacion_generadora"],
            "incluir_canceladas": True,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resumen"]["cantidad_obligaciones"] == 2
    estados = {item["estado_obligacion"] for item in data["obligaciones"]}
    assert "CANCELADA" in estados


def test_estado_cuenta_filtra_por_fechas(client, db_session) -> None:
    rg = _crear_rg(client, codigo="EC-FEC-001")
    ob_junio = _crear_ob(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        fecha_vencimiento="2026-06-30",
    )
    _crear_ob(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        fecha_vencimiento="2026-08-31",
    )

    response = client.get(
        URL,
        headers=HEADERS,
        params={
            "id_relacion_generadora": rg["id_relacion_generadora"],
            "fecha_desde": "2026-06-01",
            "fecha_hasta": "2026-07-01",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resumen"]["cantidad_obligaciones"] == 1
    assert data["obligaciones"][0]["id_obligacion_financiera"] == ob_junio["id_obligacion_financiera"]


def test_estado_cuenta_falla_si_relacion_no_existe(client) -> None:
    response = client.get(
        URL,
        headers=HEADERS,
        params={"id_relacion_generadora": 999999},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
