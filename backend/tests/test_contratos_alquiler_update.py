from sqlalchemy import text

from tests.test_contratos_alquiler_create import _payload_base
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble


def _crear_contrato_borrador(client, *, codigo: str) -> dict:
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
    data["id_inmueble_original"] = id_inmueble
    return data


def test_update_contrato_alquiler_exitoso(client, db_session) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-UPD-001")
    id_inmueble_nuevo = _crear_inmueble(client, codigo="INM-CA-UPD-001-NEW")

    payload = {
        "codigo_contrato": "CA-UPD-001-MOD",
        "fecha_inicio": "2026-06-01",
        "fecha_fin": "2027-05-31",
        "observaciones": "Modificado antes de activar",
        "objetos": [
            {"id_inmueble": id_inmueble_nuevo, "id_unidad_funcional": None, "observaciones": "Nuevo objeto"}
        ],
    }

    response = client.put(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]
    assert data["codigo_contrato"] == "CA-UPD-001-MOD"
    assert data["fecha_inicio"] == "2026-06-01"
    assert data["fecha_fin"] == "2027-05-31"
    assert data["observaciones"] == "Modificado antes de activar"
    assert data["estado_contrato"] == "borrador"
    assert data["version_registro"] == contrato["version_registro"] + 1
    assert data["condiciones_economicas_alquiler"] == []

    assert len(data["objetos"]) == 1
    assert data["objetos"][0]["id_inmueble"] == id_inmueble_nuevo
    assert isinstance(data["objetos"][0]["id_contrato_objeto"], int)

    row = db_session.execute(
        text(
            """
            SELECT codigo_contrato, fecha_inicio, version_registro
            FROM contrato_alquiler
            WHERE id_contrato_alquiler = :id
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).mappings().one()
    assert row["codigo_contrato"] == "CA-UPD-001-MOD"
    assert row["version_registro"] == contrato["version_registro"] + 1

    objetos_activos = db_session.execute(
        text(
            """
            SELECT id_inmueble
            FROM contrato_objeto_locativo
            WHERE id_contrato_alquiler = :id AND deleted_at IS NULL
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).mappings().all()
    assert len(objetos_activos) == 1
    assert objetos_activos[0]["id_inmueble"] == id_inmueble_nuevo

    objeto_anterior = db_session.execute(
        text(
            """
            SELECT deleted_at
            FROM contrato_objeto_locativo
            WHERE id_contrato_alquiler = :id
              AND id_inmueble = :id_inmueble_original
            """
        ),
        {
            "id": contrato["id_contrato_alquiler"],
            "id_inmueble_original": contrato["id_inmueble_original"],
        },
    ).mappings().one()
    assert objeto_anterior["deleted_at"] is not None


def test_update_contrato_alquiler_devuelve_404_si_no_existe(client) -> None:
    response = client.put(
        "/api/v1/contratos-alquiler/999999",
        headers={**HEADERS, "If-Match-Version": "1"},
        json=_payload_base(
            codigo_contrato="CA-UPD-NF-001",
            objetos=[{"id_inmueble": 1, "id_unidad_funcional": None, "observaciones": None}],
        ),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_update_contrato_alquiler_devuelve_400_si_estado_no_es_borrador(
    client,
) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-UPD-ST-001")

    client.post(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/condiciones-economicas-alquiler",
        headers=HEADERS,
        json={"monto_base": "150000.00", "fecha_desde": "2026-05-01"},
    )
    activate_response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/activar",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )
    assert activate_response.status_code == 200
    contrato_activo = activate_response.json()["data"]

    id_inmueble_nuevo = _crear_inmueble(client, codigo="INM-CA-UPD-ST-001-NEW")
    response = client.put(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}",
        headers={**HEADERS, "If-Match-Version": str(contrato_activo["version_registro"])},
        json=_payload_base(
            codigo_contrato="CA-UPD-ST-001-MOD",
            objetos=[{"id_inmueble": id_inmueble_nuevo, "id_unidad_funcional": None, "observaciones": None}],
        ),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["error_message"] == "Solo un contrato en estado borrador puede modificarse."


def test_update_contrato_alquiler_objeto_sin_ids_devuelve_422(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-UPD-422-NOID")

    response = client.put(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
        json={
            "codigo_contrato": "CA-UPD-422-NOID-MOD",
            "fecha_inicio": "2026-06-01",
            "objetos": [{"id_inmueble": None, "id_unidad_funcional": None, "observaciones": None}],
        },
    )

    assert response.status_code == 422


def test_update_contrato_alquiler_objeto_con_ambos_ids_devuelve_422(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-UPD-422-BOTH")

    # Pydantic valida antes de llegar al service: ambos ids presentes → 422
    response = client.put(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
        json={
            "codigo_contrato": "CA-UPD-422-BOTH-MOD",
            "fecha_inicio": "2026-06-01",
            "objetos": [{"id_inmueble": 1, "id_unidad_funcional": 2, "observaciones": None}],
        },
    )

    assert response.status_code == 422


def test_update_contrato_alquiler_devuelve_409_si_version_no_coincide(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-UPD-VER-001")
    id_inmueble_nuevo = _crear_inmueble(client, codigo="INM-CA-UPD-VER-001-NEW")

    response = client.put(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}",
        headers={**HEADERS, "If-Match-Version": "999"},
        json=_payload_base(
            codigo_contrato="CA-UPD-VER-001-MOD",
            objetos=[{"id_inmueble": id_inmueble_nuevo, "id_unidad_funcional": None, "observaciones": None}],
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "CONCURRENCY_ERROR"
    assert "If-Match-Version" in body["error_message"]
