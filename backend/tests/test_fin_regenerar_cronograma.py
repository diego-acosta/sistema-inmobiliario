"""
Tests de integración para regeneración controlada de cronograma locativo.
RegenerarCronogramaLocativoService reemplaza obligaciones futuras sin pagos
y genera nuevas con la lógica actual (prorrateo, vencimiento, obligado).
"""
from datetime import date

import pytest
from sqlalchemy import text

from app.application.common.commands import CommandContext
from app.application.financiero.services.regenerar_cronograma_locativo_service import (
    RegenerarCronogramaLocativoService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from app.infrastructure.persistence.repositories.locativo_repository import (
    LocativoRepository,
)
from tests.test_fin_event_contrato_alquiler import (
    _activar,
    _crear_condicion,
    _crear_contrato_borrador,
    _crear_locatario_principal,
    _get_obligaciones_de_relacion,
    _get_relacion_for_contrato,
)
from tests.test_disponibilidades_create import HEADERS

URL_REGENERAR = "/api/v1/financiero/contratos-alquiler/{id}/regenerar-cronograma"


# ── helpers ───────────────────────────────────────────────────────────────────

def _regenerar_via_service(db_session, id_contrato: int, fecha_corte: date):
    loc_repo = LocativoRepository(db_session)
    fin_repo = FinancieroRepository(db_session)
    service = RegenerarCronogramaLocativoService(
        locativo_repository=loc_repo,
        financiero_repository=fin_repo,
    )
    return service.execute(id_contrato, fecha_corte, CommandContext())


def _get_todas_obligaciones(db_session, id_relacion_generadora: int) -> list:
    """Incluye REEMPLAZADAS (deleted_at IS NOT NULL) para verificar trazabilidad."""
    rows = db_session.execute(
        text(
            """
            SELECT
                id_obligacion_financiera,
                periodo_desde,
                periodo_hasta,
                importe_total,
                estado_obligacion,
                deleted_at
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id
            ORDER BY periodo_desde ASC, id_obligacion_financiera ASC
            """
        ),
        {"id": id_relacion_generadora},
    ).mappings().all()
    return [dict(r) for r in rows]


def _registrar_aplicacion_directa(db_session, id_obligacion: int) -> None:
    """Inserta un movimiento y aplicación financiera para simular pago parcial."""
    id_composicion = db_session.execute(
        text(
            "SELECT id_composicion_obligacion FROM composicion_obligacion "
            "WHERE id_obligacion_financiera = :id AND deleted_at IS NULL LIMIT 1"
        ),
        {"id": id_obligacion},
    ).scalar_one()

    id_mov = db_session.execute(
        text(
            """
            INSERT INTO movimiento_financiero (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                fecha_movimiento, tipo_movimiento, importe, signo, estado_movimiento
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                CURRENT_DATE, 'PAGO', 100.00, 'CREDITO', 'APLICADO'
            )
            RETURNING id_movimiento_financiero
            """
        ),
        {"op_id": HEADERS["X-Op-Id"]},
    ).scalar_one()

    db_session.execute(
        text(
            """
            INSERT INTO aplicacion_financiera (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_movimiento_financiero, id_obligacion_financiera,
                id_composicion_obligacion, fecha_aplicacion,
                tipo_aplicacion, importe_aplicado, origen_automatico_o_manual
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_mov, :id_ob, :id_comp,
                CURRENT_DATE, 'PAGO', 100.00, 'MANUAL'
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_mov": id_mov,
            "id_ob": id_obligacion,
            "id_comp": id_composicion,
        },
    )
    db_session.execute(
        text(
            """
            UPDATE obligacion_financiera
            SET estado_obligacion = 'PARCIALMENTE_CANCELADA',
                saldo_pendiente = saldo_pendiente - 100.00
            WHERE id_obligacion_financiera = :id
            """
        ),
        {"id": id_obligacion},
    )
    db_session.commit()


# ── test: regenera futuras sin pagos ─────────────────────────────────────────

def test_regenerar_reemplaza_obligaciones_futuras_sin_pagos(client, db_session) -> None:
    """
    Contrato de 3 meses con dos condiciones (mayo@50000, jun-jul@70000).
    Regenera desde junio:
    - 2 obligaciones futuras (EMITIDA, jun+jul) → REEMPLAZADA
    - 2 nuevas obligaciones con el monto de condición 2 (70000)
    - 1ª obligación (mayo) no tocada
    """
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-BASE-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    # Dos condiciones no solapadas creadas antes de activar
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 50000.00, "2026-05-01",
        fecha_hasta="2026-05-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 70000.00, "2026-06-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones_iniciales = _get_obligaciones_de_relacion(db_session, id_rg)
    assert len(obligaciones_iniciales) == 3
    assert float(obligaciones_iniciales[0]["importe_total"]) == 50000.00
    assert float(obligaciones_iniciales[1]["importe_total"]) == 70000.00

    result = _regenerar_via_service(db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1))

    assert result.success
    assert result.data["reemplazadas"] == 2
    assert result.data["generadas"] == 2

    activas = _get_obligaciones_de_relacion(db_session, id_rg)
    assert len(activas) == 3  # mayo (original) + junio (nueva) + julio (nueva)

    # Mayo: intacta con monto original
    assert float(activas[0]["importe_total"]) == 50000.00
    assert activas[0]["estado_obligacion"] == "EMITIDA"
    assert activas[0]["periodo_desde"] == date(2026, 5, 1)

    # Junio y julio: nuevas con monto de condición 2
    assert float(activas[1]["importe_total"]) == 70000.00
    assert activas[1]["periodo_desde"] == date(2026, 6, 1)
    assert float(activas[2]["importe_total"]) == 70000.00
    assert activas[2]["periodo_desde"] == date(2026, 7, 1)


def test_regenerar_no_toca_obligacion_cancelada(client, db_session) -> None:
    """
    La obligación CANCELADA no debe ser reemplazada ni regenerada.
    """
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-CANC-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 30000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    # Cancelar manualmente la obligación de junio (período 2)
    db_session.execute(
        text(
            "UPDATE obligacion_financiera SET estado_obligacion = 'CANCELADA', "
            "saldo_pendiente = 0 WHERE id_obligacion_financiera = :id"
        ),
        {"id": obligaciones[1]["id_obligacion_financiera"]},
    )
    db_session.commit()

    result = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1)
    )

    assert result.success
    # Junio cancelada no debe ser incluida en reemplazadas
    assert result.data["reemplazadas"] == 1  # solo julio

    activas = _get_obligaciones_de_relacion(db_session, id_rg)
    estados = {ob["periodo_desde"]: ob["estado_obligacion"] for ob in activas}
    assert estados[date(2026, 6, 1)] == "CANCELADA"  # intacta


def test_regenerar_no_toca_obligacion_parcialmente_cancelada(client, db_session) -> None:
    """
    La obligación PARCIALMENTE_CANCELADA (con aplicación) no debe ser reemplazada.
    """
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-PARC-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 40000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    # Pago parcial sobre junio (índice 1)
    _registrar_aplicacion_directa(db_session, obligaciones[1]["id_obligacion_financiera"])

    result = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1)
    )

    assert result.success
    # Junio parcialmente cancelada no debe ser reemplazada
    assert result.data["reemplazadas"] == 1  # solo julio

    activas = _get_obligaciones_de_relacion(db_session, id_rg)
    estados = {ob["periodo_desde"]: ob["estado_obligacion"] for ob in activas}
    assert estados[date(2026, 6, 1)] == "PARCIALMENTE_CANCELADA"  # intacta


def test_regenerar_no_toca_obligacion_con_aplicaciones(client, db_session) -> None:
    """
    Obligación con aplicaciones (EMITIDA con pago parcial todavía en estado
    intermedio) no debe ser reemplazada porque tiene aplicacion_financiera.
    """
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-APLIC-001",
        fecha_inicio="2026-06-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 20000.00, "2026-06-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)
    assert len(obligaciones) == 2

    # Insertar aplicación financiera sobre junio sin cambiar estado aún
    id_composicion = db_session.execute(
        text(
            "SELECT id_composicion_obligacion FROM composicion_obligacion "
            "WHERE id_obligacion_financiera = :id AND deleted_at IS NULL LIMIT 1"
        ),
        {"id": obligaciones[0]["id_obligacion_financiera"]},
    ).scalar_one()
    id_mov = db_session.execute(
        text(
            """
            INSERT INTO movimiento_financiero (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                fecha_movimiento, tipo_movimiento, importe, signo, estado_movimiento
            ) VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op, :op,
                CURRENT_DATE, 'PAGO', 50.00, 'CREDITO', 'APLICADO'
            ) RETURNING id_movimiento_financiero
            """
        ),
        {"op": HEADERS["X-Op-Id"]},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO aplicacion_financiera (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_movimiento_financiero, id_obligacion_financiera,
                id_composicion_obligacion, fecha_aplicacion,
                tipo_aplicacion, importe_aplicado, origen_automatico_o_manual
            ) VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op, :op,
                :id_mov, :id_ob, :id_comp,
                CURRENT_DATE, 'PAGO', 50.00, 'MANUAL'
            )
            """
        ),
        {
            "op": HEADERS["X-Op-Id"],
            "id_mov": id_mov,
            "id_ob": obligaciones[0]["id_obligacion_financiera"],
            "id_comp": id_composicion,
        },
    )
    db_session.commit()

    result = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1)
    )

    assert result.success
    # Junio tiene aplicación → no reemplazable; solo julio
    assert result.data["reemplazadas"] == 1


