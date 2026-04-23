from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_cancel import _insertar_reserva_para_cancelar
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
    _payload_base,
)


def _insertar_venta_para_reserva(
    db_session,
    *,
    id_reserva_venta: int,
    codigo_venta: str,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO venta (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_reserva_venta,
                codigo_venta,
                fecha_venta,
                estado_venta,
                monto_total,
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
                :codigo_venta,
                TIMESTAMP '2026-04-22 11:00:00',
                'borrador',
                1000.00,
                NULL
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_reserva_venta": id_reserva_venta,
            "codigo_venta": codigo_venta,
        },
    )


def test_update_reserva_venta_actualiza_datos_comerciales_sin_tocar_objetos_ni_disponibilidad(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Ada", apellido="Lovelace")
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-UPD-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9501)

    create_response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-UPD-001",
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto original",
                }
            ],
            id_persona=id_persona,
            id_rol=9501,
        ),
    )
    assert create_response.status_code == 201
    reserva = create_response.json()["data"]

    response = client.put(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json={
            "codigo_reserva": "RV-UPD-001-EDIT",
            "fecha_reserva": "2026-04-25T15:30:00",
            "fecha_vencimiento": "2026-05-02T10:00:00",
            "observaciones": "Reserva actualizada",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["codigo_reserva"] == "RV-UPD-001-EDIT"
    assert body["data"]["fecha_reserva"] == "2026-04-25T15:30:00"
    assert body["data"]["fecha_vencimiento"] == "2026-05-02T10:00:00"
    assert body["data"]["observaciones"] == "Reserva actualizada"
    assert body["data"]["estado_reserva"] == "borrador"
    assert body["data"]["version_registro"] == 2
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["objetos"][0]["id_inmueble"] == id_inmueble
    assert body["data"]["objetos"][0]["observaciones"] == "Objeto original"

    reserva_row = db_session.execute(
        text(
            """
            SELECT
                codigo_reserva,
                fecha_reserva,
                fecha_vencimiento,
                observaciones,
                estado_reserva,
                version_registro,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()

    assert reserva_row["codigo_reserva"] == "RV-UPD-001-EDIT"
    assert str(reserva_row["fecha_reserva"]) == "2026-04-25 15:30:00"
    assert str(reserva_row["fecha_vencimiento"]) == "2026-05-02 10:00:00"
    assert reserva_row["observaciones"] == "Reserva actualizada"
    assert reserva_row["estado_reserva"] == "borrador"
    assert reserva_row["version_registro"] == 2
    assert reserva_row["id_instalacion_ultima_modificacion"] == 1
    assert str(reserva_row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]

    objetos = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM reserva_venta_objeto_inmobiliario
            WHERE id_reserva_venta = :id_reserva_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert objetos["total"] == 1

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


def test_update_reserva_venta_devuelve_404_si_esta_soft_deleted(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-UPD-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-UPD-002",
        estado_reserva="borrador",
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

    response = client.put(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json={
            "codigo_reserva": "RV-UPD-002-X",
            "fecha_reserva": "2026-04-21T10:00:00",
            "fecha_vencimiento": "2026-04-30T10:00:00",
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_reserva_venta_devuelve_409_si_if_match_no_coincide(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-UPD-003")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-UPD-003",
        estado_reserva="borrador",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.put(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}",
        headers={**HEADERS, "If-Match-Version": "999"},
        json={
            "codigo_reserva": "RV-UPD-003-X",
            "fecha_reserva": "2026-04-21T10:00:00",
            "fecha_vencimiento": "2026-04-30T10:00:00",
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_reserva_venta_devuelve_error_si_estado_no_es_modificable(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-UPD-004")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-UPD-004",
        estado_reserva="finalizada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.put(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json={
            "codigo_reserva": "RV-UPD-004-X",
            "fecha_reserva": "2026-04-21T10:00:00",
            "fecha_vencimiento": "2026-04-30T10:00:00",
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una reserva en estado borrador, activa o confirmada puede actualizarse."
    )


def test_update_reserva_venta_devuelve_error_si_ya_esta_vinculada_a_una_venta(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-UPD-005")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-UPD-005",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )
    _insertar_venta_para_reserva(
        db_session,
        id_reserva_venta=reserva["id_reserva_venta"],
        codigo_venta="V-UPD-005",
    )

    response = client.put(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json={
            "codigo_reserva": "RV-UPD-005-X",
            "fecha_reserva": "2026-04-21T10:00:00",
            "fecha_vencimiento": "2026-04-30T10:00:00",
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "La reserva no puede actualizarse porque ya esta vinculada a una venta."
    )


def test_update_reserva_venta_devuelve_error_si_codigo_reserva_ya_existe(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Grace", apellido="Hopper")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9502)

    id_inmueble_1 = _crear_inmueble(client, codigo="INM-RV-UPD-006A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-RV-UPD-006B")
    _crear_disponibilidad(
        client, id_inmueble=id_inmueble_1, estado_disponibilidad="DISPONIBLE"
    )
    _crear_disponibilidad(
        client, id_inmueble=id_inmueble_2, estado_disponibilidad="DISPONIBLE"
    )

    reserva_1 = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-UPD-006-A",
            objetos=[{"id_inmueble": id_inmueble_1, "id_unidad_funcional": None}],
            id_persona=id_persona,
            id_rol=9502,
        ),
    ).json()["data"]
    reserva_2 = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-UPD-006-B",
            objetos=[{"id_inmueble": id_inmueble_2, "id_unidad_funcional": None}],
            id_persona=id_persona,
            id_rol=9502,
        ),
    ).json()["data"]

    response = client.put(
        f"/api/v1/reservas-venta/{reserva_2['id_reserva_venta']}",
        headers={**HEADERS, "If-Match-Version": str(reserva_2["version_registro"])},
        json={
            "codigo_reserva": reserva_1["codigo_reserva"],
            "fecha_reserva": reserva_2["fecha_reserva"],
            "fecha_vencimiento": reserva_2["fecha_vencimiento"],
            "observaciones": reserva_2["observaciones"],
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Ya existe una reserva con el mismo codigo_reserva."
    )
