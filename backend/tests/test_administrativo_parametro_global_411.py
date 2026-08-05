from datetime import datetime, timedelta
from uuid import UUID

from app.infrastructure.persistence.repositories.parametro_sistema_repository import (
    ParametroSistemaRepository,
)
from sqlalchemy import text

ENDPOINT = "/api/v1/administrativo/configuracion/parametros/{}/valor-global"


def _assert_no_store(response):
    assert response.headers["cache-control"] == "no-store"


def _assert_inconsistencia_sanitizada(response, *forbidden):
    assert response.status_code == 500
    assert response.json() == {
        "ok": False,
        "error_code": "inconsistencia_parametro",
        "error_message": "La definición o el valor del parámetro resulta inconsistente.",
        "details": {},
    }
    _assert_no_store(response)
    lowered = response.text.lower()
    for token in ("sql", "constraint", "driver", "tipo_dato_parametro", "alcance_parametro", *forbidden):
        assert str(token).lower() not in lowered


def _seed_tipo(db_session, codigo="ENTERO", nombre="Entero", descripcion="Valor numérico entero sin componente decimal."):
    return db_session.execute(text("""
        INSERT INTO tipo_dato_parametro (codigo_tipo_dato, nombre_tipo_dato, descripcion_tipo_dato)
        VALUES (:codigo, :nombre, :descripcion)
        ON CONFLICT (codigo_tipo_dato) DO UPDATE SET nombre_tipo_dato=EXCLUDED.nombre_tipo_dato
        RETURNING id_tipo_dato_parametro
    """), {"codigo": codigo, "nombre": nombre, "descripcion": descripcion}).scalar_one()


def _seed_alcance(db_session, codigo="GLOBAL", nombre="Global", descripcion="Aplicable sin contexto de sucursal o instalación."):
    return db_session.execute(text("""
        INSERT INTO alcance_parametro (codigo_alcance, nombre_alcance, descripcion_alcance)
        VALUES (:codigo, :nombre, :descripcion)
        ON CONFLICT (codigo_alcance) DO UPDATE SET nombre_alcance=EXCLUDED.nombre_alcance
        RETURNING id_alcance_parametro
    """), {"codigo": codigo, "nombre": nombre, "descripcion": descripcion}).scalar_one()


def _seed_parametro(db_session, codigo, *, exponible=True, sensible=False, alcance="GLOBAL", tipo="ENTERO"):
    tipo_id = _seed_tipo(db_session, tipo, "Entero" if tipo == "ENTERO" else tipo, "desc tipo")
    alcance_id = _seed_alcance(db_session, alcance, "Global" if alcance == "GLOBAL" else alcance, "desc alcance")
    return db_session.execute(text("""
        INSERT INTO parametro_sistema (
            id_tipo_dato_parametro, id_alcance_parametro, codigo_parametro,
            nombre_parametro, descripcion, exponible_api_administrativa, es_sensible
        ) VALUES (:tipo_id, :alcance_id, :codigo, :nombre, :descripcion, :exponible, :sensible)
        RETURNING id_parametro_sistema
    """), {
        "tipo_id": tipo_id, "alcance_id": alcance_id, "codigo": codigo,
        "nombre": f"Nombre {codigo}", "descripcion": f"Descripción {codigo}",
        "exponible": exponible, "sensible": sensible,
    }).scalar_one()


def _seed_valor(db_session, parametro_id, valor="15", **overrides):
    data = {
        "id_parametro_sistema": parametro_id,
        "valor_parametro": valor,
        "es_valor_vigente": True,
        "fecha_desde": None,
        "fecha_hasta": None,
        "id_sucursal": None,
        "id_instalacion": None,
        "deleted_at": None,
    }
    data.update(overrides)
    return db_session.execute(text("""
        INSERT INTO valor_parametro (
            id_parametro_sistema, valor_parametro, es_valor_vigente, fecha_desde,
            fecha_hasta, id_sucursal, id_instalacion, deleted_at
        ) VALUES (
            :id_parametro_sistema, :valor_parametro, :es_valor_vigente, :fecha_desde,
            :fecha_hasta, :id_sucursal, :id_instalacion, :deleted_at
        ) RETURNING id_valor_parametro, uid_global, version_registro
    """), data).mappings().one()


