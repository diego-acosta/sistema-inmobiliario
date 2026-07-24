from uuid import uuid4

from sqlalchemy import text


def _headers(version=None, op_id=None):
    value = {
        "X-Op-Id": op_id or str(uuid4()),
        "X-Usuario-Id": "1",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
    }
    if version is not None:
        value["If-Match-Version"] = str(version)
    return value


def _catalogo(client):
    return client.post(
        "/api/v1/administrativo/catalogos",
        json={
            "codigo_catalogo_maestro": f"IT_{uuid4().hex[:10]}",
            "nombre_catalogo_maestro": "Items",
            "descripcion": None,
        },
        headers=_headers(),
    ).json()["data"]


def _item(client, catalogo, op_id=None):
    payload = {
        "codigo_item_catalogo": f"I_{uuid4().hex[:10]}",
        "nombre_item_catalogo": "Ítem",
        "descripcion": None,
    }
    response = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(op_id=op_id),
    )
    return response, payload


def test_item_write_crud_idempotencia_y_outbox(client, db_session):
    catalogo = _catalogo(client)
    op = str(uuid4())
    create, payload = _item(client, catalogo, op)
    assert create.status_code == 201
    item = create.json()["data"]
    assert item["estado_item_catalogo"] == "ACTIVO" and item["version_registro"] == 1
    replay = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(op_id=op),
    )
    assert replay.status_code == 201 and replay.json()["data"] == item
    updated_payload = {**payload, "nombre_item_catalogo": "Ítem editado"}
    updated = client.put(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}",  # noqa: E501
        json=updated_payload,
        headers=_headers(item["version_registro"]),
    )
    assert (
        updated.status_code == 200 and updated.json()["data"]["version_registro"] == 2
    )
    inactive = client.patch(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/estado",  # noqa: E501
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(2),
    )
    assert (
        inactive.status_code == 200
        and inactive.json()["data"]["estado_item_catalogo"] == "INACTIVO"
    )
    baja = client.patch(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/baja",  # noqa: E501
        headers=_headers(3),
    )
    assert baja.status_code == 200 and baja.json()["data"]["deleted_at"] is not None
    assert (
        client.get(
            f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items"
        ).json()["data"]["items"]
        == []
    )
    assert (
        db_session.execute(
            text(
                "SELECT count(*) FROM outbox_event WHERE aggregate_type='item_catalogo' AND aggregate_id=:id"  # noqa: E501
            ),
            {"id": item["id_item_catalogo"]},
        ).scalar_one()
        == 4
    )


def test_item_write_headers_duplicate_and_stale_version(client):
    catalogo = _catalogo(client)
    missing = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json={"codigo_item_catalogo": "A", "nombre_item_catalogo": "A"},
    )
    assert missing.status_code == 400
    first, payload = _item(client, catalogo)
    item = first.json()["data"]
    duplicate = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(),
    )
    assert (
        duplicate.status_code == 409
        and duplicate.json()["error_code"] == "DUPLICATE_CODE"
    )
    stale = client.put(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}",  # noqa: E501
        json=payload,
        headers=_headers(99),
    )
    assert (
        stale.status_code == 409 and stale.json()["error_code"] == "CONCURRENCY_ERROR"
    )


def test_estado_repetido_es_transicion_invalida_y_replay(client):
    catalogo = _catalogo(client)
    created, _ = _item(client, catalogo)
    item = created.json()["data"]
    op_id = str(uuid4())
    url = f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/estado"  # noqa: E501
    first = client.patch(
        url,
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(item["version_registro"], op_id),
    )
    replay = client.patch(
        url,
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(item["version_registro"], op_id),
    )
    repeated = client.patch(
        url,
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(first.json()["data"]["version_registro"]),
    )
    assert first.status_code == replay.status_code == 200
    assert replay.json()["data"] == first.json()["data"]
    assert repeated.status_code == 409
    assert repeated.json()["error_code"] == "INVALID_STATE_TRANSITION"


