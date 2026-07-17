from uuid import uuid4

from sqlalchemy import text


def _headers(op_id: str | None = None, version: int | None = None) -> dict[str, str]:
    headers = {
        "X-Op-Id": op_id or str(uuid4()),
        "X-Usuario-Id": "1",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
    }
    if version is not None:
        headers["If-Match-Version"] = str(version)
    return headers


def _payload(suffix: str, descripcion: str | None = "Descripción") -> dict:
    return {
        "codigo_catalogo_maestro": f"ADM368_{suffix}_{uuid4().hex[:8]}",
        "nombre_catalogo_maestro": f"Catálogo {suffix}",
        "descripcion": descripcion,
    }


def _events(db_session, event_type: str, aggregate_id: int) -> list:
    return db_session.execute(text("""
        SELECT event_type, aggregate_type, aggregate_id, payload
        FROM outbox_event
        WHERE event_type = :event_type AND aggregate_id = :aggregate_id
        ORDER BY id
    """), {"event_type": event_type, "aggregate_id": aggregate_id}).mappings().all()


def _create(client, suffix="CREATE", *, op_id=None, payload=None):
    return client.post("/api/v1/administrativo/catalogos", json=payload or _payload(suffix), headers=_headers(op_id))


def test_alta_catalogo_persiste_core_ef_y_outbox(client, db_session):
    response = _create(client, "ALTA", payload=_payload("ALTA", None))

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["version_registro"] == 1
    assert data["uid_global"]
    assert data["descripcion"] is None
    assert data["deleted_at"] is None
    row = db_session.execute(text("""
        SELECT id_instalacion_origen, id_instalacion_ultima_modificacion,
               op_id_alta, op_id_ultima_modificacion
        FROM catalogo_maestro WHERE id_catalogo_maestro = :id
    """), {"id": data["id_catalogo_maestro"]}).mappings().one()
    assert row["id_instalacion_origen"] == row["id_instalacion_ultima_modificacion"] == 1
    assert row["op_id_alta"] == row["op_id_ultima_modificacion"]
    assert len(_events(db_session, "catalogo_maestro_creado", data["id_catalogo_maestro"])) == 1


def test_alta_idempotente_y_payload_incompatible(client, db_session):
    payload = _payload("IDEMP")
    op_id = str(uuid4())
    first = _create(client, op_id=op_id, payload=payload)
    replay = _create(client, op_id=op_id, payload=payload)
    incompatible = _create(client, op_id=op_id, payload={**payload, "nombre_catalogo_maestro": "Otro"})

    assert first.status_code == replay.status_code == 201
    assert replay.json()["data"] == first.json()["data"]
    assert incompatible.status_code == 409
    assert incompatible.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    data = first.json()["data"]
    assert db_session.execute(text("SELECT COUNT(*) FROM catalogo_maestro WHERE op_id_alta = CAST(:op AS uuid)"), {"op": op_id}).scalar_one() == 1
    assert len(_events(db_session, "catalogo_maestro_creado", data["id_catalogo_maestro"])) == 1