def test_regenerar_crea_nuevas_obligaciones_correctas(client, db_session) -> None:
    """
    Las nuevas obligaciones tienen estado EMITIDA, importes correctos,
    locatario principal como obligado y CANON_LOCATIVO como composición.
    """
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-NEWOB-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
        dia_vencimiento_canon=10,
    )
    # Dos condiciones no solapadas: mayo@55000, junio@65000
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 55000.00, "2026-05-01",
        fecha_hasta="2026-05-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 65000.00, "2026-06-01")
    id_locatario = _crear_locatario_principal(
        client, db_session, contrato["id_contrato_alquiler"]
    )
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    result = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1)
    )

    assert result.success
    assert result.data["generadas"] == 1

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    activas = _get_obligaciones_de_relacion(db_session, id_rg)

    # Junio: nueva obligación con monto actualizado y vencimiento correcto
    junio = next(ob for ob in activas if ob["periodo_desde"] == date(2026, 6, 1))
    assert float(junio["importe_total"]) == 65000.00
    assert junio["estado_obligacion"] == "EMITIDA"
    assert junio["fecha_vencimiento"] == date(2026, 6, 10)

    # Verificar obligado
    obligado = db_session.execute(
        text(
            """
            SELECT oo.id_persona, oo.rol_obligado
            FROM obligacion_obligado oo
            WHERE oo.id_obligacion_financiera = :id AND oo.deleted_at IS NULL
            """
        ),
        {"id": junio["id_obligacion_financiera"]},
    ).mappings().one()
    assert obligado["id_persona"] == id_locatario
    assert obligado["rol_obligado"] == "LOCATARIO_PRINCIPAL"

    # Verificar composición
    composicion = db_session.execute(
        text(
            """
            SELECT cf.codigo_concepto_financiero
            FROM composicion_obligacion co
            JOIN concepto_financiero cf ON cf.id_concepto_financiero = co.id_concepto_financiero
            WHERE co.id_obligacion_financiera = :id AND co.deleted_at IS NULL
            """
        ),
        {"id": junio["id_obligacion_financiera"]},
    ).mappings().one()
    assert composicion["codigo_concepto_financiero"] == "CANON_LOCATIVO"


