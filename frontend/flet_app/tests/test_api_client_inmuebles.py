from app.api_client import ApiClient, ApiResult


def test_confirmar_importacion_inmuebles_envia_headers_core_ef(monkeypatch) -> None:
    captured = {}

    def fake_post(self, path, json=None, params=None, headers=None):
        captured["path"] = path
        captured["json"] = json
        captured["headers"] = headers
        return ApiResult(True, data={"creados": 1, "items": []})

    monkeypatch.setattr(ApiClient, "_post", fake_post)
    client = ApiClient(base_url="http://test")

    result = client.confirmar_importacion_inmuebles(
        [{"fila": 2, "inmueble": {"codigo_inmueble": "A1"}}],
        op_id="550e8400-e29b-41d4-a716-446655440000",
    )

    assert result.success is True
    assert captured["path"] == "/api/v1/inmuebles/importacion/confirmar"
    assert captured["json"] == {"items": [{"fila": 2, "inmueble": {"codigo_inmueble": "A1"}}]}
    assert captured["headers"] == {
        "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
        "X-Usuario-Id": "1",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
    }
    assert "If-Match-Version" not in captured["headers"]
