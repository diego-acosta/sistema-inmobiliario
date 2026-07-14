from uuid import UUID

from sqlalchemy import text

from app.api.core_ef_headers import CoreEFHeaders
from app.application.financiero.services.aplicar_indexacion_cuotas_v2_service import (
    AplicarIndexacionCuotasV2Command,
    AplicarIndexacionCuotasV2Service,
)
from app.application.financiero.services.preview_indexacion_cuotas_v2_service import PreviewIndexacionCuotasV2Service
from app.infrastructure.persistence.repositories.aplicar_indexacion_cuotas_v2_repository import AplicarIndexacionCuotasV2SqlAlchemyRepository
from app.infrastructure.persistence.repositories.preview_indexacion_cuotas_v2_repository import PreviewIndexacionCuotasV2SqlAlchemyRepository
from test_preview_indexacion_cuotas_v2_postgres_api import _cmd, _payload
from test_corridas_indexacion_cuotas_v2_sql import _create_context, _scalar

PREVIEW_CORE = CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655441000"), 1, 1, 1)
APPLY_CORE = CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655441001"), 1, 1, 1, 1)
APPLY_HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655441001",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
    "If-Match-Version": "1",
}


def _persist_preview(db_session, ctx, core=PREVIEW_CORE):
    result = PreviewIndexacionCuotasV2Service(PreviewIndexacionCuotasV2SqlAlchemyRepository(db_session)).execute(
        _cmd(ctx, persistir=True, motivo="aplicar"), core
    )
    assert result.success
    return result.data


def test_postgres_aplica_corrida_crea_trazabilidad_actualiza_obligacion_detalle_outbox_e_idempotencia(db_session):
    ctx = _create_context(db_session)
    preview = _persist_preview(db_session, ctx)
    corrida = preview["id_corrida_indexacion_financiera"]

    result = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session)).execute(
        AplicarIndexacionCuotasV2Command(corrida, preview["hash_corrida"]), APPLY_CORE
    )
    assert result.success, result.errors
    assert result.data["cantidad_aplicada"] == 2

    cab = db_session.execute(text("SELECT estado_corrida, cantidad_aplicada, fecha_aplicacion, version_registro, op_id_ultima_modificacion::text op FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id"), {"id": corrida}).mappings().one()
    assert cab["estado_corrida"] == "APLICADA"
    assert cab["cantidad_aplicada"] == 2
    assert cab["fecha_aplicacion"] is not None
    assert cab["version_registro"] > 1
    assert cab["op"] == str(APPLY_CORE.x_op_id)

    obl = db_session.execute(text("SELECT importe_total, saldo_pendiente, version_registro, op_id_ultima_modificacion::text op FROM obligacion_financiera WHERE id_obligacion_financiera=:id"), {"id": ctx["obligacion"]}).mappings().one()
    assert obl["importe_total"] == 1260
    assert obl["saldo_pendiente"] == 1260
    assert obl["version_registro"] >= 2
    assert obl["op"] == str(APPLY_CORE.x_op_id)

    assert _scalar(db_session, "SELECT COUNT(*) FROM obligacion_financiera_indexacion WHERE deleted_at IS NULL AND id_obligacion_financiera=:id", id=ctx["obligacion"]) == 1
    assert _scalar(db_session, "SELECT COUNT(*) FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera=:id AND version_resultante IS NOT NULL", id=corrida) == 2
    outbox = db_session.execute(text("SELECT event_type, aggregate_type, aggregate_id, payload FROM outbox_event WHERE aggregate_id=:id"), {"id": corrida}).mappings().one()
    assert outbox["event_type"] == "financiero.indexacion_cuotas_v2.corrida_aplicada"
    assert outbox["aggregate_type"] == "corrida_indexacion_financiera"
    assert outbox["payload"]["op_id"] == str(APPLY_CORE.x_op_id)

    again = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session)).execute(
        AplicarIndexacionCuotasV2Command(corrida, preview["hash_corrida"]), APPLY_CORE
    )
    assert again.success
    assert again.data["idempotente"] is True