def test_regenerar_mantiene_trazabilidad_de_reemplazadas(client, db_session) -> None:
    """
    Las obligaciones reemplazadas quedan físicamente en la BD con estado REEMPLAZADA
    y deleted_at seteado (soft-delete para liberar constraint único).
    """
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-TRAZ-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 30000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    ids_antes = {
        ob["id_obligacion_financiera"]
        for ob in _get_obligaciones_de_relacion(db_session, id_rg)
    }

    result = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1)
    )
    assert result.success

    # Todas las obligaciones (incluidas reemplazadas) deben existir en BD
    todas = _get_todas_obligaciones(db_session, id_rg)
    ids_todos = {ob["id_obligacion_financiera"] for ob in todas}
    assert ids_antes.issubset(ids_todos)  # las originales siguen en BD

    # Las reemplazadas tienen estado REEMPLAZADA y deleted_at seteado
    reemplazadas = [ob for ob in todas if ob["estado_obligacion"] == "REEMPLAZADA"]
    assert len(reemplazadas) == 2
    for ob in reemplazadas:
        assert ob["deleted_at"] is not None
        assert ob["periodo_desde"] >= date(2026, 6, 1)


def test_regenerar_idempotente_no_duplica_activas(client, db_session) -> None:
    """
    Llamar regenerar dos veces con la misma fecha_corte no debe dejar más
    de una obligación activa por período.
    """
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-IDEM-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 25000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    # Primera regeneración
    r1 = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1)
    )
    assert r1.success
    assert r1.data["generadas"] == 2

    # Segunda regeneración con la misma fecha_corte
    r2 = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1)
    )
    assert r2.success
    assert r2.data["generadas"] == 2

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    activas = _get_obligaciones_de_relacion(db_session, id_rg)

    # Solo debe haber 3 obligaciones activas (mayo + junio + julio)
    assert len(activas) == 3
    # Cada período aparece exactamente una vez
    periodos_activos = [ob["periodo_desde"] for ob in activas]
    assert len(periodos_activos) == len(set(periodos_activos))


