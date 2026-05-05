"""
Tests de integración para POST /api/v1/financiero/pagos.
"""
from pathlib import Path

import pytest
from sqlalchemy import text

from app.domain.financiero.parametros_mora import TASA_DIARIA_MORA_DEFAULT
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_event_contrato_alquiler import (
    _activar,
    _crear_condicion,
    _crear_contrato_borrador,
    _crear_locatario_principal,
)
from tests.test_fin_imputaciones_create import (
    _crear_obligacion,
    _crear_rg,
)

URL = "/api/v1/financiero/pagos"
TASA_DIARIA_MORA = float(TASA_DIARIA_MORA_DEFAULT)
PATCH_VALIDACION_APLICACION_SQL = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "patch_aplicacion_validacion_ignora_soft_deleted_20260505.sql"
)


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


def _install_patch_validacion_aplicacion(db_session) -> None:
    sql = PATCH_VALIDACION_APLICACION_SQL.read_text(encoding="utf-8").replace("%", "%%")
    db_session.connection().exec_driver_sql(sql)


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


def _liquidaciones_punitorio(db_session, id_obligacion: int) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT
                id_liquidacion_punitorio,
                id_obligacion_financiera,
                id_composicion_obligacion,
                uid_pago_grupo,
                codigo_pago_grupo,
                fecha_vencimiento,
                fecha_inicio_calculo,
                fecha_fin_calculo,
                base_morable,
                tasa_diaria,
                dias_calculados,
                importe_liquidado,
                estado_liquidacion,
                op_id_alta
            FROM liquidacion_punitorio
            WHERE id_obligacion_financiera = :id
              AND deleted_at IS NULL
              AND estado_liquidacion = 'ACTIVA'
            ORDER BY id_liquidacion_punitorio ASC
            """
        ),
        {"id": id_obligacion},
    ).mappings().all()
    return [dict(r) for r in rows]


def _set_aplica_punitorio(db_session, codigo: str, aplica: bool) -> None:
    db_session.execute(
        text(
            """
            UPDATE concepto_financiero
            SET aplica_punitorio = :aplica
            WHERE codigo_concepto_financiero = :codigo
              AND deleted_at IS NULL
            """
        ),
        {"codigo": codigo, "aplica": aplica},
    )


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


def _movimientos_pago_por_op_id(db_session, op_id: str) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT
                id_movimiento_financiero,
                uid_pago_grupo,
                codigo_pago_grupo
            FROM movimiento_financiero
            WHERE op_id_alta = :op_id
              AND tipo_movimiento = 'PAGO'
              AND deleted_at IS NULL
            ORDER BY id_movimiento_financiero ASC
            """
        ),
        {"op_id": op_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _post_pago(
    client,
    *,
    id_persona: int,
    monto: float,
    headers: dict,
    fecha_pago: str | None = None,
):
    body: dict = {"monto": monto}
    if fecha_pago is not None:
        body["fecha_pago"] = fecha_pago
    return client.post(URL, headers=headers, params={"id_persona": id_persona}, json=body)


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

    data = _pagar(client, id_persona, monto=10060.00, fecha_pago="2026-05-16")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    punitorio = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")
    liquidaciones = _liquidaciones_punitorio(
        db_session, ob["id_obligacion_financiera"]
    )

    assert punitorio is not None
    assert float(punitorio["importe_componente"]) == pytest.approx(60.00)
    assert float(punitorio["saldo_componente"]) == pytest.approx(0.00)
    assert len(liquidaciones) == 1
    assert liquidaciones[0]["id_composicion_obligacion"] == punitorio["id_composicion_obligacion"]
    assert str(liquidaciones[0]["uid_pago_grupo"]) == data["uid_pago_grupo"]
    assert liquidaciones[0]["codigo_pago_grupo"] == data["codigo_pago_grupo"]
    assert liquidaciones[0]["fecha_vencimiento"].isoformat() == "2026-05-10"
    assert liquidaciones[0]["fecha_inicio_calculo"].isoformat() == "2026-05-10"
    assert liquidaciones[0]["fecha_fin_calculo"].isoformat() == "2026-05-16"
    assert float(liquidaciones[0]["base_morable"]) == pytest.approx(10000.00)
    assert float(liquidaciones[0]["tasa_diaria"]) == pytest.approx(TASA_DIARIA_MORA)
    assert liquidaciones[0]["dias_calculados"] == 6
    assert float(liquidaciones[0]["importe_liquidado"]) == pytest.approx(60.00)
    assert liquidaciones[0]["estado_liquidacion"] == "ACTIVA"


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
    assert _liquidaciones_punitorio(db_session, ob["id_obligacion_financiera"]) == []


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
    liquidaciones = _liquidaciones_punitorio(
        db_session, ob["id_obligacion_financiera"]
    )
    assert len(liquidaciones) == 2
    assert liquidaciones[0]["id_liquidacion_punitorio"] != liquidaciones[1]["id_liquidacion_punitorio"]
    assert float(liquidaciones[0]["importe_liquidado"]) == pytest.approx(100.00)
    assert float(liquidaciones[1]["importe_liquidado"]) == pytest.approx(45.50)
    assert liquidaciones[1]["fecha_inicio_calculo"].isoformat() == "2026-05-20"
    assert liquidaciones[1]["fecha_fin_calculo"].isoformat() == "2026-05-25"
    assert liquidaciones[1]["dias_calculados"] == 5


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
    liquidaciones = _liquidaciones_punitorio(
        db_session, ob["id_obligacion_financiera"]
    )
    assert len(liquidaciones) == 1
    assert str(liquidaciones[0]["op_id_alta"]) == headers["X-Op-Id"]
    assert float(liquidaciones[0]["importe_liquidado"]) == pytest.approx(100.00)


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


def test_saldo_morable_usa_concepto_aplica_punitorio_para_canon(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-MORABLE-CANON-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    assert id_persona > 0
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    saldo_morable = FinancieroRepository(db_session).get_saldo_morable_pendiente(
        id_obligacion_financiera=ob["id_obligacion_financiera"]
    )

    assert float(saldo_morable) == pytest.approx(10000.00)


def test_punitorio_no_integra_base_morable(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-PUNIT-MORABLE-EXCLUYE-PUNIT-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )

    _pagar(client, id_persona, monto=50.00, fecha_pago="2026-05-20")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    punitorio = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")
    assert punitorio is not None
    assert float(punitorio["saldo_componente"]) == pytest.approx(50.00)

    saldo_morable = FinancieroRepository(db_session).get_saldo_morable_pendiente(
        id_obligacion_financiera=ob["id_obligacion_financiera"]
    )

    assert float(saldo_morable) == pytest.approx(10000.00)


def test_otro_concepto_con_aplica_punitorio_integra_base_morable(client, db_session) -> None:
    _set_aplica_punitorio(db_session, "CAPITAL_VENTA", True)
    rg = _crear_rg(client, codigo="PAG-PUNIT-MORABLE-CAPITAL-001")
    ob = _crear_obligacion(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        composiciones=[
            {"codigo_concepto_financiero": "CAPITAL_VENTA", "importe_componente": 7000.00}
        ],
    )

    saldo_morable = FinancieroRepository(db_session).get_saldo_morable_pendiente(
        id_obligacion_financiera=ob["id_obligacion_financiera"]
    )

    assert float(saldo_morable) == pytest.approx(7000.00)


def test_concepto_sin_aplica_punitorio_no_integra_base_morable(client, db_session) -> None:
    _set_aplica_punitorio(db_session, "EXPENSA_TRASLADADA", False)
    rg = _crear_rg(client, codigo="PAG-PUNIT-MORABLE-NO-APLICA-001")
    ob = _crear_obligacion(
        client,
        id_relacion_generadora=rg["id_relacion_generadora"],
        composiciones=[
            {"codigo_concepto_financiero": "EXPENSA_TRASLADADA", "importe_componente": 3000.00}
        ],
    )

    saldo_morable = FinancieroRepository(db_session).get_saldo_morable_pendiente(
        id_obligacion_financiera=ob["id_obligacion_financiera"]
    )

    assert float(saldo_morable) == pytest.approx(0.00)


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


def test_pago_multiobligacion_crea_movimientos_con_mismo_grupo(client, db_session) -> None:
    id_persona, _ = _setup(
        client, db_session,
        codigo="PAG-GRUPO-MULT-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
        monto=10000.00,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440301"}

    data = _pagar_con_headers(client, id_persona, monto=20000.00, headers=headers)
    movimientos = _movimientos_pago_por_op_id(db_session, headers["X-Op-Id"])

    assert len(data["obligaciones_pagadas"]) == 2
    assert len(movimientos) == 2
    assert data["uid_pago_grupo"] is not None
    assert data["codigo_pago_grupo"].startswith("PAGO-")
    assert {str(m["uid_pago_grupo"]) for m in movimientos} == {data["uid_pago_grupo"]}
    assert {m["codigo_pago_grupo"] for m in movimientos} == {data["codigo_pago_grupo"]}
    assert {ob["uid_pago_grupo"] for ob in data["obligaciones_pagadas"]} == {data["uid_pago_grupo"]}
    assert {ob["codigo_pago_grupo"] for ob in data["obligaciones_pagadas"]} == {data["codigo_pago_grupo"]}


def test_pago_una_obligacion_tambien_tiene_grupo(client, db_session) -> None:
    id_persona, _ = _setup(
        client, db_session,
        codigo="PAG-GRUPO-UNO-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440302"}

    data = _pagar_con_headers(client, id_persona, monto=5000.00, headers=headers)
    movimientos = _movimientos_pago_por_op_id(db_session, headers["X-Op-Id"])

    assert len(data["obligaciones_pagadas"]) == 1
    assert len(movimientos) == 1
    assert data["uid_pago_grupo"] is not None
    assert data["codigo_pago_grupo"].startswith("PAGO-")
    assert str(movimientos[0]["uid_pago_grupo"]) == data["uid_pago_grupo"]
    assert movimientos[0]["codigo_pago_grupo"] == data["codigo_pago_grupo"]


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
    assert data_2["uid_pago_grupo"] == data_1["uid_pago_grupo"]
    assert data_2["codigo_pago_grupo"] == data_1["codigo_pago_grupo"]
    assert _count_pagos_por_op_id(db_session, headers["X-Op-Id"]) == 1
    assert float(saldo_1["saldo_pendiente"]) == pytest.approx(5000.00)
    assert float(saldo_2["saldo_pendiente"]) == pytest.approx(5000.00)


def test_pago_retry_mismo_op_id_distinto_monto_devuelve_409(client, db_session) -> None:
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-IDEM-CONFLICT-MONTO-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440201"}

    data_1 = _pagar_con_headers(client, id_persona, monto=5000.00, headers=headers)
    resp = _post_pago(client, id_persona=id_persona, monto=5000.01, headers=headers)
    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    assert data_1["monto_aplicado"] == pytest.approx(5000.00)
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert _count_pagos_por_op_id(db_session, headers["X-Op-Id"]) == 1
    assert float(saldo["saldo_pendiente"]) == pytest.approx(5000.00)


def test_pago_retry_mismo_op_id_distinta_fecha_pago_devuelve_409(client, db_session) -> None:
    id_persona, contrato = _setup(
        client, db_session,
        codigo="PAG-IDEM-CONFLICT-FECHA-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440202"}

    _pagar_con_headers(client, id_persona, monto=5000.00, fecha_pago="2026-05-20", headers=headers)
    resp = _post_pago(
        client,
        id_persona=id_persona,
        monto=5000.00,
        fecha_pago="2026-05-21",
        headers=headers,
    )
    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    assert resp.status_code == 409
    assert resp.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert _count_pagos_por_op_id(db_session, headers["X-Op-Id"]) == 1
    assert float(saldo["saldo_pendiente"]) == pytest.approx(5190.00)


def test_pago_retry_mismo_op_id_distinta_persona_devuelve_409(client, db_session) -> None:
    id_persona_1, contrato_1 = _setup(
        client, db_session,
        codigo="PAG-IDEM-CONFLICT-PER-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )
    id_persona_2, contrato_2 = _setup(
        client, db_session,
        codigo="PAG-IDEM-CONFLICT-PER-002",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        monto=10000.00,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440203"}

    _pagar_con_headers(client, id_persona_1, monto=5000.00, fecha_pago="2026-05-20", headers=headers)
    resp = _post_pago(
        client,
        id_persona=id_persona_2,
        monto=5000.00,
        fecha_pago="2026-05-20",
        headers=headers,
    )
    saldo_1 = _saldos_por_contrato(db_session, contrato_1["id_contrato_alquiler"])[0]
    saldo_2 = _saldos_por_contrato(db_session, contrato_2["id_contrato_alquiler"])[0]

    assert resp.status_code == 409
    assert resp.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert _count_pagos_por_op_id(db_session, headers["X-Op-Id"]) == 1
    assert float(saldo_1["saldo_pendiente"]) == pytest.approx(5190.00)
    assert float(saldo_2["saldo_pendiente"]) == pytest.approx(10000.00)


def test_pago_conflicto_mismo_op_id_no_duplica_punitorio(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-IDEM-CONFLICT-PUNIT-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655440204"}

    _pagar_con_headers(client, id_persona, monto=50.00, fecha_pago="2026-05-20", headers=headers)
    resp = _post_pago(
        client,
        id_persona=id_persona,
        monto=51.00,
        fecha_pago="2026-05-20",
        headers=headers,
    )
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    comps = [
        c for c in _composiciones_por_obligacion(db_session, ob["id_obligacion_financiera"])
        if c["codigo_concepto_financiero"] == "PUNITORIO"
    ]

    assert resp.status_code == 409
    assert resp.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert _count_pagos_por_op_id(db_session, headers["X-Op-Id"]) == 1
    assert len(comps) == 1
    assert float(comps[0]["importe_componente"]) == pytest.approx(100.00)
    assert float(comps[0]["saldo_componente"]) == pytest.approx(50.00)


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

    data_1 = _pagar_con_headers(client, id_persona, monto=3000.00, headers=headers_1)
    data_2 = _pagar_con_headers(client, id_persona, monto=3000.00, headers=headers_2)

    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    assert _count_pagos_por_op_id(db_session, headers_1["X-Op-Id"]) == 1
    assert _count_pagos_por_op_id(db_session, headers_2["X-Op-Id"]) == 1
    assert data_1["uid_pago_grupo"] != data_2["uid_pago_grupo"]
    assert data_1["codigo_pago_grupo"] != data_2["codigo_pago_grupo"]
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


def test_lista_pagos_agrupados_persona_multiobligacion(client, db_session) -> None:
    id_persona, _ = _setup(client, db_session, codigo="PAG-AGR-001", fecha_inicio="2026-07-01", fecha_fin="2026-08-31", monto=10000.00)
    _pagar(client, id_persona, monto=15000.00)

    resp = client.get(f"/api/v1/financiero/personas/{id_persona}/pagos")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert len(data) >= 1
    assert data[0]["cantidad_obligaciones"] >= 1
    assert data[0]["cantidad_movimientos"] >= 1


def test_detalle_pago_agrupado_incluye_movs_y_aplicaciones(client, db_session) -> None:
    id_persona, _ = _setup(client, db_session, codigo="PAG-AGR-002", fecha_inicio="2026-09-01", fecha_fin="2026-10-31", monto=11000.00)
    pago = _pagar(client, id_persona, monto=12000.00)

    resp = client.get(f"/api/v1/financiero/pagos/{pago['codigo_pago_grupo']}")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["codigo_pago_grupo"] == pago["codigo_pago_grupo"]
    assert len(data["movimientos"]) >= 1
    assert len(data["aplicaciones"]) >= 1
    assert any(a.get("codigo_concepto_financiero") for a in data["aplicaciones"])


def test_detalle_pago_agrupado_404_si_codigo_no_existe(client) -> None:
    resp = client.get("/api/v1/financiero/pagos/PAGO-NO-EXISTE")
    assert resp.status_code == 404


def _recibo(client, codigo_pago_grupo: str):
    return client.get(f"/api/v1/financiero/pagos/{codigo_pago_grupo}/recibo")


def _revertir(client, codigo_pago_grupo: str, motivo: str = "Reversion de prueba"):
    return client.post(
        f"/api/v1/financiero/pagos/{codigo_pago_grupo}/revertir",
        headers=HEADERS,
        json={"motivo": motivo},
    )


def _movimientos_por_codigo_pago(db_session, codigo_pago_grupo: str) -> list[dict]:
    rows = db_session.execute(
        text(
            """
            SELECT id_movimiento_financiero, estado_movimiento, observaciones
            FROM movimiento_financiero
            WHERE codigo_pago_grupo = :codigo
              AND tipo_movimiento = 'PAGO'
              AND deleted_at IS NULL
            ORDER BY id_movimiento_financiero ASC
            """
        ),
        {"codigo": codigo_pago_grupo},
    ).mappings().all()
    return [dict(r) for r in rows]


def _count_aplicaciones_activas_por_codigo(db_session, codigo_pago_grupo: str) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM aplicacion_financiera a
            JOIN movimiento_financiero m
              ON m.id_movimiento_financiero = a.id_movimiento_financiero
            WHERE m.codigo_pago_grupo = :codigo
              AND m.tipo_movimiento = 'PAGO'
              AND m.deleted_at IS NULL
              AND a.deleted_at IS NULL
            """
        ),
        {"codigo": codigo_pago_grupo},
    ).scalar_one()


def _saldo_obligacion_y_suma_composiciones(db_session, id_obligacion: int) -> tuple[float, float]:
    row = db_session.execute(
        text(
            """
            SELECT
                o.saldo_pendiente,
                COALESCE(SUM(c.saldo_componente), 0) AS suma_componentes
            FROM obligacion_financiera o
            LEFT JOIN composicion_obligacion c
              ON c.id_obligacion_financiera = o.id_obligacion_financiera
             AND c.estado_composicion_obligacion = 'ACTIVA'
             AND c.deleted_at IS NULL
            WHERE o.id_obligacion_financiera = :id
            GROUP BY o.id_obligacion_financiera, o.saldo_pendiente
            """
        ),
        {"id": id_obligacion},
    ).mappings().one()
    return float(row["saldo_pendiente"]), float(row["suma_componentes"])


def _count_table(db_session, table_name: str) -> int:
    return db_session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()


def test_recibo_pago_agrupado_una_obligacion(client, db_session) -> None:
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="PAG-REC-UNO-001",
        fecha_inicio="2026-11-01",
        fecha_fin="2026-11-30",
        monto=10000.00,
    )
    pago = _pagar(client, id_persona, monto=10000.00)

    resp = _recibo(client, pago["codigo_pago_grupo"])

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["codigo_pago_grupo"] == pago["codigo_pago_grupo"]
    assert data["uid_pago_grupo"] == pago["uid_pago_grupo"]
    assert data["id_persona"] == id_persona
    assert data["monto_total"] == pytest.approx(10000.00)
    assert data["monto_aplicado"] == pytest.approx(10000.00)
    assert data["remanente"] == pytest.approx(0.00)
    assert data["estado_recibo"] == "BORRADOR/CONSULTA"
    assert len(data["detalle"]) == 1
    assert data["detalle"][0]["codigo_concepto_financiero"] == "CANON_LOCATIVO"
    assert data["totales_por_concepto"] == [
        {"codigo_concepto_financiero": "CANON_LOCATIVO", "importe_aplicado": 10000.0}
    ]


def test_recibo_pago_agrupado_multiobligacion(client, db_session) -> None:
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="PAG-REC-MULTI-001",
        fecha_inicio="2026-12-01",
        fecha_fin="2027-01-31",
        monto=10000.00,
    )
    pago = _pagar(client, id_persona, monto=15000.00)

    resp = _recibo(client, pago["codigo_pago_grupo"])

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["monto_total"] == pytest.approx(15000.00)
    assert data["monto_aplicado"] == pytest.approx(15000.00)
    assert len({d["id_movimiento_financiero"] for d in data["detalle"]}) == 2
    assert len({d["id_obligacion_financiera"] for d in data["detalle"]}) == 2
    totales = {
        t["codigo_concepto_financiero"]: t["importe_aplicado"]
        for t in data["totales_por_concepto"]
    }
    assert totales["CANON_LOCATIVO"] == pytest.approx(15000.00)


def test_recibo_pago_agrupado_incluye_punitorio_pagado(client, db_session) -> None:
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="PAG-REC-PUNIT-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    pago = _pagar(client, id_persona, monto=50.00, fecha_pago="2026-05-20")

    resp = _recibo(client, pago["codigo_pago_grupo"])

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["monto_total"] == pytest.approx(50.00)
    assert data["monto_aplicado"] == pytest.approx(50.00)
    assert data["detalle"][0]["codigo_concepto_financiero"] == "PUNITORIO"
    assert data["detalle"][0]["importe_aplicado"] == pytest.approx(50.00)
    assert data["totales_por_concepto"] == [
        {"codigo_concepto_financiero": "PUNITORIO", "importe_aplicado": 50.0}
    ]


def test_recibo_pago_agrupado_404_si_codigo_no_existe(client) -> None:
    resp = _recibo(client, "PAGO-REC-NO-EXISTE")

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_recibo_pago_agrupado_no_modifica_saldos_ni_crea_registros(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REC-LECTURA-001",
        fecha_inicio="2027-02-01",
        fecha_fin="2027-02-28",
        monto=10000.00,
    )
    pago = _pagar(client, id_persona, monto=4000.00)
    saldo_antes = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    movs_antes = _count_table(db_session, "movimiento_financiero")
    aplicaciones_antes = _count_table(db_session, "aplicacion_financiera")

    resp = _recibo(client, pago["codigo_pago_grupo"])

    saldo_despues = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    movs_despues = _count_table(db_session, "movimiento_financiero")
    aplicaciones_despues = _count_table(db_session, "aplicacion_financiera")
    assert resp.status_code == 200, resp.text
    assert float(saldo_despues["saldo_pendiente"]) == pytest.approx(
        float(saldo_antes["saldo_pendiente"])
    )
    assert saldo_despues["estado_obligacion"] == saldo_antes["estado_obligacion"]
    assert movs_despues == movs_antes
    assert aplicaciones_despues == aplicaciones_antes


def test_revertir_pago_simple_restaurar_saldo(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-SIMPLE-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
    )
    pago = _pagar(client, id_persona, monto=4000.00, fecha_pago="2026-05-05")

    resp = _revertir(client, pago["codigo_pago_grupo"])

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    movimientos = _movimientos_por_codigo_pago(db_session, pago["codigo_pago_grupo"])
    assert data["estado_reversion"] == "ANULADO"
    assert data["movimientos_anulados"] == 1
    assert data["aplicaciones_anuladas"] == 1
    assert float(saldo["saldo_pendiente"]) == pytest.approx(10000.00)
    assert saldo["estado_obligacion"] in {"EMITIDA", "VENCIDA"}
    assert {m["estado_movimiento"] for m in movimientos} == {"ANULADO"}
    assert _count_aplicaciones_activas_por_codigo(
        db_session, pago["codigo_pago_grupo"]
    ) == 0


def test_revertir_pago_multiobligacion_restaurar_saldos(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-MULTI-001",
        fecha_inicio="2026-11-01",
        fecha_fin="2026-12-31",
        monto=10000.00,
    )
    pago = _pagar(client, id_persona, monto=15000.00, fecha_pago="2026-11-05")

    resp = _revertir(client, pago["codigo_pago_grupo"])

    assert resp.status_code == 200, resp.text
    saldos = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])
    assert [float(s["saldo_pendiente"]) for s in saldos] == pytest.approx(
        [10000.00, 10000.00]
    )
    assert {s["estado_obligacion"] for s in saldos} == {"EMITIDA"}
    assert resp.json()["data"]["movimientos_anulados"] == 2
    assert _count_aplicaciones_activas_por_codigo(
        db_session, pago["codigo_pago_grupo"]
    ) == 0


def test_revertir_pago_con_punitorio_revierte_aplicacion_y_liquidacion(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-PUNIT-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    pago = _pagar(client, id_persona, monto=50.00, fecha_pago="2026-05-20")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    assert _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO") is not None

    resp = _revertir(client, pago["codigo_pago_grupo"])

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    ob_despues = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    punitorio = _composicion(
        db_session, ob["id_obligacion_financiera"], "PUNITORIO"
    )
    liquidaciones = _liquidaciones_punitorio(
        db_session, ob["id_obligacion_financiera"]
    )
    estados_liq = db_session.execute(
        text(
            """
            SELECT estado_liquidacion, importe_liquidado
            FROM liquidacion_punitorio
            WHERE codigo_pago_grupo = :codigo
            """
        ),
        {"codigo": pago["codigo_pago_grupo"]},
    ).mappings().all()
    assert data["liquidaciones_punitorio_anuladas"] == 1
    assert data["importe_punitorio_revertido"] == pytest.approx(100.00)
    assert punitorio is not None
    assert float(punitorio["importe_componente"]) == pytest.approx(0.00)
    assert float(punitorio["saldo_componente"]) == pytest.approx(0.00)
    assert float(ob_despues["saldo_pendiente"]) == pytest.approx(10000.00)
    assert liquidaciones == []
    assert estados_liq[0]["estado_liquidacion"] == "ANULADA"
    assert float(estados_liq[0]["importe_liquidado"]) == pytest.approx(100.00)


def test_revertir_pago_no_afecta_punitorio_de_otros_pagos(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-PUNIT-OTRO-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    pago_1 = _pagar(client, id_persona, monto=1000.00, fecha_pago="2026-05-20")
    pago_2 = _pagar(client, id_persona, monto=45.50, fecha_pago="2026-05-25")
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    resp = _revertir(client, pago_2["codigo_pago_grupo"])

    assert resp.status_code == 200, resp.text
    punitorio = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")
    liquidaciones_activas = _liquidaciones_punitorio(
        db_session, ob["id_obligacion_financiera"]
    )
    liq_2_estado = db_session.execute(
        text(
            """
            SELECT estado_liquidacion
            FROM liquidacion_punitorio
            WHERE codigo_pago_grupo = :codigo
            """
        ),
        {"codigo": pago_2["codigo_pago_grupo"]},
    ).scalar_one()
    assert punitorio is not None
    assert float(punitorio["importe_componente"]) == pytest.approx(100.00)
    assert float(punitorio["saldo_componente"]) == pytest.approx(0.00)
    assert len(liquidaciones_activas) == 1
    assert liquidaciones_activas[0]["codigo_pago_grupo"] == pago_1["codigo_pago_grupo"]
    assert float(liquidaciones_activas[0]["importe_liquidado"]) == pytest.approx(100.00)
    assert liq_2_estado == "ANULADA"


def test_revertir_pago_anterior_con_pago_posterior_devuelve_409(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-POST-001",
        fecha_inicio="2026-11-01",
        fecha_fin="2026-11-30",
        monto=10000.00,
    )
    pago_1 = _pagar(client, id_persona, monto=3000.00, fecha_pago="2026-11-05")
    _pagar(client, id_persona, monto=1000.00, fecha_pago="2026-11-06")

    resp = _revertir(client, pago_1["codigo_pago_grupo"])

    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "PAGO_TIENE_OPERACIONES_POSTERIORES"
    assert float(saldo["saldo_pendiente"]) == pytest.approx(6000.00)
    assert _count_aplicaciones_activas_por_codigo(
        db_session, pago_1["codigo_pago_grupo"]
    ) == 1


def test_revertir_pago_anterior_con_liquidacion_punitorio_posterior_devuelve_409(
    client, db_session
) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-PUNIT-POST-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=10,
    )
    pago_1 = _pagar(client, id_persona, monto=1000.00, fecha_pago="2026-05-20")
    _pagar(client, id_persona, monto=45.50, fecha_pago="2026-05-25")

    resp = _revertir(client, pago_1["codigo_pago_grupo"])

    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    punitorio = _composicion(db_session, ob["id_obligacion_financiera"], "PUNITORIO")
    liquidaciones = _liquidaciones_punitorio(
        db_session, ob["id_obligacion_financiera"]
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "PAGO_TIENE_OPERACIONES_POSTERIORES"
    assert punitorio is not None
    assert float(punitorio["importe_componente"]) == pytest.approx(145.50)
    assert len(liquidaciones) == 2


def test_revertir_pago_codigo_inexistente_devuelve_404(client) -> None:
    resp = _revertir(client, "PAGO-REV-NO-EXISTE")

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_revertir_pago_repetido_es_idempotente(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-IDEM-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
    )
    pago = _pagar(client, id_persona, monto=3000.00, fecha_pago="2026-05-05")

    resp_1 = _revertir(client, pago["codigo_pago_grupo"])
    resp_2 = _revertir(client, pago["codigo_pago_grupo"])

    assert resp_1.status_code == 200, resp_1.text
    assert resp_2.status_code == 200, resp_2.text
    assert resp_2.json()["data"]["estado_reversion"] == "YA_ANULADO"
    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    assert float(saldo["saldo_pendiente"]) == pytest.approx(10000.00)
    assert _count_aplicaciones_activas_por_codigo(
        db_session, pago["codigo_pago_grupo"]
    ) == 0


def test_retry_op_id_original_despues_de_reversion_devuelve_conflicto(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-RETRY-OP-001",
        fecha_inicio="2026-11-01",
        fecha_fin="2026-11-30",
        monto=10000.00,
    )
    headers = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655441001"}
    pago = _pagar_con_headers(
        client,
        id_persona,
        monto=3000.00,
        fecha_pago="2026-11-05",
        headers=headers,
    )
    rev = _revertir(client, pago["codigo_pago_grupo"])
    assert rev.status_code == 200, rev.text

    resp = _post_pago(
        client,
        id_persona=id_persona,
        monto=3000.00,
        fecha_pago="2026-11-05",
        headers=headers,
    )

    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "PAGO_YA_REVERTIDO"
    assert float(saldo["saldo_pendiente"]) == pytest.approx(10000.00)
    assert _count_pagos_por_op_id(db_session, headers["X-Op-Id"]) == 1


def test_pago_nuevo_despues_de_reversion_no_cuenta_aplicaciones_soft_deleted(
    client, db_session
) -> None:
    _install_patch_validacion_aplicacion(db_session)
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-NUEVO-001",
        fecha_inicio="2026-11-01",
        fecha_fin="2026-11-30",
        monto=10000.00,
    )
    headers_1 = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655441101"}
    headers_2 = {**HEADERS, "X-Op-Id": "650e8400-e29b-41d4-a716-446655441102"}
    pago_1 = _pagar_con_headers(
        client,
        id_persona,
        monto=10000.00,
        fecha_pago="2026-11-05",
        headers=headers_1,
    )
    rev = _revertir(client, pago_1["codigo_pago_grupo"])
    assert rev.status_code == 200, rev.text

    pago_2 = _pagar_con_headers(
        client,
        id_persona,
        monto=10000.00,
        fecha_pago="2026-11-06",
        headers=headers_2,
    )

    saldo = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]
    assert pago_2["monto_aplicado"] == pytest.approx(10000.00)
    assert float(saldo["saldo_pendiente"]) == pytest.approx(0.00)
    assert saldo["estado_obligacion"] == "CANCELADA"
    assert _count_aplicaciones_activas_por_codigo(
        db_session, pago_1["codigo_pago_grupo"]
    ) == 0
    assert _count_aplicaciones_activas_por_codigo(
        db_session, pago_2["codigo_pago_grupo"]
    ) == 1


def test_recibo_pago_revertido_refleja_estado_anulado(client, db_session) -> None:
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="PAG-REV-REC-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
    )
    pago = _pagar(client, id_persona, monto=2000.00, fecha_pago="2026-05-05")
    rev = _revertir(client, pago["codigo_pago_grupo"])
    assert rev.status_code == 200, rev.text

    resp = _recibo(client, pago["codigo_pago_grupo"])

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["estado_recibo"] == "ANULADO"
    assert data["detalle"][0]["estado_resultante"] == "ANULADO"
    assert data["totales_por_concepto"] == [
        {"codigo_concepto_financiero": "CANON_LOCATIVO", "importe_aplicado": 2000.0}
    ]


def test_detalle_pago_agrupado_muestra_anulado_despues_de_reversion(client, db_session) -> None:
    id_persona, _ = _setup(
        client,
        db_session,
        codigo="PAG-REV-DET-001",
        fecha_inicio="2026-11-01",
        fecha_fin="2026-11-30",
        monto=10000.00,
    )
    pago = _pagar(client, id_persona, monto=2000.00, fecha_pago="2026-11-05")
    rev = _revertir(client, pago["codigo_pago_grupo"])
    assert rev.status_code == 200, rev.text

    resp = client.get(f"/api/v1/financiero/pagos/{pago['codigo_pago_grupo']}")

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["estado_pago_grupo"] == "ANULADO"
    assert data["movimientos"][0]["estado_movimiento"] == "ANULADO"
    assert data["aplicaciones"][0]["estado_resultante"] == "ANULADO"


def test_saldo_pendiente_igual_suma_componentes_despues_de_reversion(client, db_session) -> None:
    id_persona, contrato = _setup(
        client,
        db_session,
        codigo="PAG-REV-INVARIANTE-001",
        fecha_inicio="2026-11-01",
        fecha_fin="2026-11-30",
        monto=10000.00,
    )
    pago = _pagar(client, id_persona, monto=3500.00, fecha_pago="2026-11-05")
    rev = _revertir(client, pago["codigo_pago_grupo"])
    assert rev.status_code == 200, rev.text
    ob = _saldos_por_contrato(db_session, contrato["id_contrato_alquiler"])[0]

    saldo, suma_componentes = _saldo_obligacion_y_suma_composiciones(
        db_session, ob["id_obligacion_financiera"]
    )

    assert saldo == pytest.approx(suma_componentes)
