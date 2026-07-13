from datetime import date
from uuid import UUID

import pytest
from sqlalchemy import text

from app.api.core_ef_headers import CoreEFHeaders
from app.application.financiero.services.preview_indexacion_cuotas_v2_service import (
    PreviewIndexacionCuotasV2Command,
    PreviewIndexacionCuotasV2Service,
)
from app.infrastructure.persistence.repositories.preview_indexacion_cuotas_v2_repository import (
    PreviewIndexacionCuotasV2SqlAlchemyRepository,
)
from test_corridas_indexacion_cuotas_v2_sql import (
    _create_context,
    _create_indice,
    _insert_composicion,
    _scalar,
)

HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _cmd(ctx, **overrides):
    data = dict(
        id_plan_pago_venta=ctx["plan"]["plan"],
        id_plan_pago_venta_bloque=ctx["plan"]["bloque"],
        id_plan_pago_venta_bloque_indexacion=ctx["config"],
        id_indice_financiero=ctx["indice"]["id"],
        id_indice_financiero_valor_aplicado=ctx["indice"]["aplicado"],
        fecha_corte=date(2026, 6, 30),
        periodo_aplicado=date(2026, 6, 1),
    )
    data.update(overrides)
    return PreviewIndexacionCuotasV2Command(**data)


def _payload(ctx, **overrides):
    c = _cmd(ctx, **overrides)
    return {
        "id_plan_pago_venta": c.id_plan_pago_venta,
        "id_plan_pago_venta_bloque": c.id_plan_pago_venta_bloque,
        "id_plan_pago_venta_bloque_indexacion": c.id_plan_pago_venta_bloque_indexacion,
        "id_indice_financiero": c.id_indice_financiero,
        "id_indice_financiero_valor_aplicado": c.id_indice_financiero_valor_aplicado,
        "fecha_corte": c.fecha_corte.isoformat(),
        "periodo_aplicado": c.periodo_aplicado.isoformat(),
        "persistir": c.persistir,
        "motivo": c.motivo,
    }


def _service(db_session):
    return PreviewIndexacionCuotasV2Service(
        PreviewIndexacionCuotasV2SqlAlchemyRepository(db_session)
    )


def test_postgres_estados_reales_y_fecha_corte(db_session):
    ctx = _create_context(db_session)
    service = _service(db_session)
    for estado in ["PROYECTADA", "EMITIDA", "EXIGIBLE", "VENCIDA"]:
        db_session.execute(text("UPDATE obligacion_financiera SET estado_obligacion=:e, fecha_emision=DATE '2026-05-01', fecha_vencimiento=DATE '2026-06-01' WHERE id_obligacion_financiera=:id"), {"e": estado, "id": ctx["obligacion"]})
        result = service.execute(_cmd(ctx, fecha_corte=date(2026, 6, 30)))
        det = next(d for d in result.data["detalles"] if d["id_obligacion_financiera"] == ctx["obligacion"])
        assert det["estado_elegibilidad"] == "ELEGIBLE"
        if estado == "VENCIDA":
            assert "OBLIGACION_VENCIDA_SIN_EFECTOS_POSTERIORES" in det["advertencias"]
    for estado in ["PARCIALMENTE_CANCELADA", "CANCELADA", "ANULADA", "REEMPLAZADA", "PENDIENTE_AJUSTE"]:
        db_session.execute(text("UPDATE obligacion_financiera SET estado_obligacion=:e WHERE id_obligacion_financiera=:id"), {"e": estado, "id": ctx["obligacion"]})
        result = service.execute(_cmd(ctx))
        det = next(d for d in result.data["detalles"] if d["id_obligacion_financiera"] == ctx["obligacion"])
        assert det["estado_elegibilidad"] == "EXCLUIDA"
        assert det["motivo_exclusion"] == "ESTADO_OBLIGACION_NO_ELEGIBLE"


