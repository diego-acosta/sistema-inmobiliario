from sqlalchemy import text

from app.application.inmuebles.services.consume_escrituracion_registrada_service import (
    ConsumeEscrituracionRegistradaService,
)
from app.application.inmuebles.services.consume_venta_confirmada_service import (
    ConsumeVentaConfirmadaService,
)
from app.infrastructure.persistence.repositories.inmueble_repository import (
    InmuebleRepository,
)
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)
from tests.test_disponibilidades_create import HEADERS
from tests.test_instrumentos_compraventa_create import _payload_instrumento
from tests.test_cesiones_create import _payload_cesion
from tests.test_ocupaciones_reemplazar_vigente import _crear_ocupacion_abierta
from tests.test_escrituraciones_create import _payload_escrituracion
from tests.test_reservas_venta_create import _crear_disponibilidad, _crear_inmueble
from tests.test_ventas_confirm import (
    _crear_venta_desde_reserva_publica,
    _payload_confirmar_venta,
)
from tests.test_ventas_definir_condiciones_comerciales import (
    _insertar_venta_para_condiciones,
)


def _confirmar_venta_publica(client, db_session) -> dict[str, int]:
    venta = _crear_venta_desde_reserva_publica(client, db_session)
    response = client.patch(
        f"/api/v1/ventas/{venta['id_venta']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(venta["version_registro"])},
        json=_payload_confirmar_venta(),
    )
    assert response.status_code == 200
    return {
        "id_venta": response.json()["data"]["id_venta"],
        "id_inmueble": venta["id_inmueble"],
    }


def _consume_venta_confirmada(db_session):
    return ConsumeVentaConfirmadaService(
        db=db_session,
        inmueble_repository=InmuebleRepository(db_session),
        outbox_repository=OutboxRepository(db_session),
    ).execute(limit=100)


def _consume_escrituracion_registrada(db_session):
    return ConsumeEscrituracionRegistradaService(
        db=db_session,
        inmueble_repository=InmuebleRepository(db_session),
        outbox_repository=OutboxRepository(db_session),
    ).execute(limit=100)


def test_get_venta_con_reserva_devuelve_reserva_objetos_y_disponibilidad_reservada(
    client, db_session
) -> None:
    venta = _crear_venta_desde_reserva_publica(client, db_session)

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_venta"] == venta["id_venta"]
    assert "id_reserva_venta" not in body["data"]
    assert "uid_global" not in body["data"]
    assert "observaciones" not in body["data"]
    assert "created_at" not in body["data"]
    assert "updated_at" not in body["data"]
    assert body["data"]["origen"]["venta_directa"] is False
    assert body["data"]["origen"]["con_reserva"] is not None
    assert body["data"]["origen"]["con_reserva"]["id_reserva_venta"] == venta["id_reserva_venta"]
    assert body["data"]["origen"]["con_reserva"]["estado_reserva_venta"] == "finalizada"
    assert len(body["data"]["objetos"]) == 1
    assert "id_venta_objeto" not in body["data"]["objetos"][0]
    assert isinstance(body["data"]["objetos"][0]["id_venta_objeto_inmobiliario"], int)
    assert body["data"]["objetos"][0]["disponibilidad_actual"] == "RESERVADA"
    assert body["data"]["objetos"][0]["ocupacion_actual"] is None
    assert body["data"]["integracion_inmobiliaria"]["eventos"] == []
    assert body["data"]["resumen"]["venta_cerrada_logica"] is False
    assert body["data"]["resumen"]["estado_operativo_conocido_del_activo"] == "RESERVADA"


