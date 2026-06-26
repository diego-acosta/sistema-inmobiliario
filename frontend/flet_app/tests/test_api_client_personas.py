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
