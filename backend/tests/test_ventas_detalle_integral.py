from sqlalchemy import text

from app.application.financiero.services.handle_venta_confirmada_event_service import (
    HandleVentaConfirmadaEventService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from tests.test_cesiones_create import _payload_cesion
from tests.test_disponibilidades_create import HEADERS
from tests.test_escrituraciones_create import _payload_escrituracion
from tests.test_instrumentos_compraventa_create import _payload_instrumento
from tests.test_ventas_confirm import (
    _crear_venta_desde_reserva_publica,
    _payload_confirmar_venta,
)


def _detalle(client, id_venta: int):
    return client.get(f"/api/v1/ventas/{id_venta}/detalle-integral")


def _contadores_efectos(db_session) -> dict:
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
                    (SELECT COUNT(*) FROM inbox_event) AS inbox_events,
                    (SELECT COUNT(*) FROM liquidacion_punitorio) AS punitorios
                """
            )
        ).mappings().one()
    )


def _confirmar_venta(client, db_session) -> dict:
    venta = _crear_venta_desde_reserva_publica(client, db_session)
    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    return {
        "id_venta": data["id_venta"],
        "version_registro": data["version_registro"],
        "id_inmueble": venta["id_inmueble"],
        "id_reserva_venta": venta["id_reserva_venta"],
    }


def _procesar_evento_financiero_venta(db_session, *, id_venta: int) -> dict:
    event = dict(
        db_session.execute(
            text(
                """
                SELECT id, event_type, aggregate_type, aggregate_id, payload
                FROM outbox_event
                WHERE event_type = 'venta_confirmada'
                  AND aggregate_type = 'venta'
                  AND aggregate_id = :id_venta
                """
            ),
            {"id_venta": id_venta},
        ).mappings().one()
    )
    result = HandleVentaConfirmadaEventService(
        repository=FinancieroRepository(db_session),
    ).execute(event)
    assert result.success is True
    assert result.data is not None
    return result.data


def _id_persona_parte_venta(db_session, *, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT id_persona
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'venta'
              AND id_relacion = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_relacion_persona_rol
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()["id_persona"]


def _insertar_obligado(db_session, *, id_obligacion_financiera: int, id_persona: int):
    db_session.execute(
        text(
            """
            INSERT INTO obligacion_obligado (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_obligacion_financiera,
                id_persona,
                rol_obligado,
                porcentaje_responsabilidad
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                CAST(:op_id AS uuid),
                CAST(:op_id AS uuid),
                :id_obligacion_financiera,
                :id_persona,
                'COMPRADOR',
                100.00
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_obligacion_financiera": id_obligacion_financiera,
            "id_persona": id_persona,
        },
    )


def test_detalle_integral_venta_sin_financiero_devuelve_relacion_null_y_obligaciones_vacias(
    client, db_session
) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id_venta"] == venta["id_venta"]
    assert data["estado_venta"] == "borrador"
    assert data["relacion_financiera"] is None
    assert data["obligaciones_financieras"] == []
    assert data["resumen_financiero"] == {
        "cantidad_obligaciones": 0,
        "saldo_total": "0",
        "saldo_pendiente": "0",
        "importe_cancelado": "0",
        "cantidad_vencidas": 0,
        "cantidad_canceladas": 0,
        "cantidad_anuladas": 0,
    }


def test_detalle_integral_venta_confirmada_devuelve_relacion_y_capital_venta(
    client, db_session
) -> None:
    venta = _confirmar_venta(client, db_session)
    fin = _procesar_evento_financiero_venta(db_session, id_venta=venta["id_venta"])

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["relacion_financiera"]["tipo_origen"].lower() == "venta"
    assert data["relacion_financiera"]["id_origen"] == venta["id_venta"]
    assert data["relacion_financiera"]["id_relacion_generadora"] == (
        fin["id_relacion_generadora"]
    )
    assert len(data["obligaciones_financieras"]) == 1
    obligacion = data["obligaciones_financieras"][0]
    assert obligacion["id_obligacion_financiera"] == fin["id_obligacion_financiera"]
    assert obligacion["estado_obligacion"] == "PROYECTADA"
    assert obligacion["composiciones"][0]["codigo_concepto_financiero"] == "CAPITAL_VENTA"
    assert float(obligacion["composiciones"][0]["saldo_componente"]) == 150000.00
    assert data["resumen_financiero"]["cantidad_obligaciones"] == 1
    assert float(data["resumen_financiero"]["saldo_pendiente"]) == 150000.00