def test_valor_global_entero_exitoso_y_cache_no_store(client, db_session):
    parametro_id = _seed_parametro(db_session, "TEST_411_OK")
    valor = _seed_valor(db_session, parametro_id, "15")

    response = client.get(ENDPOINT.format("TEST_411_OK"))

    assert response.status_code == 200
    _assert_no_store(response)
    data = response.json()["data"]
    assert data["estado_valor"] == "CON_VALOR_MARCADO_VIGENTE"
    assert data["definicion"]["id_parametro_sistema"] == parametro_id
    assert data["definicion"]["codigo_parametro"] == "TEST_411_OK"
    assert set(data["definicion"]["tipo"]) == {"id_tipo_dato_parametro", "codigo_tipo_dato", "nombre_tipo_dato", "descripcion_tipo_dato"}
    assert set(data["definicion"]["alcance"]) == {"id_alcance_parametro", "codigo_alcance", "nombre_alcance", "descripcion_alcance"}
    body_value = data["valor_marcado_vigente"]
    assert body_value["id_valor_parametro"] == valor["id_valor_parametro"]
    assert UUID(body_value["uid_global"]) == valor["uid_global"]
    assert body_value["valor_raw"] == "15"
    assert body_value["valor_tipado"] == 15
    assert body_value["version_registro"] == valor["version_registro"]
    assert body_value["fecha_desde"] is None
    assert body_value["fecha_hasta"] is None
    assert body_value["created_at"]
    assert body_value["updated_at"]
    forbidden = {"deleted_at", "id_sucursal", "id_instalacion", "exponible_api_administrativa", "es_sensible"}
    assert forbidden.isdisjoint(body_value)
    assert forbidden.isdisjoint(data["definicion"])


def test_selector_es_exacto_y_case_sensitive(client, db_session):
    parametro_id = _seed_parametro(db_session, "CaseSensitive411")
    _seed_valor(db_session, parametro_id, "15")
    assert client.get(ENDPOINT.format("casesensitive411")).status_code == 404
    assert client.get(ENDPOINT.format(" CaseSensitive411 ")).status_code == 404


def test_definicion_valida_sin_valor_devuelve_sin_valor(client, db_session):
    parametro_id = _seed_parametro(db_session, "TEST_411_SIN_VALOR")
    response = client.get(ENDPOINT.format("TEST_411_SIN_VALOR"))
    assert response.status_code == 200
    _assert_no_store(response)
    data = response.json()["data"]
    assert data["definicion"]["id_parametro_sistema"] == parametro_id
    assert data["estado_valor"] == "SIN_VALOR"
    assert data["valor_marcado_vigente"] is None


def test_inexistente_no_exponible_y_sensible_son_404_indistinguibles(client, db_session):
    _seed_parametro(db_session, "TEST_411_OCULTO", exponible=False, sensible=False)
    _seed_parametro(db_session, "TEST_411_SENSIBLE", exponible=False, sensible=True)
    responses = [
        client.get(ENDPOINT.format("TEST_411_NO_EXISTE")),
        client.get(ENDPOINT.format("TEST_411_OCULTO")),
        client.get(ENDPOINT.format("TEST_411_SENSIBLE")),
    ]
    assert [r.status_code for r in responses] == [404, 404, 404]
    for response in responses:
        _assert_no_store(response)
    bodies = [r.json() for r in responses]
    assert bodies[0] == bodies[1] == bodies[2]
    assert "sensible" not in responses[1].text.lower()
    assert "exponible" not in responses[1].text.lower()


def test_parametro_exponible_no_global_devuelve_409(client, db_session):
    _seed_parametro(db_session, "TEST_411_NO_GLOBAL", alcance="SUCURSAL_411")
    response = client.get(ENDPOINT.format("TEST_411_NO_GLOBAL"))
    assert response.status_code == 409
    _assert_no_store(response)
    assert response.json()["error_code"] == "conflicto_parametro"


