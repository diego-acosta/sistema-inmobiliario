from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble
from tests.test_ventas_confirm import (
    _crear_venta_desde_reserva_publica,
    _payload_confirmar_venta,
)
from tests.test_ventas_definir_condiciones_comerciales import (
    _insertar_venta_para_condiciones,
)


def _payload_cesion(
    *,
    fecha_cesion: str = "2026-04-22T14:00:00",
    tipo_cesion: str | None = "total",
) -> dict[str, object]:
    return {
        "fecha_cesion": fecha_cesion,
        "tipo_cesion": tipo_cesion,
        "observaciones": "Cesion comercial inicial",
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


def _crear_trigger_falla_cesion(db_session, *, id_venta: int) -> None:
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION trg_test_fail_cesion()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.id_venta = :id_venta_fail THEN
                    RAISE EXCEPTION 'forced failure on cesion';
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        ).bindparams(id_venta_fail=id_venta)
    )
    db_session.execute(text("DROP TRIGGER IF EXISTS trg_test_fail_cesion ON cesion"))
    db_session.execute(
        text(
            """
            CREATE TRIGGER trg_test_fail_cesion
            BEFORE INSERT ON cesion
            FOR EACH ROW
            EXECUTE FUNCTION trg_test_fail_cesion()
            """
        )
    )


def test_create_cesion_exitosa_desde_venta_confirmada_sin_instrumento(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_venta"] == venta["id_venta"]
    assert body["data"]["tipo_cesion"] == "total"

    cesion_row = db_session.execute(
        text(
            """
            SELECT id_venta, tipo_cesion, deleted_at
            FROM cesion
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert cesion_row["id_venta"] == venta["id_venta"]
    assert cesion_row["tipo_cesion"] == "total"
    assert cesion_row["deleted_at"] is None

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


def test_create_cesion_devuelve_404_si_venta_no_existe(client) -> None:
    response = client.post(
        "/api/v1/ventas/999999/cesiones",
        headers=HEADERS,
        json=_payload_cesion(),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_create_cesion_devuelve_error_si_estado_venta_es_invalido(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-CES-001")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-CES-001",
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
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una venta en estado confirmada puede registrar cesiones."
    )


def test_create_cesion_devuelve_error_si_venta_esta_incompleta(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-CES-002")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-CES-002",
        estado_venta="confirmada",
        monto_total=None,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": None,
            }
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "La venta debe tener condiciones comerciales completas antes de registrar cesiones."
    )


def test_create_cesion_multiobjeto_consistente(client, db_session) -> None:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-CES-003A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-CES-003B")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-CES-003",
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
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(tipo_cesion="parcial"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["tipo_cesion"] == "parcial"

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


def test_create_cesion_devuelve_error_si_ya_existe_cesion_activa(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    db_session.execute(
        text(
            """
            INSERT INTO cesion (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_venta,
                fecha_cesion,
                tipo_cesion,
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
                TIMESTAMP '2026-04-22 12:00:00',
                'total',
                'Cesion previa'
            )
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "id_venta": venta["id_venta"]},
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(fecha_cesion="2026-04-22T16:00:00"),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "La venta ya posee una cesion activa incompatible."
    )


def test_create_cesion_hace_rollback_completo_si_falla_la_persistencia(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    _crear_trigger_falla_cesion(db_session, id_venta=venta["id_venta"])
    db_session.commit()

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(),
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"

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
