from sqlalchemy import text

from tests.test_contratos_alquiler_baja import _crear_contrato_borrador
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_event_contrato_alquiler import (
    _activar,
    _crear_condicion,
    _crear_contrato_borrador as _crear_contrato_cronograma,
    _crear_locatario_principal,
)


def _detalle(client, id_contrato: int):
    return client.get(f"/api/v1/contratos-alquiler/{id_contrato}/detalle-integral")


def _contadores_financieros(db_session) -> dict:
    return dict(
        db_session.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM relacion_generadora) AS relaciones,
                    (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones,
                    (SELECT COUNT(*) FROM movimiento_financiero) AS movimientos,
                    (SELECT COUNT(*) FROM aplicacion_financiera) AS aplicaciones,
                    (SELECT COUNT(*) FROM movimiento_tesoreria) AS movimientos_tesoreria,
                    (SELECT COUNT(*) FROM outbox_event) AS outbox_events,
                    (SELECT COUNT(*) FROM inbox_event) AS inbox_events
                """
            )
        ).mappings().one()
    )


def test_detalle_integral_borrador_sin_financiero_devuelve_vacio(
    client, db_session
) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-DET-001")

    response = _detalle(client, contrato["id_contrato_alquiler"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]
    assert data["estado_contrato"] == "borrador"
    assert data["relacion_financiera"] is None
    assert data["obligaciones_financieras"] == []
    assert data["partes"] == []
    assert data["entrega_locativa"] is None
    assert data["restitucion_locativa"] is None
    assert data["resumen_financiero"] == {
        "cantidad_obligaciones": 0,
        "saldo_total": "0",
        "saldo_pendiente": "0",
        "importe_cancelado": "0",
        "cantidad_vencidas": 0,
        "cantidad_canceladas": 0,
        "cantidad_anuladas": 0,
    }

    assert _contadores_financieros(db_session)["relaciones"] >= 0


def test_detalle_integral_activo_con_cronograma_devuelve_relacion_y_obligaciones(
    client, db_session
) -> None:
    contrato = _crear_contrato_cronograma(
        client,
        codigo="CA-DET-002",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 1000.00, "2026-05-01")
    id_locatario = _crear_locatario_principal(
        client, db_session, contrato["id_contrato_alquiler"]
    )
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    response = _detalle(client, contrato["id_contrato_alquiler"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["relacion_financiera"]["tipo_origen"].lower() == "contrato_alquiler"
    assert data["relacion_financiera"]["id_origen"] == contrato["id_contrato_alquiler"]
    assert len(data["obligaciones_financieras"]) == 3
    assert float(data["resumen_financiero"]["saldo_total"]) == 3000.00
    assert float(data["resumen_financiero"]["saldo_pendiente"]) == 3000.00
    assert data["resumen_financiero"]["cantidad_obligaciones"] == 3

    obligacion = data["obligaciones_financieras"][0]
    assert obligacion["estado_obligacion"] == "EMITIDA"
    assert obligacion["periodo_desde"] == "2026-05-01"
    assert obligacion["composiciones"][0]["codigo_concepto_financiero"] == "CANON_LOCATIVO"
    assert float(obligacion["composiciones"][0]["saldo_componente"]) == 1000.00
    assert obligacion["obligados"][0]["id_persona"] == id_locatario
    assert obligacion["obligados"][0]["rol_obligado"] == "LOCATARIO_PRINCIPAL"


def test_detalle_integral_incluye_partes_objetos_y_condiciones(
    client, db_session
) -> None:
    contrato = _crear_contrato_cronograma(
        client,
        codigo="CA-DET-003",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
    )
    condicion = _crear_condicion(
        client, contrato["id_contrato_alquiler"], 1500.00, "2026-05-01"
    )
    id_locatario = _crear_locatario_principal(
        client, db_session, contrato["id_contrato_alquiler"]
    )

    response = _detalle(client, contrato["id_contrato_alquiler"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["objetos"]) == 1
    assert data["objetos"][0]["id_inmueble"] == contrato["objetos"][0]["id_inmueble"]
    assert len(data["condiciones_economicas_alquiler"]) == 1
    assert data["condiciones_economicas_alquiler"][0]["id_condicion_economica"] == (
        condicion["id_condicion_economica"]
    )
    assert len(data["partes"]) == 1
    assert data["partes"][0]["id_persona"] == id_locatario
    assert data["partes"][0]["codigo_rol"] == "LOCATARIO_PRINCIPAL"


def test_detalle_integral_no_crea_efectos_financieros(client, db_session) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-DET-004")
    before = _contadores_financieros(db_session)

    response = _detalle(client, contrato["id_contrato_alquiler"])

    assert response.status_code == 200
    assert _contadores_financieros(db_session) == before


def test_detalle_integral_404_si_contrato_no_existe(client) -> None:
    response = _detalle(client, 999999)

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_detalle_integral_404_si_contrato_dado_de_baja(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-DET-005")
    baja = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/baja",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )
    assert baja.status_code == 200

    response = _detalle(client, contrato["id_contrato_alquiler"])

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_detalle_integral_no_ejecuta_mora_ni_cambia_estados(
    client, db_session
) -> None:
    contrato = _crear_contrato_cronograma(
        client,
        codigo="CA-DET-006",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-05-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 1000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    db_session.execute(
        text(
            """
            UPDATE obligacion_financiera o
            SET fecha_emision = DATE '2026-01-01',
                fecha_vencimiento = DATE '2026-01-02',
                estado_obligacion = 'EMITIDA'
            FROM relacion_generadora rg
            WHERE rg.id_relacion_generadora = o.id_relacion_generadora
              AND rg.tipo_origen = 'contrato_alquiler'
              AND rg.id_origen = :id_contrato
            """
        ),
        {"id_contrato": contrato["id_contrato_alquiler"]},
    )

    response = _detalle(client, contrato["id_contrato_alquiler"])

    assert response.status_code == 200
    obligacion = response.json()["data"]["obligaciones_financieras"][0]
    assert obligacion["fecha_vencimiento"] == "2026-01-02"
    assert obligacion["estado_obligacion"] == "EMITIDA"
    assert response.json()["data"]["resumen_financiero"]["cantidad_vencidas"] == 0
