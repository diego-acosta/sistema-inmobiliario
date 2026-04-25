from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from tests.sql_failpoints import install_statement_failpoint_once
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble
from tests.test_ventas_confirm import (
    _crear_venta_desde_reserva_publica,
    _payload_confirmar_venta,
)
from tests.test_ventas_definir_condiciones_comerciales import (
    _insertar_venta_para_condiciones,
)


def _payload_escrituracion(
    *,
    fecha_escrituracion: str | None = None,
    numero_escritura: str | None = "ESC-2026-001",
) -> dict[str, object]:
    if fecha_escrituracion is None:
        fecha_escrituracion = (
            datetime.now(UTC) + timedelta(minutes=1)
        ).replace(tzinfo=None).isoformat()
    return {
        "fecha_escrituracion": fecha_escrituracion,
        "numero_escritura": numero_escritura,
        "observaciones": "Escrituracion iniciada",
    }


def _confirmar_venta_publica(client, db_session) -> dict[str, int]:
    venta = _crear_venta_desde_reserva_publica(client, db_session)
    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    return {
        "id_venta": data["id_venta"],
        "id_inmueble": venta["id_inmueble"],
    }


def _crear_trigger_falla_escrituracion(db_session, *, id_venta: int) -> None:
    install_statement_failpoint_once(
        db_session,
        statement_prefix="INSERT INTO escrituracion",
        parameter_name="id_venta",
        parameter_value=id_venta,
        error_message="forced failure on escrituracion",
    )


def test_create_escrituracion_exitosa_desde_venta_confirmada_sin_instrumento_ni_cesion(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_venta"] == venta["id_venta"]
    assert body["data"]["numero_escritura"] == "ESC-2026-001"

    escrituracion_row = db_session.execute(
        text(
            """
            SELECT id_venta, numero_escritura, deleted_at
            FROM escrituracion
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert escrituracion_row["id_venta"] == venta["id_venta"]
    assert escrituracion_row["numero_escritura"] == "ESC-2026-001"
    assert escrituracion_row["deleted_at"] is None

    venta_row = db_session.execute(
        text(
            """
            SELECT estado_venta
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert venta_row["estado_venta"] == "confirmada"

    instrumentos = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM instrumento_compraventa
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert instrumentos["total"] == 0

    cesiones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM cesion
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert cesiones["total"] == 0

    disponibilidad = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
              AND fecha_hasta IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().one()
    assert disponibilidad["estado_disponibilidad"] == "RESERVADA"

    ocupaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM ocupacion
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    ).mappings().one()
    assert ocupaciones["total"] == 0


def test_create_escrituracion_devuelve_404_si_venta_no_existe(client) -> None:
    response = client.post(
        "/api/v1/ventas/999999/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_create_escrituracion_devuelve_error_si_estado_venta_es_invalido(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-ESC-001")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-ESC-001",
        estado_venta="borrador",
        monto_total=150000,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": 150000,
            }
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una venta en estado confirmada puede registrar escrituraciones."
    )


def test_create_escrituracion_multiobjeto_consistente(client, db_session) -> None:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-ESC-002A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-ESC-002B")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-ESC-002",
        estado_venta="confirmada",
        monto_total=150000,
        objetos=[
            {
                "id_inmueble": id_inmueble_1,
                "id_unidad_funcional": None,
                "precio_asignado": 100000,
                "observaciones": "Objeto A",
            },
            {
                "id_inmueble": id_inmueble_2,
                "id_unidad_funcional": None,
                "precio_asignado": 50000,
                "observaciones": "Objeto B",
            },
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(numero_escritura="ESC-2026-002"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["numero_escritura"] == "ESC-2026-002"

    objetos_venta = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert objetos_venta["total"] == 2


def test_create_escrituracion_devuelve_error_si_ya_existe_escrituracion_activa(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    db_session.execute(
        text(
            """
            INSERT INTO escrituracion (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_venta,
                fecha_escrituracion,
                numero_escritura,
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
                :id_venta,
                TIMESTAMP '2026-04-24 09:00:00',
                'ESC-2026-PREV',
                'Escrituracion previa'
            )
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "id_venta": venta["id_venta"]},
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(fecha_escrituracion="2026-04-24T13:00:00"),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "La venta ya posee una escrituracion activa incompatible."
    )


def test_create_escrituracion_hace_rollback_completo_si_falla_la_persistencia(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    _crear_trigger_falla_escrituracion(db_session, id_venta=venta["id_venta"])
    db_session.commit()

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"

    escrituraciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM escrituracion
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert escrituraciones["total"] == 0
