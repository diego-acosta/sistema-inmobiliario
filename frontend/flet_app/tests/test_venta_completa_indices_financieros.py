from types import SimpleNamespace
from decimal import Decimal
from datetime import date

from app.api_client import ApiResult
from prototypes.venta_completa_wizard_v3_prototype import (
    CompradorWizardDraft,
    ObjetoVentaWizardDraft,
    TramoCuotasWizardDraft,
    VentaCompletaWizardV3Prototype,
    _format_period,
    _parse_month_year,
    _period_to_canonical_date,
)


class ControlledPage:
    def __init__(self):
        self.overlay = []
        self.workers = []
        self.updates = 0

    def update(self):
        self.updates += 1

    def run_thread(self, callback):
        self.workers.append(callback)

    def run_next(self):
        self.workers.pop(0)()


class FakeIndexApi:
    def __init__(self, catalogs=None, values=None):
        self.catalogs = list(catalogs or [])
        self.values = list(values or [])
        self.catalog_calls = 0
        self.value_calls = []

    def get_indices_financieros(self, **kwargs):
        self.catalog_calls += 1
        result = self.catalogs.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def get_indice_financiero_valor_aplicable(self, **kwargs):
        self.value_calls.append(kwargs)
        result = self.values.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def catalog(items=None):
    return ApiResult(True, data={"items": items if items is not None else [{
        "id_indice_financiero": 7,
        "codigo_indice_financiero": "CAC",
        "nombre_indice_financiero": "Costo de la Construcción",
    }], "total": len(items) if items is not None else 1})


def value(amount="15842.33000000"):
    return ApiResult(True, data={"valor_indice": amount, "fecha_valor": "2026-01-01", "fuente_valor": "INDEC"})


def wizard(api):
    page = ControlledPage()
    instance = VentaCompletaWizardV3Prototype(
        page,
        api=api,
        embedded=True,
    )  # type: ignore[arg-type]
    instance._capital_remaining_for_installments = lambda: Decimal("2000")  # type: ignore[method-assign]
    return instance, page


def set_basic_valid(instance):
    instance.state.tramo_capital_value = "1000.00"
    instance.state.tramo_cantidad_cuotas_value = "10"
    instance.state.tramo_fecha_display = "01/02/2026"


def change(handler, value):
    handler(SimpleNamespace(control=SimpleNamespace(value=value)))


def test_periodo_mensual_parsea_y_convierte_al_primer_dia() -> None:
    assert _parse_month_year("01/2026") == (1, 2026)
    assert _parse_month_year("12/2026") == (12, 2026)
    assert _period_to_canonical_date("01/2026") == "2026-01-01"
    assert _period_to_canonical_date("12/2026") == "2026-12-01"
    assert _format_period("2026-12-01") == "12/2026"


def test_periodo_mensual_rechaza_mes_anio_y_fecha_completa_invalidos() -> None:
    for invalid in ("00/2026", "13/2026", "01/1899", "01/2101", "1/2026", "01/01/2026"):
        assert _parse_month_year(invalid) is None
        assert _period_to_canonical_date(invalid) is None


def test_guardar_recalcula_para_sin_interes_y_se_deshabilita_al_invalidar():
    instance, _ = wizard(FakeIndexApi())
    assert instance.installment_save_button.disabled
    change(instance._on_tramo_capital_change, "1000")
    change(instance._on_tramo_cantidad_change, "10")
    change(instance._on_tramo_fecha_change, "01/02/2026")
    assert not instance.installment_save_button.disabled
    change(instance._on_tramo_capital_change, "invalido")
    assert instance.installment_save_button.disabled


def test_guardar_interes_directo_exige_tasa_valida():
    instance, _ = wizard(FakeIndexApi())
    set_basic_valid(instance)
    instance._select_installment_liquidation_method("INTERES_DIRECTO")
    instance._sync_installment_save_button()
    assert instance.installment_save_button.disabled
    change(instance._on_tramo_tasa_interes_change, "6")
    assert not instance.installment_save_button.disabled
    change(instance._on_tramo_tasa_interes_change, "invalida")
    assert instance.installment_save_button.disabled


