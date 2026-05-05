"""
Tests de integración para POST /api/v1/financiero/personas/{id_persona}/simular-pago.
La simulación no persiste cambios.
"""
from pathlib import Path

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

URL = "/api/v1/financiero/personas/{id_persona}/simular-pago"
TASA_DIARIA_MORA = float(TASA_DIARIA_MORA_DEFAULT)
PATCH_PARAMETRO_PUNITORIO_SQL = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "patch_parametro_punitorio_20260505.sql"
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _url(id_persona: int) -> str:
    return URL.format(id_persona=id_persona)


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


def _install_patch_parametro_punitorio(db_session) -> None:
    sql = PATCH_PARAMETRO_PUNITORIO_SQL.read_text(encoding="utf-8").replace("%", "%%")
    db_session.connection().exec_driver_sql(sql)


def _simular(client, id_persona: int, monto: float, fecha_corte: str | None = None) -> dict:
    body: dict = {"monto": monto}
    if fecha_corte:
        body["fecha_corte"] = fecha_corte
    resp = client.post(_url(id_persona), headers=HEADERS, json=body)
    assert resp.status_code == 200
    return resp.json()["data"]


def _pagar(client, id_persona: int, monto: float, fecha_pago: str | None = None) -> dict:
    headers = {k: v for k, v in HEADERS.items() if k != "X-Op-Id"}
    body: dict = {"monto": monto}
    if fecha_pago:
        body["fecha_pago"] = fecha_pago
    resp = client.post(
        "/api/v1/financiero/pagos",
        headers=headers,
        params={"id_persona": id_persona},
        json=body,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _saldo_obligacion_por_contrato(db_session, id_contrato: int) -> dict:
    row = db_session.execute(
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
            LIMIT 1
            """
        ),
        {"id": id_contrato},
    ).mappings().one()
    return dict(row)


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


def _concepto_id(db_session, codigo: str) -> int:
    return db_session.execute(
        text(
            """
            SELECT id_concepto_financiero
            FROM concepto_financiero
            WHERE codigo_concepto_financiero = :codigo
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"codigo": codigo},
    ).scalar_one()


def _reset_parametros_punitorio(db_session) -> None:
    db_session.execute(text("DELETE FROM parametro_punitorio"))