def test_baja_repetida_replay_y_otro_op_es_not_found(client, db_session):
    catalogo = _catalogo(client)
    created, _ = _item(client, catalogo)
    item = created.json()["data"]
    op_id = str(uuid4())
    url = f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/baja"  # noqa: E501
    first = client.patch(url, headers=_headers(item["version_registro"], op_id))
    replay = client.patch(url, headers=_headers(item["version_registro"], op_id))
    repeated = client.patch(
        url, headers=_headers(first.json()["data"]["version_registro"])
    )
    assert first.status_code == replay.status_code == 200
    assert replay.json()["data"] == first.json()["data"]
    assert repeated.status_code == 404
    assert (
        db_session.execute(
            text(
                "SELECT count(*) FROM outbox_event WHERE aggregate_id=:id AND event_type='item_catalogo_desactivado'"  # noqa: E501
            ),
            {"id": item["id_item_catalogo"]},
        ).scalar_one()
        == 1
    )


def test_error_tecnico_no_expone_detalle_interno(client, monkeypatch):
    catalogo = _catalogo(client)
    from app.infrastructure.persistence.repositories.item_catalogo_repository import (
        ItemCatalogoRepository,
    )

    secret = "SQL uq_item_catalogo driver-secret"
    monkeypatch.setattr(
        ItemCatalogoRepository,
        "create",
        lambda *args: (_ for _ in ()).throw(RuntimeError(secret)),
    )
    response = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json={"codigo_item_catalogo": "SECRETO", "nombre_item_catalogo": "Secreto"},
        headers=_headers(),
    )
    assert response.status_code == 500
    assert response.json() == {
        "ok": False,
        "error_code": "TECHNICAL_INCONSISTENCY",
        "error_message": "No se pudo procesar el ítem del catálogo.",
        "details": {},
    }
    assert secret not in response.text


def _events(db_session, item_id):
    return (
        db_session.execute(
            text(
                "SELECT event_type, aggregate_type, aggregate_id, payload FROM outbox_event WHERE aggregate_id=:id ORDER BY id"  # noqa: E501
            ),
            {"id": item_id},
        )
        .mappings()
        .all()
    )


def _row(db_session, item_id):
    return (
        db_session.execute(
            text("SELECT * FROM item_catalogo WHERE id_item_catalogo=:id"),
            {"id": item_id},
        )
        .mappings()
        .one_or_none()
    )


def test_alta_metadata_catalogos_y_conflictos_idempotentes(client, db_session):
    catalogo, otro = _catalogo(client), _catalogo(client)
    response, payload = _item(client, catalogo, str(uuid4()))
    item = response.json()["data"]
    row = _row(db_session, item["id_item_catalogo"])
    assert response.status_code == 201
    assert (
        row["uid_global"]
        and row["version_registro"] == 1
        and row["estado_item_catalogo"] == "ACTIVO"
    )
    assert (
        row["id_instalacion_origen"] == row["id_instalacion_ultima_modificacion"] == 1
    )
    assert (
        row["op_id_alta"] == row["op_id_ultima_modificacion"]
        and row["deleted_at"] is None
    )
    same_other = client.post(
        f"/api/v1/administrativo/catalogos/{otro['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(),
    )
    assert same_other.status_code == 201
    op = str(uuid4())
    assert (
        client.post(
            f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
            json={**payload, "codigo_item_catalogo": f"RE_{uuid4().hex[:7]}"},
            headers=_headers(op_id=op),
        ).status_code
        == 201
    )
    incompatible = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json={
            **payload,
            "codigo_item_catalogo": f"OT_{uuid4().hex[:7]}",
            "nombre_item_catalogo": "otro",
        },
        headers=_headers(op_id=op),
    )
    assert (
        incompatible.status_code == 409
        and incompatible.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    )


