"""
Tests de integración para GET /api/v1/financiero/personas/{id_persona}/estado-cuenta.
"""
from datetime import date
from decimal import Decimal

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
from tests.test_factura_servicio_api import (
    _crear_factura_servicio_con_responsable,
    _liquidar_recupero,
    _materializar,
    _registrar_egreso_proveedor,
)
from tests.test_impuesto_trasladado_api import (
    _crear_comprobante,
    _liquidar_impuesto,
    _registrar_egreso_impuesto,
)
from tests.test_reservas_venta_create import _crear_inmueble
from tests.test_ventas_definir_condiciones_comerciales import (
    _insertar_venta_para_condiciones,
)

URL = "/api/v1/financiero/personas/{id_persona}/estado-cuenta"
TASA_DIARIA_MORA = float(TASA_DIARIA_MORA_DEFAULT)


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


def _crear_persona(client, *, nombre: str, apellido: str) -> int:
    response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": nombre,
            "apellido": apellido,
            "razon_social": None,
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_persona"]


def _crear_deuda_venta_para_persona(
    client,
    db_session,
    *,
    id_persona: int,
    codigo: str,
    monto: Decimal,
) -> dict[str, int]:
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo}")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta=codigo,
        estado_venta="confirmada",
        monto_total=monto,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": monto,
                "observaciones": "Venta para estado de cuenta por persona",
            }
        ],
    )
    id_concepto = db_session.execute(
        text(
            """
            SELECT id_concepto_financiero
            FROM concepto_financiero
            WHERE codigo_concepto_financiero = 'CAPITAL_VENTA'
              AND deleted_at IS NULL
            """
        )
    ).scalar_one()
    id_rg = db_session.execute(
        text(
            """
            INSERT INTO relacion_generadora (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                tipo_origen, id_origen, descripcion
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                'venta', :id_venta, :descripcion
            )
            RETURNING id_relacion_generadora
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_venta": venta["id_venta"],
            "descripcion": f"Venta {codigo}",
        },
    ).scalar_one()
    id_ob = db_session.execute(
        text(
            """
            INSERT INTO obligacion_financiera (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_relacion_generadora, fecha_emision, fecha_vencimiento,
                importe_total, saldo_pendiente, estado_obligacion
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                :id_rg, DATE '2026-05-01', DATE '2026-05-31',
                :monto, :monto, 'EMITIDA'
            )
            RETURNING id_obligacion_financiera
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "id_rg": id_rg, "monto": monto},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO composicion_obligacion (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_obligacion_financiera, id_concepto_financiero,
                orden_composicion, importe_componente, saldo_componente
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                :id_ob, :id_concepto, 1, :monto, :monto
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_ob": id_ob,
            "id_concepto": id_concepto,
            "monto": monto,
        },
    )
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
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                :id_ob, :id_persona, 'COMPRADOR', 100.00
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_ob": id_ob,
            "id_persona": id_persona,
        },
    )
    return {
        "id_relacion_generadora": id_rg,
        "id_obligacion_financiera": id_ob,
        "id_venta": venta["id_venta"],
    }


def _relacion_por_contrato(db_session, id_contrato: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT id_relacion_generadora
            FROM relacion_generadora
            WHERE tipo_origen = 'contrato_alquiler'
              AND id_origen = :id_contrato
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"id_contrato": id_contrato},
    ).scalar_one()


