from sqlalchemy import text


CATALOGO_URL = "/api/v1/financiero/indices"
VALOR_URL = "/api/v1/financiero/indices/valor-aplicable"


def _crear_indice(db_session, codigo: str, *, estado: str = "ACTIVO", deleted: bool = False) -> int:
    return db_session.execute(text("""
        INSERT INTO indice_financiero (
            codigo_indice_financiero, nombre_indice_financiero, tipo_indice,
            unidad_medida, frecuencia_publicacion, estado_indice_financiero, deleted_at
        ) VALUES (:codigo, :nombre, 'IPC', 'PUNTOS', 'MENSUAL', :estado, :deleted_at)
        RETURNING id_indice_financiero
    """), {"codigo": codigo, "nombre": f"Índice {codigo}", "estado": estado,
            "deleted_at": "2099-01-01" if deleted else None}).scalar_one()


def _crear_valor(db_session, indice: int, fecha: str, *, estado: str = "PUBLICADO", publicado: str | None = "DEFAULT") -> int:
    return db_session.execute(text("""
        INSERT INTO indice_financiero_valor (
            id_indice_financiero, fecha_valor, valor_indice, fecha_publicacion,
            fuente_valor, estado_valor_indice
        ) VALUES (:indice, :fecha, 101.25000000, :publicado, 'INDEC', :estado)
        RETURNING id_indice_financiero_valor
    """), {"indice": indice, "fecha": fecha, "publicado": fecha if publicado == "DEFAULT" else publicado,
            "estado": estado}).scalar_one()


def test_catalogo_lista_activos_ordenados_y_paginados(client, db_session) -> None:
    _crear_indice(db_session, "ZZ_API")
    _crear_indice(db_session, "AA_API")
    _crear_indice(db_session, "INACTIVO_API", estado="INACTIVO")
    _crear_indice(db_session, "BORRADO_API", deleted=True)

    response = client.get(CATALOGO_URL, params={"limit": 1, "offset": 0})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 2
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert set(item) == {"id_indice_financiero", "codigo_indice_financiero", "nombre_indice_financiero", "unidad_medida", "frecuencia_publicacion", "estado_indice_financiero"}
    assert item["estado_indice_financiero"] == "ACTIVO"

    all_items = client.get(CATALOGO_URL, params={"limit": 200}).json()["data"]["items"]
    codes = [item["codigo_indice_financiero"] for item in all_items]
    assert codes == sorted(codes)
    assert "INACTIVO_API" not in codes
    assert "BORRADO_API" not in codes


def test_valor_aplicable_resuelve_por_id_codigo_y_sin_valor(client, db_session) -> None:
    indice = _crear_indice(db_session, "CAC_API")
    _crear_valor(db_session, indice, "2026-01-01")
    futuro = _crear_valor(db_session, indice, "2026-02-01")

    by_id = client.get(VALOR_URL, params={"id_indice_financiero": indice, "fecha_objetivo": "2026-01-15"})
    assert by_id.status_code == 200
    data = by_id.json()["data"]
    assert data["id_indice_financiero"] == indice
    assert data["fecha_valor"] == "2026-01-01"
    assert data["valor_indice"] == "101.25000000"

    by_code = client.get(VALOR_URL, params={"codigo_indice_financiero": " cac_api ", "fecha_objetivo": "2026-01-15"})
    assert by_code.status_code == 200
    assert by_code.json()["data"]["id_indice_financiero"] == indice

    no_value = client.get(VALOR_URL, params={"id_indice_financiero": indice, "fecha_objetivo": "2025-12-01"})
    assert no_value.status_code == 200
    assert no_value.json()["data"] is None
    assert futuro > 0


def test_valor_aplicable_valida_errores_contractuales_y_excluye_no_publicados(client, db_session) -> None:
    indice = _crear_indice(db_session, "VALIDAR_API")
    _crear_valor(db_session, indice, "2026-01-01", estado="BORRADOR")
    _crear_valor(db_session, indice, "2026-01-02", publicado=None)

    for params in ({"fecha_objetivo": "2026-01-15"}, {"id_indice_financiero": indice, "codigo_indice_financiero": "VALIDAR_API", "fecha_objetivo": "2026-01-15"}):
        response = client.get(VALOR_URL, params=params)
        assert response.status_code == 400
        assert response.json()["error_code"] == "IDENTIFICADOR_INDICE_XOR_INVALIDO"

    invalid_date = client.get(VALOR_URL, params={"id_indice_financiero": indice, "fecha_objetivo": "invalid"})
    assert invalid_date.status_code == 400
    assert invalid_date.json()["error_code"] == "FECHA_OBJETIVO_INVALIDA"

    no_published = client.get(VALOR_URL, params={"id_indice_financiero": indice, "fecha_objetivo": "2026-01-15"})
    assert no_published.status_code == 200
    assert no_published.json()["data"] is None
    assert db_session.execute(text("SELECT COUNT(*) FROM outbox_event")).scalar_one() == 0

    inactive = _crear_indice(db_session, "INACTIVO_VALOR_API", estado="INACTIVO")
    response = client.get(VALOR_URL, params={"id_indice_financiero": inactive, "fecha_objetivo": "2026-01-15"})
    assert response.status_code == 404
    assert response.json()["error_code"] == "INDICE_FINANCIERO_INACTIVO"
