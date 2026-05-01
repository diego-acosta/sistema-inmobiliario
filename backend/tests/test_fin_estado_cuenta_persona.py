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


# ── tests: fecha_corte ────────────────────────────────────────────────────────

def test_estado_cuenta_persona_sin_fecha_corte_usa_today(client, db_session) -> None:
    """Sin fecha_corte la respuesta devuelve fecha_corte = date.today()."""
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-FC-TODAY-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=20000.00,
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["fecha_corte"] == str(date.today())


def test_estado_cuenta_persona_fecha_corte_pasado_calcula_mora(client, db_session) -> None:
    """
    Obligación con vencimiento 2026-04-01.
    fecha_corte=2026-04-11 → 10 días de atraso → mora = 50000 * 0.001 * 10 = 500.
    """
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-FC-PAST-001",
        fecha_inicio="2026-04-01",
        fecha_fin="2026-04-30",
        monto=50000.00,
        dia_vencimiento_canon=1,
    )

    resp = client.get(
        _url(id_persona), headers=HEADERS, params={"fecha_corte": "2026-04-11"}
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["fecha_corte"] == "2026-04-11"
    ob = data["obligaciones"][0]
    assert ob["dias_atraso"] == 10
    assert ob["mora_calculada"] == pytest.approx(500.00)
    assert ob["total_con_mora"] == pytest.approx(50500.00)
    assert data["resumen"]["mora_calculada"] == pytest.approx(500.00)


def test_estado_cuenta_persona_fecha_corte_antes_del_vencimiento_sin_mora(client, db_session) -> None:
    """
    Obligación con vencimiento 2026-04-01.
    fecha_corte=2026-03-15 → aún no venció → dias_atraso=0, mora=0.
    """
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-FC-FUT-001",
        fecha_inicio="2026-04-01",
        fecha_fin="2026-04-30",
        monto=30000.00,
        dia_vencimiento_canon=1,
    )

    resp = client.get(
        _url(id_persona), headers=HEADERS, params={"fecha_corte": "2026-03-15"}
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["fecha_corte"] == "2026-03-15"
    ob = data["obligaciones"][0]
    assert ob["dias_atraso"] == 0
    assert ob["mora_calculada"] == pytest.approx(0.0)
    assert ob["total_con_mora"] == pytest.approx(30000.00)
    assert data["resumen"]["mora_calculada"] == pytest.approx(0.0)


def test_estado_cuenta_persona_mora_cambia_segun_fecha_corte(client, db_session) -> None:
    """
    Misma obligación con vencimiento 2026-04-01, dos fechas_corte distintas.
    fecha_corte=2026-04-06 → 5 días → mora = 50000 * 0.001 * 5 = 250.
    fecha_corte=2026-04-21 → 20 días → mora = 50000 * 0.001 * 20 = 1000.
    """
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-FC-DIFF-001",
        fecha_inicio="2026-04-01",
        fecha_fin="2026-04-30",
        monto=50000.00,
        dia_vencimiento_canon=1,
    )

    resp5 = client.get(
        _url(id_persona), headers=HEADERS, params={"fecha_corte": "2026-04-06"}
    )
    resp20 = client.get(
        _url(id_persona), headers=HEADERS, params={"fecha_corte": "2026-04-21"}
    )

    assert resp5.status_code == 200
    assert resp20.status_code == 200

    ob5 = resp5.json()["data"]["obligaciones"][0]
    ob20 = resp20.json()["data"]["obligaciones"][0]

    assert ob5["dias_atraso"] == 5
    assert ob5["mora_calculada"] == pytest.approx(250.00)
    assert ob20["dias_atraso"] == 20
    assert ob20["mora_calculada"] == pytest.approx(1000.00)


# ── tests: filtros individuales y combinaciones ───────────────────────────────

