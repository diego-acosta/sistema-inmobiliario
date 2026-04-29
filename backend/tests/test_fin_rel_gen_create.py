"""
Tests de integración para POST /api/v1/financiero/relaciones-generadoras.
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_contratos_alquiler_activate import _crear_contrato_borrador
from tests.test_disponibilidades_create import HEADERS


URL = "/api/v1/financiero/relaciones-generadoras"


# ── helpers ───────────────────────────────────────────────────────────────────

def _payload(
    *,
    tipo_origen: str = "CONTRATO_ALQUILER",
    id_origen: int,
    descripcion: str | None = None,
) -> dict:
    return {
        "tipo_origen": tipo_origen,
        "id_origen": id_origen,
        "descripcion": descripcion,
    }


def _crear_contrato(client, *, codigo: str) -> dict:
    return _crear_contrato_borrador(client, codigo=codigo)


def _crear_relacion_generadora(
    client,
    *,
    id_origen: int,
    tipo_origen: str = "CONTRATO_ALQUILER",
    descripcion: str | None = None,
) -> dict:
    response = client.post(
        URL,
        headers=HEADERS,
        json=_payload(tipo_origen=tipo_origen, id_origen=id_origen, descripcion=descripcion),
    )
    assert response.status_code == 201
    return response.json()["data"]


# ── tests exitosos ────────────────────────────────────────────────────────────

def test_fin_rel_gen_create_contrato_alquiler_ok(client, db_session) -> None:
    contrato = _crear_contrato(client, codigo="FIN-RG-C-001")

    response = client.post(
        URL,
        headers=HEADERS,
        json=_payload(id_origen=contrato["id_contrato_alquiler"], descripcion="Alquiler mes 1"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert isinstance(data["id_relacion_generadora"], int)
    assert data["tipo_origen"] == "CONTRATO_ALQUILER"
    assert data["id_origen"] == contrato["id_contrato_alquiler"]
    assert data["descripcion"] == "Alquiler mes 1"
    assert data["estado_relacion_generadora"] == "BORRADOR"
    assert data["version_registro"] == 1
    assert data["uid_global"] is not None
    assert data["fecha_alta"] is not None


def test_fin_rel_gen_create_persiste_en_db(client, db_session) -> None:
    contrato = _crear_contrato(client, codigo="FIN-RG-DB-001")

    response = client.post(
        URL,
        headers=HEADERS,
        json=_payload(id_origen=contrato["id_contrato_alquiler"]),
    )
    assert response.status_code == 201
    id_rg = response.json()["data"]["id_relacion_generadora"]

    row = db_session.execute(
        text(
            """
            SELECT
                id_relacion_generadora,
                tipo_origen,
                id_origen,
                estado_relacion_generadora,
                deleted_at
            FROM relacion_generadora
            WHERE id_relacion_generadora = :id
            """
        ),
        {"id": id_rg},
    ).mappings().one_or_none()

    assert row is not None
    assert row["tipo_origen"] == "contrato_alquiler"
    assert row["id_origen"] == contrato["id_contrato_alquiler"]
    assert row["estado_relacion_generadora"] == "BORRADOR"
    assert row["deleted_at"] is None


def test_fin_rel_gen_create_descripcion_nula(client) -> None:
    contrato = _crear_contrato(client, codigo="FIN-RG-NULL-001")

    response = client.post(
        URL,
        headers=HEADERS,
        json={"tipo_origen": "CONTRATO_ALQUILER", "id_origen": contrato["id_contrato_alquiler"]},
    )

    assert response.status_code == 201
    assert response.json()["data"]["descripcion"] is None
    assert response.json()["data"]["estado_relacion_generadora"] == "BORRADOR"


def test_fin_rel_gen_estado_invalido_falla_por_constraint_sql(client, db_session) -> None:
    contrato = _crear_contrato(client, codigo="FIN-RG-CHK-001")

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO relacion_generadora (
                    tipo_origen,
                    id_origen,
                    descripcion,
                    estado_relacion_generadora
                )
                VALUES (
                    'contrato_alquiler',
                    :id_origen,
                    'Estado invalido',
                    'INVALIDO'
                )
                """
            ),
            {"id_origen": contrato["id_contrato_alquiler"]},
        )

    db_session.rollback()


# ── tests de error: origen inexistente ───────────────────────────────────────

def test_fin_rel_gen_create_falla_contrato_inexistente(client) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json=_payload(tipo_origen="CONTRATO_ALQUILER", id_origen=999999),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
    assert body["details"]["errors"] == ["NOT_FOUND_ORIGEN"]


def test_fin_rel_gen_create_falla_venta_inexistente(client) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json=_payload(tipo_origen="VENTA", id_origen=999999),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


# ── tests de error: tipo inválido ─────────────────────────────────────────────

def test_fin_rel_gen_create_falla_tipo_invalido(client) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json=_payload(tipo_origen="INVALIDO", id_origen=1),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["details"]["errors"] == ["TIPO_ORIGEN_INVALIDO"]


def test_fin_rel_gen_create_falla_tipo_vacio(client) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json={"tipo_origen": "", "id_origen": 1},
    )

    assert response.status_code == 422


def test_fin_rel_gen_create_falla_id_origen_cero(client) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json={"tipo_origen": "CONTRATO_ALQUILER", "id_origen": 0},
    )

    assert response.status_code == 422
