"""
Tests de integración para POST /api/v1/financiero/pagos.
"""
import pytest
from sqlalchemy import text

from app.domain.financiero.parametros_mora import TASA_DIARIA_MORA_DEFAULT
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_event_contrato_alquiler import (
    _activar,
    _crear_condicion,
    _crear_contrato_borrador,
    _crear_locatario_principal,
)

URL = "/api/v1/financiero/pagos"
TASA_DIARIA_MORA = float(TASA_DIARIA_MORA_DEFAULT)


# ── helpers ───────────────────────────────────────────────────────────────────

def _setup(client, db_session, *, codigo: str, fecha_inicio: str, fecha_fin: str,
           monto: float = 20000.00, dia_vencimiento_canon: int | None = None) -> tuple[int, dict]:
    contrato = _crear_contrato_borrador(
        client, codigo=codigo,
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
        dia_vencimiento_canon=dia_vencimiento_canon,
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], monto, fecha_inicio)
    id_persona = _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])
    return id_persona, contrato


def _pagar(client, id_persona: int, monto: float, fecha_pago: str | None = None) -> dict:
    return _pagar_con_headers(client, id_persona, monto, fecha_pago=fecha_pago, headers=HEADERS)


def _pagar_con_headers(
    client,
    id_persona: int,
    monto: float,
    fecha_pago: str | None = None,
    headers: dict | None = None,
) -> dict:
    body: dict = {"monto": monto}
    if fecha_pago:
        body["fecha_pago"] = fecha_pago
    resp = client.post(
        URL, headers=headers or HEADERS,
        params={"id_persona": id_persona},
        json=body,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _saldos_por_contrato(db_session, id_contrato: int) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT o.id_obligacion_financiera, o.saldo_pendiente, o.estado_obligacion
            FROM obligacion_financiera o
            WHERE o.id_relacion_generadora = (
                SELECT id_relacion_generadora FROM relacion_generadora
                WHERE tipo_origen = 'contrato_alquiler'
                  AND id_origen = :id AND deleted_at IS NULL LIMIT 1
            ) AND o.deleted_at IS NULL
            ORDER BY o.id_obligacion_financiera ASC
            """
        ),
        {"id": id_contrato},
    ).mappings().all()
    return [dict(r) for r in rows]


def _count_pagos_por_op_id(db_session, op_id: str) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM movimiento_financiero
            WHERE op_id_alta = :op_id
              AND tipo_movimiento = 'PAGO'
              AND deleted_at IS NULL
            """
        ),
        {"op_id": op_id},
    ).scalar()


# ── tests ─────────────────────────────────────────────────────────────────────

def test_pago_total_cancela_obligaciones(client, db_session) -> None:
    """Pagar el monto total → todas las obligaciones CANCELADA, saldo=0."""
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-TOT-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
        monto=10000.00,
    )

    data = _pagar(client, id_persona, monto=20000.00)

    assert data["monto_aplicado"] == pytest.approx(20000.00)
    assert data["remanente"] == pytest.approx(0.0)
    assert len(data["obligaciones_pagadas"]) == 2
    for ob in data["obligaciones_pagadas"]:
        assert ob["estado_resultante"] == "CANCELADA"

    saldos = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])
    for s in saldos:
        assert float(s["saldo_pendiente"]) == pytest.approx(0.0)
        assert s["estado_obligacion"] == "CANCELADA"


def test_pago_parcial_reduce_saldo(client, db_session) -> None:
    """Monto parcial → primera obligación CANCELADA, segunda PARCIALMENTE_CANCELADA."""
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-PARC-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
        monto=10000.00,
    )

    data = _pagar(client, id_persona, monto=15000.00)

    assert data["monto_aplicado"] == pytest.approx(15000.00)
    assert data["remanente"] == pytest.approx(0.0)
    assert len(data["obligaciones_pagadas"]) == 2
    # Primera cubierta totalmente
    assert data["obligaciones_pagadas"][0]["estado_resultante"] == "CANCELADA"
    # Segunda parcialmente
    assert data["obligaciones_pagadas"][1]["estado_resultante"] == "PARCIALMENTE_CANCELADA"

    saldos = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])
    assert float(saldos[0]["saldo_pendiente"]) == pytest.approx(0.0)
    assert float(saldos[1]["saldo_pendiente"]) == pytest.approx(5000.00)