def test_alta_padre_inexistente_baja_y_rollback_outbox(client, db_session, monkeypatch):
    payload = {
        "codigo_item_catalogo": f"ROLL_{uuid4().hex[:7]}",
        "nombre_item_catalogo": "Rollback",
    }
    assert (
        client.post(
            "/api/v1/administrativo/catalogos/999999/items",
            json=payload,
            headers=_headers(),
        ).status_code
        == 404
    )
    catalogo = _catalogo(client)
    baja = client.patch(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/baja",
        headers=_headers(catalogo["version_registro"]),
    )
    assert baja.status_code == 200
    assert (
        client.post(
            f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
            json=payload,
            headers=_headers(),
        ).status_code
        == 404
    )
    active = _catalogo(client)
    from app.infrastructure.persistence.repositories.outbox_repository import (
        OutboxRepository,
    )

    monkeypatch.setattr(
        OutboxRepository,
        "add_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("private outbox")),
    )
    failed = client.post(
        f"/api/v1/administrativo/catalogos/{active['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(),
    )
    assert failed.status_code == 500 and "private outbox" not in failed.text
    assert (
        db_session.execute(
            text("SELECT count(*) FROM item_catalogo WHERE codigo_item_catalogo=:code"),
            {"code": payload["codigo_item_catalogo"]},
        ).scalar_one()
        == 0
    )


def test_update_replay_preserva_metadata_y_rollback(client, db_session, monkeypatch):
    catalogo = _catalogo(client)
    created, payload = _item(client, catalogo)
    item = created.json()["data"]
    original = _row(db_session, item["id_item_catalogo"])
    new = {
        **payload,
        "codigo_item_catalogo": f"UP_{uuid4().hex[:7]}",
        "nombre_item_catalogo": "Actualizado",
        "descripcion": "Nueva",
    }
    op = str(uuid4())
    url = f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}"  # noqa: E501
    updated = client.put(url, json=new, headers=_headers(item["version_registro"], op))
    replay = client.put(url, json=new, headers=_headers(item["version_registro"], op))
    assert (
        updated.status_code == replay.status_code == 200
        and updated.json()["data"] == replay.json()["data"]
    )
    row = _row(db_session, item["id_item_catalogo"])
    assert (
        row["version_registro"] == 2
        and row["uid_global"] == original["uid_global"]
        and row["op_id_alta"] == original["op_id_alta"]
    )
    from app.infrastructure.persistence.repositories.outbox_repository import (
        OutboxRepository,
    )

    monkeypatch.setattr(
        OutboxRepository,
        "add_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError()),
    )
    failed = client.put(
        url, json={**new, "nombre_item_catalogo": "No persiste"}, headers=_headers(2)
    )
    assert (
        failed.status_code == 500
        and _row(db_session, item["id_item_catalogo"])["nombre_item_catalogo"]
        == "Actualizado"
    )


def test_estado_readonly_invalido_replay_incompatible_y_rollback(
    client, db_session, monkeypatch
):
    catalogo = _catalogo(client)
    created, _ = _item(client, catalogo)
    item = created.json()["data"]
    url = f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/estado"  # noqa: E501
    op = str(uuid4())
    inactive = client.patch(
        url, json={"estado_item_catalogo": "INACTIVO"}, headers=_headers(1, op)
    )
    assert (
        inactive.status_code == 200
        and client.get(
            f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
            params={"estado_item_catalogo": "INACTIVO"},
        ).json()["data"]["total"]
        == 1
    )
    incompatible = client.patch(
        url, json={"estado_item_catalogo": "ACTIVO"}, headers=_headers(2, op)
    )
    assert (
        incompatible.status_code == 409
        and incompatible.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    )
    invalid = client.patch(
        url, json={"estado_item_catalogo": "BAJA"}, headers=_headers(2)
    )
    assert (
        invalid.status_code == 422
        and _row(db_session, item["id_item_catalogo"])["estado_item_catalogo"]
        == "INACTIVO"
    )
    from app.infrastructure.persistence.repositories.outbox_repository import (
        OutboxRepository,
    )

    monkeypatch.setattr(
        OutboxRepository,
        "add_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError()),
    )
    assert (
        client.patch(
            url, json={"estado_item_catalogo": "ACTIVO"}, headers=_headers(2)
        ).status_code
        == 500
    )
    assert (
        _row(db_session, item["id_item_catalogo"])["estado_item_catalogo"] == "INACTIVO"
    )


