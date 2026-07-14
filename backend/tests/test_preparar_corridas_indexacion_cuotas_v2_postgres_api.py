from datetime import date
from uuid import UUID

from sqlalchemy import text

from app.api.core_ef_headers import CoreEFHeaders
from app.application.financiero.services.preparar_corridas_indexacion_cuotas_v2_service import (
    PrepararCorridasIndexacionCuotasV2Command,
    PrepararCorridasIndexacionCuotasV2Service,
)
from app.application.financiero.services.preview_indexacion_cuotas_v2_service import PreviewIndexacionCuotasV2Service
from app.infrastructure.persistence.repositories.preparar_corridas_indexacion_cuotas_v2_repository import PrepararCorridasIndexacionCuotasV2SqlAlchemyRepository
from app.infrastructure.persistence.repositories.preview_indexacion_cuotas_v2_repository import PreviewIndexacionCuotasV2SqlAlchemyRepository
from test_corridas_indexacion_cuotas_v2_sql import _create_context, _create_plan_bloque, _insert_composicion, _insert_ofi, _scalar

HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}

URL = "/api/v1/financiero/indexacion-cuotas-v2/valores-indice/{}/preparar-corridas"


def _preparar_service(db_session):
    return PrepararCorridasIndexacionCuotasV2Service(
        PrepararCorridasIndexacionCuotasV2SqlAlchemyRepository(db_session),
        PreviewIndexacionCuotasV2Service(PreviewIndexacionCuotasV2SqlAlchemyRepository(db_session)),
    )


def _core(op_id: str = HEADERS["X-Op-Id"]):
    return CoreEFHeaders(UUID(op_id), 1, 1, 1)


def _hacer_vencidas(db_session, *ids):
    for id_obl in ids:
        db_session.execute(text("UPDATE obligacion_financiera SET fecha_emision=DATE '2026-06-01', fecha_vencimiento=DATE '2026-06-30' WHERE id_obligacion_financiera=:id"), {"id": id_obl})
    db_session.flush()


def _snapshot_deuda(db_session, obligacion):
    return db_session.execute(text("""
        SELECT o.importe_total, o.saldo_pendiente,
               COALESCE(SUM(co.importe_componente) FILTER (WHERE cf.codigo_concepto_financiero='AJUSTE_INDEXACION' AND co.deleted_at IS NULL), 0) AS ajuste,
               (SELECT COUNT(*) FROM obligacion_financiera_indexacion ofi WHERE ofi.id_obligacion_financiera=o.id_obligacion_financiera AND ofi.deleted_at IS NULL) AS trazas
        FROM obligacion_financiera o
        LEFT JOIN composicion_obligacion co ON co.id_obligacion_financiera=o.id_obligacion_financiera
        LEFT JOIN concepto_financiero cf ON cf.id_concepto_financiero=co.id_concepto_financiero
        WHERE o.id_obligacion_financiera=:id
        GROUP BY o.id_obligacion_financiera
    """), {"id": obligacion}).mappings().one()