def test_catalogo_es_async_loading_visible_y_carga_codigo_nombre():
    api = FakeIndexApi(catalogs=[catalog()])
    instance, page = wizard(api)
    instance._load_indices_catalog()
    assert instance.state.indices_catalogo_loading
    assert api.catalog_calls == 0
    assert len(page.workers) == 1
    page.run_next()
    instance._sync_installment_form_controls()
    assert instance.state.indices_catalogo_loaded
    assert instance.tramo_indice_selector.options[0].text == "CAC — Costo de la Construcción"
    assert "ID índice financiero backend" not in str(instance._build_installment_liquidation_section())


def test_catalogo_error_payload_invalido_y_excepcion_permiten_reintento():
    api = FakeIndexApi(catalogs=[
        ApiResult(False, error_message="sin conexión"),
        ApiResult(True, data={"items": "invalido", "total": 0}),
        RuntimeError("transitorio"),
        catalog(),
    ])
    instance, page = wizard(api)
    for expected_call in range(1, 4):
        instance._load_indices_catalog()
        page.run_next()
        assert not instance.state.indices_catalogo_loaded
        assert not instance.state.indices_catalogo_loading
        assert instance.state.indices_catalogo_error
        assert api.catalog_calls == expected_call
    instance._load_indices_catalog()
    page.run_next()
    assert instance.state.indices_catalogo_loaded
    assert instance.state.indices_catalogo_error is None
    assert api.catalog_calls == 4


def prepare_indexed(instance):
    set_basic_valid(instance)
    instance.state.tramo_metodo_liquidacion = "INDEXACION"
    instance.state.indices_catalogo = catalog().data["items"]
    instance.state.tramo_periodo_base_indice_display = "01/2026"
    instance.state.tramo_fecha_base_indice_iso = "2026-01-01"


def test_valor_async_loading_exito_y_recalculo_guardar():
    api = FakeIndexApi(values=[value()])
    instance, page = wizard(api)
    prepare_indexed(instance)
    change(instance._on_tramo_indice_change, "7")
    assert instance.state.tramo_valor_indice_loading
    assert instance.installment_save_button.disabled
    assert api.value_calls == []
    page.run_next()
    assert api.value_calls == [
        {"fecha_objetivo": "2026-01-01", "id_indice_financiero": 7}
    ]
    assert instance.state.tramo_valor_indice_status == "RESUELTO"
    assert instance.state.tramo_valor_base_indice_value == "15842.33000000"
    assert not instance.installment_save_button.disabled


def test_valor_data_null_y_error_bloquean_guardar():
    api = FakeIndexApi(values=[ApiResult(True, data=None), ApiResult(False, error_message="contrato")])
    instance, page = wizard(api)
    prepare_indexed(instance)
    change(instance._on_tramo_indice_change, "7")
    page.run_next()
    assert instance.state.tramo_valor_indice_status == "SIN_VALOR"
    assert instance.installment_save_button.disabled
    change(instance._on_tramo_fecha_base_indice_change, "02/2026")
    page.run_next()
    assert instance.state.tramo_valor_indice_status == "ERROR"
    assert instance.installment_save_button.disabled


def test_respuesta_obsoleta_no_sobrescribe_seleccion_nueva():
    api = FakeIndexApi(values=[value("100"), value("200")])
    instance, page = wizard(api)
    prepare_indexed(instance)
    change(instance._on_tramo_indice_change, "7")
    first_worker = page.workers.pop(0)
    change(instance._on_tramo_fecha_base_indice_change, "02/2026")
    first_worker()
    assert instance.state.tramo_valor_indice_status == "PENDIENTE"
    assert instance.state.tramo_valor_base_indice_value == ""
    page.run_next()
    assert instance.state.tramo_valor_indice_status == "RESUELTO"
    assert instance.state.tramo_valor_base_indice_value == "200"


