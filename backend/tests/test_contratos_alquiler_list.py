from tests.test_contratos_alquiler_create import _payload_base
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble
from tests.test_fin_event_contrato_alquiler import (
    _activar,
    _crear_condicion,
    _crear_contrato_borrador as _crear_contrato_con_cronograma,
    _crear_locatario_principal,
)
from sqlalchemy import text


def _crear_contrato_simple(client, *, codigo: str) -> dict:
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo}")

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato=codigo,
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
        ),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    data["id_inmueble"] = id_inmueble
    return data


def test_list_contratos_alquiler_devuelve_items_y_total(client) -> None:
    contrato_a = _crear_contrato_simple(client, codigo="CA-LIST-001")
    contrato_b = _crear_contrato_simple(client, codigo="CA-LIST-002")

    response = client.get("/api/v1/contratos-alquiler")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "data" in body
    assert body["data"]["total"] >= 2
    assert len(body["data"]["items"]) >= 2

    item = body["data"]["items"][0]
    assert "id_contrato_alquiler" in item
    assert "uid_global" in item
    assert "version_registro" in item
    assert "codigo_contrato" in item
    assert "fecha_inicio" in item
    assert "estado_contrato" in item
    assert "deleted_at" not in item

    codigos = {i["codigo_contrato"] for i in body["data"]["items"]}
    assert contrato_a["codigo_contrato"] in codigos
    assert contrato_b["codigo_contrato"] in codigos


def test_list_contratos_alquiler_filtra_por_estado(client) -> None:
    _crear_contrato_simple(client, codigo="CA-LIST-EST-001")

    response_borrador = client.get(
        "/api/v1/contratos-alquiler?estado_contrato=borrador&codigo_contrato=CA-LIST-EST-001"
    )
    assert response_borrador.status_code == 200
    body = response_borrador.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["codigo_contrato"] == "CA-LIST-EST-001"
    assert body["data"]["items"][0]["estado_contrato"] == "borrador"

    response_inexistente = client.get(
        "/api/v1/contratos-alquiler?estado_contrato=activo&codigo_contrato=CA-LIST-EST-001"
    )
    assert response_inexistente.status_code == 200
    assert response_inexistente.json()["data"]["total"] == 0
    assert response_inexistente.json()["data"]["items"] == []


def test_list_contratos_alquiler_paginacion(client) -> None:
    _crear_contrato_simple(client, codigo="CA-LIST-PGN-001")
    _crear_contrato_simple(client, codigo="CA-LIST-PGN-002")
    _crear_contrato_simple(client, codigo="CA-LIST-PGN-003")

    response_page1 = client.get("/api/v1/contratos-alquiler?limit=2&offset=0")
    assert response_page1.status_code == 200
    body_page1 = response_page1.json()
    assert body_page1["data"]["total"] >= 3
    assert len(body_page1["data"]["items"]) == 2

    response_page2 = client.get("/api/v1/contratos-alquiler?limit=2&offset=2")
    assert response_page2.status_code == 200
    body_page2 = response_page2.json()
    assert len(body_page2["data"]["items"]) >= 1

    ids_page1 = {i["id_contrato_alquiler"] for i in body_page1["data"]["items"]}
    ids_page2 = {i["id_contrato_alquiler"] for i in body_page2["data"]["items"]}
    assert ids_page1.isdisjoint(ids_page2)


def test_list_contratos_alquiler_filtra_por_id_inmueble(client) -> None:
    contrato = _crear_contrato_simple(client, codigo="CA-LIST-INM-001")
    id_inmueble = contrato["id_inmueble"]

    response = client.get(f"/api/v1/contratos-alquiler?id_inmueble={id_inmueble}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total"] >= 1
    codigos = {i["codigo_contrato"] for i in body["data"]["items"]}
    assert "CA-LIST-INM-001" in codigos

    response_otro = client.get("/api/v1/contratos-alquiler?id_inmueble=999999")
    assert response_otro.status_code == 200
    assert response_otro.json()["data"]["total"] == 0


def _contadores_no_mutacion(db_session) -> dict:
    return dict(
        db_session.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM relacion_generadora) AS relaciones,
                    (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones,
                    (SELECT COUNT(*) FROM movimiento_financiero) AS movimientos,
                    (SELECT COUNT(*) FROM outbox_event) AS outbox_events,
                    (SELECT COUNT(*) FROM inbox_event) AS inbox_events
                """
            )
        ).mappings().one()
    )


def test_list_contratos_alquiler_ui_enriquece_sin_duplicar_y_no_muta(
    client, db_session
) -> None:
    contrato = _crear_contrato_con_cronograma(
        client,
        codigo="CA-LIST-UI-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-06-30",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 1000.00, "2026-05-01")
    id_locatario = _crear_locatario_principal(
        client, db_session, contrato["id_contrato_alquiler"]
    )
    otro_inmueble = _crear_inmueble(client, codigo="INM-CA-LIST-UI-OTRO")
    db_session.execute(
        text(
            """
            INSERT INTO contrato_objeto_locativo (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_contrato_alquiler, id_inmueble, id_unidad_funcional, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_contrato, :id_inmueble, NULL, 'Objeto adicional'
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_contrato": contrato["id_contrato_alquiler"],
            "id_inmueble": otro_inmueble,
        },
    )
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])
    before = _contadores_no_mutacion(db_session)

    response = client.get(
        "/api/v1/contratos-alquiler",
        params={
            "q": "CA-LIST-UI-001",
            "id_persona": id_locatario,
            "rol_codigo": "LOCATARIO_PRINCIPAL",
            "con_saldo": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["total"] == 1
    item = body["items"][0]
    assert item["codigo_contrato"] == "CA-LIST-UI-001"
    assert len(item["partes_resumen"]) == 1
    assert item["partes_resumen"][0]["id_persona"] == id_locatario
    assert len(item["objetos_resumen"]) == 2
    assert item["relacion_financiera"]["cantidad_obligaciones"] == 2
    assert float(item["relacion_financiera"]["saldo_pendiente_total"]) == 2000.00
    assert item["acciones_ui"]["puede_abrir_detalle"] is True
    assert _contadores_no_mutacion(db_session) == before
