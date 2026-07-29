from app.api_client import ApiClient, ApiResult


def test_listado_indices_envia_paginacion_y_conserva_envelope_data(monkeypatch) -> None:
    captured = {}

    def fake_get(self, path, params=None, **kwargs):
        captured.update(path=path, params=params)
        return ApiResult(True, data={"items": [{"id_indice_financiero": 7}], "total": 1})

    monkeypatch.setattr(ApiClient, "_get", fake_get)
    result = ApiClient(base_url="http://test").get_indices_financieros(limit=20, offset=40)

    assert result.success
    assert result.data == {"items": [{"id_indice_financiero": 7}], "total": 1}
    assert captured == {
        "path": "/api/v1/financiero/indices",
        "params": {"limit": 20, "offset": 40},
    }


def test_valor_aplicable_envia_identificador_y_fecha_y_preserva_data_null(monkeypatch) -> None:
    captured = {}

    def fake_get(self, path, params=None, **kwargs):
        captured.update(path=path, params=params)
        return ApiResult(True, data=None, status_code=200)

    monkeypatch.setattr(ApiClient, "_get", fake_get)
    result = ApiClient(base_url="http://test").get_indice_financiero_valor_aplicable(
        fecha_objetivo="2026-01-15", id_indice_financiero=7
    )

    assert result.success and result.data is None
    assert captured["path"] == "/api/v1/financiero/indices/valor-aplicable"
    assert captured["params"] == {
        "fecha_objetivo": "2026-01-15",
        "id_indice_financiero": 7,
        "codigo_indice_financiero": None,
    }


def test_cliente_propaga_error_http_de_indices(monkeypatch) -> None:
    monkeypatch.setattr(
        ApiClient,
        "_get",
        lambda *args, **kwargs: ApiResult(
            False, error_message="HTTP 500 INTERNAL_ERROR", status_code=500
        ),
    )
    result = ApiClient(base_url="http://test").get_indices_financieros()
    assert not result.success
    assert result.status_code == 500