def _pagar_persona(
    client,
    *,
    id_persona: int,
    monto: float,
    fecha_pago: str = "2026-05-10",
    **scope,
) -> dict:
    body = {"monto": monto, "fecha_pago": fecha_pago}
    body.update(scope)
    response = client.post(
        "/api/v1/financiero/pagos",
        headers={k: v for k, v in HEADERS.items() if k != "X-Op-Id"},
        params={"id_persona": id_persona},
        json=body,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _obligacion_por_relacion(db_session, id_relacion_generadora: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT id_obligacion_financiera
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id_rg
              AND deleted_at IS NULL
            ORDER BY id_obligacion_financiera ASC
            LIMIT 1
            """
        ),
        {"id_rg": id_relacion_generadora},
    ).scalar_one()


def _agregar_punitorio_manual(db_session, *, id_obligacion: int, importe: Decimal) -> None:
    id_concepto = db_session.execute(
        text(
            """
            SELECT id_concepto_financiero
            FROM concepto_financiero
            WHERE codigo_concepto_financiero = 'PUNITORIO'
              AND deleted_at IS NULL
            """
        )
    ).scalar_one()
    orden = db_session.execute(
        text(
            """
            SELECT COALESCE(MAX(orden_composicion), 0) + 1
            FROM composicion_obligacion
            WHERE id_obligacion_financiera = :id_obligacion
              AND deleted_at IS NULL
            """
        ),
        {"id_obligacion": id_obligacion},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO composicion_obligacion (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_obligacion_financiera, id_concepto_financiero,
                orden_composicion, importe_componente, saldo_componente
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                :id_obligacion, :id_concepto, :orden, :importe, :importe
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_obligacion": id_obligacion,
            "id_concepto": id_concepto,
            "orden": orden,
            "importe": importe,
        },
    )


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

    resp = client.get(
        _url(id_persona), headers=HEADERS, params={"fecha_corte": "2026-05-01"}
    )

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
    dia_vencimiento_canon=1 → vencimiento 2026-04-01, hoy 2026-05-01.
    Con 5 dias de gracia, la mora inicia el 2026-04-06.
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

    dias_esperados = max((date.today() - date(2026, 4, 6)).days, 0)
    assert ob["dias_atraso"] == dias_esperados
    assert ob["mora_calculada"] == pytest.approx(
        50000.00 * TASA_DIARIA_MORA * dias_esperados
    )
    assert ob["tasa_diaria_mora"] == pytest.approx(TASA_DIARIA_MORA)
    assert ob["total_con_mora"] == pytest.approx(50000.00 + ob["mora_calculada"])
    assert data["resumen"]["mora_calculada"] == pytest.approx(ob["mora_calculada"])
    assert data["resumen"]["total_con_mora"] == pytest.approx(ob["total_con_mora"])


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

    resp = client.get(
        _url(id_persona),
        headers=HEADERS,
        params={"vencidas": True, "fecha_corte": "2026-05-01"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    # Solo Abril tiene vencimiento < hoy
    assert len(data["obligaciones"]) == 1
    ob = data["obligaciones"][0]
    assert ob["fecha_vencimiento"] < "2026-05-01"


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
    fecha_corte=2026-04-11 → 5 días de mora por gracia.
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
    mora_esperada = 50000.00 * TASA_DIARIA_MORA * 5
    assert ob["dias_atraso"] == 5
    assert ob["mora_calculada"] == pytest.approx(mora_esperada)
    assert ob["total_con_mora"] == pytest.approx(50000.00 + mora_esperada)
    assert data["resumen"]["mora_calculada"] == pytest.approx(mora_esperada)


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
    fecha_corte=2026-04-05 → dentro de gracia → mora = 0.
    fecha_corte=2026-04-06 → límite exacto de gracia → mora = 0.
    fecha_corte=2026-04-21 → 15 días de mora.
    """
    id_persona, _ = _setup_contrato_con_obligaciones(
        client, db_session,
        codigo="ECP-FC-DIFF-001",
        fecha_inicio="2026-04-01",
        fecha_fin="2026-04-30",
        monto=50000.00,
        dia_vencimiento_canon=1,
    )

    resp_dentro = client.get(
        _url(id_persona), headers=HEADERS, params={"fecha_corte": "2026-04-05"}
    )
    resp_limite = client.get(
        _url(id_persona), headers=HEADERS, params={"fecha_corte": "2026-04-06"}
    )
    resp_fuera = client.get(
        _url(id_persona), headers=HEADERS, params={"fecha_corte": "2026-04-21"}
    )

    assert resp_dentro.status_code == 200
    assert resp_limite.status_code == 200
    assert resp_fuera.status_code == 200

    ob_dentro = resp_dentro.json()["data"]["obligaciones"][0]
    ob_limite = resp_limite.json()["data"]["obligaciones"][0]
    ob_fuera = resp_fuera.json()["data"]["obligaciones"][0]

    assert ob_dentro["dias_atraso"] == 0
    assert ob_dentro["mora_calculada"] == pytest.approx(0.00)
    assert ob_limite["dias_atraso"] == 0
    assert ob_limite["mora_calculada"] == pytest.approx(0.00)
    assert ob_fuera["dias_atraso"] == 15
    assert ob_fuera["mora_calculada"] == pytest.approx(750.00)


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


def test_estado_cuenta_persona_agrupa_contrato_locativo_por_relacion(
    client, db_session
) -> None:
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client,
        db_session,
        codigo="ECP-GRP-LOC-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-06-30",
        monto=12000.00,
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    grupos = {g["grupo_origen_deuda"]: g for g in data["grupos_deuda"]}
    locativo = grupos["LOCATIVO"]
    assert locativo["saldo_total"] == pytest.approx(24000.00)
    assert data["resumen"]["saldo_locativo"] == pytest.approx(24000.00)
    assert len(locativo["relaciones"]) == 1
    relacion = locativo["relaciones"][0]
    assert relacion["tipo_origen"] == "CONTRATO_ALQUILER"
    assert relacion["id_origen"] == contrato["id_contrato_alquiler"]
    assert relacion["cantidad_obligaciones"] == 2
    assert relacion["saldo_total"] == pytest.approx(24000.00)
    assert all(
        ob["composiciones"][0]["codigo_concepto_financiero"] == "CANON_LOCATIVO"
        for ob in relacion["obligaciones"]
    )


def test_estado_cuenta_persona_agrupa_dos_ventas_en_bloques_separados(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Venta", apellido="Agrupada")
    venta_1 = _crear_deuda_venta_para_persona(
        client,
        db_session,
        id_persona=id_persona,
        codigo="ECP-GRP-VTA-001",
        monto=Decimal("100000.00"),
    )
    venta_2 = _crear_deuda_venta_para_persona(
        client,
        db_session,
        id_persona=id_persona,
        codigo="ECP-GRP-VTA-002",
        monto=Decimal("50000.00"),
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    venta = next(g for g in data["grupos_deuda"] if g["grupo_origen_deuda"] == "VENTA")
    assert data["resumen"]["saldo_venta"] == pytest.approx(150000.00)
    assert venta["saldo_total"] == pytest.approx(150000.00)
    assert len(venta["relaciones"]) == 2
    relaciones = {r["id_relacion_generadora"]: r for r in venta["relaciones"]}
    assert set(relaciones) == {
        venta_1["id_relacion_generadora"],
        venta_2["id_relacion_generadora"],
    }
    assert sorted(r["saldo_total"] for r in relaciones.values()) == [
        50000.0,
        100000.0,
    ]
    assert all(
        r["obligaciones"][0]["composiciones"][0]["codigo_concepto_financiero"]
        == "CAPITAL_VENTA"
        for r in relaciones.values()
    )


def test_estado_cuenta_persona_agrupa_factura_servicio_materializada_en_trasladados(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="ECP-GRP-SRV-001"
    )
    materializada = _materializar(client, id_factura)
    assert materializada.status_code == 201
    id_rg = materializada.json()["data"]["id_relacion_generadora"]

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    trasladados = next(
        g for g in data["grupos_deuda"] if g["grupo_origen_deuda"] == "TRASLADADOS"
    )
    assert data["resumen"]["saldo_trasladados"] == pytest.approx(25000.00)
    assert trasladados["saldo_total"] == pytest.approx(25000.00)
    assert len(trasladados["relaciones"]) == 1
    relacion = trasladados["relaciones"][0]
    assert relacion["id_relacion_generadora"] == id_rg
    assert relacion["tipo_origen"] == "FACTURA_SERVICIO"
    assert relacion["obligaciones"][0]["composiciones"][0][
        "codigo_concepto_financiero"
    ] == "SERVICIO_TRASLADADO"


def test_estado_cuenta_persona_muestra_servicio_recuperado_en_trasladados(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="ECP-GRP-REC-001"
    )
    egreso = _registrar_egreso_proveedor(client, db_session, id_factura)
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.0}],
    )
    assert liquidacion.status_code == 201, liquidacion.text
    id_rg = liquidacion.json()["data"]["id_relacion_generadora"]

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    trasladados = next(
        g for g in data["grupos_deuda"] if g["grupo_origen_deuda"] == "TRASLADADOS"
    )
    assert data["resumen"]["saldo_trasladados"] == pytest.approx(25000.00)
    relacion = next(
        r for r in trasladados["relaciones"] if r["id_relacion_generadora"] == id_rg
    )
    assert relacion["tipo_origen"] == "LIQUIDACION_RECUPERO"
    obligacion = relacion["obligaciones"][0]
    assert obligacion["composiciones"][0]["codigo_concepto_financiero"] == (
        "SERVICIO_RECUPERADO"
    )


def test_estado_cuenta_persona_muestra_impuesto_trasladado_en_trasladados(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Impuesto", apellido="Trasladado")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-ECP-IMP",
        modalidad_gestion_impuesto="EMPRESA_PAGA_Y_RECUPERA",
    ).json()["data"]
    egreso = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000ec01",
    )
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000ec02",
    )
    assert liquidacion.status_code == 201, liquidacion.text
    id_rg = liquidacion.json()["data"]["id_relacion_generadora"]

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    trasladados = next(
        g for g in data["grupos_deuda"] if g["grupo_origen_deuda"] == "TRASLADADOS"
    )
    assert data["resumen"]["saldo_trasladados"] == pytest.approx(15000.00)
    relacion = next(
        r for r in trasladados["relaciones"] if r["id_relacion_generadora"] == id_rg
    )
    assert relacion["tipo_origen"] == "LIQUIDACION_IMPUESTO_TRASLADADO"
    obligacion = relacion["obligaciones"][0]
    assert obligacion["composiciones"][0]["codigo_concepto_financiero"] == (
        "IMPUESTO_TRASLADADO"
    )


