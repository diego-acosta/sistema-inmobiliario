from __future__ import annotations

from typing import Any

import flet as ft

from app.api_client import ApiClient, ApiResult
from app.components.loading_state import DeferredLoadingContainer
from app.pages.ventas_page import (
    VentaDetailView,
    _obligacion_indexacion_label,
    _plan_pago_v2_integral_view,
)


def _walk(control: object):
    yield control
    if isinstance(control, ft.Control):
        for attr in ("controls", "tabs", "rows", "cells", "columns"):
            for child in getattr(control, attr, None) or []:
                yield from _walk(child)
        child = getattr(control, "content", None)
        if child is not None:
            yield from _walk(child)


def _texts(control: ft.Control) -> str:
    values: list[str] = []
    for item in _walk(control):
        value = getattr(item, "value", None) or getattr(item, "text", None)
        if isinstance(value, str):
            values.append(value)
    return "\n".join(values)


class FakeApi:
    def __init__(self, plan_result: ApiResult) -> None:
        self.plan_result = plan_result
        self.plan_calls: list[int] = []

    def get_venta_detalle_integral(self, id_venta: int) -> ApiResult:
        return ApiResult(
            True,
            data={
                "id_venta": id_venta,
                "codigo_venta": "V-371",
                "estado_venta": "CONFIRMADA",
                "fecha_venta": "2026-07-01",
                "moneda": "ARS",
                "condiciones_comerciales": {"moneda": "ARS", "monto_total": "1000"},
                "resumen_financiero": {},
                "objetos": [],
                "partes": [],
                "obligaciones_financieras": [],
            },
        )

    def get_plan_pago_venta_v2_integral(self, id_venta: int) -> ApiResult:
        self.plan_calls.append(id_venta)
        return self.plan_result


