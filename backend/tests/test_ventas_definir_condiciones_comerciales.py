from decimal import Decimal

from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _crear_disponibilidad,
    _crear_inmueble,
)


def _insertar_venta_para_condiciones(
    db_session,
    *,
    codigo_venta: str,
    estado_venta: str,
    objetos: list[dict[str, object]],
    monto_total: Decimal | None = None,
) -> dict[str, object]:
    venta = db_session.execute(
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
                NULL,
                :codigo_venta,
                TIMESTAMP '2026-04-22 11:00:00',
                :estado_venta,
                :monto_total,
                'Venta para condiciones comerciales'
            )
            RETURNING id_venta, version_registro
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "codigo_venta": codigo_venta,
            "estado_venta": estado_venta,
            "monto_total": monto_total,
        },
    ).mappings().one()

    venta_objetos: list[dict[str, object]] = []
    for objeto in objetos:
        venta_objeto = db_session.execute(
            text(
                """
                INSERT INTO venta_objeto_inmobiliario (
                    uid_global,
                    version_registro,
                    created_at,
                    updated_at,
                    id_instalacion_origen,
                    id_instalacion_ultima_modificacion,
                    op_id_alta,
                    op_id_ultima_modificacion,
                    id_venta,
                    id_inmueble,
                    id_unidad_funcional,
                    precio_asignado,
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
                    :id_inmueble,
                    :id_unidad_funcional,
                    :precio_asignado,
                    :observaciones
                )
                RETURNING id_venta_objeto, version_registro
                """
            ),
            {
                "op_id": HEADERS["X-Op-Id"],
                "id_venta": venta["id_venta"],
                "id_inmueble": objeto.get("id_inmueble"),
                "id_unidad_funcional": objeto.get("id_unidad_funcional"),
                "precio_asignado": objeto.get("precio_asignado"),
                "observaciones": objeto.get("observaciones"),
            },
        ).mappings().one()
        venta_objetos.append(
            {
                "id_venta_objeto": venta_objeto["id_venta_objeto"],
                "version_registro": venta_objeto["version_registro"],
                "id_inmueble": objeto.get("id_inmueble"),
                "id_unidad_funcional": objeto.get("id_unidad_funcional"),
                "precio_asignado": objeto.get("precio_asignado"),
            }
        )

    return {
        "id_venta": venta["id_venta"],
        "version_registro": venta["version_registro"],
        "objetos": venta_objetos,
    }


def _crear_trigger_falla_update_venta_objeto(
    db_session, *, id_venta_objeto: int
) -> None:
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION trg_test_fail_update_venta_objeto()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.id_venta_objeto = :id_venta_objeto_fail THEN
                    RAISE EXCEPTION 'forced failure on venta_objeto_inmobiliario update';
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        ).bindparams(id_venta_objeto_fail=id_venta_objeto)
    )
    db_session.execute(
        text(
            "DROP TRIGGER IF EXISTS trg_test_fail_update_venta_objeto ON venta_objeto_inmobiliario"
        )
    )
    db_session.execute(
        text(
            """
            CREATE TRIGGER trg_test_fail_update_venta_objeto
            BEFORE UPDATE ON venta_objeto_inmobiliario
            FOR EACH ROW
            EXECUTE FUNCTION trg_test_fail_update_venta_objeto()
            """
        )
    )


def _payload_condiciones(
    *,
    monto_total: float,
    objetos: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "monto_total": monto_total,
        "objetos": objetos,
    }