def _insert_parametro_punitorio(
    db_session,
    *,
    alcance_tipo: str,
    tasa_diaria: float,
    dias_gracia: int = 5,
    fecha_desde: str = "1900-01-01",
    fecha_hasta: str | None = None,
    estado_parametro: str = "ACTIVO",
    id_relacion_generadora: int | None = None,
    id_concepto_financiero: int | None = None,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO parametro_punitorio (
                alcance_tipo,
                id_relacion_generadora,
                id_concepto_financiero,
                tasa_diaria,
                dias_gracia,
                fecha_desde,
                fecha_hasta,
                estado_parametro
            )
            VALUES (
                :alcance_tipo,
                :id_relacion_generadora,
                :id_concepto_financiero,
                :tasa_diaria,
                :dias_gracia,
                :fecha_desde,
                :fecha_hasta,
                :estado_parametro
            )
            """
        ),
        {
            "alcance_tipo": alcance_tipo,
            "id_relacion_generadora": id_relacion_generadora,
            "id_concepto_financiero": id_concepto_financiero,
            "tasa_diaria": tasa_diaria,
            "dias_gracia": dias_gracia,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "estado_parametro": estado_parametro,
        },
    )


def _saldo_componente(db_session, id_obligacion: int, codigo: str) -> float | None:
    row = db_session.execute(
        text(
            """
            SELECT c.saldo_componente
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE c.id_obligacion_financiera = :id
              AND cf.codigo_concepto_financiero = :codigo
              AND c.deleted_at IS NULL
              AND cf.deleted_at IS NULL
            ORDER BY c.id_composicion_obligacion ASC
            LIMIT 1
            """
        ),
        {"id": id_obligacion, "codigo": codigo},
    ).scalar_one_or_none()
    return float(row) if row is not None else None


# ── tests ─────────────────────────────────────────────────────────────────────

def test_simular_pago_cubre_deuda_total(client, db_session) -> None:
    """Monto >= deuda total → monto_aplicado = deuda, remanente = monto - deuda."""
    id_persona, _ = _setup(
        client, db_session,
        codigo="SIM-TOT-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
        monto=10000.00,
    )
    # 2 períodos × 10000 = deuda total 20000
    data = _simular(client, id_persona, monto=25000.00)

    assert data["monto_ingresado"] == pytest.approx(25000.00)
    assert data["monto_aplicado"] == pytest.approx(20000.00)
    assert data["remanente"] == pytest.approx(5000.00)
    assert data["total_deuda_considerada"] == pytest.approx(20000.00)
    assert len(data["detalle"]) == 2
    for d in data["detalle"]:
        assert d["saldo_restante_simulado"] == pytest.approx(0.0)
        assert d["monto_aplicado"] == pytest.approx(d["total_a_cubrir"])


def test_simular_pago_parcial(client, db_session) -> None:
    """Monto cubre solo la primera obligación; segunda queda con saldo."""
    id_persona, _ = _setup(
        client, db_session,
        codigo="SIM-PARC-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
        monto=10000.00,
    )
    # primera cubre totalmente, segunda queda sin cubrir
    data = _simular(client, id_persona, monto=10000.00)

    assert data["monto_aplicado"] == pytest.approx(10000.00)
    assert data["remanente"] == pytest.approx(0.0)
    assert len(data["detalle"]) == 2
    assert data["detalle"][0]["monto_aplicado"] == pytest.approx(10000.00)
    assert data["detalle"][0]["saldo_restante_simulado"] == pytest.approx(0.0)
    assert data["detalle"][1]["monto_aplicado"] == pytest.approx(0.0)
    assert data["detalle"][1]["saldo_restante_simulado"] == pytest.approx(10000.00)


def test_simular_pago_persona_sin_deuda(client, db_session) -> None:
    """Persona sin obligaciones → detalle vacío, monto_aplicado=0, remanente=monto."""
    resp_p = client.post(
        "/api/v1/personas", headers=HEADERS,
        json={"tipo_persona": "FISICA", "nombre": "Sin", "apellido": "Deuda",
              "razon_social": None, "estado_persona": "ACTIVA", "observaciones": None},
    )
    assert resp_p.status_code == 201
    id_persona = resp_p.json()["data"]["id_persona"]

    data = _simular(client, id_persona, monto=5000.00)

    assert data["monto_aplicado"] == pytest.approx(0.0)
    assert data["remanente"] == pytest.approx(5000.00)
    assert data["total_deuda_considerada"] == pytest.approx(0.0)
    assert data["detalle"] == []


def test_simular_pago_incluye_mora_dinamica(client, db_session) -> None:
    """
    Obligación con vencimiento 2026-05-15, saldo 50000.
    fecha_corte=2026-05-25 → 5 días de mora por gracia.
    total_a_cubrir = saldo + mora con tasa diaria centralizada.
    """
    id_persona, _ = _setup(
        client, db_session,
        codigo="SIM-MORA-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=50000.00,
        dia_vencimiento_canon=15,
    )

    data = _simular(client, id_persona, monto=999999.00, fecha_corte="2026-05-25")

    ob = data["detalle"][0]
    mora_esperada = 50000.00 * TASA_DIARIA_MORA * 10
    assert ob["mora_calculada"] == pytest.approx(mora_esperada)
    assert ob["total_a_cubrir"] == pytest.approx(50000.00 + mora_esperada)
    assert data["total_deuda_considerada"] == pytest.approx(50000.00 + mora_esperada)


def test_simular_pago_mora_respeta_dias_gracia(client, db_session) -> None:
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="SIM-GRACIA-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    dentro = _simular(client, id_persona, monto=999999.00, fecha_corte="2026-05-14")
    limite = _simular(client, id_persona, monto=999999.00, fecha_corte="2026-05-15")
    fuera = _simular(client, id_persona, monto=999999.00, fecha_corte="2026-05-16")

    assert dentro["detalle"][0]["mora_calculada"] == pytest.approx(0.00)
    assert limite["detalle"][0]["mora_calculada"] == pytest.approx(0.00)
    assert fuera["detalle"][0]["mora_calculada"] == pytest.approx(
        10000.00 * TASA_DIARIA_MORA * 6
    )


def test_parametro_punitorio_sin_fila_usa_default_tecnico(client, db_session) -> None:
    _install_patch_parametro_punitorio(db_session)
    _reset_parametros_punitorio(db_session)
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="SIM-PARAM-DEFAULT-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    data = _simular(client, id_persona, monto=999999.00, fecha_corte="2026-05-16")

    assert data["detalle"][0]["mora_calculada"] == pytest.approx(
        10000.00 * TASA_DIARIA_MORA * 6
    )


def test_parametro_punitorio_global_vigente_se_usa_en_simulacion_y_pago(
    client, db_session
) -> None:
    _install_patch_parametro_punitorio(db_session)
    _reset_parametros_punitorio(db_session)
    _insert_parametro_punitorio(
        db_session,
        alcance_tipo="GLOBAL",
        tasa_diaria=0.002,
        dias_gracia=5,
    )
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="SIM-PARAM-GLOBAL-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    sim = _simular(client, id_persona, monto=999999.00, fecha_corte="2026-05-16")
    pago = _pagar(client, id_persona, monto=999999.00, fecha_pago="2026-05-16")

    esperado = 10000.00 + (10000.00 * 0.002 * 6)
    assert sim["detalle"][0]["mora_calculada"] == pytest.approx(120.00)
    assert sim["total_deuda_considerada"] == pytest.approx(esperado)
    assert pago["monto_aplicado"] == pytest.approx(esperado)


def test_parametro_punitorio_concepto_overridea_global(client, db_session) -> None:
    _install_patch_parametro_punitorio(db_session)
    _reset_parametros_punitorio(db_session)
    _insert_parametro_punitorio(
        db_session,
        alcance_tipo="GLOBAL",
        tasa_diaria=0.001,
        dias_gracia=5,
    )
    _insert_parametro_punitorio(
        db_session,
        alcance_tipo="CONCEPTO",
        id_concepto_financiero=_concepto_id(db_session, "CANON_LOCATIVO"),
        tasa_diaria=0.003,
        dias_gracia=5,
    )
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="SIM-PARAM-CONC-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    data = _simular(client, id_persona, monto=999999.00, fecha_corte="2026-05-16")

    assert data["detalle"][0]["mora_calculada"] == pytest.approx(10000.00 * 0.003 * 6)


def test_parametro_punitorio_relacion_overridea_concepto(client, db_session) -> None:
    _install_patch_parametro_punitorio(db_session)
    _reset_parametros_punitorio(db_session)
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="SIM-PARAM-REL-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    _insert_parametro_punitorio(
        db_session,
        alcance_tipo="GLOBAL",
        tasa_diaria=0.001,
        dias_gracia=5,
    )
    _insert_parametro_punitorio(
        db_session,
        alcance_tipo="CONCEPTO",
        id_concepto_financiero=_concepto_id(db_session, "CANON_LOCATIVO"),
        tasa_diaria=0.003,
        dias_gracia=5,
    )
    _insert_parametro_punitorio(
        db_session,
        alcance_tipo="RELACION_GENERADORA",
        id_relacion_generadora=_relacion_por_contrato(
            db_session, contrato["id_contrato_alquiler"]
        ),
        tasa_diaria=0.004,
        dias_gracia=5,
    )

    data = _simular(client, id_persona, monto=999999.00, fecha_corte="2026-05-16")

    assert data["detalle"][0]["mora_calculada"] == pytest.approx(10000.00 * 0.004 * 6)


def test_parametro_punitorio_respeta_vigencia_e_inactivos(client, db_session) -> None:
    _install_patch_parametro_punitorio(db_session)
    _reset_parametros_punitorio(db_session)
    _insert_parametro_punitorio(
        db_session,
        alcance_tipo="GLOBAL",
        tasa_diaria=0.009,
        dias_gracia=5,
        estado_parametro="INACTIVO",
    )
    _insert_parametro_punitorio(
        db_session,
        alcance_tipo="GLOBAL",
        tasa_diaria=0.008,
        dias_gracia=5,
        fecha_desde="2026-04-01",
        fecha_hasta="2026-05-15",
    )
    _insert_parametro_punitorio(
        db_session,
        alcance_tipo="GLOBAL",
        tasa_diaria=0.002,
        dias_gracia=5,
        fecha_desde="2026-05-16",
    )
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="SIM-PARAM-VIG-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    data = _simular(client, id_persona, monto=999999.00, fecha_corte="2026-05-16")

    assert data["detalle"][0]["mora_calculada"] == pytest.approx(10000.00 * 0.002 * 6)


def test_simular_pago_punitorio_existente_no_integra_base_morable(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="SIM-PUNIT-MORABLE-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=50.00, fecha_pago="2026-05-20")
    ob_antes = _saldo_obligacion_por_contrato(
        db_session, contrato["id_contrato_alquiler"]
    )
    assert float(ob_antes["saldo_pendiente"]) == pytest.approx(10050.00)
    assert _saldo_componente(
        db_session, ob_antes["id_obligacion_financiera"], "PUNITORIO"
    ) == pytest.approx(50.00)

    sim = _simular(client, id_persona, monto=10100.00, fecha_corte="2026-05-25")
    detalle = sim["detalle"][0]

    assert detalle["saldo_pendiente"] == pytest.approx(10050.00)
    assert detalle["mora_calculada"] == pytest.approx(
        10000.00 * TASA_DIARIA_MORA * 5
    )
    assert detalle["total_a_cubrir"] == pytest.approx(10100.00)
    assert sim["monto_aplicado"] == pytest.approx(10100.00)
    assert sim["remanente"] == pytest.approx(0.00)

    ob_despues_sim = _saldo_obligacion_por_contrato(
        db_session, contrato["id_contrato_alquiler"]
    )
    assert float(ob_despues_sim["saldo_pendiente"]) == pytest.approx(10050.00)

    pago = _pagar(client, id_persona, monto=10100.00, fecha_pago="2026-05-25")

    assert pago["monto_aplicado"] == pytest.approx(sim["monto_aplicado"])
    assert pago["remanente"] == pytest.approx(sim["remanente"])
    assert pago["obligaciones_pagadas"][0]["monto_aplicado"] == pytest.approx(
        detalle["total_a_cubrir"]
    )


def test_simular_pago_remanente_cuando_sobra_monto(client, db_session) -> None:
    """Monto >> deuda → remanente = monto - total_deuda."""
    id_persona, _ = _setup(
        client, db_session,
        codigo="SIM-REM-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )

    data = _simular(client, id_persona, monto=50000.00)

    assert data["remanente"] == pytest.approx(40000.00)
    assert data["monto_aplicado"] == pytest.approx(10000.00)


def test_simular_pago_no_modifica_saldos_en_db(client, db_session) -> None:
    """Después de simular, los saldos en DB no cambian."""
    id_persona, contrato = _setup(
        client, db_session,
        codigo="SIM-NODB-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=30000.00,
    )

    # Leer saldo antes
    saldo_antes = db_session.execute(
        text(
            """
            SELECT SUM(o.saldo_pendiente)
            FROM obligacion_financiera o
            WHERE o.id_relacion_generadora = (
                SELECT id_relacion_generadora FROM relacion_generadora
                WHERE tipo_origen = 'contrato_alquiler'
                  AND id_origen = :id AND deleted_at IS NULL LIMIT 1
            ) AND o.deleted_at IS NULL
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).scalar()

    _simular(client, id_persona, monto=30000.00)

    # Leer saldo después
    saldo_despues = db_session.execute(
        text(
            """
            SELECT SUM(o.saldo_pendiente)
            FROM obligacion_financiera o
            WHERE o.id_relacion_generadora = (
                SELECT id_relacion_generadora FROM relacion_generadora
                WHERE tipo_origen = 'contrato_alquiler'
                  AND id_origen = :id AND deleted_at IS NULL LIMIT 1
            ) AND o.deleted_at IS NULL
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).scalar()

    assert float(saldo_antes) == float(saldo_despues)


def test_simular_pago_vencidas_primero(client, db_session) -> None:
    """
    Dos obligaciones: una con vencimiento cercano (2026-05-15) y otra lejano (2026-12-31).
    Con fecha_corte=2026-06-01: mayo es vencida → aparece primero en detalle.
    """
    id_persona, _ = _setup(
        client, db_session,
        codigo="SIM-ORD-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
        monto=10000.00,
        dia_vencimiento_canon=1,
    )
    # Mayo: venc 2026-05-01, Junio: venc 2026-06-01
    # Con fecha_corte=2026-06-15: mayo < junio_15 → vencida; junio_01 < junio_15 → vencida también
    # Usar fecha_corte=2026-05-15: mayo (05-01) < 05-15 → vencida; junio (06-01) >= 05-15 → futura
    data = _simular(client, id_persona, monto=1.00, fecha_corte="2026-05-15")

    assert len(data["detalle"]) == 2
    # primera obligación debe ser la vencida (mayo: 2026-05-01 < 2026-05-15)
    # segunda la futura (junio: 2026-06-01 >= 2026-05-15)
    # Verificamos que la primera tiene mora (vencida) y la segunda no
    assert data["detalle"][0]["mora_calculada"] > 0
    assert data["detalle"][1]["mora_calculada"] == pytest.approx(0.0)


def test_simular_pago_404_persona_inexistente(client) -> None:
    """Persona inexistente → 404."""
    resp = client.post(_url(999999), headers=HEADERS, json={"monto": 1000.0})
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_simular_pago_400_monto_cero(client, db_session) -> None:
    """monto=0 → 422 por validación Pydantic."""
    resp_p = client.post(
        "/api/v1/personas", headers=HEADERS,
        json={"tipo_persona": "FISICA", "nombre": "Test", "apellido": "MC",
              "razon_social": None, "estado_persona": "ACTIVA", "observaciones": None},
    )
    id_persona = resp_p.json()["data"]["id_persona"]

    resp = client.post(_url(id_persona), headers=HEADERS, json={"monto": 0})
    assert resp.status_code == 422