def _plan_data() -> dict[str, Any]:
    corrida_rel = {
        "id_corrida_indexacion_financiera": 10,
        "estado_corrida": "PENDIENTE_APLICACION",
        "origen_corrida": "PUBLICACION_INDICE",
        "estado_elegibilidad": "ELEGIBLE",
        "codigo_error": None,
    }
    corrida_aplicada = {
        "id_corrida_indexacion_financiera": 9,
        "estado_corrida": "APLICADA",
        "origen_corrida": "CORRIDA_POSTERIOR",
        "estado_elegibilidad": "ELEGIBLE",
        "codigo_error": None,
    }
    return {
        "id_venta": 371,
        "plan_pago_venta": {
            "id_plan_pago_venta": 20,
            "metodo_plan_pago": "PLAN_POR_BLOQUES",
            "estado_plan_pago": "GENERADO",
            "moneda": "ARS",
        },
        "resumen": {
            "cantidad_bloques": 1,
            "cantidad_obligaciones": 2,
            "total_capital": "1000.00",
            "total_interes": "0",
            "total_ajuste_indexacion": "100.1234",
            "total_obligaciones": "1100.1234",
            "cantidad_obligaciones_con_indexacion": 1,
            "cantidad_obligados_total": 2,
            "cantidad_obligaciones_con_multiples_obligados": 1,
            "cantidad_obligaciones_proyectadas_sin_indexacion": 1,
        },
        "bloques": [
            {
                "numero_bloque": 1,
                "etiqueta_bloque": "Indexado",
                "tipo_bloque": "TRAMO_CUOTAS",
                "metodo_liquidacion": "INDEXACION",
                "importe_total_bloque": "1100.1234",
                "indexacion": {
                    "codigo_indice_financiero": "CAC",
                    "nombre_indice_financiero": "CAC",
                    "fecha_base_indice": "2026-01-01",
                    "valor_base_indice": "2.5",
                },
                "obligaciones": [
                    {
                        "id_obligacion_financiera": 100,
                        "numero_obligacion": 1,
                        "numero_cuota_asociada": 1,
                        "tipo_item_cronograma": "CUOTA",
                        "fecha_vencimiento": "2026-02-10",
                        "capital_original": "1000",
                        "ajuste_indexacion": "100.1234",
                        "importe_vigente": "1100.1234",
                        "saldo_pendiente": "1100.1234",
                        "moneda": "ARS",
                        "estado_obligacion": "PENDIENTE",
                        "estado_indexacion_presentacion": "CON_INDICE_APLICADO",
                        "origen_indexacion": "AL_NACIMIENTO",
                        "indexacion": {
                            "id_indice_financiero": 1,
                            "fecha_base_indice": "2026-01-01",
                            "valor_base_indice": "2.5",
                            "fecha_aplicacion_indice": "2026-02-01",
                            "valor_aplicado_indice": "2.75000000",
                            "coeficiente_indexacion": "1.10000000",
                            "modo_indexacion": "POR_COEFICIENTE",
                        },
                        "corrida_relacionada": corrida_rel,
                        "corrida_aplicada_vigente": corrida_aplicada,
                    },
                    {
                        "id_obligacion_financiera": 101,
                        "numero_obligacion": 2,
                        "tipo_item_cronograma": "CUOTA",
                        "fecha_vencimiento": "2026-03-10",
                        "capital_original": "1000",
                        "ajuste_indexacion": "0",
                        "importe_vigente": "1000",
                        "saldo_pendiente": "1000",
                        "moneda": "ARS",
                        "estado_obligacion": "PENDIENTE",
                        "estado_indexacion_presentacion": "PROYECTADA_SIN_INDICE",
                        "origen_indexacion": None,
                        "indexacion": None,
                        "corrida_relacionada": None,
                        "corrida_aplicada_vigente": None,
                    },
                ],
            }
        ],
        "corridas_indexacion": [
            {
                "id_corrida_indexacion_financiera": 10,
                "estado_corrida": "PENDIENTE_APLICACION",
                "origen_corrida": "PUBLICACION_INDICE",
                "codigo_indice_financiero": "CAC",
                "periodo_aplicado": "2026-02-01",
                "fecha_corte": "2026-02-28",
                "fecha_preparacion": "2026-03-01T10:00:00",
                "fecha_aplicacion": None,
                "cantidad_analizada": 2,
                "cantidad_elegible": 1,
                "cantidad_excluida": 1,
                "cantidad_aplicada": 0,
                "cantidad_error": 1,
                "codigo_error": None,
                "etapa_error": None,
                "diagnostico_tecnico": None,
                "capital_analizado_total": "2000",
                "ajuste_total": "100",
                "importe_total": "2100",
                "exclusiones": [
                    {
                        "id_corrida_indexacion_financiera": 10,
                        "id_obligacion_financiera": 101,
                        "estado_elegibilidad": "EXCLUIDA",
                        "motivo_exclusion": "SIN_INDICE",
                        "codigo_error": None,
                        "detalle_controlado": "No publicado",
                    }
                ],
                "errores": [
                    {
                        "id_corrida_indexacion_financiera": 10,
                        "id_obligacion_financiera": 100,
                        "estado_elegibilidad": "ERROR",
                        "motivo_exclusion": None,
                        "codigo_error": "VALOR_INVALIDO",
                        "detalle_controlado": "Valor inválido",
                    }
                ],
                "obligaciones_afectadas": [],
            },
            {
                "id_corrida_indexacion_financiera": 11,
                "estado_corrida": "FALLIDA",
                "origen_corrida": "PUBLICACION_INDICE",
                "codigo_indice_financiero": "CAC",
                "periodo_aplicado": "2026-03-01",
                "fecha_corte": "2026-03-31",
                "fecha_preparacion": "2026-04-01T10:00:00",
                "fecha_aplicacion": None,
                "cantidad_analizada": 0,
                "cantidad_elegible": 0,
                "cantidad_excluida": 0,
                "cantidad_aplicada": 0,
                "cantidad_error": 1,
                "codigo_error": "ERR_CAB",
                "etapa_error": "PREPARACION",
                "diagnostico_tecnico": "Falla controlada",
                "capital_analizado_total": "0",
                "ajuste_total": "0",
                "importe_total": "0",
                "exclusiones": [],
                "errores": [],
                "obligaciones_afectadas": [],
            },
        ],
    }


