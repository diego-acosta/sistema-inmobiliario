from uuid import uuid4

from sqlalchemy import text

from tests.test_administrativo_usuarios import _headers, _payload


def _crear_usuario(client, suffix: str) -> dict:
    response = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload(f"ROL-{suffix}"),
        headers=_headers(),
    )
    assert response.status_code == 201
    return response.json()["data"]


def _crear_rol(db_session, suffix: str = "ROL") -> int:
    return db_session.execute(
        text(
            """
            INSERT INTO rol_seguridad (codigo_rol, nombre_rol, descripcion, estado_rol)
            VALUES (:codigo, :nombre, 'Rol de seguridad para pruebas', 'ACTIVO')
            RETURNING id_rol_seguridad
            """
        ),
        {"codigo": f"ADM_ASIG_{suffix}_{uuid4().hex[:8]}", "nombre": f"Rol asignación {suffix}"},
    ).scalar_one()


def _asignar(client, id_usuario: int, id_rol: int, op_id: str | None = None):
    return client.post(
        f"/api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad",
        json={"id_rol_seguridad": id_rol},
        headers=_headers(op_id),
    )


def test_listar_roles_seguridad_de_usuario(client, db_session):
    usuario = _crear_usuario(client, "LIST")
    id_rol = _crear_rol(db_session, "LIST")
    created = _asignar(client, usuario["id_usuario"], id_rol).json()["data"]

    response = client.get(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad"
    )

    assert response.status_code == 200
    assert any(
        item["id_usuario_rol_seguridad"] == created["id_usuario_rol_seguridad"]
        for item in response.json()["data"]
    )


def test_asignar_rol_a_usuario(client, db_session):
    usuario = _crear_usuario(client, "CREATE")
    id_rol = _crear_rol(db_session, "CREATE")

    response = _asignar(client, usuario["id_usuario"], id_rol)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id_usuario"] == usuario["id_usuario"]
    assert data["id_rol_seguridad"] == id_rol
    assert data["version_registro"] == 1
    assert data["deleted_at"] is None


def test_asignar_rol_inexistente_devuelve_404(client):
    usuario = _crear_usuario(client, "ROL404")

    response = _asignar(client, usuario["id_usuario"], 999999999)

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_asignar_usuario_inexistente_devuelve_404(client, db_session):
    id_rol = _crear_rol(db_session, "USR404")

    response = _asignar(client, 999999999, id_rol)

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_post_retry_mismo_op_id_no_duplica_asignacion(client, db_session):
    usuario = _crear_usuario(client, "RETRY")
    id_rol = _crear_rol(db_session, "RETRY")
    op_id = str(uuid4())

    first = _asignar(client, usuario["id_usuario"], id_rol, op_id)
    retry = _asignar(client, usuario["id_usuario"], id_rol, op_id)

    assert first.status_code == 201
    assert retry.status_code == 201
    assert retry.json()["data"] == first.json()["data"]
    count = db_session.execute(
        text("SELECT COUNT(*) FROM usuario_rol_seguridad WHERE op_id_alta = :op_id"),
        {"op_id": op_id},
    ).scalar_one()
    assert count == 1


def test_post_retry_mismo_op_id_payload_distinto_devuelve_409(client, db_session):
    usuario = _crear_usuario(client, "RETRY-DIFF")
    id_rol = _crear_rol(db_session, "RETRY-DIFF-A")
    id_rol_distinto = _crear_rol(db_session, "RETRY-DIFF-B")
    op_id = str(uuid4())

    first = _asignar(client, usuario["id_usuario"], id_rol, op_id)
    retry = _asignar(client, usuario["id_usuario"], id_rol_distinto, op_id)

    assert first.status_code == 201
    assert retry.status_code == 409
    assert retry.json()["error_code"] == "IDEMPOTENT_DUPLICATE"


