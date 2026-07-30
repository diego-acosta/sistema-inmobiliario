from app.infrastructure.persistence.repositories.parametro_sistema_repository import (
    ParametroSistemaRepository,
)
from sqlalchemy import text

ENDPOINT = "/api/v1/administrativo/configuracion/parametros"


def _seed_tipo(db_session, codigo: str, nombre: str) -> int:
    return db_session.execute(
        text("""
            INSERT INTO tipo_dato_parametro (codigo_tipo_dato, nombre_tipo_dato)
            VALUES (:codigo, :nombre)
            RETURNING id_tipo_dato_parametro
        """),
        {"codigo": codigo, "nombre": nombre},
    ).scalar_one()


def _seed_alcance(db_session, codigo: str, nombre: str) -> int:
    return db_session.execute(
        text("""
            INSERT INTO alcance_parametro (codigo_alcance, nombre_alcance)
            VALUES (:codigo, :nombre)
            RETURNING id_alcance_parametro
        """),
        {"codigo": codigo, "nombre": nombre},
    ).scalar_one()


def _seed_parametro(
    db_session,
    *,
    tipo_id: int,
    alcance_id: int,
    codigo: str,
    nombre: str,
    descripcion: str | None = None,
) -> int:
    return db_session.execute(
        text("""
            INSERT INTO parametro_sistema (
                id_tipo_dato_parametro,
                id_alcance_parametro,
                codigo_parametro,
                nombre_parametro,
                descripcion
            ) VALUES (
                :tipo_id, :alcance_id, :codigo, :nombre, :descripcion
            )
            RETURNING id_parametro_sistema
        """),
        {
            "tipo_id": tipo_id,
            "alcance_id": alcance_id,
            "codigo": codigo,
            "nombre": nombre,
            "descripcion": descripcion,
        },
    ).scalar_one()


def test_lista_vacia(client, db_session):
    db_session.execute(text("DELETE FROM parametro_sistema"))

    response = client.get(ENDPOINT)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": {"items": [], "total": 0}}


def test_lista_definiciones_con_tipo_y_alcance(client, db_session):
    tipo_id = _seed_tipo(db_session, "TEST_TIPO_407", "Tipo de prueba")
    alcance_id = _seed_alcance(db_session, "TEST_ALCANCE_407", "Alcance de prueba")
    parametro_id = _seed_parametro(
        db_session,
        tipo_id=tipo_id,
        alcance_id=alcance_id,
        codigo="TEST_PARAM_A",
        nombre="Parámetro A",
        descripcion="Definición neutral de prueba",
    )

    response = client.get(ENDPOINT)

    assert response.status_code == 200
    item = next(
        item
        for item in response.json()["data"]["items"]
        if item["id_parametro_sistema"] == parametro_id
    )
    assert item == {
        "id_parametro_sistema": parametro_id,
        "codigo_parametro": "TEST_PARAM_A",
        "nombre_parametro": "Parámetro A",
        "descripcion": "Definición neutral de prueba",
        "tipo": {
            "id_tipo_dato_parametro": tipo_id,
            "codigo_tipo_dato": "TEST_TIPO_407",
            "nombre_tipo_dato": "Tipo de prueba",
        },
        "alcance": {
            "id_alcance_parametro": alcance_id,
            "codigo_alcance": "TEST_ALCANCE_407",
            "nombre_alcance": "Alcance de prueba",
        },
    }


def test_orden_estable_por_codigo(client, db_session):
    tipo_id = _seed_tipo(db_session, "TEST_TIPO_ORDEN_407", "Tipo orden")
    alcance_id = _seed_alcance(db_session, "TEST_ALCANCE_ORDEN_407", "Alcance orden")
    _seed_parametro(
        db_session,
        tipo_id=tipo_id,
        alcance_id=alcance_id,
        codigo="TEST_PARAM_B",
        nombre="B",
    )
    _seed_parametro(
        db_session,
        tipo_id=tipo_id,
        alcance_id=alcance_id,
        codigo="TEST_PARAM_A",
        nombre="A",
    )

    response = client.get(ENDPOINT)

    codigos = [
        item["codigo_parametro"]
        for item in response.json()["data"]["items"]
        if item["codigo_parametro"].startswith("TEST_PARAM_")
    ]
    assert codigos == sorted(codigos)


def test_get_sin_headers_write_y_sin_efectos_persistentes(client, db_session):
    tipo_id = _seed_tipo(db_session, "TEST_TIPO_READ_407", "Tipo read")
    alcance_id = _seed_alcance(db_session, "TEST_ALCANCE_READ_407", "Alcance read")
    _seed_parametro(
        db_session,
        tipo_id=tipo_id,
        alcance_id=alcance_id,
        codigo="TEST_PARAM_READ",
        nombre="Read",
    )
    tables = (
        "parametro_sistema",
        "tipo_dato_parametro",
        "alcance_parametro",
        "outbox_event",
    )
    before = {
        table: db_session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        for table in tables
    }

    response = client.get(ENDPOINT)

    after = {
        table: db_session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        for table in tables
    }
    assert response.status_code == 200
    assert before == after


def test_error_tecnico_sanitizado(client, monkeypatch):
    internal_message = "driver SQL interno que no debe exponerse"

    def fail(_self):
        raise RuntimeError(internal_message)

    monkeypatch.setattr(ParametroSistemaRepository, "list_definiciones", fail)

    response = client.get(ENDPOINT)

    assert response.status_code == 500
    assert response.json() == {
        "ok": False,
        "error_code": "TECHNICAL_INCONSISTENCY",
        "error_message": "No se pudo consultar el inventario de parámetros.",
        "details": {},
    }
    assert internal_message not in response.text