def test_api_client_get_plan_pago_v2_es_readlike_sin_headers(monkeypatch) -> None:
    captured = {}

    def fake_get(self, path, params=None, *, preserve_envelope=False):
        captured.update(
            {"path": path, "params": params, "preserve_envelope": preserve_envelope}
        )
        return ApiResult(True, data=_plan_data())

    monkeypatch.setattr(ApiClient, "_get", fake_get)
    result = ApiClient(base_url="http://test").get_plan_pago_venta_v2_integral(371)
    assert result.success is True
    assert captured == {
        "path": "/api/v1/ventas/371/plan-pago-v2",
        "params": None,
        "preserve_envelope": False,
    }


def test_plan_pago_v2_not_found_muestra_vacio_amigable() -> None:
    control = _plan_pago_v2_integral_view(
        ApiResult(
            False,
            status_code=404,
            error_code="NOT_FOUND_PLAN_PAGO_V2",
            error_message="HTTP 404",
        )
    )
    text = _texts(control)
    assert "La venta no tiene un Plan Pago V2 materializado" in text
    assert "HTTP 404" not in text


def test_plan_pago_v2_renderiza_corridas_exclusiones_errores_y_sin_write() -> None:
    control = _plan_pago_v2_integral_view(ApiResult(True, data=_plan_data()))
    text = _texts(control)
    assert "Plan Pago V2" not in text  # el título lo agrega la ficha contenedora
    assert "QUERY_READLIKE" in text
    assert "ARS 1.100,12" in text
    assert "Proyectada sin índice" in text
    assert "Indexada al nacimiento" in text
    assert "Al nacimiento" in text
    assert "Pendiente" in text
    assert "Pendientes" in text
    assert "Aplicadas" in text
    assert "Historial de corridas" in text
    assert "\n11\n" in f"\n{text}\n"
    assert "Fallida" in text
    assert "Fallidas" in text
    assert "ERR_CAB" in text
    assert "Falla controlada" in text
    assert "Exclusiones" in text
    assert "SIN_INDICE" in text
    assert "No publicado" in text
    assert "Errores por obligación" in text
    assert "VALOR_INVALIDO" in text
    assert "Valor inválido" in text
    assert "Preparar" not in text
    assert "Aplicar" not in text
    assert "Confirmar corrida" not in text


def test_corrida_renderiza_las_tres_colecciones_en_secciones_separadas() -> None:
    data = _plan_data()
    corrida = data["corridas_indexacion"][0]
    corrida["obligaciones_afectadas"] = [
        {
            "id_obligacion_financiera": 100,
            "estado_elegibilidad": "ELEGIBLE",
            "motivo_exclusion": None,
            "codigo_error": None,
            "detalle_controlado": "Aplicada correctamente",
        }
    ]
    control = _plan_pago_v2_integral_view(ApiResult(True, data=data))

    sections = [
        item
        for item in _walk(control)
        if isinstance(item, ft.Column)
        and item.controls
        and isinstance(item.controls[0], ft.Text)
        and item.controls[0].value
        in {"Obligaciones afectadas", "Exclusiones", "Errores por obligación"}
    ]
    section_texts = {str(section.controls[0].value): _texts(section) for section in sections}

    assert set(section_texts) == {
        "Obligaciones afectadas",
        "Exclusiones",
        "Errores por obligación",
    }
    assert "Aplicada correctamente" in section_texts["Obligaciones afectadas"]
    assert "SIN_INDICE" in section_texts["Exclusiones"]
    assert "No publicado" in section_texts["Exclusiones"]
    assert "VALOR_INVALIDO" in section_texts["Errores por obligación"]
    assert "Valor inválido" in section_texts["Errores por obligación"]