def test_definir_condiciones_comerciales_venta_multiobjeto_actualiza_precios_y_total(
    client, db_session
) -> None:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-VTA-COND-001")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-VTA-COND-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_1, estado_disponibilidad="DISPONIBLE")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_2, estado_disponibilidad="DISPONIBLE")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-COND-001",
        estado_venta="borrador",
        objetos=[
            {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None, "precio_asignado": None},
            {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None, "precio_asignado": None},
        ],
    )

    disponibilidades_antes = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM disponibilidad
            WHERE id_inmueble IN (:id_inmueble_1, :id_inmueble_2)
              AND deleted_at IS NULL
            """
        ),
        {
            "id_inmueble_1": id_inmueble_1,
            "id_inmueble_2": id_inmueble_2,
        },
    ).mappings().one()["total"]

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_condiciones(
            monto_total=150000.00,
            objetos=[
                {
                    "id_inmueble": id_inmueble_1,
                    "id_unidad_funcional": None,
                    "precio_asignado": 100000.00,
                },
                {
                    "id_inmueble": id_inmueble_2,
                    "id_unidad_funcional": None,
                    "precio_asignado": 50000.00,
                },
            ],
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_venta"] == venta["id_venta"]
    assert body["data"]["estado_venta"] == "borrador"
    assert Decimal(body["data"]["monto_total"]) == Decimal("150000.00")
    assert len(body["data"]["objetos"]) == 2

    venta_row = db_session.execute(
        text(
            """
            SELECT estado_venta, monto_total, version_registro
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert venta_row["estado_venta"] == "borrador"
    assert venta_row["monto_total"] == Decimal("150000.00")
    assert venta_row["version_registro"] == 2

    venta_objetos = db_session.execute(
        text(
            """
            SELECT id_inmueble, precio_asignado, version_registro
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_venta_objeto
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().all()
    assert venta_objetos == [
        {
            "id_inmueble": id_inmueble_1,
            "precio_asignado": Decimal("100000.00"),
            "version_registro": 2,
        },
        {
            "id_inmueble": id_inmueble_2,
            "precio_asignado": Decimal("50000.00"),
            "version_registro": 2,
        },
    ]

    disponibilidades_despues = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM disponibilidad
            WHERE id_inmueble IN (:id_inmueble_1, :id_inmueble_2)
              AND deleted_at IS NULL
            """
        ),
        {
            "id_inmueble_1": id_inmueble_1,
            "id_inmueble_2": id_inmueble_2,
        },
    ).mappings().one()["total"]
    assert disponibilidades_despues == disponibilidades_antes

    ocupaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM ocupacion
            WHERE id_inmueble IN (:id_inmueble_1, :id_inmueble_2)
              AND deleted_at IS NULL
            """
        ),
        {
            "id_inmueble_1": id_inmueble_1,
            "id_inmueble_2": id_inmueble_2,
        },
    ).mappings().one()["total"]
    assert ocupaciones == 0

    obligaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM obligacion_financiera")
    ).mappings().one()["total"]
    assert obligaciones == 0


def test_definir_condiciones_comerciales_venta_acepta_suma_exacta(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-COND-003")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-COND-002",
        estado_venta="borrador",
        objetos=[
            {"id_inmueble": id_inmueble, "id_unidad_funcional": None, "precio_asignado": None}
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_condiciones(
            monto_total=99999.99,
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "precio_asignado": 99999.99,
                }
            ],
        ),
    )

    assert response.status_code == 200
    assert Decimal(response.json()["data"]["monto_total"]) == Decimal("99999.99")


def test_definir_condiciones_comerciales_venta_devuelve_404_si_no_existe(
    client,
) -> None:
    response = client.post(
        "/api/v1/ventas/999999/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": "1"},
        json=_payload_condiciones(
            monto_total=100000.00,
            objetos=[
                {
                    "id_inmueble": 1,
                    "id_unidad_funcional": None,
                    "precio_asignado": 100000.00,
                }
            ],
        ),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_definir_condiciones_comerciales_venta_devuelve_404_si_esta_eliminada(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-COND-013")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-COND-009",
        estado_venta="borrador",
        objetos=[
            {"id_inmueble": id_inmueble, "id_unidad_funcional": None, "precio_asignado": None}
        ],
    )
    db_session.execute(
        text(
            """
            UPDATE venta
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_condiciones(
            monto_total=100000.00,
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "precio_asignado": 100000.00,
                }
            ],
        ),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_definir_condiciones_comerciales_venta_devuelve_error_si_falta_un_objeto(
    client, db_session
) -> None:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-VTA-COND-004")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-VTA-COND-005")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-COND-003",
        estado_venta="borrador",
        objetos=[
            {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None, "precio_asignado": None},
            {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None, "precio_asignado": None},
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_condiciones(
            monto_total=100000.00,
            objetos=[
                {
                    "id_inmueble": id_inmueble_1,
                    "id_unidad_funcional": None,
                    "precio_asignado": 100000.00,
                }
            ],
        ),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Deben informarse todos los objetos vigentes de la venta, sin faltantes ni extras."
    )


