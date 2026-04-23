from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
    _crear_unidad_funcional,
    _payload_base,
)


def _crear_reserva_base(client, *, codigo_reserva: str, id_persona: int, id_rol: int) -> dict:
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo_reserva}")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )

    create_response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva=codigo_reserva,
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "observaciones": f"Objeto {codigo_reserva}",
                }
            ],
            id_persona=id_persona,
            id_rol=id_rol,
        ),
    )
    assert create_response.status_code == 201
    data = create_response.json()["data"]
    data["id_inmueble"] = id_inmueble
    return data


def test_get_reserva_venta_devuelve_detalle_con_shape_contractual(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Ada", apellido="Lovelace")
    id_inmueble = _crear_inmueble(client, codigo="INM-RES-GET-001")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9401)

    create_response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-GET-001",
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto principal",
                }
            ],
            id_persona=id_persona,
            id_rol=9401,
        ),
    )
    assert create_response.status_code == 201
    reserva = create_response.json()["data"]

    response = client.get(f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_reserva_venta"] == reserva["id_reserva_venta"]
    assert body["data"]["uid_global"] == reserva["uid_global"]
    assert body["data"]["version_registro"] == reserva["version_registro"]
    assert body["data"]["codigo_reserva"] == "RV-GET-001"
    assert body["data"]["estado_reserva"] == "borrador"
    assert body["data"]["observaciones"] == "Reserva de prueba"
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["objetos"][0]["id_inmueble"] == id_inmueble
    assert body["data"]["objetos"][0]["id_unidad_funcional"] is None
    assert "deleted_at" not in body["data"]
    assert "participaciones" not in body["data"]


def test_get_reserva_venta_multiobjeto_devuelve_objetos_en_orden_persistido(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Margaret", apellido="Hamilton")
    id_inmueble = _crear_inmueble(client, codigo="INM-RES-GET-002")
    id_unidad_funcional = _crear_unidad_funcional(
        client,
        id_inmueble=id_inmueble,
        codigo="UF-RES-GET-002",
    )
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    _crear_disponibilidad(
        client,
        id_unidad_funcional=id_unidad_funcional,
        estado_disponibilidad="DISPONIBLE",
    )
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9402)

    create_response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-GET-002",
            objetos=[
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto inmueble",
                },
                {
                    "id_inmueble": None,
                    "id_unidad_funcional": id_unidad_funcional,
                    "observaciones": "Objeto unidad funcional",
                },
            ],
            id_persona=id_persona,
            id_rol=9402,
        ),
    )
    assert create_response.status_code == 201
    reserva = create_response.json()["data"]

    response = client.get(f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]["objetos"]) == 2
    assert body["data"]["objetos"][0]["id_inmueble"] == id_inmueble
    assert body["data"]["objetos"][0]["id_unidad_funcional"] is None
    assert body["data"]["objetos"][1]["id_inmueble"] is None
    assert body["data"]["objetos"][1]["id_unidad_funcional"] == id_unidad_funcional