def test_regenerar_falla_si_no_existe_contrato(db_session) -> None:
    result = _regenerar_via_service(db_session, 999999, date(2026, 6, 1))
    assert not result.success
    assert "NOT_FOUND_CONTRATO" in result.errors


def test_regenerar_falla_si_no_existe_cronograma(client, db_session) -> None:
    """Contrato existente pero sin cronograma generado → NOT_FOUND_RELACION_GENERADORA."""
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-NOREL-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 10000.00, "2026-05-01")
    # No activamos → sin relacion_generadora

    result = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1)
    )
    assert not result.success
    assert "NOT_FOUND_RELACION_GENERADORA" in result.errors


def test_regenerar_fecha_corte_posterior_a_fin_retorna_vacio(client, db_session) -> None:
    """fecha_corte > fecha_fin del contrato → resultado vacío sin error."""
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-POSTFIN-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 10000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    result = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 8, 1)
    )
    assert result.success
    assert result.data["razon"] == "fecha_corte_posterior_a_fin"
    assert result.data["reemplazadas"] == 0
    assert result.data["generadas"] == 0


def test_regenerar_via_endpoint_http(client, db_session) -> None:
    """El endpoint HTTP regenera correctamente y devuelve estructura esperada."""
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-HTTP-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    # Dos condiciones no solapadas creadas antes de activar
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 60000.00, "2026-05-01",
        fecha_hasta="2026-05-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 80000.00, "2026-06-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    response = client.post(
        URL_REGENERAR.format(id=contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json={"fecha_corte": "2026-06-01"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["reemplazadas"] == 2
    assert body["data"]["generadas"] == 2

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    activas = _get_obligaciones_de_relacion(db_session, id_rg)
    assert len(activas) == 3
    junio = next(ob for ob in activas if ob["periodo_desde"] == date(2026, 6, 1))
    assert float(junio["importe_total"]) == 80000.00


def test_regenerar_con_prorrateo_en_nuevas_obligaciones(client, db_session) -> None:
    """
    La regeneración aplica prorrateo cuando hay cambio de condición a mitad de mes.
    Tres condiciones creadas antes de activar: mayo@30000, jun1-15@30000, jun16+@40000.
    """
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-PROR-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
    )
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 30000.00, "2026-05-01",
        fecha_hasta="2026-05-31",
    )
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 30000.00, "2026-06-01",
        fecha_hasta="2026-06-15",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 40000.00, "2026-06-16")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    result = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 1)
    )

    assert result.success
    assert result.data["generadas"] == 2  # 2 segmentos de junio

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    activas = _get_obligaciones_de_relacion(db_session, id_rg)

    junio_segs = [ob for ob in activas if ob["periodo_desde"] >= date(2026, 6, 1)]
    assert len(junio_segs) == 2
    assert junio_segs[0]["periodo_desde"] == date(2026, 6, 1)
    assert junio_segs[0]["periodo_hasta"] == date(2026, 6, 15)
    assert junio_segs[1]["periodo_desde"] == date(2026, 6, 16)
    assert junio_segs[1]["periodo_hasta"] == date(2026, 6, 30)
    # Suma de importes proporcionales (30 días junio: 15 + 15)
    total_jun = sum(float(ob["importe_total"]) for ob in junio_segs)
    assert total_jun == pytest.approx(30000 * 15 / 30 + 40000 * 15 / 30, abs=0.05)


def test_regenerar_desde_mitad_de_mes_prorratea_periodo_recortado(client, db_session) -> None:
    """
    Si fecha_corte cae dentro del mes, reemplaza la obligacion solapada sin pagos
    y genera una obligacion parcial desde fecha_corte.
    """
    contrato = _crear_contrato_borrador(
        client, codigo="REGEN-PARC-MID-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 30000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    iniciales = _get_obligaciones_de_relacion(db_session, id_rg)
    assert len(iniciales) == 3

    result = _regenerar_via_service(
        db_session, contrato["id_contrato_alquiler"], date(2026, 6, 15)
    )

    assert result.success
    assert result.data["reemplazadas"] == 2
    assert result.data["generadas"] == 2

    activas = _get_obligaciones_de_relacion(db_session, id_rg)
    assert len(activas) == 3
    junio = next(ob for ob in activas if ob["periodo_desde"] == date(2026, 6, 15))
    julio = next(ob for ob in activas if ob["periodo_desde"] == date(2026, 7, 1))
    assert junio["periodo_hasta"] == date(2026, 6, 30)
    assert float(junio["importe_total"]) == pytest.approx(30000 * 16 / 30, abs=0.01)
    assert float(julio["importe_total"]) == pytest.approx(30000.00)