def test_postgres_pagos_imputaciones_y_punitorios_excluyen_pero_anulados_no(db_session):
    ctx = _create_context(db_session)
    mov = _scalar(db_session, """
        INSERT INTO movimiento_financiero (fecha_movimiento,tipo_movimiento,importe,signo,estado_movimiento)
        VALUES (DATE '2026-06-15','PAGO',10.00,'CREDITO','APLICADO') RETURNING id_movimiento_financiero
    """)
    app = _scalar(db_session, """
        INSERT INTO aplicacion_financiera (id_movimiento_financiero,id_obligacion_financiera,fecha_aplicacion,tipo_aplicacion,orden_aplicacion,importe_aplicado)
        VALUES (:mov,:obl,DATE '2026-06-15','MANUAL',1,10.00) RETURNING id_aplicacion_financiera
    """, mov=mov, obl=ctx["obligacion"])
    det = _service(db_session).execute(_cmd(ctx)).data["detalles"][0]
    assert det["motivo_exclusion"] == "OBLIGACION_CON_IMPUTACIONES_ACTIVAS"
    db_session.execute(text("UPDATE aplicacion_financiera SET deleted_at=CURRENT_TIMESTAMP WHERE id_aplicacion_financiera=:id"), {"id": app})
    db_session.execute(text("UPDATE movimiento_financiero SET estado_movimiento='ANULADO' WHERE id_movimiento_financiero=:id"), {"id": mov})
    det = _service(db_session).execute(_cmd(ctx)).data["detalles"][0]
    assert det["estado_elegibilidad"] == "ELEGIBLE"
    punitorio = _scalar(db_session, "SELECT id_concepto_financiero FROM concepto_financiero WHERE codigo_concepto_financiero='PUNITORIO'")
    _insert_composicion(db_session, ctx["obligacion"], punitorio, 5)
    det = _service(db_session).execute(_cmd(ctx)).data["detalles"][0]
    assert det["motivo_exclusion"] == "OBLIGACION_CON_MORA_INCOMPATIBLE"


def test_postgres_persistido_core_ef_snapshots_fecha_publicacion_idempotencia_y_payload_hash(db_session):
    ctx = _create_context(db_session)
    core = CoreEFHeaders(UUID(HEADERS["X-Op-Id"]), 1, 1, 1)
    result = _service(db_session).execute(_cmd(ctx, persistir=True, motivo="m1"), core)
    assert result.success
    corrida = result.data["id_corrida_indexacion_financiera"]
    row = db_session.execute(text("""
        SELECT fecha_publicacion_indice, op_id::text, op_id_alta::text, op_id_ultima_modificacion::text,
               id_instalacion_origen, id_instalacion_ultima_modificacion, payload_hash
        FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id
    """), {"id": corrida}).mappings().one()
    assert str(row["fecha_publicacion_indice"]) == "2026-06-02"
    assert row["op_id"] == HEADERS["X-Op-Id"]
    assert row["op_id_alta"] == HEADERS["X-Op-Id"]
    assert row["op_id_ultima_modificacion"] == HEADERS["X-Op-Id"]
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    det = db_session.execute(text("""
        SELECT op_id_alta::text AS op_id_alta, op_id_ultima_modificacion::text AS op_id_ultima_modificacion,
               snapshot_antes, snapshot_despues
        FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera=:id LIMIT 1
    """), {"id": corrida}).mappings().one()
    assert det["op_id_alta"] == HEADERS["X-Op-Id"]
    assert det["op_id_ultima_modificacion"] == HEADERS["X-Op-Id"]
    assert det["snapshot_antes"]["estado_obligacion"] == "PROYECTADA"
    assert det["snapshot_despues"]["estado_elegibilidad"] == "ELEGIBLE"
    assert _service(db_session).execute(_cmd(ctx, persistir=True, motivo="m1"), core).data["id_corrida_indexacion_financiera"] == corrida
    assert not _service(db_session).execute(_cmd(ctx, persistir=True, motivo="otro"), core).success
    assert not _service(db_session).execute(_cmd(ctx, persistir=True, motivo="m1", fecha_corte=date(2026, 7, 1)), core).success