def test_detalle_integral_incluye_objetos_condiciones_partes_y_recursos_comerciales(
    client, db_session
) -> None:
    venta = _confirmar_venta(client, db_session)

    instrumento = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            objetos=[
                {
                    "id_inmueble": venta["id_inmueble"],
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto alcanzado",
                }
            ]
        ),
    )
    assert instrumento.status_code == 201
    cesion = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(),
    )
    assert cesion.status_code == 201
    escrituracion = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(numero_escritura="ESC-DET-INT-001"),
    )
    assert escrituracion.status_code == 201

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["reserva_origen"]["id_reserva_venta"] == venta["id_reserva_venta"]
    assert len(data["objetos"]) == 1
    assert data["objetos"][0]["id_inmueble"] == venta["id_inmueble"]
    assert float(data["condiciones_comerciales"]["monto_total"]) == 150000.00
    assert data["condiciones_comerciales"]["moneda"] is None
    assert float(data["condiciones_comerciales"]["objetos"][0]["precio_asignado"]) == 150000.00
    assert len(data["partes"]) == 1
    assert data["partes"][0]["codigo_rol"] == "ROL-COM-9301"
    assert len(data["instrumentos_compraventa"]) == 1
    assert len(data["cesiones"]) == 1
    assert len(data["escrituraciones"]) == 1
    assert len(data["integracion_inmobiliaria"]["eventos"]) == 2


def test_detalle_integral_incluye_obligados_si_existen(client, db_session) -> None:
    venta = _confirmar_venta(client, db_session)
    fin = _procesar_evento_financiero_venta(db_session, id_venta=venta["id_venta"])
    id_persona = _id_persona_parte_venta(db_session, id_venta=venta["id_venta"])
    _insertar_obligado(
        db_session,
        id_obligacion_financiera=fin["id_obligacion_financiera"],
        id_persona=id_persona,
    )

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    obligados = response.json()["data"]["obligaciones_financieras"][0]["obligados"]
    assert len(obligados) == 1
    assert obligados[0]["id_persona"] == id_persona
    assert obligados[0]["rol_obligado"] == "COMPRADOR"


def test_detalle_integral_no_crea_efectos_ni_ejecuta_mora(client, db_session) -> None:
    venta = _confirmar_venta(client, db_session)
    fin = _procesar_evento_financiero_venta(db_session, id_venta=venta["id_venta"])
    db_session.execute(
        text(
            """
            UPDATE obligacion_financiera
            SET fecha_emision = DATE '2026-01-01',
                fecha_vencimiento = DATE '2026-01-02',
                estado_obligacion = 'EMITIDA'
            WHERE id_obligacion_financiera = :id_obligacion_financiera
            """
        ),
        {"id_obligacion_financiera": fin["id_obligacion_financiera"]},
    )
    before = _contadores_efectos(db_session)

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 200
    assert _contadores_efectos(db_session) == before
    obligacion = response.json()["data"]["obligaciones_financieras"][0]
    assert obligacion["fecha_vencimiento"] == "2026-01-02"
    assert obligacion["estado_obligacion"] == "EMITIDA"
    assert response.json()["data"]["resumen_financiero"]["cantidad_vencidas"] == 0


def test_detalle_integral_404_si_venta_no_existe(client) -> None:
    response = _detalle(client, 999999)

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_detalle_integral_404_si_venta_dada_de_baja(client, db_session) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)
    db_session.execute(
        text(
            """
            UPDATE venta
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    )

    response = _detalle(client, venta["id_venta"])

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