def test_get_reserva_venta_devuelve_404_si_no_existe(client) -> None:
    response = client.get("/api/v1/reservas-venta/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "NOT_FOUND"
    assert body["error_message"] == "La reserva indicada no existe."


def test_list_reservas_venta_devuelve_items_total_y_paginacion_basica(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Katherine", apellido="Johnson")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9403)

    reserva_1 = _crear_reserva_base(
        client,
        codigo_reserva="RV-LIST-001",
        id_persona=id_persona,
        id_rol=9403,
    )
    reserva_2 = _crear_reserva_base(
        client,
        codigo_reserva="RV-LIST-002",
        id_persona=id_persona,
        id_rol=9403,
    )
    reserva_3 = _crear_reserva_base(
        client,
        codigo_reserva="RV-LIST-003",
        id_persona=id_persona,
        id_rol=9403,
    )

    response = client.get("/api/v1/reservas-venta?limit=2&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["total"] >= 3
    assert len(body["data"]["items"]) == 2
    assert body["data"]["items"][0]["codigo_reserva"] == reserva_3["codigo_reserva"]
    assert body["data"]["items"][1]["codigo_reserva"] == reserva_2["codigo_reserva"]
    assert "deleted_at" not in body["data"]["items"][0]
    assert reserva_1["codigo_reserva"] not in [
        item["codigo_reserva"] for item in body["data"]["items"]
    ]


def test_list_reservas_venta_filtra_por_codigo_estado_y_vigente(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Dorothy", apellido="Vaughan")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9404)

    borrador = _crear_reserva_base(
        client,
        codigo_reserva="RV-FILTRO-BORRADOR",
        id_persona=id_persona,
        id_rol=9404,
    )
    activa = _crear_reserva_base(
        client,
        codigo_reserva="RV-FILTRO-ACTIVA",
        id_persona=id_persona,
        id_rol=9404,
    )
    confirmar = _crear_reserva_base(
        client,
        codigo_reserva="RV-FILTRO-CONFIRMADA",
        id_persona=id_persona,
        id_rol=9404,
    )

    activate_response = client.post(
        f"/api/v1/reservas-venta/{activa['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(activa["version_registro"])},
    )
    assert activate_response.status_code == 200

    confirm_activate_response = client.post(
        f"/api/v1/reservas-venta/{confirmar['id_reserva_venta']}/activar",
        headers={**HEADERS, "If-Match-Version": str(confirmar["version_registro"])},
    )
    assert confirm_activate_response.status_code == 200
    confirmada_activa = confirm_activate_response.json()["data"]

    confirm_response = client.post(
        f"/api/v1/reservas-venta/{confirmar['id_reserva_venta']}/confirmar",
        headers={
            **HEADERS,
            "If-Match-Version": str(confirmada_activa["version_registro"]),
        },
    )
    assert confirm_response.status_code == 200

    by_codigo = client.get(
        "/api/v1/reservas-venta?codigo_reserva=RV-FILTRO-ACTIVA"
    )
    assert by_codigo.status_code == 200
    assert by_codigo.json()["data"]["total"] == 1
    assert by_codigo.json()["data"]["items"][0]["codigo_reserva"] == "RV-FILTRO-ACTIVA"

    by_estado = client.get("/api/v1/reservas-venta?estado_reserva=confirmada")
    assert by_estado.status_code == 200
    items_estado = by_estado.json()["data"]["items"]
    assert len(items_estado) == 1
    assert items_estado[0]["codigo_reserva"] == "RV-FILTRO-CONFIRMADA"

    vigentes = client.get("/api/v1/reservas-venta?vigente=true")
    assert vigentes.status_code == 200
    codigos_vigentes = {item["codigo_reserva"] for item in vigentes.json()["data"]["items"]}
    assert "RV-FILTRO-ACTIVA" in codigos_vigentes
    assert "RV-FILTRO-CONFIRMADA" in codigos_vigentes
    assert borrador["codigo_reserva"] not in codigos_vigentes

    no_vigentes = client.get("/api/v1/reservas-venta?vigente=false")
    assert no_vigentes.status_code == 200
    codigos_no_vigentes = {
        item["codigo_reserva"] for item in no_vigentes.json()["data"]["items"]
    }
    assert borrador["codigo_reserva"] in codigos_no_vigentes


def test_list_reservas_venta_filtra_por_rango_de_fechas_y_excluye_deleted_at(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Mary", apellido="Jackson")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9405)

    fuera_rango = _crear_reserva_base(
        client,
        codigo_reserva="RV-RANGO-001",
        id_persona=id_persona,
        id_rol=9405,
    )
    dentro_rango = _crear_reserva_base(
        client,
        codigo_reserva="RV-RANGO-002",
        id_persona=id_persona,
        id_rol=9405,
    )

    db_session.execute(
        text(
            """
            UPDATE reserva_venta
            SET fecha_reserva = TIMESTAMP '2026-04-10 10:00:00'
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": fuera_rango["id_reserva_venta"]},
    )
    db_session.execute(
        text(
            """
            UPDATE reserva_venta
            SET fecha_reserva = TIMESTAMP '2026-04-22 10:00:00'
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": dentro_rango["id_reserva_venta"]},
    )
    db_session.execute(
        text(
            """
            UPDATE reserva_venta
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": fuera_rango["id_reserva_venta"]},
    )

    response = client.get(
        "/api/v1/reservas-venta?fecha_desde=2026-04-20T00:00:00&fecha_hasta=2026-04-23T00:00:00"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total"] >= 1
    codigos = {item["codigo_reserva"] for item in body["data"]["items"]}
    assert "RV-RANGO-002" in codigos
    assert "RV-RANGO-001" not in codigos