def test_estado_cuenta_persona_post_pago_por_relacion_reduce_solo_alquiler(
    client, db_session
) -> None:
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client,
        db_session,
        codigo="ECP-PAGO-SCOPE-LOC",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=1000.00,
        dia_vencimiento_canon=20,
    )
    id_rg_locativo = _relacion_por_contrato(
        db_session, contrato["id_contrato_alquiler"]
    )
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="ECP-PAGO-SCOPE-REC"
    )
    egreso = _registrar_egreso_proveedor(
        client, db_session, id_factura, importe=500.00
    )
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.0}],
        importe=500.00,
    )
    assert liquidacion.status_code == 201, liquidacion.text
    id_rg_recupero = liquidacion.json()["data"]["id_relacion_generadora"]

    _pagar_persona(
        client,
        id_persona=id_persona,
        monto=400.00,
        id_relacion_generadora=id_rg_locativo,
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    grupos = {g["grupo_origen_deuda"]: g for g in data["grupos_deuda"]}
    assert data["resumen"]["saldo_locativo"] == pytest.approx(600.00)
    assert data["resumen"]["saldo_trasladados"] == pytest.approx(500.00)
    locativo = grupos["LOCATIVO"]["relaciones"][0]
    trasladados = grupos["TRASLADADOS"]["relaciones"][0]
    assert locativo["id_relacion_generadora"] == id_rg_locativo
    assert locativo["saldo_total"] == pytest.approx(600.00)
    assert trasladados["id_relacion_generadora"] == id_rg_recupero
    assert trasladados["saldo_total"] == pytest.approx(500.00)


def test_estado_cuenta_persona_post_pago_por_relacion_reduce_solo_impuesto(
    client, db_session
) -> None:
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client,
        db_session,
        codigo="ECP-PAGO-SCOPE-IMP",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=1000.00,
    )
    id_rg_locativo = _relacion_por_contrato(
        db_session, contrato["id_contrato_alquiler"]
    )
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-ECP-PAGO-SCOPE-IMP",
        modalidad_gestion_impuesto="EMPRESA_PAGA_Y_RECUPERA",
        importe_total=500.00,
    ).json()["data"]
    egreso = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        importe_pagado=500.00,
        op_id="00000000-0000-0000-0000-00000000ed01",
    )
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        importe_total_trasladar=500.00,
        op_id="00000000-0000-0000-0000-00000000ed02",
    )
    assert liquidacion.status_code == 201, liquidacion.text
    impuesto = liquidacion.json()["data"]

    _pagar_persona(
        client,
        id_persona=id_persona,
        monto=300.00,
        id_relacion_generadora=impuesto["id_relacion_generadora"],
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    grupos = {g["grupo_origen_deuda"]: g for g in data["grupos_deuda"]}
    assert data["resumen"]["saldo_locativo"] == pytest.approx(1000.00)
    assert data["resumen"]["saldo_trasladados"] == pytest.approx(200.00)
    assert grupos["LOCATIVO"]["relaciones"][0]["id_relacion_generadora"] == id_rg_locativo
    assert grupos["LOCATIVO"]["relaciones"][0]["saldo_total"] == pytest.approx(1000.00)
    assert grupos["TRASLADADOS"]["relaciones"][0]["id_relacion_generadora"] == (
        impuesto["id_relacion_generadora"]
    )
    assert grupos["TRASLADADOS"]["relaciones"][0]["saldo_total"] == pytest.approx(200.00)


def test_estado_cuenta_persona_post_pago_global_explicito_refleja_orden_global(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Global", apellido="Explicito")
    venta = _crear_deuda_venta_para_persona(
        client,
        db_session,
        id_persona=id_persona,
        codigo="ECP-PAGO-GLOBAL-VTA",
        monto=Decimal("1000.00"),
    )
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="ECP-PAGO-GLOBAL-REC"
    )
    egreso = _registrar_egreso_proveedor(
        client, db_session, id_factura, importe=500.00
    )
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.0}],
        importe=500.00,
    )
    assert liquidacion.status_code == 201, liquidacion.text
    recupero = liquidacion.json()["data"]

    data_pago = _pagar_persona(
        client,
        id_persona=id_persona,
        monto=1200.00,
        alcance_pago="GLOBAL_PERSONA",
    )

    assert [o["id_obligacion_financiera"] for o in data_pago["obligaciones_pagadas"]] == [
        venta["id_obligacion_financiera"],
        recupero["id_obligacion_financiera"],
    ]
    resp = client.get(_url(id_persona), headers=HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["resumen"]["saldo_total"] == pytest.approx(300.00)
    assert data["resumen"]["saldo_venta"] == pytest.approx(0.00)
    assert data["resumen"]["saldo_trasladados"] == pytest.approx(300.00)
    assert data["grupos_deuda"][0]["grupo_origen_deuda"] == "TRASLADADOS"
    assert data["grupos_deuda"][0]["relaciones"][0]["id_relacion_generadora"] == (
        recupero["id_relacion_generadora"]
    )


def test_estado_cuenta_persona_punitorio_queda_en_relacion_de_obligacion(
    client, db_session
) -> None:
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client,
        db_session,
        codigo="ECP-PUNIT-ACCESORIO",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=500.00,
    )
    id_rg = _relacion_por_contrato(db_session, contrato["id_contrato_alquiler"])
    id_ob = _obligacion_por_relacion(db_session, id_rg)
    _agregar_punitorio_manual(db_session, id_obligacion=id_ob, importe=Decimal("100.00"))

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert [g["grupo_origen_deuda"] for g in data["grupos_deuda"]] == ["LOCATIVO"]
    relacion = data["grupos_deuda"][0]["relaciones"][0]
    assert relacion["id_relacion_generadora"] == id_rg
    codigos = {
        c["codigo_concepto_financiero"]
        for c in relacion["obligaciones"][0]["composiciones"]
    }
    assert codigos == {"CANON_LOCATIVO", "PUNITORIO"}
    assert relacion["saldo_total"] == pytest.approx(600.00)