def test_filtro_estado_devuelve_solo_estado_solicitado(client, db_session) -> None:
    """estado=EMITIDA excluye las que fueron forzadas a VENCIDA."""
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-EST-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-06-30",
        monto=10000.00,
    )
    # Forzar la primera obligación a VENCIDA
    db_session.execute(
        text(
            """
            UPDATE obligacion_financiera
            SET estado_obligacion = 'VENCIDA'
            WHERE id_obligacion_financiera = (
                SELECT o.id_obligacion_financiera
                FROM obligacion_financiera o
                WHERE o.id_relacion_generadora = (
                    SELECT id_relacion_generadora FROM relacion_generadora
                    WHERE tipo_origen = 'contrato_alquiler'
                      AND id_origen = :id_contrato AND deleted_at IS NULL LIMIT 1
                ) AND o.deleted_at IS NULL
                ORDER BY o.id_obligacion_financiera ASC
                LIMIT 1
            )
            """
        ),
        {"id_contrato": contrato["id_contrato_alquiler"]},
    )

    resp_emitida = client.get(_url(id_persona), headers=HEADERS, params={"estado": "EMITIDA"})
    resp_vencida = client.get(_url(id_persona), headers=HEADERS, params={"estado": "VENCIDA"})

    assert resp_emitida.status_code == 200
    assert resp_vencida.status_code == 200
    emitidas = resp_emitida.json()["data"]["obligaciones"]
    vencidas = resp_vencida.json()["data"]["obligaciones"]
    assert len(emitidas) == 1
    assert len(vencidas) == 1
    assert all(o["estado_obligacion"] == "EMITIDA" for o in emitidas)
    assert all(o["estado_obligacion"] == "VENCIDA" for o in vencidas)


def test_filtro_id_origen_devuelve_solo_obligaciones_del_origen(client, db_session) -> None:
    """id_origen filtra por relacion_generadora.id_origen."""
    id_persona, contrato1 = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-ID-OR-A",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
    )
    # Segundo contrato para la misma persona
    from tests.test_fin_event_contrato_alquiler import _crear_contrato_borrador, _crear_condicion
    from tests.test_reservas_venta_create import _crear_inmueble
    inmueble2 = _crear_inmueble(client, codigo="INM-ECP-ID-OR-B")
    from tests.test_contratos_alquiler_create import _payload_base
    resp2 = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="ECP-ID-OR-B",
            objetos=[{"id_inmueble": inmueble2, "id_unidad_funcional": None, "observaciones": None}],
            fecha_inicio="2026-05-01",
            fecha_fin="2026-05-31",
        ),
    )
    assert resp2.status_code == 201
    contrato2 = resp2.json()["data"]
    _crear_condicion(client, contrato2["id_contrato_alquiler"], 20000.00, "2026-05-01")
    # Reusar el mismo locatario ya creado insertando relacion_persona_rol
    id_rol = db_session.execute(
        text("SELECT id_rol_participacion FROM rol_participacion WHERE codigo_rol = 'LOCATARIO_PRINCIPAL' LIMIT 1")
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_persona, id_rol_participacion,
                tipo_relacion, id_relacion, fecha_desde, fecha_hasta, observaciones
            ) VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id, :id_persona, :id_rol,
                'contrato_alquiler', :id_contrato, TIMESTAMP '2026-05-01', NULL, NULL
            )
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "id_persona": id_persona,
         "id_rol": id_rol, "id_contrato": contrato2["id_contrato_alquiler"]},
    )
    from tests.test_fin_event_contrato_alquiler import _activar
    _activar(client, contrato2["id_contrato_alquiler"], contrato2["version_registro"])

    resp = client.get(
        _url(id_persona), headers=HEADERS,
        params={"id_origen": contrato1["id_contrato_alquiler"]},
    )

    assert resp.status_code == 200
    obs = resp.json()["data"]["obligaciones"]
    assert len(obs) == 1
    assert obs[0]["id_origen"] == contrato1["id_contrato_alquiler"]


def test_filtro_rango_fechas_vencimiento(client, db_session) -> None:
    """fecha_vencimiento_desde/hasta filtra por rango de vencimiento."""
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-RANGO-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-07-31",
        monto=10000.00,
        dia_vencimiento_canon=1,
    )
    # Mayo: venc 2026-05-01, Junio: 2026-06-01, Julio: 2026-07-01
    resp = client.get(
        _url(id_persona), headers=HEADERS,
        params={"fecha_vencimiento_desde": "2026-05-15", "fecha_vencimiento_hasta": "2026-06-15"},
    )

    assert resp.status_code == 200
    obs = resp.json()["data"]["obligaciones"]
    assert len(obs) == 1
    assert obs[0]["fecha_vencimiento"] == "2026-06-01"


