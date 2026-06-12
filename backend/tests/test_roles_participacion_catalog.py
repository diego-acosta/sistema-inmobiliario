from sqlalchemy import text


def _crear_rol(
    db_session,
    *,
    id_rol_participacion: int,
    codigo_rol: str,
    nombre_rol: str,
    deleted: bool = False,
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
                :nombre_rol, NULL, 'ACTIVO',
                CASE WHEN :deleted THEN CURRENT_TIMESTAMP ELSE NULL END
            )
            """
        ),
        {
            "id_rol_participacion": id_rol_participacion,
            "codigo_rol": codigo_rol,
            "nombre_rol": nombre_rol,
            "deleted": deleted,
        },
    )


def test_list_roles_participacion_filtra_comprador_y_soft_delete(
    client, db_session
) -> None:
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
        codigo_rol="COMPRADOR",
        nombre_rol="Comprador eliminado",
        deleted=True,
    )

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