def test_deuda_consolidada_post_pago_por_relacion_muestra_saldos_aislados(
    client, db_session
) -> None:
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client,
        db_session,
        codigo="ECP-DEUDA-CAN",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=1000.00,
        dia_vencimiento_canon=20,
    )
    id_rg_canon = _relacion_por_contrato(db_session, contrato["id_contrato_alquiler"])
    id_ob_canon = _obligacion_por_relacion(db_session, id_rg_canon)
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="ECP-DEUDA-REC"
    )
    egreso = _registrar_egreso_proveedor(
        client, db_session, id_factura, importe=500.00
    )
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.0}],
        importe=500.00,
    )
    assert liquidacion.status_code == 201, liquidacion.text
    recupero = liquidacion.json()["data"]

    _pagar_persona(
        client,
        id_persona=id_persona,
        monto=400.00,
        id_relacion_generadora=id_rg_canon,
    )

    deuda_canon = client.get(
        "/api/v1/financiero/deuda",
        headers=HEADERS,
        params={"id_relacion_generadora": id_rg_canon},
    )
    deuda_recupero = client.get(
        "/api/v1/financiero/deuda",
        headers=HEADERS,
        params={"id_relacion_generadora": recupero["id_relacion_generadora"]},
    )

    assert deuda_canon.status_code == 200, deuda_canon.text
    assert deuda_recupero.status_code == 200, deuda_recupero.text
    item_canon = deuda_canon.json()["data"]["items"][0]
    item_recupero = deuda_recupero.json()["data"]["items"][0]
    assert item_canon["id_obligacion_financiera"] == id_ob_canon
    assert item_canon["saldo_pendiente"] == pytest.approx(600.00)
    assert item_canon["composiciones"][0]["saldo_componente"] == pytest.approx(600.00)
    assert item_recupero["id_obligacion_financiera"] == recupero["id_obligacion_financiera"]
    assert item_recupero["saldo_pendiente"] == pytest.approx(500.00)
    assert item_recupero["composiciones"][0]["saldo_componente"] == pytest.approx(500.00)