def test_baja_bloquea_operaciones_y_rollback(client, db_session, monkeypatch):
    catalogo = _catalogo(client)
    created, payload = _item(client, catalogo)
    item = created.json()["data"]
    url = f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/baja"  # noqa: E501
    from app.infrastructure.persistence.repositories.outbox_repository import (
        OutboxRepository,
    )

    monkeypatch.setattr(
        OutboxRepository,
        "add_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError()),
    )
    assert client.patch(url, headers=_headers(1)).status_code == 500
    assert _row(db_session, item["id_item_catalogo"])["deleted_at"] is None
    monkeypatch.undo()
    deleted = client.patch(url, headers=_headers(1))
    assert deleted.status_code == 200
    update = client.put(url.removesuffix("/baja"), json=payload, headers=_headers(2))
    state = client.patch(
        url.removesuffix("/baja") + "/estado",
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(2),
    )
    duplicate = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(),
    )
    assert (
        update.status_code == state.status_code == 404 and duplicate.status_code == 409
    )


def test_alta_colision_concurrente_op_id_devuelve_replay(
    client, db_session, monkeypatch
):
    catalogo = _catalogo(client)
    op_id = str(uuid4())
    created, payload = _item(client, catalogo, op_id)
    original = __import__(
        "app.infrastructure.persistence.repositories.item_catalogo_repository",
        fromlist=["ItemCatalogoRepository"],
    ).ItemCatalogoRepository
    original_lookup = original.by_op_alta
    calls = 0

    def miss_initial(self, requested_op_id):
        nonlocal calls
        calls += 1
        return None if calls == 1 else original_lookup(self, requested_op_id)

    monkeypatch.setattr(original, "by_op_alta", miss_initial)
    monkeypatch.setattr(
        original,
        "_constraint_name",
        staticmethod(lambda exc: "ux_item_catalogo_op_id_alta"),
    )
    replay = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(op_id=op_id),
    )
    item = created.json()["data"]
    assert calls == 2 and replay.status_code == 201 and replay.json()["data"] == item
    assert (
        db_session.execute(
            text(
                "SELECT count(*) FROM item_catalogo WHERE op_id_alta=CAST(:op AS uuid)"
            ),
            {"op": op_id},
        ).scalar_one()
        == 1
    )
    assert len(_events(db_session, item["id_item_catalogo"])) == 1


def test_alta_colision_concurrente_incompatible_y_fila_ausente(client, monkeypatch):
    catalogo = _catalogo(client)
    op_id = str(uuid4())
    _, payload = _item(client, catalogo, op_id)
    from app.infrastructure.persistence.repositories.item_catalogo_repository import (
        ItemCatalogoRepository,
    )

    lookup = ItemCatalogoRepository.by_op_alta
    calls = 0

    def miss_then_find(self, requested_op_id):
        nonlocal calls
        calls += 1
        return None if calls == 1 else lookup(self, requested_op_id)

    monkeypatch.setattr(ItemCatalogoRepository, "by_op_alta", miss_then_find)
    monkeypatch.setattr(
        ItemCatalogoRepository,
        "_constraint_name",
        staticmethod(lambda exc: "ux_item_catalogo_op_id_alta"),
    )
    incompatible = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json={**payload, "nombre_item_catalogo": "Distinto"},
        headers=_headers(op_id=op_id),
    )
    assert (
        calls == 2
        and incompatible.status_code == 409
        and incompatible.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    )
    monkeypatch.setattr(ItemCatalogoRepository, "by_op_alta", lambda *args: None)
    absent = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(op_id=op_id),
    )
    assert absent.status_code == 500 and absent.json()["details"] == {}


