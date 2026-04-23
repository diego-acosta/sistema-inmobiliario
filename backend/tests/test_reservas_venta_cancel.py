from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _payload_base
from tests.test_reservas_venta_generate_venta import _payload_generar_venta
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
)


def _insertar_reserva_para_cancelar(
    db_session,
    *,
    codigo_reserva: str,
    estado_reserva: str,
    objetos: list[dict[str, int | None]],
) -> dict[str, int]:
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
                'Reserva para cancelar'
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


def _crear_trigger_falla_cancelacion_disponibilidad(db_session, *, id_inmueble: int) -> None:
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION trg_test_fail_disponibilidad_liberada()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.estado_disponibilidad = 'DISPONIBLE'
                   AND NEW.id_inmueble = :id_inmueble_fail THEN
                    RAISE EXCEPTION 'forced failure on disponibilidad liberada';
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        ).bindparams(id_inmueble_fail=id_inmueble)
    )
    db_session.execute(
        text("DROP TRIGGER IF EXISTS trg_test_fail_disponibilidad_liberada ON disponibilidad")
    )
    db_session.execute(
        text(
            """
            CREATE TRIGGER trg_test_fail_disponibilidad_liberada
            BEFORE INSERT ON disponibilidad
            FOR EACH ROW
            EXECUTE FUNCTION trg_test_fail_disponibilidad_liberada()
            """
        )
    )


def test_cancel_reserva_venta_borrador_la_pasa_a_cancelada_sin_efectos(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CAN-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-CAN-001",
        estado_reserva="borrador",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["estado_reserva"] == "cancelada"
    assert body["data"]["version_registro"] == 2

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
    assert reserva_row["estado_reserva"] == "cancelada"
    assert reserva_row["version_registro"] == 2

    disponibilidades = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad, fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().all()
    assert len(disponibilidades) == 1
    assert disponibilidades[0]["estado_disponibilidad"] == "DISPONIBLE"
    assert disponibilidades[0]["fecha_hasta"] is None


def test_cancel_reserva_venta_activa_la_pasa_a_cancelada_sin_efectos(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CAN-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-CAN-002",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["estado_reserva"] == "cancelada"
    assert body["data"]["version_registro"] == 2

    disponibilidades = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().one()
    assert disponibilidades["total"] == 1


def test_cancel_reserva_venta_confirmada_libera_disponibilidad_y_no_toca_ocupacion_ni_venta(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CAN-003")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="RESERVADA")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-CAN-003",
        estado_reserva="confirmada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    ventas_antes = db_session.execute(text("SELECT COUNT(*) AS total FROM venta")).mappings().one()

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["estado_reserva"] == "cancelada"
    assert body["data"]["version_registro"] == 2

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
    assert reserva_row["estado_reserva"] == "cancelada"
    assert reserva_row["version_registro"] == 2

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
    assert len(disponibilidades) == 2
    assert any(
        row["estado_disponibilidad"] == "RESERVADA" and row["fecha_hasta"] is not None
        for row in disponibilidades
    )
    assert any(
        row["estado_disponibilidad"] == "DISPONIBLE" and row["fecha_hasta"] is None
        for row in disponibilidades
    )

    ocupaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM ocupacion
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().one()
    assert ocupaciones["total"] == 0

    ventas_despues = db_session.execute(text("SELECT COUNT(*) AS total FROM venta")).mappings().one()
    assert ventas_despues["total"] == ventas_antes["total"] == 0


def test_cancel_reserva_venta_devuelve_error_si_estado_es_invalido(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CAN-004")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-CAN-004",
        estado_reserva="finalizada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una reserva en estado borrador, activa o confirmada puede cancelarse."
    )


def test_cancel_reserva_venta_devuelve_error_de_concurrencia(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CAN-005")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-CAN-005",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/cancelar",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_cancel_reserva_venta_hace_rollback_completo_si_falla_liberacion_multiobjeto(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-RV-CAN-006A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-RV-CAN-006B")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_1, estado_disponibilidad="RESERVADA")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_2, estado_disponibilidad="RESERVADA")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-CAN-006",
        estado_reserva="confirmada",
        objetos=[
            {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None},
            {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None},
        ],
    )
    _crear_trigger_falla_cancelacion_disponibilidad(db_session, id_inmueble=id_inmueble_2)
    db_session.commit()

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"

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
    assert reserva_row["estado_reserva"] == "confirmada"
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
        assert disponibilidades[0]["estado_disponibilidad"] == "RESERVADA"
        assert disponibilidades[0]["fecha_hasta"] is None

    ocupaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM ocupacion")
    ).mappings().one()
    assert ocupaciones["total"] == 0

    ventas = db_session.execute(text("SELECT COUNT(*) AS total FROM venta")).mappings().one()
    assert ventas["total"] == 0


def test_cancel_reserva_venta_devuelve_error_si_tiene_venta_activa_asociada(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Linus", apellido="Cancel")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9403)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-CAN-007")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")

    create_response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-CAN-007",
            objetos=[{"id_inmueble": id_inmueble, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9403,
        ),
    )
    assert create_response.status_code == 201
    reserva = create_response.json()["data"]

    activate_response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )
    assert activate_response.status_code == 200
    reserva_activa = activate_response.json()["data"]

    confirm_response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva_activa["version_registro"])},
    )
    assert confirm_response.status_code == 200
    reserva_confirmada = confirm_response.json()["data"]

    generate_response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/generar-venta",
        headers={**HEADERS, "If-Match-Version": str(reserva_confirmada["version_registro"])},
        json=_payload_generar_venta(codigo_venta="V-CAN-007"),
    )
    assert generate_response.status_code == 201

    venta = db_session.execute(
        text(
            """
            SELECT id_venta, version_registro
            FROM venta
            WHERE id_reserva_venta = :id_reserva_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()

    # Simula el caso inconsistente que se quiere bloquear:
    # existe una venta activa vinculada mientras la reserva sigue confirmada.
    db_session.execute(
        text(
            """
            UPDATE reserva_venta
            SET estado_reserva = 'confirmada',
                version_registro = :version_registro
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {
            "id_reserva_venta": reserva["id_reserva_venta"],
            "version_registro": reserva_confirmada["version_registro"],
        },
    )
    db_session.execute(
        text(
            """
            UPDATE venta
            SET estado_venta = 'activa'
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/cancelar",
        headers={
            **HEADERS,
            "If-Match-Version": str(reserva_confirmada["version_registro"]),
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"
    assert (
        response.json()["error_message"]
        == "La reserva ya participa en una venta activa vinculada."
    )

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
    assert reserva_row["estado_reserva"] == "confirmada"
    assert reserva_row["version_registro"] == reserva_confirmada["version_registro"]

    venta_row = db_session.execute(
        text(
            """
            SELECT estado_venta, id_reserva_venta
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert venta_row["estado_venta"] == "activa"
    assert venta_row["id_reserva_venta"] == reserva["id_reserva_venta"]
