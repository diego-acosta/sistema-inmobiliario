from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_cancel import (
    _crear_trigger_falla_cancelacion_disponibilidad,
    _insertar_reserva_para_cancelar,
)
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_disponibilidad,
    _crear_inmueble,
)


def test_expire_reserva_venta_activa_la_pasa_a_vencida_sin_efectos(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-VEN-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-VEN-001",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/vencer",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["estado_reserva"] == "vencida"
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
    assert reserva_row["estado_reserva"] == "vencida"
    assert reserva_row["version_registro"] == 2


def test_expire_reserva_venta_desde_activa_no_impacta_disponibilidad(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-VEN-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-VEN-002",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/vencer",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200

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


def test_expire_reserva_venta_confirmada_libera_disponibilidad_y_no_toca_ocupacion_ni_venta(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-VEN-003")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="RESERVADA")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-VEN-003",
        estado_reserva="confirmada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    ventas_antes = db_session.execute(text("SELECT COUNT(*) AS total FROM venta")).mappings().one()

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/vencer",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["estado_reserva"] == "vencida"
    assert body["data"]["version_registro"] == 2

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
        text("SELECT COUNT(*) AS total FROM ocupacion")
    ).mappings().one()
    assert ocupaciones["total"] == 0

    ventas_despues = db_session.execute(text("SELECT COUNT(*) AS total FROM venta")).mappings().one()
    assert ventas_despues["total"] == ventas_antes["total"] == 0


def test_expire_reserva_venta_devuelve_error_si_estado_es_invalido(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-VEN-004")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-VEN-004",
        estado_reserva="borrador",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/vencer",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una reserva en estado activa o confirmada puede vencerse."
    )


def test_expire_reserva_venta_devuelve_error_de_concurrencia(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RV-VEN-005")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-VEN-005",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/vencer",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_expire_reserva_venta_hace_rollback_completo_si_falla_liberacion_multiobjeto(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-RV-VEN-006A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-RV-VEN-006B")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_1, estado_disponibilidad="RESERVADA")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_2, estado_disponibilidad="RESERVADA")
    reserva = _insertar_reserva_para_cancelar(
        db_session,
        codigo_reserva="RV-VEN-006",
        estado_reserva="confirmada",
        objetos=[
            {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None},
            {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None},
        ],
    )
    _crear_trigger_falla_cancelacion_disponibilidad(db_session, id_inmueble=id_inmueble_2)
    db_session.commit()

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/vencer",
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