def test_op_ultima_modificacion_no_se_reutiliza_entre_items(client, db_session):
    catalogo = _catalogo(client)
    first_response, first_payload = _item(client, catalogo)
    second_response, second_payload = _item(client, catalogo)
    first, second = first_response.json()["data"], second_response.json()["data"]
    op_id = str(uuid4())
    first_url = (
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}"
        f"/items/{first['id_item_catalogo']}"
    )
    second_url = (
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}"
        f"/items/{second['id_item_catalogo']}"
    )
    update = client.put(
        first_url,
        json={**first_payload, "nombre_item_catalogo": "Primer cambio"},
        headers=_headers(first["version_registro"], op_id),
    )
    conflict = client.put(
        second_url,
        json={**second_payload, "nombre_item_catalogo": "No debe cambiar"},
        headers=_headers(second["version_registro"], op_id),
    )
    assert update.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    persisted = _row(db_session, second["id_item_catalogo"])
    assert persisted["version_registro"] == second["version_registro"]
    assert persisted["nombre_item_catalogo"] == second_payload["nombre_item_catalogo"]
    assert not [
        event
        for event in _events(db_session, second["id_item_catalogo"])
        if event["event_type"] == "item_catalogo_modificado"
    ]


def test_op_ultima_modificacion_bloquea_estado_y_baja_entre_items(client, db_session):
    catalogo = _catalogo(client)
    first_response, _ = _item(client, catalogo)
    second_response, _ = _item(client, catalogo)
    first, second = first_response.json()["data"], second_response.json()["data"]
    op_id = str(uuid4())
    first_state = (
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}"
        f"/items/{first['id_item_catalogo']}/estado"
    )
    second_state = (
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}"
        f"/items/{second['id_item_catalogo']}/estado"
    )
    assert (
        client.patch(
            first_state,
            json={"estado_item_catalogo": "INACTIVO"},
            headers=_headers(1, op_id),
        ).status_code
        == 200
    )
    conflict_state = client.patch(
        second_state,
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(1, op_id),
    )
    conflict_baja = client.patch(
        second_state.removesuffix("/estado") + "/baja", headers=_headers(1, op_id)
    )
    assert conflict_state.status_code == conflict_baja.status_code == 409
    assert (
        conflict_state.json()["error_code"]
        == conflict_baja.json()["error_code"]
        == "IDEMPOTENT_DUPLICATE"
    )
    persisted = _row(db_session, second["id_item_catalogo"])
    assert persisted["estado_item_catalogo"] == "ACTIVO"
    assert persisted["deleted_at"] is None and persisted["version_registro"] == 1
    assert len(_events(db_session, second["id_item_catalogo"])) == 1


def test_change_serializa_op_antes_del_lookup_global(client, monkeypatch):
    catalogo = _catalogo(client)
    created, payload = _item(client, catalogo)
    item = created.json()["data"]
    from app.infrastructure.persistence.repositories.item_catalogo_repository import (
        ItemCatalogoRepository,
    )

    calls = []
    lock = ItemCatalogoRepository._lock_operation
    lookup = ItemCatalogoRepository.by_op_ultima_modificacion

    def tracked_lock(self, op_id):
        calls.append("lock")
        return lock(self, op_id)

    def tracked_lookup(self, op_id):
        calls.append("lookup")
        return lookup(self, op_id)

    monkeypatch.setattr(ItemCatalogoRepository, "_lock_operation", tracked_lock)
    monkeypatch.setattr(
        ItemCatalogoRepository, "by_op_ultima_modificacion", tracked_lookup
    )
    url = (
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}"
        f"/items/{item['id_item_catalogo']}"
    )
    response = client.put(
        url,
        json={**payload, "nombre_item_catalogo": "Con lock"},
        headers=_headers(item["version_registro"]),
    )
    assert response.status_code == 200
    assert calls[:2] == ["lock", "lookup"]


