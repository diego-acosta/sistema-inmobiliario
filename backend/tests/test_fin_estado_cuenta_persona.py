"""
Tests de integración para GET /api/v1/financiero/personas/{id_persona}/estado-cuenta.
"""
from datetime import date

import pytest
from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_event_contrato_alquiler import (
    _activar,
    _crear_condicion,
    _crear_contrato_borrador,
    _crear_locatario_principal,
)

URL = "/api/v1/financiero/personas/{id_persona}/estado-cuenta"


# ── helpers ───────────────────────────────────────────────────────────────────

def _url(id_persona: int) -> str:
    return URL.format(id_persona=id_persona)


def _setup_contrato_con_obligaciones(
    client,
    db_session,
    *,
    codigo: str,
    fecha_inicio: str,
    fecha_fin: str,
    monto: float = 50000.00,
    dia_vencimiento_canon: int | None = None,
) -> tuple[int, dict]:
    """Crea contrato, condición, locatario y activa → devuelve (id_persona, contrato_data)."""
    contrato = _crear_contrato_borrador(
        client,
        codigo=codigo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        dia_vencimiento_canon=dia_vencimiento_canon,
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], monto, fecha_inicio)
    id_persona = _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])
    return id_persona, contrato


# ── tests ─────────────────────────────────────────────────────────────────────

def test_estado_cuenta_persona_con_deuda_devuelve_resumen_correcto(client, db_session) -> None:
    """Persona con 3 obligaciones → resumen refleja saldo y cantidad correcta."""
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-PEND-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-07-31",
        monto=30000.00,
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["id_persona"] == id_persona
    assert len(data["obligaciones"]) == 3
    assert data["resumen"]["saldo_pendiente_total"] == pytest.approx(90000.00)
    for ob in data["obligaciones"]:
        assert ob["porcentaje_responsabilidad"] == pytest.approx(100.0)
        assert ob["monto_responsabilidad"] == pytest.approx(ob["saldo_pendiente"])
        assert ob["tipo_origen"] == "CONTRATO_ALQUILER"


def test_estado_cuenta_persona_separa_vencida_futura(client, db_session) -> None:
    """
    Contrato 2026-04-01 → 2026-06-30, dia_vencimiento_canon=1:
    - Abril: vencimiento 2026-04-01 (pasado) → saldo_vencido
    - Mayo: vencimiento 2026-05-01 (hoy) → saldo_futuro (no es < hoy)
    - Junio: vencimiento 2026-06-01 (futuro) → saldo_futuro
    """
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-VF-001",
        fecha_inicio="2026-04-01",
        fecha_fin="2026-06-30",
        monto=10000.00,
        dia_vencimiento_canon=1,
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    resumen = data["resumen"]

    # Abril tiene vencimiento 2026-04-01 < hoy (2026-05-01) → vencida
    assert resumen["saldo_vencido"] == pytest.approx(10000.00)
    # Mayo + Junio → futuro
    assert resumen["saldo_futuro"] == pytest.approx(20000.00)
    assert resumen["saldo_pendiente_total"] == pytest.approx(30000.00)


def test_estado_cuenta_persona_incluye_mora_dinamica(client, db_session) -> None:
    """
    Obligación con fecha_vencimiento en el pasado → mora_calculada > 0.
    dia_vencimiento_canon=1 → vencimiento 2026-04-01, hoy 2026-05-01 → 30 días.
    mora = 50000 * 0.001 * 30 = 1500.00
    """
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-MORA-001",
        fecha_inicio="2026-04-01",
        fecha_fin="2026-04-30",
        monto=50000.00,
        dia_vencimiento_canon=1,
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    ob = data["obligaciones"][0]

    assert ob["dias_atraso"] == 30
    assert ob["mora_calculada"] == pytest.approx(1500.00)
    assert ob["tasa_diaria_mora"] == pytest.approx(0.001)
    # total_con_mora = (50000 + 1500) * 100 / 100 = 51500
    assert ob["total_con_mora"] == pytest.approx(51500.00)
    assert data["resumen"]["mora_calculada"] == pytest.approx(1500.00)
    assert data["resumen"]["total_con_mora"] == pytest.approx(51500.00)


def test_estado_cuenta_persona_sin_deuda_devuelve_cero(client, db_session) -> None:
    """Persona sin ninguna obligación → resumen en cero, lista vacía."""
    resp_persona = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Sin",
            "apellido": "Deuda",
            "razon_social": None,
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    assert resp_persona.status_code == 201
    id_persona = resp_persona.json()["data"]["id_persona"]

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id_persona"] == id_persona
    assert data["obligaciones"] == []
    assert data["resumen"]["saldo_pendiente_total"] == 0.0
    assert data["resumen"]["saldo_vencido"] == 0.0
    assert data["resumen"]["saldo_futuro"] == 0.0
    assert data["resumen"]["mora_calculada"] == 0.0
    assert data["resumen"]["total_con_mora"] == 0.0


