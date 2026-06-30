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