def test_filtro_combinado_tipo_origen_y_estado(client, db_session) -> None:
    """tipo_origen AND estado se combinan correctamente."""
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-COMB-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-06-30",
        monto=10000.00,
    )
    # Forzar una a VENCIDA
    db_session.execute(
        text(
            """
            UPDATE obligacion_financiera SET estado_obligacion = 'VENCIDA'
            WHERE id_obligacion_financiera = (
                SELECT o.id_obligacion_financiera
                FROM obligacion_financiera o
                WHERE o.id_relacion_generadora = (
                    SELECT id_relacion_generadora FROM relacion_generadora
                    WHERE tipo_origen = 'contrato_alquiler'
                      AND id_origen = :id AND deleted_at IS NULL LIMIT 1
                ) AND o.deleted_at IS NULL
                ORDER BY o.id_obligacion_financiera ASC
                LIMIT 1
            )
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    )

    # tipo_origen=CONTRATO_ALQUILER AND estado=EMITIDA → solo la EMITIDA
    resp = client.get(
        _url(id_persona), headers=HEADERS,
        params={"tipo_origen": "CONTRATO_ALQUILER", "estado": "EMITIDA"},
    )
    assert resp.status_code == 200
    obs = resp.json()["data"]["obligaciones"]
    assert len(obs) == 1
    assert obs[0]["estado_obligacion"] == "EMITIDA"
    assert obs[0]["tipo_origen"] == "CONTRATO_ALQUILER"


def test_filtro_vencidas_usa_fecha_corte_personalizada(client, db_session) -> None:
    """
    vencidas=True respeta fecha_corte.
    Obligación con vencimiento 2026-04-01:
    - fecha_corte=2026-04-15 → incluida (2026-04-01 < 2026-04-15)
    - fecha_corte=2026-03-15 → excluida (2026-04-01 >= 2026-03-15)
    """
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-VFC-001",
        fecha_inicio="2026-04-01",
        fecha_fin="2026-04-30",
        monto=10000.00,
        dia_vencimiento_canon=1,
    )

    resp_incluida = client.get(
        _url(id_persona), headers=HEADERS,
        params={"vencidas": True, "fecha_corte": "2026-04-15"},
    )
    resp_excluida = client.get(
        _url(id_persona), headers=HEADERS,
        params={"vencidas": True, "fecha_corte": "2026-03-15"},
    )

    assert resp_incluida.status_code == 200
    assert resp_excluida.status_code == 200
    assert len(resp_incluida.json()["data"]["obligaciones"]) == 1
    assert resp_excluida.json()["data"]["obligaciones"] == []


def test_filtro_vencidas_y_rango_sin_interseccion_devuelve_vacio(client, db_session) -> None:
    """
    vencidas=True (< fecha_corte=2026-05-01) combinado con
    fecha_vencimiento_desde=2026-06-01 es contradictorio → lista vacía, sin error.
    """
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-CONTRA-001",
        fecha_inicio="2026-04-01",
        fecha_fin="2026-06-30",
        monto=10000.00,
        dia_vencimiento_canon=1,
    )

    resp = client.get(
        _url(id_persona), headers=HEADERS,
        params={
            "vencidas": True,
            "fecha_corte": "2026-05-01",
            "fecha_vencimiento_desde": "2026-06-01",
        },
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["obligaciones"] == []


def test_filtro_rango_invertido_devuelve_vacio_sin_error(client, db_session) -> None:
    """
    fecha_vencimiento_desde > fecha_vencimiento_hasta es un rango imposible.
    No debe devolver error 400; devuelve lista vacía con 200.
    """
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-INV-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
    )

    resp = client.get(
        _url(id_persona), headers=HEADERS,
        params={"fecha_vencimiento_desde": "2026-12-01", "fecha_vencimiento_hasta": "2026-01-01"},
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["obligaciones"] == []