def test_estado_cuenta_persona_excluye_anulada_y_reemplazada(client, db_session) -> None:
    """ANULADA y REEMPLAZADA no aparecen aunque existan en DB."""
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-EXCL-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=20000.00,
    )

    # Forzar estado ANULADA directamente en DB
    db_session.execute(
        text(
            """
            UPDATE obligacion_financiera
            SET estado_obligacion = 'ANULADA'
            WHERE id_relacion_generadora = (
                SELECT id_relacion_generadora FROM relacion_generadora
                WHERE tipo_origen = 'contrato_alquiler'
                  AND id_origen = :id_contrato
                  AND deleted_at IS NULL
                LIMIT 1
            )
              AND deleted_at IS NULL
            """
        ),
        {"id_contrato": contrato["id_contrato_alquiler"]},
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["obligaciones"] == []
    assert data["resumen"]["saldo_pendiente_total"] == 0.0


def test_estado_cuenta_persona_respeta_porcentaje_responsabilidad(client, db_session) -> None:
    """
    Si porcentaje_responsabilidad != 100, monto_responsabilidad es proporcional.
    Se inserta un segundo obligado con 50% sobre la misma obligación.
    """
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-PCT-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=40000.00,
    )

    # Crear segunda persona
    resp2 = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Segundo",
            "apellido": "Obligado",
            "razon_social": None,
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    assert resp2.status_code == 201
    id_persona2 = resp2.json()["data"]["id_persona"]

    # Obtener la obligación creada
    ob_row = db_session.execute(
        text(
            """
            SELECT id_obligacion_financiera FROM obligacion_financiera
            WHERE id_relacion_generadora = (
                SELECT id_relacion_generadora FROM relacion_generadora
                WHERE tipo_origen = 'contrato_alquiler'
                  AND id_origen = :id_contrato
                  AND deleted_at IS NULL
                LIMIT 1
            )
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"id_contrato": contrato["id_contrato_alquiler"]},
    ).scalar_one()

    # Insertar segundo obligado con 50%
    db_session.execute(
        text(
            """
            INSERT INTO obligacion_obligado (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_obligacion_financiera, id_persona,
                rol_obligado, porcentaje_responsabilidad
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_ob, :id_persona2, 'GARANTE', 50.00
            )
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "id_ob": ob_row, "id_persona2": id_persona2},
    )

    resp = client.get(_url(id_persona2), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["obligaciones"]) == 1
    ob = data["obligaciones"][0]
    assert ob["porcentaje_responsabilidad"] == pytest.approx(50.0)
    assert ob["monto_responsabilidad"] == pytest.approx(20000.00)
    assert ob["saldo_pendiente"] == pytest.approx(40000.00)


def test_estado_cuenta_persona_404_si_persona_no_existe(client) -> None:
    """Persona inexistente devuelve 404."""
    resp = client.get(_url(999999), headers=HEADERS)

    assert resp.status_code == 404
    body = resp.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_estado_cuenta_persona_filtra_por_tipo_origen(client, db_session) -> None:
    """Filtro tipo_origen=CONTRATO_ALQUILER incluye; tipo_origen=VENTA devuelve vacío."""
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-TIP-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=15000.00,
    )

    resp_loc = client.get(
        _url(id_persona), headers=HEADERS, params={"tipo_origen": "CONTRATO_ALQUILER"}
    )
    assert resp_loc.status_code == 200
    assert len(resp_loc.json()["data"]["obligaciones"]) == 1

    resp_venta = client.get(
        _url(id_persona), headers=HEADERS, params={"tipo_origen": "VENTA"}
    )
    assert resp_venta.status_code == 200
    assert resp_venta.json()["data"]["obligaciones"] == []


def test_estado_cuenta_persona_filtra_por_vencidas(client, db_session) -> None:
    """Filtro vencidas=True devuelve solo las obligaciones vencidas con saldo."""
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-VENC-001",
        fecha_inicio="2026-04-01",
        fecha_fin="2026-06-30",
        monto=10000.00,
        dia_vencimiento_canon=1,
    )

    resp = client.get(_url(id_persona), headers=HEADERS, params={"vencidas": True})

    assert resp.status_code == 200
    data = resp.json()["data"]
    # Solo Abril tiene vencimiento < hoy
    assert len(data["obligaciones"]) == 1
    ob = data["obligaciones"][0]
    assert ob["fecha_vencimiento"] < str(date.today())
