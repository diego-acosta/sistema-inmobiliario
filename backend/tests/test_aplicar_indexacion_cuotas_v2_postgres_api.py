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


def _persist_preview(db_session, ctx):
    result = PreviewIndexacionCuotasV2Service(PreviewIndexacionCuotasV2SqlAlchemyRepository(db_session)).execute(
        _cmd(ctx, persistir=True, motivo="aplicar"), PREVIEW_CORE
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