def test_alta_rechaza_headers_y_codigo_duplicado(client):
    missing = client.post("/api/v1/administrativo/catalogos", json=_payload("MISSING"))
    assert missing.status_code == 400
    assert missing.json()["details"]["header"] == "X-Op-Id"
    invalid = client.post("/api/v1/administrativo/catalogos", json=_payload("INVALID"), headers={**_headers(), "X-Instalacion-Id": "x"})
    assert invalid.status_code == 400
    payload = _payload("DUP")
    assert _create(client, payload=payload).status_code == 201
    duplicate = _create(client, payload=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "TECHNICAL_INCONSISTENCY"


def test_update_versionado_idempotencia_y_metadata(client, db_session):
    created = _create(client, "UPDATE").json()["data"]
    original = db_session.execute(text("SELECT uid_global, created_at, id_instalacion_origen, op_id_alta FROM catalogo_maestro WHERE id_catalogo_maestro = :id"), {"id": created["id_catalogo_maestro"]}).mappings().one()
    payload = _payload("UPDATED")
    op_id = str(uuid4())
    first = client.put(f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}", json=payload, headers=_headers(op_id, created["version_registro"]))
    replay = client.put(f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}", json=payload, headers=_headers(op_id, created["version_registro"]))

    assert first.status_code == replay.status_code == 200
    updated = first.json()["data"]
    assert replay.json()["data"] == updated
    assert updated["version_registro"] == created["version_registro"] + 1
    persisted = db_session.execute(text("SELECT uid_global, created_at, id_instalacion_origen, op_id_alta, id_instalacion_ultima_modificacion FROM catalogo_maestro WHERE id_catalogo_maestro = :id"), {"id": created["id_catalogo_maestro"]}).mappings().one()
    assert {key: persisted[key] for key in original} == dict(original)
    assert persisted["id_instalacion_ultima_modificacion"] == 1
    assert len(_events(db_session, "catalogo_maestro_modificado", created["id_catalogo_maestro"])) == 1


def test_update_conflictos_y_headers(client):
    created = _create(client, "UPDATE-CONFLICT").json()["data"]
    payload = _payload("UPDATE-CONFLICT-NEW")
    missing = client.put(f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}", json=payload, headers=_headers())
    stale = client.put(f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}", json=payload, headers=_headers(version=99))
    assert missing.status_code == 400
    assert missing.json()["details"]["header"] == "If-Match-Version"
    assert stale.status_code == 409
    assert stale.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_es_replay_unico_y_oculta_catalogo(client, db_session):
    created = _create(client, "BAJA").json()["data"]
    op_id = str(uuid4())
    first = client.patch(f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}/baja", headers=_headers(op_id, created["version_registro"]))
    replay = client.patch(f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}/baja", headers=_headers(op_id, created["version_registro"]))

    assert first.status_code == replay.status_code == 200
    baja = first.json()["data"]
    assert baja["deleted_at"] is not None
    assert baja["version_registro"] == created["version_registro"] + 1
    assert replay.json()["data"] == baja
    assert len(_events(db_session, "catalogo_maestro_desactivado", created["id_catalogo_maestro"])) == 1
    assert client.get(f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}").status_code == 404
    assert client.get("/api/v1/administrativo/catalogos", params={"q": created["codigo_catalogo_maestro"]}).json()["data"]["items"] == []
    assert db_session.execute(text("SELECT COUNT(*) FROM catalogo_maestro WHERE id_catalogo_maestro = :id"), {"id": created["id_catalogo_maestro"]}).scalar_one() == 1


def test_baja_repetida_con_otro_op_y_outbox_fallido_revierte(client, db_session, monkeypatch):
    created = _create(client, "BAJA-CONFLICT").json()["data"]
    first = client.patch(f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}/baja", headers=_headers(version=created["version_registro"]))
    repeated = client.patch(f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}/baja", headers=_headers(version=first.json()["data"]["version_registro"]))
    assert repeated.status_code == 404

    other = _create(client, "OUTBOX-FAIL").json()["data"]
    from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository
    monkeypatch.setattr(OutboxRepository, "add_event", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("outbox falló")))
    failed = client.patch(f"/api/v1/administrativo/catalogos/{other['id_catalogo_maestro']}/baja", headers=_headers(version=other["version_registro"]))
    assert failed.status_code == 500
    row = db_session.execute(text("SELECT deleted_at, version_registro FROM catalogo_maestro WHERE id_catalogo_maestro = :id"), {"id": other["id_catalogo_maestro"]}).mappings().one()
    assert row["deleted_at"] is None and row["version_registro"] == other["version_registro"]


def test_update_rechaza_codigo_duplicado_y_catalogo_dado_de_baja(client):
    first = _create(client, "UPDATE-DUP-A").json()["data"]
    second = _create(client, "UPDATE-DUP-B").json()["data"]
    duplicate = client.put(
        f"/api/v1/administrativo/catalogos/{second['id_catalogo_maestro']}",
        json={
            "codigo_catalogo_maestro": first["codigo_catalogo_maestro"],
            "nombre_catalogo_maestro": "Duplicado",
            "descripcion": None,
        },
        headers=_headers(version=second["version_registro"]),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "TECHNICAL_INCONSISTENCY"
    baja = client.patch(
        f"/api/v1/administrativo/catalogos/{first['id_catalogo_maestro']}/baja",
        headers=_headers(version=first["version_registro"]),
    )
    update_deleted = client.put(
        f"/api/v1/administrativo/catalogos/{first['id_catalogo_maestro']}",
        json=_payload("UPDATE-DELETED"),
        headers=_headers(version=baja.json()["data"]["version_registro"]),
    )
    assert update_deleted.status_code == 404


def test_falla_outbox_en_update_revierte_cambio(client, db_session, monkeypatch):
    created = _create(client, "UPDATE-OUTBOX-FAIL").json()["data"]
    original = db_session.execute(text("""
        SELECT codigo_catalogo_maestro, nombre_catalogo_maestro, descripcion, version_registro
        FROM catalogo_maestro WHERE id_catalogo_maestro = :id
    """), {"id": created["id_catalogo_maestro"]}).mappings().one()
    from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository
    monkeypatch.setattr(OutboxRepository, "add_event", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("outbox falló")))
    failed = client.put(
        f"/api/v1/administrativo/catalogos/{created['id_catalogo_maestro']}",
        json=_payload("UPDATE-OUTBOX-FAIL-NEW"),
        headers=_headers(version=created["version_registro"]),
    )
    assert failed.status_code == 500
    persisted = db_session.execute(text("""
        SELECT codigo_catalogo_maestro, nombre_catalogo_maestro, descripcion, version_registro
        FROM catalogo_maestro WHERE id_catalogo_maestro = :id
    """), {"id": created["id_catalogo_maestro"]}).mappings().one()
    assert dict(persisted) == dict(original)
