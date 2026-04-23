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
from tests.test_reservas_venta_update import _insertar_venta_para_reserva


def test_baja_reserva_venta_borrador_aplica_soft_delete_sin_tocar_disponibilidad(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Barbara", apellido="Liskov")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9601)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-DEL-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")

    create_response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-DEL-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
            id_persona=id_persona,
            id_rol=9601,
        ),
    )
    assert create_response.status_code == 201
    reserva = create_response.json()["data"]

    response = client.patch(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/baja",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"] == {
        "id_reserva_venta": reserva["id_reserva_venta"],
        "version_registro": 2,
        "deleted": True,
    }

    reserva_row = db_session.execute(
        text(
            """
            SELECT version_registro, deleted_at
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["version_registro"] == 2
    assert reserva_row["deleted_at"] is not None

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

    get_response = client.get(f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}")
    assert get_response.status_code == 404


def test_baja_reserva_venta_devuelve_404_si_ya_esta_soft_deleted(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-DEL-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-DEL-002",
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

    response = client.patch(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/baja",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_reserva_venta_devuelve_409_si_if_match_no_coincide(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-DEL-003")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-DEL-003",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.patch(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/baja",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_reserva_venta_devuelve_error_si_estado_es_confirmada(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-DEL-004")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="RESERVADA")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-DEL-004",
        estado_reserva="confirmada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.patch(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/baja",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una reserva en estado borrador o activa puede darse de baja."
    )

    reserva_row = db_session.execute(
        text(
            """
            SELECT deleted_at, version_registro
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["deleted_at"] is None
    assert reserva_row["version_registro"] == 1

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


def test_baja_reserva_venta_devuelve_error_si_ya_esta_vinculada_a_una_venta(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-DEL-005")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-DEL-005",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )
    _insertar_venta_para_reserva(
        db_session,
        id_reserva_venta=reserva["id_reserva_venta"],
        codigo_venta="V-DEL-005",
    )

    response = client.patch(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/baja",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "La reserva no puede darse de baja porque ya esta vinculada a una venta."
    )

    reserva_row = db_session.execute(
        text(
            """
            SELECT deleted_at
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["deleted_at"] is None