def test_pago_multiples_obligaciones(client, db_session) -> None:
    """Pago cubre 3 obligaciones generadas por contrato trimestral."""
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-MULT-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
        monto=10000.00,
    )

    data = _pagar(client, id_persona, monto=30000.00)

    assert len(data["obligaciones_pagadas"]) == 3
    assert data["monto_aplicado"] == pytest.approx(30000.00)
    assert data["remanente"] == pytest.approx(0.0)


def test_pago_persona_sin_deuda_no_aplica(client, db_session) -> None:
    """Persona sin obligaciones → monto_aplicado=0, remanente=monto."""
    resp_p = client.post(
        "/api/v1/personas", headers=HEADERS,
        json={"tipo_persona": "FISICA", "nombre": "Sin", "apellido": "Deuda",
              "razon_social": None, "estado_persona": "ACTIVA", "observaciones": None},
    )
    id_persona = resp_p.json()["data"]["id_persona"]

    data = _pagar(client, id_persona, monto=5000.00)

    assert data["monto_aplicado"] == pytest.approx(0.0)
    assert data["remanente"] == pytest.approx(5000.00)
    assert data["obligaciones_pagadas"] == []


def test_pago_con_mora_consume_del_monto(client, db_session) -> None:
    """
    Obligación saldo=50000, vencimiento=2026-05-15, fecha_pago=2026-05-25.
    La mora usa la tasa diaria centralizada y 5 dias por gracia.
    Pagando saldo + mora: el monto se consume integro (remanente=0).
    DB saldo reducido en 50000 (mora no persiste en DB). Estado CANCELADA.
    """
    id_persona, _ = _setup(
        client, db_session,
        codigo="PAG-MORA-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=50000.00,
        dia_vencimiento_canon=15,
    )

    monto_con_mora = 50000.00 + (50000.00 * TASA_DIARIA_MORA * 5)
    data = _pagar(client, id_persona, monto=monto_con_mora, fecha_pago="2026-05-25")

    # La mora consume del monto, pero no se aplica a saldo.
    assert data["monto_ingresado"] == pytest.approx(monto_con_mora)
    assert data["monto_aplicado"] == pytest.approx(50000.00)
    assert data["remanente"] == pytest.approx(0.0)
    ob = data["obligaciones_pagadas"][0]
    assert ob["estado_resultante"] == "CANCELADA"