def test_postgres_ajuste_negativo_persistido_no_viola_checks(db_session):
    ctx = _create_context(db_session)
    neg = _scalar(db_session, """
        INSERT INTO indice_financiero_valor (id_indice_financiero,fecha_valor,valor_indice,fecha_publicacion,estado_valor_indice)
        VALUES (:i,DATE '2026-07-01',80.00000000,DATE '2026-07-02','PUBLICADO') RETURNING id_indice_financiero_valor
    """, i=ctx["indice"]["id"])
    result = _service(db_session).execute(_cmd(ctx, id_indice_financiero_valor_aplicado=neg, persistir=True), CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655440001"), 1, 1, 1))
    assert result.success
    row = db_session.execute(text("SELECT ajuste_nuevo, diferencia_neta, motivo_exclusion, snapshot_despues FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera=:id LIMIT 1"), {"id": result.data["id_corrida_indexacion_financiera"]}).mappings().one()
    assert row["ajuste_nuevo"] == 0
    assert row["diferencia_neta"] == 0
    assert row["motivo_exclusion"] == "AJUSTE_NEGATIVO_NO_SOPORTADO"
    assert row["snapshot_despues"]["ajuste_objetivo_calculado"] == "-200.00"


def test_postgres_hash_mutaciones_relevantes_y_orden_estable(db_session):
    ctx = _create_context(db_session)
    service = _service(db_session)
    h1 = service.execute(_cmd(ctx)).data["hash_corrida"]
    db_session.execute(text("UPDATE obligacion_financiera SET version_registro=version_registro+1 WHERE id_obligacion_financiera=:id"), {"id": ctx["obligacion"]})
    assert service.execute(_cmd(ctx)).data["hash_corrida"] != h1


def test_postgres_rollback_si_falla_detalle(db_session):
    ctx = _create_context(db_session)
    repo = PreviewIndexacionCuotasV2SqlAlchemyRepository(db_session)
    original = repo.create_corrida_preview

    def fail_after_header(payload, detalles):
        payload = dict(payload)
        bad = [dict(detalles[0], id_composicion_capital_venta=detalles[0]["id_composicion_ajuste_indexacion"])]
        return original(payload, bad)

    repo.create_corrida_preview = fail_after_header
    with pytest.raises(Exception):
        PreviewIndexacionCuotasV2Service(repo).execute(_cmd(ctx, persistir=True), CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655440099"), 1, 1, 1))
    db_session.rollback()
    assert db_session.execute(text("SELECT COUNT(*) FROM corrida_indexacion_financiera WHERE op_id='550e8400-e29b-41d4-a716-446655440099'" )).scalar() == 0


def test_api_preview_efimero_persistido_headers_errores_y_decimal(client, db_session):
    ctx = _create_context(db_session)
    response = client.post("/api/v1/financiero/indexacion-cuotas-v2/preview", json=_payload(ctx))
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["modo"] == "EFIMERA"
    assert body["coeficiente_indexacion"] == "1.25000000"

    payload = _payload(ctx, persistir=True)
    response = client.post("/api/v1/financiero/indexacion-cuotas-v2/preview", json=payload)
    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"

    response = client.post("/api/v1/financiero/indexacion-cuotas-v2/preview", headers=HEADERS, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["modo"] == "PERSISTIDA"

    bad = {**payload, "persistir": False, "id_indice_financiero_valor_aplicado": ctx["otro_indice"]["aplicado"]}
    response = client.post("/api/v1/financiero/indexacion-cuotas-v2/preview", json=bad)
    assert response.status_code == 409
    assert response.json()["error_code"] == "VALOR_INDICE_APLICADO_INCOMPATIBLE"
