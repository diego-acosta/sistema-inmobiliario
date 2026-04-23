from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_rol_participacion_activo,
    _insertar_reserva_conflictiva,
    _insertar_venta_conflictiva,
)


def _insertar_reserva_para_confirmar(
    db_session,
    *,
    codigo_reserva: str,
    estado_reserva: str,
    objetos: list[dict[str, int | None]],
) -> dict:
    reserva = db_session.execute(
        text(
            """
            INSERT INTO reserva_venta (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                CAST(:op_id AS uuid),
                CAST(:op_id AS uuid),
                :codigo_reserva,
                TIMESTAMP '2026-04-21 10:00:00',
                :estado_reserva,
                TIMESTAMP '2026-04-30 10:00:00',
                'Reserva para confirmar'
            )
            RETURNING id_reserva_venta, version_registro
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "codigo_reserva": codigo_reserva,
            "estado_reserva": estado_reserva,
        },
    ).mappings().one()

    for objeto in objetos:
        db_session.execute(
            text(
                """
                INSERT INTO reserva_venta_objeto_inmobiliario (
                    uid_global,
                    version_registro,
                    created_at,
                    updated_at,
                    id_instalacion_origen,
                    id_instalacion_ultima_modificacion,
                    op_id_alta,
                    op_id_ultima_modificacion,
                    id_reserva_venta,
                    id_inmueble,
                    id_unidad_funcional,
                    observaciones
                )
                VALUES (
                    gen_random_uuid(),
                    1,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    1,
                    1,
                    CAST(:op_id AS uuid),
                    CAST(:op_id AS uuid),
                    :id_reserva_venta,
                    :id_inmueble,
                    :id_unidad_funcional,
                    NULL
                )
                """
            ),
            {
                "op_id": HEADERS["X-Op-Id"],
                "id_reserva_venta": reserva["id_reserva_venta"],
                "id_inmueble": objeto["id_inmueble"],
                "id_unidad_funcional": objeto["id_unidad_funcional"],
            },
        )

    return {
        "id_reserva_venta": reserva["id_reserva_venta"],
        "version_registro": reserva["version_registro"],
    }


def _crear_trigger_falla_confirmacion_disponibilidad(db_session, *, id_inmueble: int) -> None:
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION trg_test_fail_disponibilidad_reservada()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.estado_disponibilidad = 'RESERVADA'
                   AND NEW.id_inmueble = :id_inmueble_fail THEN
                    RAISE EXCEPTION 'forced failure on disponibilidad reservada';
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        ).bindparams(id_inmueble_fail=id_inmueble)
    )
    db_session.execute(
        text("DROP TRIGGER IF EXISTS trg_test_fail_disponibilidad_reservada ON disponibilidad")
    )
    db_session.execute(
        text(
            """
            CREATE TRIGGER trg_test_fail_disponibilidad_reservada
            BEFORE INSERT ON disponibilidad
            FOR EACH ROW
            EXECUTE FUNCTION trg_test_fail_disponibilidad_reservada()
            """
        )
    )


def test_confirm_reserva_venta_confirma_y_reemplaza_disponibilidad(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CONF-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-CONF-001",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_reserva_venta"] == reserva["id_reserva_venta"]
    assert body["data"]["version_registro"] == 2
    assert body["data"]["estado_reserva"] == "confirmada"
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["objetos"][0]["id_inmueble"] == id_inmueble

    reserva_row = db_session.execute(
        text(
            """
            SELECT estado_reserva, version_registro, deleted_at
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["estado_reserva"] == "confirmada"
    assert reserva_row["version_registro"] == 2
    assert reserva_row["deleted_at"] is None

    disponibilidad_rows = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad, fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().all()
    assert len(disponibilidad_rows) == 2
    assert any(
        row["estado_disponibilidad"] == "DISPONIBLE" and row["fecha_hasta"] is not None
        for row in disponibilidad_rows
    )
    assert any(
        row["estado_disponibilidad"] == "RESERVADA" and row["fecha_hasta"] is None
        for row in disponibilidad_rows
    )

    ocupaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM ocupacion
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().one()
    assert ocupaciones["total"] == 0


def test_confirm_reserva_venta_devuelve_404_si_no_existe(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)

    response = client.post(
        "/api/v1/reservas-venta/999999/confirmar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "NOT_FOUND"
    assert body["error_message"] == "La reserva o el objeto inmobiliario indicado no existe."


def test_confirm_reserva_venta_devuelve_404_si_esta_eliminada(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CONF-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-CONF-002",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )
    db_session.execute(
        text(
            """
            UPDATE reserva_venta
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "NOT_FOUND"


def test_confirm_reserva_venta_devuelve_error_si_estado_es_invalido(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CONF-003")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-CONF-003",
        estado_reserva="borrador",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["error_message"] == "Solo una reserva en estado activa puede confirmarse."


def test_confirm_reserva_venta_devuelve_error_de_concurrencia(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CONF-004")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-CONF-004",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "CONCURRENCY_ERROR"
    assert (
        body["error_message"]
        == "If-Match-Version es requerido y debe coincidir con version_registro."
    )


def test_confirm_reserva_venta_devuelve_error_si_un_objeto_no_es_elegible(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CONF-005")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="NO_DISPONIBLE",
    )
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-CONF-005",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "El objeto inmobiliario indicado no esta disponible para confirmar la reserva."
    )


def test_confirm_reserva_venta_devuelve_error_si_hay_conflicto_con_venta_activa(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CONF-006")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _insertar_venta_conflictiva(
        db_session,
        id_inmueble=id_inmueble,
        codigo_venta="V-CONF-006",
    )
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-CONF-006",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "El objeto inmobiliario indicado ya participa en una venta activa incompatible."
    )


def test_confirm_reserva_venta_devuelve_error_si_hay_conflicto_con_reserva_activa(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CONF-007")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _insertar_reserva_conflictiva(
        db_session,
        id_inmueble=id_inmueble,
        codigo_reserva="RV-CONFLICTO-007",
    )
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-CONF-007",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "El objeto inmobiliario indicado ya participa en una reserva vigente incompatible."
    )


def test_confirm_reserva_venta_hace_rollback_completo_si_falla_un_objeto(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-RV-CONF-008A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-RV-CONF-008B")
    _crear_disponibilidad(
        client, id_inmueble=id_inmueble_1, estado_disponibilidad="DISPONIBLE"
    )
    _crear_disponibilidad(
        client, id_inmueble=id_inmueble_2, estado_disponibilidad="DISPONIBLE"
    )
    reserva = _insertar_reserva_para_confirmar(
        db_session,
        codigo_reserva="RV-CONF-008",
        estado_reserva="activa",
        objetos=[
            {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None},
            {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None},
        ],
    )
    _crear_trigger_falla_confirmacion_disponibilidad(
        db_session,
        id_inmueble=id_inmueble_2,
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "INTERNAL_ERROR"

    reserva_row = db_session.execute(
        text(
            """
            SELECT estado_reserva, version_registro
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["estado_reserva"] == "activa"
    assert reserva_row["version_registro"] == 1

    for id_inmueble in (id_inmueble_1, id_inmueble_2):
        disponibilidades = db_session.execute(
            text(
                """
                SELECT estado_disponibilidad, fecha_hasta
                FROM disponibilidad
                WHERE id_inmueble = :id_inmueble
                  AND id_unidad_funcional IS NULL
                  AND deleted_at IS NULL
                ORDER BY id_disponibilidad
                """
            ),
            {"id_inmueble": id_inmueble},
        ).mappings().all()
        assert len(disponibilidades) == 1
        assert disponibilidades[0]["estado_disponibilidad"] == "DISPONIBLE"
        assert disponibilidades[0]["fecha_hasta"] is None