def test_limpieza_invalida_worker_pendiente():
    api = FakeIndexApi(values=[value()])
    instance, page = wizard(api)
    prepare_indexed(instance)
    change(instance._on_tramo_indice_change, "7")
    instance._clear_installment_form_state()
    page.run_next()
    assert instance.state.tramo_valor_indice_status == "PENDIENTE"
    assert instance.state.tramo_valor_base_indice_value == ""
    assert instance.installment_save_button.disabled


def test_periodo_visible_y_draft_conserva_fecha_canonica() -> None:
    instance, _ = wizard(FakeIndexApi())
    prepare_indexed(instance)
    instance.state.tramo_id_indice_financiero_value = "7"
    instance.state.tramo_codigo_indice_visual_value = "CAC"
    instance.state.tramo_valor_base_indice_value = "15842.33"
    instance.state.tramo_valor_indice_status = "RESUELTO"
    data = instance._validate_installment_index_fields()
    assert instance.tramo_fecha_base_indice_field.label == "Período base del índice"
    assert instance.tramo_fecha_base_indice_field.hint_text == "MM/AAAA"
    assert instance.tramo_valor_base_indice_field.read_only
    assert data == {
        "id_indice_financiero": "7",
        "codigo_indice_visual": "CAC",
        "fecha_base_indice_iso": "2026-01-01",
        "periodo_base_indice_display": "01/2026",
        "valor_base_indice": "15842.33",
    }


def _confirmation_ready(instance, *, sale_date: str, indexed: bool) -> None:
    instance.state.fecha_venta_iso = sale_date
    instance.state.codigo_venta = "VD-CORTE"
    instance.state.moneda = "ARS"
    instance.state.forma_pago = "FINANCIADO"
    instance.state.objetos = [
        ObjetoVentaWizardDraft("INMUEBLE", 1, None, "Inmueble", "1000.00", persisted=True)
    ]
    instance.state.compradores = [
        CompradorWizardDraft(1, "Comprador", "100.00", "4", persisted=True)
    ]
    instance.state.tramos_cuotas = [
        TramoCuotasWizardDraft(
            importe_total_bloque="1000.00",
            cantidad_cuotas=1,
            fecha_primer_vencimiento_iso="2026-02-01",
            fecha_primer_vencimiento_display="01/02/2026",
            metodo_liquidacion="INDEXACION" if indexed else "SIN_INTERES",
            id_indice_financiero="7" if indexed else None,
            codigo_indice_visual="CAC" if indexed else None,
            fecha_base_indice_iso="2026-01-01" if indexed else None,
            periodo_base_indice_display="01/2026" if indexed else None,
            valor_base_indice="100.00" if indexed else None,
        )
    ]


def test_fecha_corte_solo_se_agrega_a_confirmacion_historica_indexada() -> None:
    fixed_today = date(2026, 7, 28)
    cases = [
        ("2026-07-28", False, False),
        ("2026-07-28", True, False),
        ("2026-01-01", False, False),
        ("2026-01-01", True, True),
    ]
    for sale_date, indexed, expects_cutoff in cases:
        instance, _ = wizard(FakeIndexApi())
        assert not hasattr(instance, "fecha_corte_field")
        instance._current_operational_date = lambda: fixed_today  # type: ignore[method-assign]
        _confirmation_ready(instance, sale_date=sale_date, indexed=indexed)
        preview_before = instance._build_plan_payment_preview_payload()
        payload = instance._build_confirm_sale_direct_payload()
        assert ("fecha_corte" in payload) is expects_cutoff
        if expects_cutoff:
            assert payload["fecha_corte"] == "2026-07-28"
        assert payload["generar_venta"]["fecha_venta"] == f"{sale_date}T00:00:00"
        assert payload["plan_pago_v2"] == preview_before
