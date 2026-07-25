from types import SimpleNamespace

from app.api_client import ApiResult
from prototypes.venta_completa_wizard_v3_prototype import VentaCompletaWizardV3Prototype


class FakePage:
    overlay = []

    def update(self) -> None:
        pass


class FakeIndexApi:
    def __init__(self, *, catalog_error=False, value=None, value_error=False):
        self.catalog_error = catalog_error
        self.value = value
        self.value_error = value_error
        self.value_calls = []

    def get_indices_financieros(self, **kwargs):
        if self.catalog_error:
            return ApiResult(False, error_message="sin conexión")
        return ApiResult(
            True,
            data={
                "items": [
                    {
                        "id_indice_financiero": 7,
                        "codigo_indice_financiero": "CAC",
                        "nombre_indice_financiero": "Costo de la Construcción",
                    }
                ],
                "total": 1,
            },
        )

    def get_indice_financiero_valor_aplicable(self, **kwargs):
        self.value_calls.append(kwargs)
        if self.value_error:
            return ApiResult(False, error_message="contrato inválido", status_code=400)
        return ApiResult(True, data=self.value)


def _wizard(api):
    wizard = VentaCompletaWizardV3Prototype(FakePage(), api=api)  # type: ignore[arg-type]
    wizard.state.tramo_metodo_liquidacion = "INDEXACION"
    return wizard


def test_catalogo_real_muestra_codigo_nombre_y_no_expone_id_tecnico() -> None:
    wizard = _wizard(FakeIndexApi())
    wizard._load_indices_catalog()
    control = wizard._build_installment_liquidation_section()
    wizard._sync_installment_form_controls()

    assert wizard.tramo_indice_selector.options[0].text == "CAC — Costo de la Construcción"
    assert "ID índice financiero backend" not in str(control)
    assert wizard.state.indices_catalogo_error is None


def test_catalogo_vacio_y_error_tienen_estados_diferenciados() -> None:
    empty = _wizard(FakeIndexApi())
    empty.api.get_indices_financieros = lambda **kwargs: ApiResult(True, data={"items": [], "total": 0})
    empty._load_indices_catalog()
    empty._sync_tramo_indice_feedback()
    assert empty.tramo_indice_feedback.value == "No hay índices activos disponibles."

    failed = _wizard(FakeIndexApi(catalog_error=True))
    failed._load_indices_catalog()
    assert "No se pudo cargar" in (failed.state.indices_catalogo_error or "")


def test_seleccion_y_fecha_resuelven_valor_y_guardan_id_interno() -> None:
    api = FakeIndexApi(value={"valor_indice": "15842.33000000", "fecha_valor": "2026-01-01", "fuente_valor": "INDEC"})
    wizard = _wizard(api)
    wizard._load_indices_catalog()
    wizard.state.tramo_fecha_base_indice_display = "15/01/2026"
    wizard.state.tramo_fecha_base_indice_iso = "2026-01-15"
    wizard._on_tramo_indice_change(SimpleNamespace(control=SimpleNamespace(value="7")))

    assert wizard.state.tramo_id_indice_financiero_value == "7"
    assert wizard.state.tramo_codigo_indice_visual_value == "CAC"
    assert wizard.state.tramo_valor_base_indice_value == "15842.33000000"
    assert wizard.state.tramo_valor_indice_status == "RESUELTO"
    assert api.value_calls == [{"fecha_objetivo": "2026-01-15", "id_indice_financiero": 7}]


def test_data_null_error_y_cambios_invalidan_valor_previo() -> None:
    no_value = _wizard(FakeIndexApi(value=None))
    no_value.state.tramo_id_indice_financiero_value = "7"
    no_value.state.tramo_fecha_base_indice_iso = "2026-01-15"
    no_value._resolve_index_value_if_ready()
    assert no_value.state.tramo_valor_indice_status == "SIN_VALOR"
    assert not no_value._can_save_installment_block()

    failed = _wizard(FakeIndexApi(value_error=True))
    failed.state.tramo_id_indice_financiero_value = "7"
    failed.state.tramo_fecha_base_indice_iso = "2026-01-15"
    failed._resolve_index_value_if_ready()
    assert failed.state.tramo_valor_indice_status == "ERROR"
    assert "contrato inválido" in (failed.state.tramo_valor_indice_error or "")

    failed.state.tramo_valor_base_indice_value = "123"
    failed._on_tramo_fecha_base_indice_change(SimpleNamespace(control=SimpleNamespace(value="16/01/2026")))
    assert failed.state.tramo_valor_base_indice_value == ""


def test_tramo_indexado_valido_habilita_guardar_y_draft_conserva_contrato() -> None:
    wizard = _wizard(FakeIndexApi())
    wizard.state.tramo_capital_value = "1000.00"
    wizard.state.tramo_cantidad_cuotas_value = "10"
    wizard.state.tramo_fecha_display = "01/02/2026"
    wizard.state.tramo_id_indice_financiero_value = "7"
    wizard.state.tramo_codigo_indice_visual_value = "CAC"
    wizard.state.tramo_fecha_base_indice_display = "15/01/2026"
    wizard.state.tramo_fecha_base_indice_iso = "2026-01-15"
    wizard.state.tramo_valor_base_indice_value = "15842.33"
    wizard.state.tramo_valor_indice_status = "RESUELTO"
    wizard._capital_remaining_for_installments = lambda: 2000  # type: ignore[method-assign]

    assert wizard._can_save_installment_block()
    data = wizard._validate_installment_index_fields()
    assert data == {
        "id_indice_financiero": "7",
        "codigo_indice_visual": "CAC",
        "fecha_base_indice_iso": "2026-01-15",
        "fecha_base_indice_display": "15/01/2026",
        "valor_base_indice": "15842.33",
    }