def test_no_selecciona_contextuales_eliminados_ni_no_vigentes(client, db_session):
    parametro_id = _seed_parametro(db_session, "TEST_411_FILTROS")
    db_session.execute(text("ALTER TABLE valor_parametro DISABLE TRIGGER trg_biu_valor_parametro_validar_alcance"))
    try:
        _seed_valor(db_session, parametro_id, "16", id_sucursal=1)
        _seed_valor(db_session, parametro_id, "17", id_instalacion=1)
    finally:
        db_session.execute(text("ALTER TABLE valor_parametro ENABLE TRIGGER trg_biu_valor_parametro_validar_alcance"))
    _seed_valor(db_session, parametro_id, "18", deleted_at=datetime.now())
    _seed_valor(db_session, parametro_id, "19", es_valor_vigente=False)
    response = client.get(ENDPOINT.format("TEST_411_FILTROS"))
    assert response.status_code == 200
    _assert_no_store(response)
    assert response.json()["data"]["estado_valor"] == "SIN_VALOR"


def test_no_evalua_fechas_para_seleccionar_valor(client, db_session):
    parametro_id = _seed_parametro(db_session, "TEST_411_FECHAS")
    _seed_valor(db_session, parametro_id, "20", fecha_desde=datetime.now() + timedelta(days=30), fecha_hasta=datetime.now() + timedelta(days=60))
    response = client.get(ENDPOINT.format("TEST_411_FECHAS"))
    assert response.status_code == 200
    _assert_no_store(response)
    assert response.json()["data"]["valor_marcado_vigente"]["valor_tipado"] == 20


def test_entero_invalido_devuelve_500_sanitizado(client, db_session):
    parametro_id = _seed_parametro(db_session, "TEST_411_INVALIDO")
    _seed_valor(db_session, parametro_id, "15.0")
    response = client.get(ENDPOINT.format("TEST_411_INVALIDO"))
    _assert_inconsistencia_sanitizada(response, "15.0")


def test_cardinalidad_mayor_que_uno_devuelve_500_sanitizado(client, monkeypatch):
    def duplicate(_self, _codigo):
        base = {
            "id_parametro_sistema": 1, "codigo_parametro": "TEST", "nombre_parametro": "Test", "descripcion": None,
            "exponible_api_administrativa": True, "es_sensible": False,
            "id_tipo_dato_parametro": 1, "codigo_tipo_dato": "ENTERO", "nombre_tipo_dato": "Entero", "descripcion_tipo_dato": None,
            "id_alcance_parametro": 1, "codigo_alcance": "GLOBAL", "nombre_alcance": "Global", "descripcion_alcance": None,
            "uid_global": "00000000-0000-0000-0000-000000000000", "valor_raw": "1", "version_registro": 1,
            "es_valor_vigente": True, "fecha_desde": None, "fecha_hasta": None,
            "valor_created_at": datetime.now(), "valor_updated_at": datetime.now(),
        }
        return [dict(base, id_valor_parametro=1), dict(base, id_valor_parametro=2)]
    monkeypatch.setattr(ParametroSistemaRepository, "get_definicion_con_valor_global_marcado_vigente", duplicate)
    response = client.get(ENDPOINT.format("TEST"))
    _assert_inconsistencia_sanitizada(response)


def test_entero_ascii_estricto_acepta_positivo_cero_y_negativo(client, db_session):
    casos = [("TEST_411_INT_POS", "15", 15), ("TEST_411_INT_ZERO", "0", 0), ("TEST_411_INT_NEG", "-15", -15)]
    for codigo, raw, tipado in casos:
        parametro_id = _seed_parametro(db_session, codigo)
        _seed_valor(db_session, parametro_id, raw)
        response = client.get(ENDPOINT.format(codigo))
        assert response.status_code == 200
        _assert_no_store(response)
        valor = response.json()["data"]["valor_marcado_vigente"]
        assert valor["valor_raw"] == raw
        assert valor["valor_tipado"] == tipado