def test_estado_excepcional_tiene_prioridad_sobre_origen_corrida_posterior() -> None:
    base = {"origen_indexacion": "CORRIDA_POSTERIOR"}
    assert _obligacion_indexacion_label(
        {**base, "estado_indexacion_presentacion": "CON_ERROR"}
    ) == "Con error"
    assert _obligacion_indexacion_label(
        {**base, "estado_indexacion_presentacion": "EXCLUIDA"}
    ) == "Excluida"


def test_estado_exitoso_de_corrida_posterior_mantiene_badge_ajustada() -> None:
    assert _obligacion_indexacion_label(
        {
            "estado_indexacion_presentacion": "CON_INDICE_APLICADO",
            "origen_indexacion": "CORRIDA_POSTERIOR",
        }
    ) == "Ajustada por corrida"


class FakeMountedPage:
    def __init__(self) -> None:
        self.updated: list[ft.Control] = []

    def run_thread(self, callback):
        callback()

    def update(self, control):
        self.updated.append(control)


def _find_deferred_loader(control: ft.Control) -> DeferredLoadingContainer:
    for item in _walk(control):
        if isinstance(item, DeferredLoadingContainer):
            return item
    raise AssertionError("No se encontró DeferredLoadingContainer")


def test_ficha_venta_muestra_carga_inicial_y_no_bloquea_detalle_principal() -> None:
    api = FakeApi(ApiResult(True, data=_plan_data()))
    control = VentaDetailView(api, lambda *args, **kwargs: None, 371).build()  # type: ignore[arg-type]
    text = _texts(control)
    assert api.plan_calls == []
    assert "V-371" in text
    assert "Plan Pago V2" in text
    assert "Cargando Plan Pago V2" in text
    assert "Historial de corridas" not in text
    assert "Nueva corrida" not in text


def test_loader_plan_pago_v2_consulta_una_vez_y_reemplaza_por_contenido(
    monkeypatch,
) -> None:
    api = FakeApi(ApiResult(True, data=_plan_data()))
    control = VentaDetailView(api, lambda *args, **kwargs: None, 371).build()  # type: ignore[arg-type]
    loader = _find_deferred_loader(control)

    fake_page = FakeMountedPage()
    monkeypatch.setattr(
        "app.components.loading_state.get_control_page", lambda _: fake_page
    )

    loader.did_mount()
    loader.did_mount()

    text = _texts(loader)
    assert api.plan_calls == [371]
    assert "Historial de corridas" in text
    assert "Pendientes" in text
    assert fake_page.updated


def test_loader_plan_pago_v2_reemplaza_por_vacio_amigable(monkeypatch) -> None:
    api = FakeApi(
        ApiResult(
            False,
            status_code=404,
            error_code="NOT_FOUND_PLAN_PAGO_V2",
            error_message="HTTP 404",
        )
    )
    control = VentaDetailView(api, lambda *args, **kwargs: None, 371).build()  # type: ignore[arg-type]
    loader = _find_deferred_loader(control)
    monkeypatch.setattr(
        "app.components.loading_state.get_control_page", lambda _: FakeMountedPage()
    )

    loader.did_mount()

    text = _texts(loader)
    assert api.plan_calls == [371]
    assert "La venta no tiene un Plan Pago V2 materializado" in text
    assert "HTTP 404" not in text


def test_loader_plan_pago_v2_reemplaza_por_error_controlado(monkeypatch) -> None:
    api = FakeApi(
        ApiResult(
            False,
            status_code=500,
            error_code="INTERNAL_ERROR",
            error_message="HTTP 500 | INTERNAL_ERROR",
        )
    )
    control = VentaDetailView(api, lambda *args, **kwargs: None, 371).build()  # type: ignore[arg-type]
    loader = _find_deferred_loader(control)
    monkeypatch.setattr(
        "app.components.loading_state.get_control_page", lambda _: FakeMountedPage()
    )

    loader.did_mount()

    text = _texts(loader)
    assert api.plan_calls == [371]
    assert "HTTP 500 | INTERNAL_ERROR" in text
    assert "Aplicar" not in text