def test_estado_cuenta_persona_servicio_recuperado_mora_por_aplica_punitorio(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="ECP-MORA-REC"
    )
    egreso = _registrar_egreso_proveedor(client, db_session, id_factura)
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.0}],
    )
    assert liquidacion.status_code == 201, liquidacion.text

    resp = client.get(
        _url(id_persona),
        headers=HEADERS,
        params={"fecha_corte": "2026-06-20"},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    obligacion = data["obligaciones"][0]
    mora_esperada = 25000.00 * TASA_DIARIA_MORA * 5
    assert obligacion["composiciones"][0]["codigo_concepto_financiero"] == (
        "SERVICIO_RECUPERADO"
    )
    assert obligacion["mora_calculada"] == pytest.approx(mora_esperada)
    assert data["resumen"]["mora_calculada"] == pytest.approx(mora_esperada)


def test_estado_cuenta_persona_impuesto_trasladado_no_mora_por_default(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Impuesto", apellido="SinMora")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-ECP-IMP-SIN-MORA",
        modalidad_gestion_impuesto="EMPRESA_PAGA_Y_RECUPERA",
    ).json()["data"]
    egreso = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000ec11",
    )
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000ec12",
    )
    assert liquidacion.status_code == 201, liquidacion.text

    resp = client.get(
        _url(id_persona),
        headers=HEADERS,
        params={"fecha_corte": "2026-06-20"},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    obligacion = data["obligaciones"][0]
    assert obligacion["composiciones"][0]["codigo_concepto_financiero"] == (
        "IMPUESTO_TRASLADADO"
    )
    assert obligacion["mora_calculada"] == pytest.approx(0.0)
    assert data["resumen"]["mora_calculada"] == pytest.approx(0.0)


def test_estado_cuenta_persona_excluye_cancelada_sin_saldo_por_default(
    client, db_session
) -> None:
    id_persona, contrato = _setup_contrato_con_obligaciones(
        client,
        db_session,
        codigo="ECP-CANCELADA-SIN-SALDO",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=20000.00,
    )
    id_obligacion = db_session.execute(
        text(
            """
            SELECT o.id_obligacion_financiera
            FROM obligacion_financiera o
            JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = o.id_relacion_generadora
            WHERE rg.tipo_origen = 'contrato_alquiler'
              AND rg.id_origen = :id_contrato
              AND o.deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"id_contrato": contrato["id_contrato_alquiler"]},
    ).scalar_one()
    db_session.execute(
        text(
            """
            UPDATE composicion_obligacion
            SET saldo_componente = 0
            WHERE id_obligacion_financiera = :id_obligacion
              AND deleted_at IS NULL
            """
        ),
        {"id_obligacion": id_obligacion},
    )
    db_session.execute(
        text(
            """
            UPDATE obligacion_financiera
            SET saldo_pendiente = 0,
                estado_obligacion = 'CANCELADA'
            WHERE id_obligacion_financiera = :id_obligacion
            """
        ),
        {"id_obligacion": id_obligacion},
    )

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["obligaciones"] == []
    assert data["grupos_deuda"] == []
    assert data["resumen"]["saldo_pendiente_total"] == pytest.approx(0.0)

    resp_cancelada = client.get(
        _url(id_persona), params={"estado": "CANCELADA"}, headers=HEADERS
    )

    assert resp_cancelada.status_code == 200
    data_cancelada = resp_cancelada.json()["data"]
    assert len(data_cancelada["obligaciones"]) == 1
    assert data_cancelada["obligaciones"][0]["estado_obligacion"] == "CANCELADA"


def test_estado_cuenta_persona_read_only_no_modifica_saldos_ni_estados(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="ECP-READONLY-001"
    )
    materializada = _materializar(client, id_factura)
    assert materializada.status_code == 201
    id_obligacion = materializada.json()["data"]["id_obligacion_financiera"]
    before = db_session.execute(
        text(
            """
            SELECT estado_obligacion, importe_total, saldo_pendiente
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id_obligacion
            """
        ),
        {"id_obligacion": id_obligacion},
    ).mappings().one()

    resp = client.get(_url(id_persona), headers=HEADERS)

    after = db_session.execute(
        text(
            """
            SELECT estado_obligacion, importe_total, saldo_pendiente
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id_obligacion
            """
        ),
        {"id_obligacion": id_obligacion},
    ).mappings().one()
    assert resp.status_code == 200
    assert after["estado_obligacion"] == before["estado_obligacion"]
    assert after["importe_total"] == before["importe_total"]
    assert after["saldo_pendiente"] == before["saldo_pendiente"]


def test_estado_cuenta_persona_punitorio_alquiler_queda_en_bloque_locativo(
    client, db_session
) -> None:
    id_persona, _ = _setup_contrato_con_obligaciones(
        client,
        db_session,
        codigo="ECP-GRP-PUNIT-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
        dia_vencimiento_canon=1,
    )
    pago = client.post(
        "/api/v1/financiero/pagos",
        headers=HEADERS,
        params={"id_persona": id_persona},
        json={"monto": 50.00, "fecha_pago": "2026-05-20"},
    )
    assert pago.status_code == 201

    resp = client.get(
        _url(id_persona),
        headers=HEADERS,
        params={"fecha_corte": "2026-05-20"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    locativo = next(
        g for g in data["grupos_deuda"] if g["grupo_origen_deuda"] == "LOCATIVO"
    )
    composiciones = locativo["relaciones"][0]["obligaciones"][0]["composiciones"]
    assert {c["codigo_concepto_financiero"] for c in composiciones} >= {
        "CANON_LOCATIVO",
        "PUNITORIO",
    }


def test_estado_cuenta_persona_saldos_jerarquicos_suman(client, db_session) -> None:
    id_persona, _ = _setup_contrato_con_obligaciones(
        client,
        db_session,
        codigo="ECP-GRP-SUM-LOC",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
        monto=10000.00,
    )
    _crear_deuda_venta_para_persona(
        client,
        db_session,
        id_persona=id_persona,
        codigo="ECP-GRP-SUM-VTA",
        monto=Decimal("20000.00"),
    )
    id_factura, id_inmueble, id_servicio, _ = _crear_factura_servicio_con_responsable(
        client,
        db_session,
        codigo="ECP-GRP-SUM-SRV",
    )
    db_session.execute(
        text(
            """
            UPDATE asignacion_servicio_responsable
            SET id_persona = :id_persona
            WHERE id_servicio = :id_servicio
              AND id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {
            "id_persona": id_persona,
            "id_servicio": id_servicio,
            "id_inmueble": id_inmueble,
        },
    )
    materializada = _materializar(client, id_factura)
    assert materializada.status_code == 201

    resp = client.get(_url(id_persona), headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()["data"]
    resumen = data["resumen"]
    grupos = data["grupos_deuda"]
    assert resumen["saldo_total"] == pytest.approx(
        resumen["saldo_locativo"]
        + resumen["saldo_venta"]
        + resumen["saldo_trasladados"]
        + resumen["saldo_otros"]
    )
    assert resumen["saldo_total"] == pytest.approx(
        sum(g["saldo_total"] for g in grupos)
    )
    for grupo in grupos:
        assert grupo["saldo_total"] == pytest.approx(
            sum(r["saldo_total"] for r in grupo["relaciones"])
        )
        for relacion in grupo["relaciones"]:
            assert relacion["saldo_total"] == pytest.approx(
                sum(o["saldo_pendiente"] for o in relacion["obligaciones"])
            )
            assert all(o["composiciones"] for o in relacion["obligaciones"])
