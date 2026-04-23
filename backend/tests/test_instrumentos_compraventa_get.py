from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_instrumentos_compraventa_create import (
    _confirmar_venta_publica,
    _payload_instrumento,
)


def test_get_venta_instrumentos_compraventa_devuelve_items_y_total(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    create_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            objetos=[
                {
                    "id_inmueble": venta["id_inmueble"],
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto principal",
                }
            ]
        ),
    )
    assert create_response.status_code == 201
    instrumento = create_response.json()["data"]

    response = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["total"] == 1
    assert len(body["data"]["items"]) == 1
    item = body["data"]["items"][0]
    assert item["id_instrumento_compraventa"] == instrumento["id_instrumento_compraventa"]
    assert item["id_venta"] == venta["id_venta"]
    assert item["tipo_instrumento"] == "boleto"
    assert item["estado_instrumento"] == "generado"
    assert item["deleted_at"] is None
    assert len(item["objetos"]) == 1
    assert item["objetos"][0]["id_inmueble"] == venta["id_inmueble"]


def test_get_venta_instrumentos_compraventa_filtra_y_excluye_deleted_at(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    boleto_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            tipo_instrumento="boleto",
            objetos=[
                {
                    "id_inmueble": venta["id_inmueble"],
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto boleto",
                }
            ],
        ),
    )
    assert boleto_response.status_code == 201
    id_boleto = boleto_response.json()["data"]["id_instrumento_compraventa"]

    contrato_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa",
        headers=HEADERS,
        json=_payload_instrumento(
            tipo_instrumento="contrato",
            numero_instrumento="CT-2026-001",
            objetos=[
                {
                    "id_inmueble": venta["id_inmueble"],
                    "id_unidad_funcional": None,
                    "observaciones": "Objeto contrato",
                }
            ],
        ),
    )
    assert contrato_response.status_code == 201
    id_contrato = contrato_response.json()["data"]["id_instrumento_compraventa"]

    db_session.execute(
        text(
            """
            UPDATE instrumento_compraventa
            SET
                estado_instrumento = 'firmado',
                fecha_instrumento = TIMESTAMP '2026-04-24 09:00:00'
            WHERE id_instrumento_compraventa = :id_instrumento_compraventa
            """
        ),
        {"id_instrumento_compraventa": id_contrato},
    )
    db_session.execute(
        text(
            """
            UPDATE instrumento_compraventa
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_instrumento_compraventa = :id_instrumento_compraventa
            """
        ),
        {"id_instrumento_compraventa": id_boleto},
    )

    by_tipo = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa?tipo_instrumento=contrato"
    )
    assert by_tipo.status_code == 200
    items_tipo = by_tipo.json()["data"]["items"]
    assert len(items_tipo) == 1
    assert items_tipo[0]["id_instrumento_compraventa"] == id_contrato

    by_estado = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa?estado_instrumento=firmado"
    )
    assert by_estado.status_code == 200
    items_estado = by_estado.json()["data"]["items"]
    assert len(items_estado) == 1
    assert items_estado[0]["id_instrumento_compraventa"] == id_contrato

    by_fecha = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa?fecha_desde=2026-04-24T00:00:00&fecha_hasta=2026-04-25T00:00:00"
    )
    assert by_fecha.status_code == 200
    items_fecha = by_fecha.json()["data"]["items"]
    assert len(items_fecha) == 1
    assert items_fecha[0]["id_instrumento_compraventa"] == id_contrato

    all_response = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/instrumentos-compraventa"
    )
    assert all_response.status_code == 200
    all_ids = {
        item["id_instrumento_compraventa"]
        for item in all_response.json()["data"]["items"]
    }
    assert id_contrato in all_ids
    assert id_boleto not in all_ids


def test_get_venta_instrumentos_compraventa_devuelve_404_si_venta_no_existe(
    client,
) -> None:
    response = client.get("/api/v1/ventas/999999/instrumentos-compraventa")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "NOT_FOUND"
    assert body["error_message"] == "La venta indicada no existe."