def test_pago_mora_respeta_dias_gracia(client, db_session) -> None:
    id_persona_dentro, _ = _setup(
        client,
        db_session,
        codigo="PAG-GRACIA-DENTRO-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    dentro = _pagar(client, id_persona_dentro, monto=10010.00, fecha_pago="2026-05-14")

    id_persona_limite, _ = _setup(
        client,
        db_session,
        codigo="PAG-GRACIA-LIMITE-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    limite = _pagar(client, id_persona_limite, monto=10010.00, fecha_pago="2026-05-15")

    id_persona_fuera, _ = _setup(
        client,
        db_session,
        codigo="PAG-GRACIA-FUERA-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    fuera = _pagar(client, id_persona_fuera, monto=10010.00, fecha_pago="2026-05-16")

    assert dentro["remanente"] == pytest.approx(10.00)
    assert limite["remanente"] == pytest.approx(10.00)
    assert fuera["remanente"] == pytest.approx(0.00)
    assert fuera["monto_aplicado"] == pytest.approx(10000.00)


def test_pago_remanente_si_sobra_monto(client, db_session) -> None:
    """Monto > deuda total → remanente = monto - deuda."""
    id_persona, _ = _setup(
        client, db_session,
        codigo="PAG-REM-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )

    data = _pagar(client, id_persona, monto=50000.00)

    assert data["remanente"] == pytest.approx(40000.00)
    assert data["monto_aplicado"] == pytest.approx(10000.00)


def test_pago_no_duplica_saldo_en_llamada_simple(client, db_session) -> None:
    """Una sola llamada aplica exactamente monto; no dobla el efecto."""
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-DUP-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )

    _pagar(client, id_persona, monto=5000.00)

    saldos = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])
    assert float(saldos[0]["saldo_pendiente"]) == pytest.approx(5000.00)
    assert saldos[0]["estado_obligacion"] == "PARCIALMENTE_CANCELADA"


def test_pago_404_persona_inexistente(client) -> None:
    """Persona inexistente → 404."""
    resp = client.post(
        URL, headers=HEADERS,
        params={"id_persona": 999999},
        json={"monto": 1000.0},
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_pago_422_monto_invalido(client, db_session) -> None:
    """monto=0 → 422 por validación Pydantic."""
    resp_p = client.post(
        "/api/v1/personas", headers=HEADERS,
        json={"tipo_persona": "FISICA", "nombre": "Test", "apellido": "P",
              "razon_social": None, "estado_persona": "ACTIVA", "observaciones": None},
    )
    id_persona = resp_p.json()["data"]["id_persona"]
    resp = client.post(
        URL, headers=HEADERS,
        params={"id_persona": id_persona},
        json={"monto": 0},
    )
    assert resp.status_code == 422


def test_pago_atomico_crea_movimiento_y_aplicacion(client, db_session) -> None:
    """Verificar que movimiento_financiero y aplicacion_financiera existen en DB después del pago."""
    id_persona, _ = _setup(
        client, db_session,
        codigo="PAG-MOV-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )

    data = _pagar(client, id_persona, monto=10000.00)

    id_mov = data["obligaciones_pagadas"][0]["id_movimiento_financiero"]

    count_mov = db_session.execute(
        text("SELECT COUNT(*) FROM movimiento_financiero WHERE id_movimiento_financiero = :id"),
        {"id": id_mov},
    ).scalar()
    count_aplic = db_session.execute(
        text("SELECT COUNT(*) FROM aplicacion_financiera WHERE id_movimiento_financiero = :id"),
        {"id": id_mov},
    ).scalar()

    assert count_mov == 1
    assert count_aplic >= 1


def test_pago_retry_mismo_op_id_no_duplica_movimiento_ni_saldo(client, db_session) -> None:
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-IDEM-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440001"}

    data_1 = _pagar_con_headers(client, id_persona, monto=5000.00, headers=headers)
    saldo_1 = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    data_2 = _pagar_con_headers(client, id_persona, monto=5000.00, headers=headers)
    saldo_2 = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    assert data_2 == data_1
    assert _count_pagos_por_op_id(db_session, headers["X-Op-Id"]) == 1
    assert float(saldo_1["saldo_pendiente"]) == pytest.approx(5000.00)
    assert float(saldo_2["saldo_pendiente"]) == pytest.approx(5000.00)


def test_pago_retry_mismo_op_id_con_mora_devuelve_resultado_original(client, db_session) -> None:
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-IDEM-MORA-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=50000.00,
        dia_vencimiento_canon=15,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440004"}

    monto_con_mora = 50000.00 + (50000.00 * TASA_DIARIA_MORA * 5)
    data_1 = _pagar_con_headers(
        client, id_persona, monto=monto_con_mora, fecha_pago="2026-05-25", headers=headers
    )
    data_2 = _pagar_con_headers(
        client, id_persona, monto=monto_con_mora, fecha_pago="2026-05-25", headers=headers
    )
    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    assert data_2 == data_1
    assert data_2["remanente"] == pytest.approx(0.0)
    assert _count_pagos_por_op_id(db_session, headers["X-Op-Id"]) == 1
    assert float(saldo["saldo_pendiente"]) == pytest.approx(0.0)


def test_pago_op_id_distinto_registra_nuevo_pago_si_queda_saldo(client, db_session) -> None:
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-IDEM-002",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )
    headers_1 = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440002"}
    headers_2 = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440003"}

    _pagar_con_headers(client, id_persona, monto=3000.00, headers=headers_1)
    _pagar_con_headers(client, id_persona, monto=3000.00, headers=headers_2)

    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    assert _count_pagos_por_op_id(db_session, headers_1["X-Op-Id"]) == 1
    assert _count_pagos_por_op_id(db_session, headers_2["X-Op-Id"]) == 1
    assert float(saldo["saldo_pendiente"]) == pytest.approx(4000.00)


def test_pago_sin_op_id_mantiene_comportamiento_no_idempotente(client, db_session) -> None:
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-IDEM-003",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )
    headers = {k: v for k, v in HEADERS.items() if k != "X-Op-Id"}

    _pagar_con_headers(client, id_persona, monto=3000.00, headers=headers)
    _pagar_con_headers(client, id_persona, monto=3000.00, headers=headers)

    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    count_mov = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM movimiento_financiero
            WHERE tipo_movimiento = 'PAGO'
              AND op_id_alta IS NULL
              AND deleted_at IS NULL
            """
        )
    ).scalar()

    assert count_mov == 2
    assert float(saldo["saldo_pendiente"]) == pytest.approx(4000.00)