def test_baja_logica_asignacion_y_no_aparece_en_listado_activo(client, db_session):
    usuario = _crear_usuario(client, "BAJA")
    id_rol = _crear_rol(db_session, "BAJA")
    asignacion = _asignar(client, usuario["id_usuario"], id_rol).json()["data"]

    response = client.patch(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad/{asignacion['id_usuario_rol_seguridad']}/baja",
        headers=_headers(version=asignacion["version_registro"]),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["fecha_hasta"] is not None
    assert data["deleted_at"] is not None
    assert data["version_registro"] == asignacion["version_registro"] + 1

    active = client.get(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad"
    )
    assert all(
        item["id_usuario_rol_seguridad"] != asignacion["id_usuario_rol_seguridad"]
        for item in active.json()["data"]
    )

    all_items = client.get(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad?incluir_bajas=true"
    )
    assert any(
        item["id_usuario_rol_seguridad"] == asignacion["id_usuario_rol_seguridad"]
        for item in all_items.json()["data"]
    )


def test_baja_sin_if_match_version_devuelve_validation_error(client, db_session):
    usuario = _crear_usuario(client, "NO-IFMATCH")
    id_rol = _crear_rol(db_session, "NO-IFMATCH")
    asignacion = _asignar(client, usuario["id_usuario"], id_rol).json()["data"]

    response = client.patch(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad/{asignacion['id_usuario_rol_seguridad']}/baja",
        headers=_headers(),
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert response.json()["details"]["header"] == "If-Match-Version"


def test_baja_version_desactualizada_devuelve_concurrency_error(client, db_session):
    usuario = _crear_usuario(client, "STALE")
    id_rol = _crear_rol(db_session, "STALE")
    asignacion = _asignar(client, usuario["id_usuario"], id_rol).json()["data"]

    response = client.patch(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad/{asignacion['id_usuario_rol_seguridad']}/baja",
        headers=_headers(version=asignacion["version_registro"] + 10),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_listar_usuarios_de_rol_seguridad(client, db_session):
    usuario = _crear_usuario(client, "BYROL")
    id_rol = _crear_rol(db_session, "BYROL")
    asignacion = _asignar(client, usuario["id_usuario"], id_rol).json()["data"]

    response = client.get(f"/api/v1/administrativo/roles-seguridad/{id_rol}/usuarios")

    assert response.status_code == 200
    assert any(
        item["id_usuario_rol_seguridad"] == asignacion["id_usuario_rol_seguridad"]
        for item in response.json()["data"]
    )


def _outbox_events(db_session, event_type: str, aggregate_id: int | None = None):
    where = "WHERE event_type = :event_type"
    params = {"event_type": event_type}
    if aggregate_id is not None:
        where += " AND aggregate_id = :aggregate_id"
        params["aggregate_id"] = aggregate_id
    return db_session.execute(
        text(
            f"""
            SELECT event_type, aggregate_type, aggregate_id, payload
            FROM outbox_event
            {where}
            ORDER BY id
            """
        ),
        params,
    ).mappings().all()


def test_asignar_rol_crea_outbox_event(client, db_session):
    usuario = _crear_usuario(client, "OUTBOX-CREATE")
    id_rol = _crear_rol(db_session, "OUTBOX-CREATE")

    response = _asignar(client, usuario["id_usuario"], id_rol)

    assert response.status_code == 201
    asignacion = response.json()["data"]
    events = _outbox_events(
        db_session,
        "rol_asignado_a_usuario",
        asignacion["id_usuario_rol_seguridad"],
    )
    assert len(events) == 1
    assert events[0]["aggregate_type"] == "usuario_rol_seguridad"
    assert events[0]["payload"]["id_usuario"] == usuario["id_usuario"]
    assert events[0]["payload"]["id_rol_seguridad"] == id_rol


def test_baja_asignacion_crea_outbox_event(client, db_session):
    usuario = _crear_usuario(client, "OUTBOX-BAJA")
    id_rol = _crear_rol(db_session, "OUTBOX-BAJA")
    asignacion = _asignar(client, usuario["id_usuario"], id_rol).json()["data"]

    response = client.patch(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad/{asignacion['id_usuario_rol_seguridad']}/baja",
        headers=_headers(version=asignacion["version_registro"]),
    )

    assert response.status_code == 200
    baja = response.json()["data"]
    events = _outbox_events(
        db_session,
        "rol_revocado_de_usuario",
        asignacion["id_usuario_rol_seguridad"],
    )
    assert len(events) == 1
    assert events[0]["aggregate_type"] == "usuario_rol_seguridad"
    assert events[0]["payload"]["version_registro"] == baja["version_registro"]
    assert events[0]["payload"]["fecha_hasta"] is not None


def test_falla_outbox_en_creacion_revierte_asignacion(client, db_session, monkeypatch):
    from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository

    usuario = _crear_usuario(client, "OUTBOX-FAIL-CREATE")
    id_rol = _crear_rol(db_session, "OUTBOX-FAIL-CREATE")
    op_id = str(uuid4())

    def _raise(*args, **kwargs):
        raise RuntimeError("outbox falló")

    monkeypatch.setattr(OutboxRepository, "add_event", _raise)

    response = _asignar(client, usuario["id_usuario"], id_rol, op_id)

    assert response.status_code == 500
    assert response.json()["error_code"] == "TECHNICAL_INCONSISTENCY"
    count = db_session.execute(
        text("SELECT COUNT(*) FROM usuario_rol_seguridad WHERE op_id_alta = :op_id"),
        {"op_id": op_id},
    ).scalar_one()
    assert count == 0


def test_falla_outbox_en_baja_revierte_baja(client, db_session, monkeypatch):
    from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository

    usuario = _crear_usuario(client, "OUTBOX-FAIL-BAJA")
    id_rol = _crear_rol(db_session, "OUTBOX-FAIL-BAJA")
    asignacion = _asignar(client, usuario["id_usuario"], id_rol).json()["data"]

    def _raise(*args, **kwargs):
        raise RuntimeError("outbox falló")

    monkeypatch.setattr(OutboxRepository, "add_event", _raise)

    response = client.patch(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad/{asignacion['id_usuario_rol_seguridad']}/baja",
        headers=_headers(version=asignacion["version_registro"]),
    )

    assert response.status_code == 500
    row = db_session.execute(
        text(
            """
            SELECT fecha_hasta, deleted_at, version_registro
            FROM usuario_rol_seguridad
            WHERE id_usuario_rol_seguridad = :id
            """
        ),
        {"id": asignacion["id_usuario_rol_seguridad"]},
    ).mappings().one()
    assert row["fecha_hasta"] is None
    assert row["deleted_at"] is None
    assert row["version_registro"] == asignacion["version_registro"]


def test_post_retry_mismo_op_id_no_duplica_outbox(client, db_session):
    usuario = _crear_usuario(client, "RETRY-OUTBOX")
    id_rol = _crear_rol(db_session, "RETRY-OUTBOX")
    op_id = str(uuid4())

    first = _asignar(client, usuario["id_usuario"], id_rol, op_id)
    retry = _asignar(client, usuario["id_usuario"], id_rol, op_id)

    assert first.status_code == 201
    assert retry.status_code == 201
    asignacion = first.json()["data"]
    events = _outbox_events(
        db_session,
        "rol_asignado_a_usuario",
        asignacion["id_usuario_rol_seguridad"],
    )
    assert len(events) == 1


def test_baja_retry_mismo_op_id_no_duplica_outbox_ni_version(client, db_session):
    usuario = _crear_usuario(client, "BAJA-RETRY-OUTBOX")
    id_rol = _crear_rol(db_session, "BAJA-RETRY-OUTBOX")
    asignacion = _asignar(client, usuario["id_usuario"], id_rol).json()["data"]
    op_id = str(uuid4())

    first = client.patch(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad/{asignacion['id_usuario_rol_seguridad']}/baja",
        headers=_headers(op_id, version=asignacion["version_registro"]),
    )
    retry = client.patch(
        f"/api/v1/administrativo/usuarios/{usuario['id_usuario']}/roles-seguridad/{asignacion['id_usuario_rol_seguridad']}/baja",
        headers=_headers(op_id, version=asignacion["version_registro"]),
    )

    assert first.status_code == 200
    assert retry.status_code == 200
    assert retry.json()["data"]["version_registro"] == first.json()["data"]["version_registro"]
    events = _outbox_events(
        db_session,
        "rol_revocado_de_usuario",
        asignacion["id_usuario_rol_seguridad"],
    )
    assert len(events) == 1


def test_asignar_mismo_rol_activo_distinto_op_id_devuelve_409(client, db_session):
    usuario = _crear_usuario(client, "DUP-ACTIVO")
    id_rol = _crear_rol(db_session, "DUP-ACTIVO")

    first = _asignar(client, usuario["id_usuario"], id_rol, str(uuid4()))
    duplicate = _asignar(client, usuario["id_usuario"], id_rol, str(uuid4()))

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "TECHNICAL_INCONSISTENCY"
    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM usuario_rol_seguridad
            WHERE id_usuario = :id_usuario
              AND id_rol_seguridad = :id_rol_seguridad
              AND deleted_at IS NULL
              AND fecha_hasta IS NULL
            """
        ),
        {"id_usuario": usuario["id_usuario"], "id_rol_seguridad": id_rol},
    ).scalar_one()
    assert count == 1


def test_get_roles_usuario_inexistente_devuelve_404(client):
    response = client.get("/api/v1/administrativo/usuarios/999999999/roles-seguridad")

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_get_usuarios_por_rol_inexistente_devuelve_404(client):
    response = client.get("/api/v1/administrativo/roles-seguridad/999999999/usuarios")

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
