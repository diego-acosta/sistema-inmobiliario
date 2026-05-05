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
    headers = {k: v for k, v in HEADERS.items() if k != "X-Op-Id"}
    return _pagar_con_headers(client, id_persona, monto, fecha_pago=fecha_pago, headers=headers)


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


def _relacion_por_contrato(db_session, id_contrato: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT id_relacion_generadora
            FROM relacion_generadora
            WHERE tipo_origen = 'contrato_alquiler'
              AND id_origen = :id
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"id": id_contrato},
    ).scalar_one()


def _composiciones_por_obligacion(db_session, id_obligacion: int) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT
                c.id_composicion_obligacion,
                cf.codigo_concepto_financiero,
                c.importe_componente,
                c.saldo_componente
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE c.id_obligacion_financiera = :id
              AND c.deleted_at IS NULL
            ORDER BY c.orden_composicion ASC
            """
        ),
        {"id": id_obligacion},
    ).mappings().all()
    return [dict(r) for r in rows]


def _composicion(db_session, id_obligacion: int, codigo: str) -> dict | None:
    for comp in _composiciones_por_obligacion(db_session, id_obligacion):
        if comp["codigo_concepto_financiero"] == codigo:
            return comp
    return None


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
    El punitorio usa tasa diaria centralizada y gracia como umbral.
    Fuera de gracia calcula desde vencimiento y persiste como PUNITORIO.
    """
    id_persona, _ = _setup(
        client, db_session,
        codigo="PAG-MORA-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=50000.00,
        dia_vencimiento_canon=15,
    )

    monto_con_mora = 50000.00 + (50000.00 * TASA_DIARIA_MORA * 10)
    data = _pagar(client, id_persona, monto=monto_con_mora, fecha_pago="2026-05-25")

    assert data["monto_ingresado"] == pytest.approx(monto_con_mora)
    assert data["monto_aplicado"] == pytest.approx(monto_con_mora)
    assert data["remanente"] == pytest.approx(0.0)
    ob = data["obligaciones_pagadas"][0]
    assert ob["estado_resultante"] == "CANCELADA"


def test_pago_posterior_a_gracia_crea_composicion_punitorio(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-CREA-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=10060.00, fecha_pago="2026-05-16")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    punitorio = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")

    assert punitorio is not None
    assert float(punitorio["importe_componente"]) == pytest.approx(60.00)
    assert float(punitorio["saldo_componente"]) == pytest.approx(0.00)


def test_pago_dentro_de_gracia_no_crea_punitorio(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-GRACIA-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=500.00, fecha_pago="2026-05-15")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    assert _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO") is None


def test_primer_pago_posterior_a_gracia_calcula_desde_vencimiento(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-DESDE-VTO-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=100.00, fecha_pago="2026-05-20")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    punitorio = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")

    assert punitorio is not None
    assert float(punitorio["importe_componente"]) == pytest.approx(100.00)
    assert float(punitorio["saldo_componente"]) == pytest.approx(0.00)


def test_pago_anterior_al_vencimiento_no_corta_tramo(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-PREVIO-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=1000.00, fecha_pago="2026-05-05")
    _pagar(client, id_persona, monto=90.00, fecha_pago="2026-05-20")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    punitorio = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")

    assert punitorio is not None
    assert float(punitorio["importe_componente"]) == pytest.approx(90.00)


def test_segundo_pago_posterior_calcula_desde_ultimo_pago_posterior(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-SEGUNDO-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=1000.00, fecha_pago="2026-05-20")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    punitorio_1 = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")
    assert punitorio_1 is not None
    assert float(punitorio_1["importe_componente"]) == pytest.approx(100.00)

    _pagar(client, id_persona, monto=45.50, fecha_pago="2026-05-25")
    punitorio_2 = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")
    count_punitorio = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM composicion_obligacion co
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
            WHERE co.id_obligacion_financiera = :id
              AND cf.codigo_concepto_financiero = 'PUNITORIO'
              AND co.deleted_at IS NULL
            """
        ),
        {"id": ob["id_obligacion_financiera"]},
    ).scalar_one()

    assert punitorio_2 is not None
    assert count_punitorio == 1
    assert float(punitorio_2["importe_componente"]) == pytest.approx(145.50)
    assert float(punitorio_2["saldo_componente"]) == pytest.approx(0.00)


def test_pago_parcial_solo_parte_punitorio_deja_saldo_pendiente(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-PARCIAL-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=50.00, fecha_pago="2026-05-20")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    punitorio = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")
    canon = _composicion(db_session, ob["id_obligacion_financiera"], "CANON_LOCATIVO")

    assert punitorio is not None
    assert float(punitorio["importe_componente"]) == pytest.approx(100.00)
    assert float(punitorio["saldo_componente"]) == pytest.approx(50.00)
    assert canon is not None
    assert float(canon["saldo_componente"]) == pytest.approx(10000.00)
    assert float(ob["saldo_pendiente"]) == pytest.approx(10050.00)


def test_retry_mismo_op_id_no_duplica_punitorio(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-IDEM-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440101"}

    data_1 = _pagar_con_headers(client, id_persona, monto=50.00, fecha_pago="2026-05-20", headers=headers)
    data_2 = _pagar_con_headers(client, id_persona, monto=50.00, fecha_pago="2026-05-20", headers=headers)
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    comps = [
        c for c in _composiciones_por_obligacion(db_session, ob["id_obligacion_financiera"])
        if c["codigo_concepto_financiero"] == "PUNITORIO"
    ]

    assert data_2 == data_1
    assert len(comps) == 1
    assert float(comps[0]["importe_componente"]) == pytest.approx(100.00)
    assert float(comps[0]["saldo_componente"]) == pytest.approx(50.00)


def test_saldo_pendiente_obligacion_incluye_punitorio_pendiente(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-SALDO-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=50.00, fecha_pago="2026-05-20")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    assert float(ob["saldo_pendiente"]) == pytest.approx(10050.00)


def test_estado_cuenta_muestra_composicion_punitorio_persistida(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-EC-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=50.00, fecha_pago="2026-05-20")
    id_relacion = _relacion_por_contrato(db_session, contrato["id_contrato_alquiler"])
    resp = client.get(
        "/api/v1/financiero/estado-cuenta",
        headers=HEADERS,
        params={"id_relacion_generadora": id_relacion},
    )

    assert resp.status_code == 200
    comps = resp.json()["data"]["obligaciones"][0]["composiciones"]
    punitorios = [c for c in comps if c["codigo_concepto_financiero"] == "PUNITORIO"]
    assert len(punitorios) == 1
    assert punitorios[0]["saldo_componente"] == pytest.approx(50.00)


def test_pago_persona_no_crea_interes_mora_en_v1(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-NO-INTERES-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=50.00, fecha_pago="2026-05-20")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    assert _composicion(db_session, ob["id_obligacion_financiera"], "INTERES_MORA") is None


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
    assert fuera["monto_aplicado"] == pytest.approx(10010.00)


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

    monto_con_mora = 50000.00 + (50000.00 * TASA_DIARIA_MORA * 10)
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