def test_postgres_conflicto_version_persiste_fallida_y_rollback(db_session):
    ctx = _create_context(db_session)
    preview = _persist_preview(db_session, ctx)
    corrida = preview["id_corrida_indexacion_financiera"]
    db_session.execute(text("UPDATE obligacion_financiera SET version_registro=version_registro+1 WHERE id_obligacion_financiera=:id"), {"id": ctx["obligacion"]})
    db_session.commit()

    result = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session)).execute(
        AplicarIndexacionCuotasV2Command(corrida, preview["hash_corrida"]), APPLY_CORE
    )
    assert not result.success
    assert result.errors == ["VERSION_OBLIGACION_INCOMPATIBLE"]
    cab = db_session.execute(text("SELECT estado_corrida, codigo_error FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id"), {"id": corrida}).mappings().one()
    assert cab["estado_corrida"] == "FALLIDA"
    assert cab["codigo_error"] == "VERSION_OBLIGACION_INCOMPATIBLE"
    assert _scalar(db_session, "SELECT COUNT(*) FROM outbox_event WHERE aggregate_id=:id", id=corrida) == 0


def test_api_aplicar_headers_exito_conflictos(client, db_session):
    ctx = _create_context(db_session)
    preview = _persist_preview(db_session, ctx)
    corrida = preview["id_corrida_indexacion_financiera"]
    response = client.post(f"/api/v1/financiero/indexacion-cuotas-v2/corridas/{corrida}/aplicar", json={"hash_corrida": preview["hash_corrida"]})
    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"

    response = client.post(f"/api/v1/financiero/indexacion-cuotas-v2/corridas/{corrida}/aplicar", headers=APPLY_HEADERS, json={"hash_corrida": "bad"})
    assert response.status_code == 409
    assert response.json()["error_code"] == "HASH_CORRIDA_INVALIDO"

    response = client.post(f"/api/v1/financiero/indexacion-cuotas-v2/corridas/{corrida}/aplicar", headers=APPLY_HEADERS, json={"hash_corrida": preview["hash_corrida"]})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["estado_corrida"] == "APLICADA"


def _recompute_hash_from_db(db_session, corrida: int) -> str:
    repo = AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session)
    service = AplicarIndexacionCuotasV2Service(repo)
    cab = repo.get_corrida_for_update(corrida)
    detalles = repo.list_detalles_for_update(corrida)
    assert cab is not None
    return service._recomputar_hash(cab, detalles)


def test_postgres_hash_de_preview_permanece_estable_despues_de_aplicar(db_session):
    ctx = _create_context(db_session)
    preview = _persist_preview(db_session, ctx)
    corrida = preview["id_corrida_indexacion_financiera"]
    hash_original = preview["hash_corrida"]
    snapshots = {
        row["id_corrida_indexacion_financiera_detalle"]: (row["snapshot_antes"], row["snapshot_despues"])
        for row in db_session.execute(text("""
            SELECT id_corrida_indexacion_financiera_detalle, snapshot_antes, snapshot_despues
            FROM corrida_indexacion_financiera_detalle
            WHERE id_corrida_indexacion_financiera=:id
        """), {"id": corrida}).mappings()
    }

    service = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session))
    result = service.execute(AplicarIndexacionCuotasV2Command(corrida, hash_original), APPLY_CORE)
    assert result.success, result.errors

    hash_recomputado = _recompute_hash_from_db(db_session, corrida)
    assert hash_recomputado == hash_original

    detalles = db_session.execute(text("""
        SELECT id_corrida_indexacion_financiera_detalle, id_composicion_ajuste_indexacion,
               id_obligacion_financiera_indexacion, version_resultante, snapshot_antes, snapshot_despues
        FROM corrida_indexacion_financiera_detalle
        WHERE id_corrida_indexacion_financiera=:id
    """), {"id": corrida}).mappings().all()
    assert detalles
    for detalle in detalles:
        assert detalle["id_composicion_ajuste_indexacion"] is not None
        assert detalle["id_obligacion_financiera_indexacion"] is not None
        assert detalle["version_resultante"] is not None
        before, after = snapshots[detalle["id_corrida_indexacion_financiera_detalle"]]
        assert detalle["snapshot_antes"] == before
        assert detalle["snapshot_despues"] == after
        assert "aplicada" not in detalle["snapshot_despues"]

    outbox_count = _scalar(db_session, "SELECT COUNT(*) FROM outbox_event WHERE aggregate_id=:id", id=corrida)
    replay = service.execute(AplicarIndexacionCuotasV2Command(corrida, hash_original), APPLY_CORE)
    assert replay.success
    assert replay.data["idempotente"] is True
    assert _scalar(db_session, "SELECT COUNT(*) FROM outbox_event WHERE aggregate_id=:id", id=corrida) == outbox_count
    assert _recompute_hash_from_db(db_session, corrida) == hash_original


