from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

HEADERS = {"X-Op-Id": "550e8400-e29b-41d4-a716-446655440255", "X-Usuario-Id": "1", "X-Sucursal-Id": "1", "X-Instalacion-Id": "1"}


def _apply_patch(db_session):
    db_session.execute(text(Path("backend/database/patch_caja_operativa_base_20260704.sql").read_text()))
    db_session.execute(text(Path("backend/database/patch_apertura_cierre_caja_operativa_20260706.sql").read_text()))
    db_session.execute(text(Path("backend/database/patch_movimientos_caja_operativa_20260710.sql").read_text()))


def _crear_caja_y_apertura(client):
    caja = client.post("/api/v1/operativo/cajas", json={"id_sucursal": 1, "id_instalacion": 1, "codigo_caja": f"CJ-MOV-{uuid4().hex[:8]}", "nombre_caja": "Caja Mov", "tipo_caja": "GENERAL", "moneda_base": "ARS", "estado_caja": "ACTIVA"}, headers={**HEADERS, "X-Op-Id": str(uuid4())})
    assert caja.status_code == 201, caja.text
    apertura = client.post(f"/api/v1/operativo/cajas/{caja.json()['data']['id_caja']}/aperturas", json={"id_sucursal": 1, "id_instalacion": 1, "fecha_hora_apertura": "2026-07-10T09:00:00", "saldo_inicial": 100, "moneda": "ARS"}, headers={**HEADERS, "X-Op-Id": str(uuid4())})
    assert apertura.status_code == 201, apertura.text
    return caja.json()["data"], apertura.json()["data"]


def _payload(**overrides):
    data = {"fecha_hora_movimiento": "2026-07-10T10:00:00", "tipo_movimiento": "INGRESO", "concepto_movimiento": "INGRESO_MANUAL", "monto": 50, "moneda": "ARS", "sentido": "ENTRADA", "descripcion": "Ingreso manual", "observaciones": "ok"}
    data.update(overrides)
    return data


def test_registrar_movimiento_ok_metadata_outbox_replay_y_detalle(client, db_session):
    _apply_patch(db_session)
    _, apertura = _crear_caja_y_apertura(client)
    headers = {**HEADERS, "X-Op-Id": str(uuid4())}
    url = f"/api/v1/operativo/cajas/aperturas/{apertura['id_apertura_caja']}/movimientos"

    first = client.post(url, json=_payload(), headers=headers)
    second = client.post(url, json=_payload(), headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    data = first.json()["data"]
    assert data["id_movimiento_caja"] == second.json()["data"]["id_movimiento_caja"]
    assert data["version_registro"] == 1
    assert data["id_usuario_movimiento"] == 1
    assert data["op_id_alta"] == headers["X-Op-Id"]
    assert data["id_caja"] == apertura["id_caja"]
    assert db_session.execute(text("SELECT COUNT(*) FROM caja_operativa_movimiento")).scalar() == 1
    assert db_session.execute(text("SELECT COUNT(*) FROM outbox_event WHERE event_type='caja_operativa_movimiento_registrado'")).scalar() == 1
    detail = client.get(f"/api/v1/operativo/cajas/movimientos/{data['id_movimiento_caja']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["id_movimiento_caja"] == data["id_movimiento_caja"]


def test_replay_incompatible_y_validaciones_negocio(client, db_session):
    _apply_patch(db_session)
    _, apertura = _crear_caja_y_apertura(client)
    headers = {**HEADERS, "X-Op-Id": str(uuid4())}
    url = f"/api/v1/operativo/cajas/aperturas/{apertura['id_apertura_caja']}/movimientos"
    assert client.post(url, json=_payload(), headers=headers).status_code == 201
    incompatible = client.post(url, json=_payload(monto=60), headers=headers)
    assert incompatible.status_code == 409
    assert incompatible.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    assert client.post(url, json=_payload(moneda="USD"), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 400
    assert client.post(url, json=_payload(fecha_hora_movimiento="2026-07-10T08:59:00"), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 400
    assert client.post(url, json=_payload(tipo_movimiento="INGRESO", sentido="SALIDA"), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 400
    assert client.post("/api/v1/operativo/cajas/aperturas/999999/movimientos", json=_payload(), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 404
    assert client.post(url, json=_payload(), headers={}).status_code == 400


def test_no_permite_apertura_cerrada_y_validaciones_422(client, db_session):
    _apply_patch(db_session)
    _, apertura = _crear_caja_y_apertura(client)
    close = client.patch(f"/api/v1/operativo/cajas/aperturas/{apertura['id_apertura_caja']}/cerrar", json={"fecha_hora_cierre": "2026-07-10T11:00:00", "saldo_declarado_cierre": 100}, headers={**HEADERS, "X-Op-Id": str(uuid4()), "If-Match-Version": "1"})
    assert close.status_code == 200
    url = f"/api/v1/operativo/cajas/aperturas/{apertura['id_apertura_caja']}/movimientos"
    assert client.post(url, json=_payload(), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 409
    assert client.post(url, json=_payload(monto=0), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 422
    assert client.post(url, json=_payload(moneda="EUR"), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 422
    assert client.post(url, json=_payload(tipo_movimiento="OTRO"), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 422
    assert client.post(url, json=_payload(sentido="OTRO"), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 422


def test_listados_filtros_detalle_inexistente_e_indices(client, db_session):
    _apply_patch(db_session)
    caja, apertura = _crear_caja_y_apertura(client)
    url = f"/api/v1/operativo/cajas/aperturas/{apertura['id_apertura_caja']}/movimientos"
    created = client.post(url, json=_payload(), headers={**HEADERS, "X-Op-Id": str(uuid4())})
    assert created.status_code == 201
    assert len(client.get(url).json()["data"]) == 1
    general = client.get("/api/v1/operativo/cajas/movimientos", params={"id_sucursal": 1, "id_instalacion": 1, "id_caja": caja["id_caja"], "id_apertura_caja": apertura["id_apertura_caja"]})
    assert general.status_code == 200
    assert len(general.json()["data"]) == 1
    assert client.get("/api/v1/operativo/cajas/movimientos/999999").status_code == 404
    indexes = set(db_session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'caja_operativa_movimiento'
    """)).scalars().all())
    assert "ux_caja_operativa_movimiento_uid_global" in indexes
    assert "ux_caja_operativa_movimiento_op_id_alta" in indexes
    assert "ix_caja_operativa_movimiento_apertura" in indexes
    assert "ix_caja_operativa_movimiento_caja" in indexes