def test_get_venta_sin_reserva_devuelve_origen_directo_y_sin_ocupacion(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-GET-001")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-GET-001",
        estado_venta="confirmada",
        monto_total=150000,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": 150000,
                "observaciones": "Objeto sin reserva",
            }
        ],
    )

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}")

    assert response.status_code == 200
    body = response.json()
    assert "id_reserva_venta" not in body["data"]
    assert "uid_global" not in body["data"]
    assert "observaciones" not in body["data"]
    assert "created_at" not in body["data"]
    assert "updated_at" not in body["data"]
    assert body["data"]["origen"]["venta_directa"] is True
    assert body["data"]["origen"]["con_reserva"] is None
    assert body["data"]["objetos"][0]["id_inmueble"] == id_inmueble
    assert isinstance(body["data"]["objetos"][0]["id_venta_objeto_inmobiliario"], int)
    assert body["data"]["objetos"][0]["disponibilidad_actual"] == "DISPONIBLE"
    assert body["data"]["objetos"][0]["ocupacion_actual"] is None


def test_get_venta_multiobjeto_devuelve_objetos_y_disponibilidad_actual_por_objeto(
    client, db_session
) -> None:
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-VTA-GET-002A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-VTA-GET-002B")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_1, estado_disponibilidad="DISPONIBLE")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_2, estado_disponibilidad="DISPONIBLE")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-GET-002",
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

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]["objetos"]) == 2
    estados = {
        item["id_inmueble"]: item["disponibilidad_actual"]
        for item in body["data"]["objetos"]
    }
    assert estados[id_inmueble_1] == "DISPONIBLE"
    assert estados[id_inmueble_2] == "DISPONIBLE"
    assert body["data"]["resumen"]["estado_operativo_conocido_del_activo"] == "DISPONIBLE"


def test_get_venta_devuelve_ocupacion_actual_simple_si_hay_una_unica_vigente(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-GET-OC-001")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    _crear_ocupacion_abierta(client, id_inmueble, tipo_ocupacion="PROPIA")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-GET-OC-001",
        estado_venta="confirmada",
        monto_total=150000,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": 150000,
                "observaciones": "Objeto con ocupacion",
            }
        ],
    )

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["objetos"][0]["disponibilidad_actual"] == "DISPONIBLE"
    assert body["data"]["objetos"][0]["ocupacion_actual"] == "PROPIA"


def test_get_venta_devuelve_instrumentos_cesiones_y_escrituraciones_asociadas(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    instrumento_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            objetos=[
                {
                    "id_inmueble": venta["id_inmueble"],
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto alcanzado",
                }
            ]
        ),
    )
    assert instrumento_response.status_code == 201

    cesion_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(),
    )
    assert cesion_response.status_code == 201

    escrituracion_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )
    assert escrituracion_response.status_code == 201

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]["instrumentos_compraventa"]) == 1
    assert len(body["data"]["cesiones"]) == 1
    assert len(body["data"]["escrituraciones"]) == 1
    assert body["data"]["resumen"]["venta_cerrada_logica"] is True
    assert body["data"]["resumen"]["estado_operativo_conocido_del_activo"] == "RESERVADA"


def test_get_venta_devuelve_estado_integracion_con_eventos_emitidos_y_efecto_por_objeto(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    escrituracion_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )
    assert escrituracion_response.status_code == 201

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}")

    assert response.status_code == 200
    body = response.json()
    eventos = body["data"]["integracion_inmobiliaria"]["eventos"]

    assert len(eventos) == 2
    assert eventos[0]["nombre_evento"] == "venta_confirmada"
    assert eventos[0]["estado"] == "PENDING"
    assert eventos[0]["publicado_en"] is None
    assert eventos[0]["objetos"] == [
        {
            "id_inmueble": venta["id_inmueble"],
            "id_unidad_funcional": None,
            "efecto_inmobiliario": {
                "disponibilidad": "SIN_CAMBIO",
                "ocupacion": "SIN_CAMBIO",
            },
        }
    ]

    assert eventos[1]["nombre_evento"] == "escrituracion_registrada"
    assert eventos[1]["estado"] == "PENDING"
    assert eventos[1]["publicado_en"] is None
    assert eventos[1]["objetos"] == [
        {
            "id_inmueble": venta["id_inmueble"],
            "id_unidad_funcional": None,
            "efecto_inmobiliario": {
                "disponibilidad": "RESERVADA->NO_DISPONIBLE",
                "ocupacion": "SIN_CAMBIO",
            },
        }
    ]