def test_postgres_replay_devuelve_cantidad_real_y_no_duplica(db_session):
    ctx = _create_context(db_session)
    preview = _persist_preview(db_session, ctx)
    corrida = preview["id_corrida_indexacion_financiera"]
    service = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session))
    first = service.execute(AplicarIndexacionCuotasV2Command(corrida, preview["hash_corrida"]), APPLY_CORE)
    assert first.success
    versions = dict(db_session.execute(text("SELECT id_obligacion_financiera, version_registro FROM obligacion_financiera WHERE id_obligacion_financiera IN (:a,:b)"), {"a": ctx["obligacion"], "b": ctx["otra_obligacion"]}).all())
    outbox_count = _scalar(db_session, "SELECT COUNT(*) FROM outbox_event WHERE aggregate_id=:id", id=corrida)
    ajuste_count = _scalar(db_session, "SELECT COUNT(*) FROM composicion_obligacion co JOIN concepto_financiero cf ON cf.id_concepto_financiero=co.id_concepto_financiero WHERE co.id_obligacion_financiera=:id AND cf.codigo_concepto_financiero='AJUSTE_INDEXACION' AND co.deleted_at IS NULL", id=ctx["obligacion"])

    replay = service.execute(AplicarIndexacionCuotasV2Command(corrida, preview["hash_corrida"]), APPLY_CORE)
    assert replay.success
    assert replay.data["idempotente"] is True
    assert replay.data["cantidad_aplicada"] == 2
    assert _scalar(db_session, "SELECT COUNT(*) FROM outbox_event WHERE aggregate_id=:id", id=corrida) == outbox_count
    assert _scalar(db_session, "SELECT COUNT(*) FROM composicion_obligacion co JOIN concepto_financiero cf ON cf.id_concepto_financiero=co.id_concepto_financiero WHERE co.id_obligacion_financiera=:id AND cf.codigo_concepto_financiero='AJUSTE_INDEXACION' AND co.deleted_at IS NULL", id=ctx["obligacion"]) == ajuste_count
    assert dict(db_session.execute(text("SELECT id_obligacion_financiera, version_registro FROM obligacion_financiera WHERE id_obligacion_financiera IN (:a,:b)"), {"a": ctx["obligacion"], "b": ctx["otra_obligacion"]}).all()) == versions

    bad = service.execute(AplicarIndexacionCuotasV2Command(corrida, "0" * 64), APPLY_CORE)
    assert not bad.success
    assert bad.errors == ["IDEMPOTENCIA_PAYLOAD_INCOMPATIBLE"]


def test_postgres_hash_persistido_inconsistente_no_marca_fallida_ni_muta(db_session):
    ctx = _create_context(db_session)
    preview = _persist_preview(db_session, ctx)
    corrida = preview["id_corrida_indexacion_financiera"]
    db_session.execute(text("UPDATE corrida_indexacion_financiera_detalle SET importe_nuevo = importe_nuevo + 1 WHERE id_corrida_indexacion_financiera_detalle = (SELECT id_corrida_indexacion_financiera_detalle FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera=:id LIMIT 1)"), {"id": corrida})
    db_session.commit()
    result = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session)).execute(
        AplicarIndexacionCuotasV2Command(corrida, preview["hash_corrida"]), APPLY_CORE
    )
    assert not result.success
    assert result.errors == ["CORRIDA_HASH_PERSISTIDO_INCONSISTENTE"]
    assert _scalar(db_session, "SELECT COUNT(*) FROM outbox_event WHERE aggregate_id=:id", id=corrida) == 0
    assert _scalar(db_session, "SELECT estado_corrida FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id", id=corrida) == "PREVISUALIZADA"


def test_postgres_formula_inconsistente_error_controlado_sin_fallida(db_session):
    ctx = _create_context(db_session)
    preview = _persist_preview(db_session, ctx)
    corrida = preview["id_corrida_indexacion_financiera"]
    db_session.execute(text("UPDATE corrida_indexacion_financiera_detalle SET diferencia_neta = diferencia_neta + 1 WHERE id_corrida_indexacion_financiera=:id"), {"id": corrida})
    new_hash = _recompute_hash_from_db(db_session, corrida)
    db_session.execute(text("UPDATE corrida_indexacion_financiera SET hash_corrida=:h WHERE id_corrida_indexacion_financiera=:id"), {"h": new_hash, "id": corrida})
    db_session.commit()
    version_corrida = _scalar(db_session, "SELECT version_registro FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id", id=corrida)
    result = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session)).execute(
        AplicarIndexacionCuotasV2Command(corrida, new_hash), CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655441021"), 1, 1, 1, version_corrida)
    )
    assert not result.success
    assert result.errors == ["DETALLE_CORRIDA_INCONSISTENTE"]
    assert _scalar(db_session, "SELECT estado_corrida FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id", id=corrida) == "PREVISUALIZADA"