def test_api_crea_varios_bloques_replay_fecha_deterministica_y_no_modifica_deuda(client, db_session):
    ctx1 = _create_context(db_session)
    plan2 = _create_plan_bloque(db_session, "PREP-B")
    config2 = _scalar(db_session, """
        INSERT INTO plan_pago_venta_bloque_indexacion (
            id_plan_pago_venta_bloque, id_indice_financiero, fecha_base_indice, valor_base_indice,
            modo_indexacion, base_calculo_indexacion, tipo_generacion_indexada, politica_valor_no_disponible
        ) VALUES (:bloque, :indice, DATE '2026-01-01', 100, 'POR_COEFICIENTE',
                  'CAPITAL_INICIAL_BLOQUE', 'DEFINITIVA', 'ERROR_SI_NO_EXISTE')
        RETURNING id_plan_pago_venta_bloque_indexacion
    """, bloque=plan2["bloque"], indice=ctx1["indice"]["id"])
    relacion2 = _scalar(db_session, "INSERT INTO relacion_generadora (tipo_origen, id_origen, estado_relacion_generadora) VALUES ('venta', :venta, 'ACTIVA') RETURNING id_relacion_generadora", venta=plan2["venta"])
    generacion2 = _scalar(db_session, """
        INSERT INTO generacion_cronograma_financiero (id_relacion_generadora, id_plan_pago_venta, tipo_generacion, clave_generacion, estado_generacion)
        VALUES (:relacion, :plan, 'PLAN_PAGO_VENTA_V2', :clave, 'GENERADA') RETURNING id_generacion_cronograma_financiero
    """, relacion=relacion2, plan=plan2["plan"], clave=f"GCF-PREP-{plan2['plan']}")
    obligacion2 = _scalar(db_session, """
        INSERT INTO obligacion_financiera (id_relacion_generadora, fecha_emision, fecha_vencimiento, importe_total, saldo_pendiente, moneda, estado_obligacion, es_proyectada, id_generacion_cronograma_financiero, id_plan_pago_venta_bloque, numero_obligacion, tipo_item_cronograma, clave_funcional_origen)
        VALUES (:relacion, DATE '2026-06-01', DATE '2026-06-30', 700, 700, 'ARS', 'PROYECTADA', true, :generacion, :bloque, 1, 'CUOTA', :clave) RETURNING id_obligacion_financiera
    """, relacion=relacion2, generacion=generacion2, bloque=plan2["bloque"], clave=f"OBL-PREP-{plan2['bloque']}")
    _insert_composicion(db_session, obligacion2, ctx1["capital"], 700)
    _insert_composicion(db_session, obligacion2, ctx1["ajuste"], 100)
    _insert_ofi(db_session, obligacion2, config2, ctx1["indice"])
    _hacer_vencidas(db_session, ctx1["obligacion"], ctx1["otra_obligacion"])
    before = _snapshot_deuda(db_session, ctx1["obligacion"])

    resp = client.post(URL.format(ctx1["indice"]["aplicado"]), headers=HEADERS, json={"motivo": "auto"})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["fecha_corte"] == "2026-06-30"
    assert data["periodo_aplicado"] == "2026-06-01"
    assert data["cantidad_corridas_creadas"] == 2
    assert data["cantidad_corridas_existentes"] == 0
    ids = [r["id_corrida_indexacion_financiera"] for r in data["resultados"]]
    assert len(ids) == len(set(ids)) == 2
    rows = db_session.execute(text("SELECT id_corrida_indexacion_financiera, id_plan_pago_venta_bloque, origen_corrida, estado_corrida, fecha_corte FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera = ANY(:ids)"), {"ids": ids}).mappings().all()
    assert {r["origen_corrida"] for r in rows} == {"PUBLICACION_INDICE"}
    assert {r["estado_corrida"] for r in rows} == {"PREVISUALIZADA"}
    assert {str(r["fecha_corte"]) for r in rows} == {"2026-06-30"}
    for row in rows:
        detalles = db_session.execute(text("""
            SELECT DISTINCT o.id_plan_pago_venta_bloque
            FROM corrida_indexacion_financiera_detalle d
            JOIN obligacion_financiera o ON o.id_obligacion_financiera=d.id_obligacion_financiera
            WHERE d.id_corrida_indexacion_financiera=:id
        """), {"id": row["id_corrida_indexacion_financiera"]}).scalars().all()
        assert detalles == [row["id_plan_pago_venta_bloque"]]
    assert _snapshot_deuda(db_session, ctx1["obligacion"]) == before

    replay = client.post(URL.format(ctx1["indice"]["aplicado"]), headers={**HEADERS, "X-Op-Id": "550e8400-e29b-41d4-a716-446655440099"}, json={})
    assert replay.status_code == 200
    assert replay.json()["data"]["cantidad_corridas_creadas"] == 0
    assert replay.json()["data"]["cantidad_corridas_existentes"] == 2
    assert _scalar(db_session, "SELECT COUNT(*) FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera = ANY(:ids)", ids=ids) == 3


