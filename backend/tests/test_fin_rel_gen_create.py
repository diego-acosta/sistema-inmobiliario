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


def _crear_factura_servicio(db_session, *, codigo: str) -> int:
    id_inmueble = db_session.execute(
        text(
            """
            INSERT INTO inmueble (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_inmueble, nombre_inmueble,
                estado_administrativo, estado_juridico
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :codigo, :nombre,
                'ACTIVO', 'REGULAR'
            )
            RETURNING id_inmueble
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "codigo": f"INM-{codigo}", "nombre": codigo},
    ).scalar_one()
    id_servicio = db_session.execute(
        text(
            """
            INSERT INTO servicio (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_servicio, nombre_servicio, estado_servicio
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :codigo, :nombre, 'ACTIVO'
            )
            RETURNING id_servicio
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "codigo": f"SRV-{codigo}", "nombre": codigo},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO inmueble_servicio (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_inmueble, id_servicio, estado
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_inmueble, :id_servicio, 'ACTIVO'
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_inmueble": id_inmueble,
            "id_servicio": id_servicio,
        },
    )
    return db_session.execute(
        text(
            """
            INSERT INTO factura_servicio (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_servicio, id_inmueble, id_unidad_funcional,
                proveedor, numero_factura,
                fecha_emision, fecha_vencimiento,
                periodo_desde, periodo_hasta,
                importe_total
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_servicio, :id_inmueble, NULL,
                :proveedor, :numero_factura,
                '2026-05-01', '2026-05-20',
                '2026-05-01', '2026-05-31',
                12500.00
            )
            RETURNING id_factura_servicio
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_servicio": id_servicio,
            "id_inmueble": id_inmueble,
            "proveedor": f"Proveedor {codigo}",
            "numero_factura": f"FAC-{codigo}",
        },
    ).scalar_one()


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


def test_fin_rel_gen_create_factura_servicio_ok(client, db_session) -> None:
    id_factura = _crear_factura_servicio(db_session, codigo="FIN-RG-FS-001")

    response = client.post(
        URL,
        headers=HEADERS,
        json=_payload(
            tipo_origen="FACTURA_SERVICIO",
            id_origen=id_factura,
            descripcion="Factura externa de servicio",
        ),
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["tipo_origen"] == "FACTURA_SERVICIO"
    assert data["id_origen"] == id_factura
    assert data["descripcion"] == "Factura externa de servicio"
    row = db_session.execute(
        text(
            """
            SELECT tipo_origen, id_origen
            FROM relacion_generadora
            WHERE id_relacion_generadora = :id
            """
        ),
        {"id": data["id_relacion_generadora"]},
    ).mappings().one()
    assert row["tipo_origen"] == "factura_servicio"
    assert row["id_origen"] == id_factura


def test_fin_rel_gen_create_factura_servicio_idempotente(client, db_session) -> None:
    id_factura = _crear_factura_servicio(db_session, codigo="FIN-RG-FS-IDEMP")

    response_1 = client.post(
        URL,
        headers=HEADERS,
        json=_payload(tipo_origen="FACTURA_SERVICIO", id_origen=id_factura),
    )
    response_2 = client.post(
        URL,
        headers=HEADERS,
        json=_payload(tipo_origen="FACTURA_SERVICIO", id_origen=id_factura),
    )

    assert response_1.status_code == 201, response_1.text
    assert response_2.status_code == 201, response_2.text
    data_1 = response_1.json()["data"]
    data_2 = response_2.json()["data"]
    assert data_2["id_relacion_generadora"] == data_1["id_relacion_generadora"]
    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM relacion_generadora
            WHERE tipo_origen = 'factura_servicio'
              AND id_origen = :id_factura
              AND deleted_at IS NULL
            """
        ),
        {"id_factura": id_factura},
    ).scalar_one()
    assert count == 1


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

def test_fin_rel_gen_create_falla_factura_servicio_inexistente(client) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json=_payload(tipo_origen="FACTURA_SERVICIO", id_origen=999999),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
    assert body["details"]["errors"] == ["NOT_FOUND_ORIGEN"]


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
