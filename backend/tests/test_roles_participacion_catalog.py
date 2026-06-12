from sqlalchemy import text


def _crear_rol(
    db_session,
    *,
    id_rol_participacion: int,
    codigo_rol: str,
    nombre_rol: str,
    deleted: bool = False,
    estado_rol: str = "ACTIVO",
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO rol_participacion (
                id_rol_participacion, uid_global, version_registro, created_at,
                updated_at, id_instalacion_origen,
                id_instalacion_ultima_modificacion, op_id_alta,
                op_id_ultima_modificacion, codigo_rol, nombre_rol,
                descripcion, estado_rol, deleted_at
            )
            VALUES (
                :id_rol_participacion, gen_random_uuid(), 1,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 1,
                gen_random_uuid(), gen_random_uuid(), :codigo_rol,
                :nombre_rol, NULL, :estado_rol,
                CASE WHEN :deleted THEN CURRENT_TIMESTAMP ELSE NULL END
            )
            """
        ),
        {
            "id_rol_participacion": id_rol_participacion,
            "codigo_rol": codigo_rol,
            "nombre_rol": nombre_rol,
            "deleted": deleted,
            "estado_rol": estado_rol,
        },
    )


def _crear_roles_catalogo(db_session) -> None:
    _crear_rol(
        db_session,
        id_rol_participacion=9101,
        codigo_rol="COMPRADOR",
        nombre_rol="Comprador",
    )
    _crear_rol(
        db_session,
        id_rol_participacion=9102,
        codigo_rol="VENDEDOR",
        nombre_rol="Vendedor",
    )
    _crear_rol(
        db_session,
        id_rol_participacion=9103,
        codigo_rol="GARANTE_ELIMINADO",
        nombre_rol="Garante eliminado",
        deleted=True,
    )

    _crear_rol(
        db_session,
        id_rol_participacion=9104,
        codigo_rol="ROL_INACTIVO",
        nombre_rol="Rol inactivo",
        estado_rol="INACTIVO",
    )


def test_list_roles_participacion_filtra_por_codigo_comprador(
    client, db_session
) -> None:
    _crear_roles_catalogo(db_session)

    response = client.get("/api/v1/roles-participacion?codigo=COMPRADOR")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"] == [
        {
            "id_rol_participacion": 9101,
            "codigo_rol": "COMPRADOR",
            "nombre_rol": "Comprador",
            "deleted_at": None,
        }
    ]


def test_list_roles_participacion_excluye_soft_deleted_e_inactivos_sin_filtro(
    client, db_session
) -> None:
    _crear_roles_catalogo(db_session)

    response = client.get("/api/v1/roles-participacion")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True

    codigos = {item["codigo_rol"] for item in payload["data"]}
    assert "COMPRADOR" in codigos
    assert "VENDEDOR" in codigos
    assert "GARANTE_ELIMINADO" not in codigos
    assert "ROL_INACTIVO" not in codigos


def test_list_roles_participacion_filtra_por_codigo_inactivo_devuelve_vacio(
    client, db_session
) -> None:
    _crear_roles_catalogo(db_session)

    response = client.get("/api/v1/roles-participacion?codigo=ROL_INACTIVO")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"] == []