def test_api_rechaza_fecha_corte_headers_y_valores_invalidos(client, db_session):
    ctx = _create_context(db_session)
    assert client.post(URL.format(ctx["indice"]["aplicado"]), json={}).status_code == 400
    assert client.post(URL.format(999999), headers=HEADERS, json={}).status_code == 404
    borrador = _scalar(db_session, """
        INSERT INTO indice_financiero_valor (id_indice_financiero, fecha_valor, valor_indice, estado_valor_indice)
        VALUES (:i, DATE '2026-07-01', 130, 'BORRADOR') RETURNING id_indice_financiero_valor
    """, i=ctx["indice"]["id"])
    assert client.post(URL.format(borrador), headers=HEADERS, json={}).status_code == 404
    resp = client.post(URL.format(ctx["indice"]["aplicado"]), headers=HEADERS, json={"fecha_corte": "2026-07-31"})
    assert resp.status_code == 422


def test_service_sin_obligaciones_otro_indice_aplicada_y_recuperacion_concurrente(db_session):
    ctx = _create_context(db_session)
    # Obligaciones posteriores a fin de mes => el preview formal devuelve SIN_OBLIGACIONES_ANALIZABLES.
    result = _preparar_service(db_session).execute(PrepararCorridasIndexacionCuotasV2Command(ctx["indice"]["aplicado"]), _core())
    assert result.success
    assert result.data["cantidad_sin_obligaciones"] == 1
    assert result.data["cantidad_corridas_creadas"] == 0
    assert _scalar(db_session, "SELECT COUNT(*) FROM corrida_indexacion_financiera WHERE origen_corrida='PUBLICACION_INDICE'") == 0

    _hacer_vencidas(db_session, ctx["obligacion"], ctx["otra_obligacion"])
    created = _preparar_service(db_session).execute(PrepararCorridasIndexacionCuotasV2Command(ctx["indice"]["aplicado"]), _core("550e8400-e29b-41d4-a716-446655440010"))
    corrida = created.data["resultados"][0]["id_corrida_indexacion_financiera"]
    db_session.execute(text("UPDATE corrida_indexacion_financiera SET estado_corrida='APLICADA', fecha_aplicacion=CURRENT_TIMESTAMP WHERE id_corrida_indexacion_financiera=:id"), {"id": corrida})
    db_session.flush()
    again = _preparar_service(db_session).execute(PrepararCorridasIndexacionCuotasV2Command(ctx["indice"]["aplicado"]), _core("550e8400-e29b-41d4-a716-446655440011"))
    assert again.data["cantidad_corridas_existentes"] == 1
    assert _scalar(db_session, "SELECT COUNT(*) FROM corrida_indexacion_financiera WHERE id_plan_pago_venta_bloque_indexacion=:c AND origen_corrida='PUBLICACION_INDICE'", c=ctx["config"]) == 1
    db_session.commit()

    otro = _preparar_service(db_session).execute(PrepararCorridasIndexacionCuotasV2Command(ctx["otro_indice"]["aplicado"]), _core("550e8400-e29b-41d4-a716-446655440012"))
    assert otro.data["cantidad_configuraciones_analizadas"] == 1
    assert otro.data["resultados"][0]["id_plan_pago_venta_bloque_indexacion"] == ctx["config_otro_indice"]

    class RaceRepo(PrepararCorridasIndexacionCuotasV2SqlAlchemyRepository):
        def __init__(self, db):
            super().__init__(db)
            self.first = True
        def get_corrida_existente(self, **kwargs):
            if self.first:
                self.first = False
                return None
            return super().get_corrida_existente(**kwargs)

    race_repo = RaceRepo(db_session)
    race = PrepararCorridasIndexacionCuotasV2Service(race_repo, PreviewIndexacionCuotasV2Service(PreviewIndexacionCuotasV2SqlAlchemyRepository(db_session))).execute(PrepararCorridasIndexacionCuotasV2Command(ctx["indice"]["aplicado"]), _core("550e8400-e29b-41d4-a716-446655440013"))
    assert race.success
    assert race.data["cantidad_corridas_existentes"] == 1
    assert db_session.execute(text("SELECT 1")).scalar() == 1