def test_advisory_lock_serializa_update_concurrente_en_dos_sesiones():
    """Update is the real concurrent case; estado and baja share change's critical section."""  # noqa: E501
    import threading

    from app.api.core_ef_headers import CoreEFHeaders
    from app.config.database import engine
    from app.infrastructure.persistence.repositories.catalogo_maestro_repository import (  # noqa: E501
        CatalogoMaestroRepository,
    )
    from app.infrastructure.persistence.repositories.item_catalogo_repository import (
        ItemCatalogoIdempotencyConflictError,
        ItemCatalogoRepository,
    )
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    setup = factory()
    try:
        catalogo = CatalogoMaestroRepository(setup).create(
            {
                "codigo_catalogo_maestro": f"LOCK_{uuid4().hex[:10]}",
                "nombre_catalogo_maestro": "Lock",
                "descripcion": None,
            },
            CoreEFHeaders(uuid4(), 1, 1, 1),
        )
        first = ItemCatalogoRepository(setup).create(
            catalogo["id_catalogo_maestro"],
            {
                "codigo_item_catalogo": f"LA_{uuid4().hex[:8]}",
                "nombre_item_catalogo": "A",
                "descripcion": None,
            },
            CoreEFHeaders(uuid4(), 1, 1, 1),
        )
        second = ItemCatalogoRepository(setup).create(
            catalogo["id_catalogo_maestro"],
            {
                "codigo_item_catalogo": f"LB_{uuid4().hex[:8]}",
                "nombre_item_catalogo": "B",
                "descripcion": None,
            },
            CoreEFHeaders(uuid4(), 1, 1, 1),
        )
    finally:
        setup.close()

    barrier = threading.Barrier(2)
    op_id = uuid4()
    results: list[object] = []

    def _update(item, name):
        session = factory()
        try:
            barrier.wait(timeout=5)
            result = ItemCatalogoRepository(session).change(
                catalogo["id_catalogo_maestro"],
                item["id_item_catalogo"],
                {
                    "codigo_item_catalogo": item["codigo_item_catalogo"],
                    "nombre_item_catalogo": name,
                    "descripcion": None,
                },
                CoreEFHeaders(op_id, 1, 1, 1),
                1,
                "update",
            )
            results.append(("ok", result))
        except ItemCatalogoIdempotencyConflictError:
            results.append(("conflict", None))
        finally:
            session.close()

    threads = [
        threading.Thread(target=_update, args=(first, "A cambiado")),
        threading.Thread(target=_update, args=(second, "B cambiado")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert not any(thread.is_alive() for thread in threads)
    assert sorted(result[0] for result in results) == ["conflict", "ok"]
    verify = factory()
    try:
        rows = (
            verify.execute(
                text(
                    "SELECT id_item_catalogo, nombre_item_catalogo, version_registro FROM item_catalogo WHERE id_item_catalogo IN (:first, :second) ORDER BY id_item_catalogo"  # noqa: E501
                ),
                {
                    "first": first["id_item_catalogo"],
                    "second": second["id_item_catalogo"],
                },
            )
            .mappings()
            .all()
        )
        assert sum(row["version_registro"] == 2 for row in rows) == 1
        assert (
            verify.execute(
                text(
                    "SELECT count(*) FROM item_catalogo WHERE op_id_ultima_modificacion=CAST(:op AS uuid)"  # noqa: E501
                ),
                {"op": str(op_id)},
            ).scalar_one()
            == 1
        )
        assert (
            verify.execute(
                text(
                    "SELECT count(*) FROM outbox_event WHERE event_type='item_catalogo_modificado' AND aggregate_id IN (:first, :second)"  # noqa: E501
                ),
                {
                    "first": first["id_item_catalogo"],
                    "second": second["id_item_catalogo"],
                },
            ).scalar_one()
            == 1
        )
    finally:
        verify.close()