def test_postgres_conflicto_ajuste_y_trazabilidad_marcan_fallida(db_session):
    ctx = _create_context(db_session)
    preview = _persist_preview(db_session, ctx)
    corrida = preview["id_corrida_indexacion_financiera"]
    db_session.execute(text("UPDATE composicion_obligacion SET importe_componente=importe_componente+1, saldo_componente=saldo_componente+1 WHERE id_composicion_obligacion=:id"), {"id": ctx["comp_ajuste"]})
    version_obl = _scalar(db_session, "SELECT version_registro FROM obligacion_financiera WHERE id_obligacion_financiera=:id", id=ctx["obligacion"])
    db_session.execute(text("UPDATE corrida_indexacion_financiera_detalle SET version_esperada=:v WHERE id_corrida_indexacion_financiera=:id AND id_obligacion_financiera=:obl"), {"v": version_obl, "id": corrida, "obl": ctx["obligacion"]})
    new_hash_ajuste = _recompute_hash_from_db(db_session, corrida)
    db_session.execute(text("UPDATE corrida_indexacion_financiera SET hash_corrida=:h WHERE id_corrida_indexacion_financiera=:id"), {"h": new_hash_ajuste, "id": corrida})
    db_session.commit()
    version_corrida = _scalar(db_session, "SELECT version_registro FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id", id=corrida)
    result = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session)).execute(
        AplicarIndexacionCuotasV2Command(corrida, new_hash_ajuste), CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655441020"), 1, 1, 1, version_corrida)
    )
    assert not result.success
    assert result.errors == ["AJUSTE_INDEXACION_INCOMPATIBLE"]
    assert _scalar(db_session, "SELECT estado_corrida FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id", id=corrida) == "FALLIDA"



def test_api_hash_obligatorio_replay_y_body_distinto(client, db_session):
    ctx = _create_context(db_session)
    preview = _persist_preview(db_session, ctx)
    corrida = preview["id_corrida_indexacion_financiera"]
    no_body_hash = client.post(f"/api/v1/financiero/indexacion-cuotas-v2/corridas/{corrida}/aplicar", headers=APPLY_HEADERS, json={})
    assert no_body_hash.status_code == 422

    ok = client.post(f"/api/v1/financiero/indexacion-cuotas-v2/corridas/{corrida}/aplicar", headers=APPLY_HEADERS, json={"hash_corrida": preview["hash_corrida"]})
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["cantidad_aplicada"] == 2
    replay = client.post(f"/api/v1/financiero/indexacion-cuotas-v2/corridas/{corrida}/aplicar", headers=APPLY_HEADERS, json={"hash_corrida": preview["hash_corrida"]})
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["idempotente"] is True
    assert replay.json()["data"]["cantidad_aplicada"] == 2
    changed = client.post(f"/api/v1/financiero/indexacion-cuotas-v2/corridas/{corrida}/aplicar", headers=APPLY_HEADERS, json={"hash_corrida": "0" * 64})
    assert changed.status_code == 409
    assert changed.json()["error_code"] == "IDEMPOTENCIA_PAYLOAD_INCOMPATIBLE"


def test_postgres_trazabilidad_concurrente_marca_fallida(db_session):
    ctx2 = _create_context(db_session)
    preview2 = _persist_preview(db_session, ctx2, CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655441010"), 1, 1, 1))
    corrida2 = preview2["id_corrida_indexacion_financiera"]
    db_session.execute(text("UPDATE obligacion_financiera_indexacion SET valor_aplicado_indice=valor_aplicado_indice+1 WHERE id_obligacion_financiera_indexacion=:id"), {"id": ctx2["ofi"]})
    db_session.commit()
    result2 = AplicarIndexacionCuotasV2Service(AplicarIndexacionCuotasV2SqlAlchemyRepository(db_session)).execute(
        AplicarIndexacionCuotasV2Command(corrida2, preview2["hash_corrida"]), CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655441011"), 1, 1, 1, 1)
    )
    assert not result2.success
    assert result2.errors == ["TRAZABILIDAD_INDEXACION_INCOMPATIBLE"]
    assert _scalar(db_session, "SELECT estado_corrida FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera=:id", id=corrida2) == "FALLIDA"
