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


def _payload_instrumento(
    *,
    tipo_instrumento: str = "boleto",
    numero_instrumento: str | None = "BC-2026-001",
    objetos: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "tipo_instrumento": tipo_instrumento,
        "numero_instrumento": numero_instrumento,
        "fecha_instrumento": "2026-04-22T09:00:00",
        "estado_instrumento": "generado",
        "observaciones": "Boleto inicial",
        "objetos": objetos or [],
    }


def _crear_trigger_falla_instrumento_objeto(db_session, *, id_inmueble: int) -> None:
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION trg_test_fail_instrumento_objeto()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.id_inmueble = :id_inmueble_fail THEN
                    RAISE EXCEPTION 'forced failure on instrumento_objeto_inmobiliario';
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        ).bindparams(id_inmueble_fail=id_inmueble)
    )
    db_session.execute(
        text(
            "DROP TRIGGER IF EXISTS trg_test_fail_instrumento_objeto ON instrumento_objeto_inmobiliario"
        )
    )
    db_session.execute(
        text(
            """
            CREATE TRIGGER trg_test_fail_instrumento_objeto
            BEFORE INSERT ON instrumento_objeto_inmobiliario
            FOR EACH ROW
            EXECUTE FUNCTION trg_test_fail_instrumento_objeto()
            """
        )
    )


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
        "version_registro": data["version_registro"],
        "id_inmueble": venta["id_inmueble"],
    }


def test_create_instrumento_compraventa_exitosa(client, db_session) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            objetos=[
                {
                    "id_inmueble": venta["id_inmueble"],
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto alcanzado por el instrumento",
                }
            ]
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_venta"] == venta["id_venta"]
    assert body["data"]["tipo_instrumento"] == "boleto"
    assert body["data"]["estado_instrumento"] == "generado"
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["objetos"][0]["id_inmueble"] == venta["id_inmueble"]

    instrumento_row = db_session.execute(
        text(
            """
            SELECT tipo_instrumento, estado_instrumento, id_venta, deleted_at
            FROM instrumento_compraventa
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta["id_venta"]},
    ).mappings().one()
    assert instrumento_row["tipo_instrumento"] == "boleto"
    assert instrumento_row["estado_instrumento"] == "generado"
    assert instrumento_row["deleted_at"] is None


def test_create_instrumento_compraventa_devuelve_404_si_venta_no_existe(client) -> None:
    response = client.post(
        "/api/v1/ventas/999999/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_create_instrumento_compraventa_devuelve_error_si_estado_venta_es_invalido(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-INS-001")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-INS-001",
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
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto alcanzado por el instrumento",
                }
            ]
        ),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una venta en estado confirmada puede emitir instrumentos de compraventa."
    )


def test_create_instrumento_compraventa_devuelve_error_si_venta_esta_incompleta(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-INS-002")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-INS-002",
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
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto alcanzado por el instrumento",
                }
            ]
        ),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "La venta debe tener condiciones comerciales completas antes de emitir instrumentos."
    )


def test_create_instrumento_compraventa_multiobjeto_consistente(client, db_session) -> None:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-INS-003A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-INS-003B")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-INS-003",
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
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            numero_instrumento="BC-2026-003",
            objetos=[
                {
                    "id_inmueble": id_inmueble_1,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto A",
                },
                {
                    "id_inmueble": id_inmueble_2,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto B",
                },
            ],
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["data"]["objetos"]) == 2
    assert {obj["id_inmueble"] for obj in body["data"]["objetos"]} == {
        id_inmueble_1,
        id_inmueble_2,
    }


def test_create_instrumento_compraventa_hace_rollback_completo_si_falla_un_objeto(
    client, db_session
) -> None:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-INS-004A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-INS-004B")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-INS-004",
        estado_venta="confirmada",
        monto_total=150000,
        objetos=[
            {
                "id_inmueble": id_inmueble_1,
                "id_unidad_funcional": None,
                "precio_asignado": 100000,
            },
            {
                "id_inmueble": id_inmueble_2,
                "id_unidad_funcional": None,
                "precio_asignado": 50000,
            },
        ],
    )
    _crear_trigger_falla_instrumento_objeto(db_session, id_inmueble=id_inmueble_2)
    db_session.commit()

    response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            numero_instrumento="BC-2026-004",
            objetos=[
                {
                    "id_inmueble": id_inmueble_1,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto A",
                },
                {
                    "id_inmueble": id_inmueble_2,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto B",
                },
            ],
        ),
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"

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

    instrumento_objetos = db_session.execute(
        text("SELECT COUNT(*) AS total FROM instrumento_objeto_inmobiliario")
    ).mappings().one()
    assert instrumento_objetos["total"] == 0
