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


def test_crear_datos_asociados_persona_envia_headers_core_ef(monkeypatch) -> None:
    calls = []

    def fake_post(self, path, json=None, params=None, headers=None):
        calls.append({"path": path, "json": json, "headers": headers})
        return ApiResult(True, data={})

    monkeypatch.setattr(ApiClient, "_post", fake_post)
    client = ApiClient(base_url="http://testserver")
    op_id = "550e8400-e29b-41d4-a716-446655440000"

    client.crear_persona_documento(
        42, {"tipo_documento": "DNI", "numero_documento": "123"}, op_id=op_id
    )
    client.crear_persona_contacto(
        42, {"tipo_contacto": "EMAIL", "valor_contacto": "a@b.com"}, op_id=op_id
    )
    client.crear_persona_domicilio(
        42, {"tipo_domicilio": "REAL", "direccion": "Calle 1"}, op_id=op_id
    )

    assert [call["path"] for call in calls] == [
        "/api/v1/personas/42/documentos",
        "/api/v1/personas/42/contactos",
        "/api/v1/personas/42/domicilios",
    ]
    for call in calls:
        assert call["headers"] == {
            "X-Op-Id": op_id,
            "X-Usuario-Id": "1",
            "X-Sucursal-Id": "1",
            "X-Instalacion-Id": "1",
        }
        assert "If-Match-Version" not in call["headers"]
