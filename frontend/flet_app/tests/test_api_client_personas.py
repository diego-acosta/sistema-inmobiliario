from __future__ import annotations

from app.api_client import ApiClient, ApiResult


def test_crear_persona_envia_headers_core_ef(monkeypatch) -> None:
    captured = {}

    def fake_post(self, path, json=None, params=None, headers=None):
        captured["path"] = path
        captured["json"] = json
        captured["headers"] = headers
        return ApiResult(True, data={"id_persona": 1})

    monkeypatch.setattr(ApiClient, "_post", fake_post)
    client = ApiClient(base_url="http://testserver")
    payload = {"tipo_persona": "FISICA", "nombre": "Ada"}

    result = client.crear_persona(payload, op_id="550e8400-e29b-41d4-a716-446655440000")

    assert result.success is True
    assert captured["path"] == "/api/v1/personas"
    assert captured["json"] == payload
    assert captured["headers"] == {
        "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
        "X-Usuario-Id": "1",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
    }
    assert "If-Match-Version" not in captured["headers"]


def test_actualizar_persona_envia_headers_core_ef_e_if_match(monkeypatch) -> None:
    captured = {}

    def fake_put(self, path, json=None, params=None, headers=None):
        captured["path"] = path
        captured["json"] = json
        captured["headers"] = headers
        return ApiResult(True, data={"id_persona": 1, "version_registro": 8})

    monkeypatch.setattr(ApiClient, "_put", fake_put)
    client = ApiClient(base_url="http://testserver")
    payload = {
        "tipo_persona": "FISICA",
        "nombre": "Ada",
        "apellido": "Byron",
        "razon_social": None,
        "estado_persona": "ACTIVA",
        "observaciones": "Actualizada",
    }

    result = client.actualizar_persona(
        42,
        payload,
        if_match_version=7,
        op_id="550e8400-e29b-41d4-a716-446655440000",
    )

    assert result.success is True
    assert captured["path"] == "/api/v1/personas/42"
    assert captured["json"] == payload
    assert captured["headers"] == {
        "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
        "X-Usuario-Id": "1",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
        "If-Match-Version": "7",
    }


def test_actualizar_persona_documento_envia_headers_core_ef_e_if_match(monkeypatch) -> None:
    captured = {}

    def fake_put(self, path, json=None, params=None, headers=None):
        captured["path"] = path
        captured["json"] = json
        captured["headers"] = headers
        return ApiResult(True, data={"id_persona_documento": 10, "version_registro": 4})

    monkeypatch.setattr(ApiClient, "_put", fake_put)
    client = ApiClient(base_url="http://testserver")
    payload = {"tipo_documento": "DNI", "numero_documento": "12345678"}

    result = client.actualizar_persona_documento(
        42,
        10,
        payload,
        if_match_version=3,
        op_id="550e8400-e29b-41d4-a716-446655440000",
    )

    assert result.success is True
    assert captured["path"] == "/api/v1/personas/42/documentos/10"
    assert captured["json"] == payload
    assert captured["headers"] == {
        "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
        "X-Usuario-Id": "1",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
        "If-Match-Version": "3",
    }


def test_actualizar_persona_datos_principales_envia_headers_core_ef(monkeypatch) -> None:
    captured = {}

    def fake_put(self, path, json=None, params=None, headers=None):
        captured["path"] = path
        captured["json"] = json
        captured["headers"] = headers
        return ApiResult(True, data={"id_persona": 42, "version_registro": 8})

    monkeypatch.setattr(ApiClient, "_put", fake_put)
    client = ApiClient(base_url="http://testserver")
    payload = {"persona": {"version_registro": 7}, "documento_identidad": None, "identificacion_fiscal": None}

    result = client.actualizar_persona_datos_principales(
        42, payload, op_id="550e8400-e29b-41d4-a716-446655440000"
    )

    assert result.success is True
    assert captured["path"] == "/api/v1/personas/42/datos-principales"
    assert captured["json"] == payload
    assert captured["headers"] == {
        "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
        "X-Usuario-Id": "1",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
    }