def test_entero_ascii_estricto_rechaza_representaciones_invalidas(client, db_session):
    casos = ["+15", " 15", "15 ", "15.0", "1e3", "-", "--15", "١٥"]
    for index, raw in enumerate(casos):
        codigo = f"TEST_411_INT_INVALIDO_{index}"
        parametro_id = _seed_parametro(db_session, codigo)
        _seed_valor(db_session, parametro_id, raw)
        response = client.get(ENDPOINT.format(codigo))
        _assert_inconsistencia_sanitizada(response, raw)


def test_tipo_no_entero_sin_valor_devuelve_500_no_sin_valor(client, db_session):
    _seed_parametro(db_session, "TEST_411_TIPO_TEXTO_SIN_VALOR", tipo="TEXTO_411")
    response = client.get(ENDPOINT.format("TEST_411_TIPO_TEXTO_SIN_VALOR"))
    _assert_inconsistencia_sanitizada(response, "TEXTO_411")


def test_tipo_no_entero_con_valor_devuelve_500_sanitizado(client, db_session):
    parametro_id = _seed_parametro(db_session, "TEST_411_TIPO_TEXTO_CON_VALOR", tipo="TEXTO_VALOR_411")
    _seed_valor(db_session, parametro_id, "15")
    response = client.get(ENDPOINT.format("TEST_411_TIPO_TEXTO_CON_VALOR"))
    _assert_inconsistencia_sanitizada(response, "TEXTO_VALOR_411", "15")


def _seed_parametro_con_referencia_degradada(db_session, codigo, *, tipo_id, alcance_id):
    db_session.execute(text("ALTER TABLE parametro_sistema DISABLE TRIGGER ALL"))
    try:
        return db_session.execute(text("""
            INSERT INTO parametro_sistema (
                id_tipo_dato_parametro, id_alcance_parametro, codigo_parametro,
                nombre_parametro, descripcion, exponible_api_administrativa, es_sensible
            ) VALUES (:tipo_id, :alcance_id, :codigo, :nombre, NULL, true, false)
            RETURNING id_parametro_sistema
        """), {
            "tipo_id": tipo_id,
            "alcance_id": alcance_id,
            "codigo": codigo,
            "nombre": f"Nombre {codigo}",
        }).scalar_one()
    finally:
        db_session.execute(text("ALTER TABLE parametro_sistema ENABLE TRIGGER ALL"))


def test_tipo_referenciado_ausente_devuelve_500_no_404(client, db_session):
    alcance_id = _seed_alcance(db_session)
    _seed_parametro_con_referencia_degradada(
        db_session, "TEST_411_TIPO_AUSENTE", tipo_id=987654321, alcance_id=alcance_id
    )
    response = client.get(ENDPOINT.format("TEST_411_TIPO_AUSENTE"))
    _assert_inconsistencia_sanitizada(response)


def test_alcance_referenciado_ausente_devuelve_500_no_404(client, db_session):
    tipo_id = _seed_tipo(db_session)
    _seed_parametro_con_referencia_degradada(
        db_session, "TEST_411_ALCANCE_AUSENTE", tipo_id=tipo_id, alcance_id=987654322
    )
    response = client.get(ENDPOINT.format("TEST_411_ALCANCE_AUSENTE"))
    _assert_inconsistencia_sanitizada(response)


def test_error_tecnico_inesperado_lleva_no_store(client, monkeypatch):
    def fail(_self, _codigo):
        raise RuntimeError("driver SQL interno")

    monkeypatch.setattr(
        ParametroSistemaRepository,
        "get_definicion_con_valor_global_marcado_vigente",
        fail,
    )
    response = client.get(ENDPOINT.format("TEST_411_TECNICO"))
    assert response.status_code == 500
    assert response.json()["error_code"] == "TECHNICAL_INCONSISTENCY"
    _assert_no_store(response)
    assert "driver" not in response.text.lower()
    assert "sql" not in response.text.lower()