def test_definir_condiciones_comerciales_venta_devuelve_error_si_precio_es_invalido(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-COND-006")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-COND-004",
        estado_venta="borrador",
        objetos=[
            {"id_inmueble": id_inmueble, "id_unidad_funcional": None, "precio_asignado": None}
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_condiciones(
            monto_total=1.00,
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "precio_asignado": 0,
                }
            ],
        ),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "precio_asignado debe ser mayor que cero para cada objeto."
    )


def test_definir_condiciones_comerciales_venta_devuelve_error_si_la_suma_no_coincide(
    client, db_session
) -> None:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-VTA-COND-007")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-VTA-COND-008")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-COND-005",
        estado_venta="borrador",
        objetos=[
            {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None, "precio_asignado": None},
            {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None, "precio_asignado": None},
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_condiciones(
            monto_total=150000.00,
            objetos=[
                {
                    "id_inmueble": id_inmueble_1,
                    "id_unidad_funcional": None,
                    "precio_asignado": 100000.00,
                },
                {
                    "id_inmueble": id_inmueble_2,
                    "id_unidad_funcional": None,
                    "precio_asignado": 40000.00,
                },
            ],
        ),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "La suma de precio_asignado debe coincidir exactamente con monto_total."
    )


def test_definir_condiciones_comerciales_venta_devuelve_error_si_estado_es_invalido(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-COND-009")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-COND-006",
        estado_venta="activa",
        objetos=[
            {"id_inmueble": id_inmueble, "id_unidad_funcional": None, "precio_asignado": None}
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_condiciones(
            monto_total=100000.00,
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "precio_asignado": 100000.00,
                }
            ],
        ),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una venta en estado borrador puede definir condiciones comerciales."
    )


def test_definir_condiciones_comerciales_venta_devuelve_error_de_concurrencia(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-COND-010")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-COND-007",
        estado_venta="borrador",
        objetos=[
            {"id_inmueble": id_inmueble, "id_unidad_funcional": None, "precio_asignado": None}
        ],
    )

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": "999"},
        json=_payload_condiciones(
            monto_total=100000.00,
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "precio_asignado": 100000.00,
                }
            ],
        ),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_definir_condiciones_comerciales_venta_hace_rollback_si_falla_un_objeto(
    client, db_session
) -> None:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-VTA-COND-011")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-VTA-COND-012")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_1, estado_disponibilidad="DISPONIBLE")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_2, estado_disponibilidad="DISPONIBLE")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-COND-008",
        estado_venta="borrador",
        monto_total=Decimal("120000.00"),
        objetos=[
            {
                "id_inmueble": id_inmueble_1,
                "id_unidad_funcional": None,
                "precio_asignado": Decimal("70000.00"),
            },
            {
                "id_inmueble": id_inmueble_2,
                "id_unidad_funcional": None,
                "precio_asignado": Decimal("50000.00"),
            },
        ],
    )
    _crear_trigger_falla_update_venta_objeto(
        db_session,
        id_venta_objeto=venta["objetos"][1]["id_venta_objeto"],
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/definir-condiciones-comerciales",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_condiciones(
            monto_total=150000.00,
            objetos=[
                {
                    "id_inmueble": id_inmueble_1,
                    "id_unidad_funcional": None,
                    "precio_asignado": 100000.00,
                },
                {
                    "id_inmueble": id_inmueble_2,
                    "id_unidad_funcional": None,
                    "precio_asignado": 50000.00,
                },
            ],
        ),
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"

    venta_row = db_session.execute(
        text(
            """
            SELECT monto_total, version_registro
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert venta_row["monto_total"] == Decimal("120000.00")
    assert venta_row["version_registro"] == 1

    venta_objetos = db_session.execute(
        text(
            """
            SELECT id_inmueble, precio_asignado, version_registro
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_venta_objeto
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().all()
    assert venta_objetos == [
        {
            "id_inmueble": id_inmueble_1,
            "precio_asignado": Decimal("70000.00"),
            "version_registro": 1,
        },
        {
            "id_inmueble": id_inmueble_2,
            "precio_asignado": Decimal("50000.00"),
            "version_registro": 1,
        },
    ]

    disponibilidades = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM disponibilidad
            WHERE id_inmueble IN (:id_inmueble_1, :id_inmueble_2)
              AND deleted_at IS NULL
            """
        ),
        {
            "id_inmueble_1": id_inmueble_1,
            "id_inmueble_2": id_inmueble_2,
        },
    ).mappings().one()["total"]
    assert disponibilidades == 2