def test_get_venta_devuelve_estado_integracion_actualizado_a_published_tras_consumo(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    escrituracion_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(numero_escritura="ESC-GET-INT-001"),
    )
    assert escrituracion_response.status_code == 201

    venta_result = _consume_venta_confirmada(db_session)
    assert venta_result.success is True

    escrituracion_result = _consume_escrituracion_registrada(db_session)
    assert escrituracion_result.success is True

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}")

    assert response.status_code == 200
    body = response.json()
    eventos = body["data"]["integracion_inmobiliaria"]["eventos"]

    assert [evento["estado"] for evento in eventos] == ["PUBLISHED", "PUBLISHED"]
    assert all(evento["publicado_en"] is not None for evento in eventos)
    assert body["data"]["objetos"][0]["disponibilidad_actual"] == "RESERVADA"
    assert (
        eventos[1]["objetos"][0]["efecto_inmobiliario"]["disponibilidad"]
        == "RESERVADA->NO_DISPONIBLE"
    )


def test_get_venta_devuelve_estado_integracion_rejected_si_el_consumo_falla(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    escrituracion_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(numero_escritura="ESC-GET-INT-002"),
    )
    assert escrituracion_response.status_code == 201

    venta_result = _consume_venta_confirmada(db_session)
    assert venta_result.success is True

    db_session.execute(
        text(
            """
            UPDATE disponibilidad
            SET estado_disponibilidad = 'BLOQUEADA'
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": venta["id_inmueble"]},
    )
    db_session.commit()

    escrituracion_result = _consume_escrituracion_registrada(db_session)
    assert escrituracion_result.success is False
    assert escrituracion_result.errors == ["CURRENT_NOT_RESERVADA"]

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}")

    assert response.status_code == 200
    body = response.json()
    eventos = body["data"]["integracion_inmobiliaria"]["eventos"]

    assert [evento["estado"] for evento in eventos] == ["PUBLISHED", "REJECTED"]
    assert eventos[1]["publicado_en"] is None
    assert (
        eventos[1]["objetos"][0]["efecto_inmobiliario"]["disponibilidad"]
        == "RESERVADA->NO_DISPONIBLE"
    )
    assert body["data"]["objetos"][0]["disponibilidad_actual"] == "BLOQUEADA"


def test_get_venta_devuelve_disponibilidad_actual_null_si_hay_ambiguedad(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VTA-GET-AMB-001")
    venta = _insertar_venta_para_condiciones(
        db_session,
        codigo_venta="V-GET-AMB-001",
        estado_venta="confirmada",
        monto_total=150000,
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "precio_asignado": 150000,
                "observaciones": "Objeto con disponibilidad ambigua",
            }
        ],
    )

    db_session.execute(
        text(
            """
            INSERT INTO disponibilidad (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
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
                :id_inmueble,
                NULL,
                'DISPONIBLE',
                TIMESTAMP '2026-04-20 10:00:00',
                NULL,
                'estado vigente A',
                NULL
            ),
            (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                CAST(:op_id AS uuid),
                CAST(:op_id AS uuid),
                :id_inmueble,
                NULL,
                'RESERVADA',
                TIMESTAMP '2026-04-21 10:00:00',
                NULL,
                'estado vigente B',
                NULL
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_inmueble": id_inmueble,
        },
    )

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["objetos"][0]["disponibilidad_actual"] is None
    assert body["data"]["resumen"]["estado_operativo_conocido_del_activo"] is None


def test_get_venta_devuelve_404_si_no_existe(client) -> None:
    response = client.get("/api/v1/ventas/999999")

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
