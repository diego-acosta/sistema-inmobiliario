from __future__ import annotations

from copy import deepcopy
from typing import Any

import flet as ft

from app.api_client import ApiClient, ApiResult
from app.components.loading_state import DeferredLoadingContainer
from app.pages.ventas_page import (
    VentaDetailView,
    _estado_pago_label,
    _obligacion_indexacion_label,
    _plan_pago_v2_integral_view,
    _porcentaje_ajuste_presentacion,
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


def _find_control_by_data(
    control: object,
    data: str,
    control_type: type[ft.Control],
):
    matches = [
        item
        for item in _walk(control)
        if isinstance(item, control_type) and getattr(item, "data", None) == data
    ]
    assert len(matches) == 1
    return matches[0]


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
                        "composiciones": [
                            {
                                "codigo_concepto_financiero": "CAPITAL_VENTA",
                                "importe_componente": "1000",
                                "saldo_componente": "1000",
                                "moneda_componente": "ARS",
                            },
                            {
                                "codigo_concepto_financiero": "AJUSTE_INDEXACION",
                                "importe_componente": "100.1234",
                                "saldo_componente": "100.1234",
                                "moneda_componente": "ARS",
                            },
                        ],
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
                        "composiciones": [
                            {
                                "codigo_concepto_financiero": "CAPITAL_VENTA",
                                "importe_componente": "1000",
                                "saldo_componente": "1000",
                                "moneda_componente": "ARS",
                            }
                        ],
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
                "errores_por_obligacion": [
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


def _three_cuota_plan_data() -> dict[str, Any]:
    """Return a fresh three-obligation fixture spanning three payment blocks."""

    def obligation(
        obligation_id: int,
        cuota: int,
        numero: int,
        vencimiento: str,
        composiciones: list[dict[str, str]],
    ) -> dict[str, Any]:
        return {
            "id_obligacion_financiera": obligation_id,
            "numero_obligacion": numero,
            "numero_cuota_asociada": cuota,
            "tipo_item_cronograma": "CUOTA",
            "fecha_vencimiento": vencimiento,
            "capital_original": "1000",
            "ajuste_indexacion": "100" if obligation_id == 103 else "0",
            "importe_vigente": "1100" if obligation_id == 103 else "1000",
            "saldo_pendiente": "1100" if obligation_id == 103 else "1000",
            "moneda": "ARS",
            "estado_obligacion": "PENDIENTE",
            "estado_indexacion_presentacion": (
                "CON_INDICE_APLICADO"
                if obligation_id == 103
                else "PROYECTADA_SIN_INDICE"
            ),
            "origen_indexacion": "AL_NACIMIENTO" if obligation_id == 103 else None,
            "indexacion": None,
            "composiciones": composiciones,
            "corrida_relacionada": None,
            "corrida_aplicada_vigente": None,
        }

    data = {
        "id_venta": 371,
        "plan_pago_venta": {
            "id_plan_pago_venta": 20,
            "metodo_plan_pago": "PLAN_POR_BLOQUES",
            "estado_plan_pago": "GENERADO",
            "moneda": "ARS",
        },
        "resumen": {
            "cantidad_bloques": 3,
            "cantidad_obligaciones": 3,
            "total_capital": "3000",
            "total_interes": "0",
            "total_ajuste_indexacion": "100",
            "total_obligaciones": "3100",
            "cantidad_obligaciones_con_indexacion": 1,
            "cantidad_obligados_total": 3,
            "cantidad_obligaciones_con_multiples_obligados": 0,
            "cantidad_obligaciones_proyectadas_sin_indexacion": 2,
        },
        "bloques": [
            {
                "numero_bloque": 1,
                "etiqueta_bloque": "Tramo 1",
                "tipo_bloque": "TRAMO_CUOTAS",
                "metodo_liquidacion": "FIJO",
                "importe_total_bloque": "1000",
                "indexacion": None,
                "obligaciones": [
                    obligation(
                        101,
                        7,
                        41,
                        "2026-03-10",
                        [
                            {
                                "codigo_concepto_financiero": "CAPITAL_VENTA",
                                "importe_componente": "1000",
                                "saldo_componente": "1000",
                                "moneda_componente": "ARS",
                            }
                        ],
                    )
                ],
            },
            {
                "numero_bloque": 2,
                "etiqueta_bloque": "Tramo 2",
                "tipo_bloque": "TRAMO_CUOTAS",
                "metodo_liquidacion": "FIJO",
                "importe_total_bloque": "1000",
                "indexacion": None,
                "obligaciones": [
                    obligation(
                        102,
                        8,
                        42,
                        "2027-01-10",
                        [
                            {
                                "codigo_concepto_financiero": "CAPITAL_VENTA",
                                "importe_componente": "1000",
                                "saldo_componente": "1000",
                                "moneda_componente": "ARS",
                            }
                        ],
                    )
                ],
            },
            {
                "numero_bloque": 3,
                "etiqueta_bloque": "Tramo 3",
                "tipo_bloque": "TRAMO_CUOTAS",
                "metodo_liquidacion": "INDEXACION",
                "importe_total_bloque": "1100",
                "indexacion": {
                    "codigo_indice_financiero": "CAC",
                    "fecha_base_indice": "2026-01-01",
                    "valor_base_indice": "2.5",
                },
                "obligaciones": [
                    obligation(
                        103,
                        9,
                        43,
                        "2026-02-10",
                        [
                            {
                                "codigo_concepto_financiero": "CAPITAL_VENTA",
                                "importe_componente": "1000",
                                "saldo_componente": "1000",
                                "moneda_componente": "ARS",
                            },
                            {
                                "codigo_concepto_financiero": "AJUSTE_INDEXACION",
                                "importe_componente": "100",
                                "saldo_componente": "100",
                                "moneda_componente": "ARS",
                            },
                        ],
                    )
                ],
            },
        ],
        "corridas_indexacion": [],
    }
    return deepcopy(data)


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
    assert "Pendiente" in text
    assert "Pendientes" in text
    assert "Aplicadas" in text
    assert "Corridas de indexación" in text
    assert "Historial de corridas" not in text
    technical = _find_control_by_data(control, "tecnico-corrida-11", ft.Container)
    assert technical.visible is False
    technical_text = _texts(technical)
    assert "ID corrida: 11" in technical_text
    assert "ERR_CAB" in technical_text
    assert "Falla controlada" in technical_text
    assert "Fallida" in text
    assert "Fallidas" in text
    assert "Exclusiones" in text
    assert "SIN_INDICE" in text
    assert "No publicado" in text
    assert "Errores" in text
    assert "Errores por obligación" not in text
    assert "VALOR_INVALIDO" in text
    assert "Valor inválido" in text
    assert "Preparar" not in text
    assert "Aplicar" not in text
    assert "Confirmar corrida" not in text


def test_corrida_renderiza_colecciones_compactas_en_detalle() -> None:
    data = _plan_data()
    corrida = data["corridas_indexacion"][0]
    corrida["obligaciones_afectadas"] = [
        {
            "id_obligacion_financiera": 100,
            "estado_elegibilidad": "ELEGIBLE",
            "detalle_controlado": "Aplicada correctamente",
        }
    ]
    corrida_id = corrida["id_corrida_indexacion_financiera"]
    control = _plan_pago_v2_integral_view(ApiResult(True, data=data))
    toggle = _find_control_by_data(
        control, f"toggle-corrida-{corrida_id}", ft.TextButton
    )
    detail = _find_control_by_data(
        control, f"detalle-corrida-{corrida_id}", ft.Container
    )
    assert detail.visible is False
    assert toggle.text == "Ver detalle"
    toggle.on_click(None)  # type: ignore[misc]
    assert detail.visible is True
    assert toggle.text == "Ocultar detalle"
    text = _texts(detail)
    for value in (
        "Resultado",
        "Obligaciones afectadas",
        "Exclusiones",
        "Errores",
        "Aplicada correctamente",
        "SIN_INDICE",
        "No publicado",
        "VALOR_INVALIDO",
        "Valor inválido",
    ):
        assert value in text
    assert "Errores por obligación" not in text
    toggle.on_click(None)  # type: ignore[misc]
    assert detail.visible is False
    assert toggle.text == "Ver detalle"


def test_historial_corridas_inicia_oculto_y_se_abre() -> None:
    control = _plan_pago_v2_integral_view(ApiResult(True, data=_plan_data()))
    history = _find_control_by_data(control, "historial-corridas", ft.Container)
    toggle = _find_control_by_data(control, "toggle-historial-corridas", ft.TextButton)
    assert history.visible is False
    assert toggle.text == toggle.tooltip == "Ver historial"
    toggle.on_click(None)  # type: ignore[misc]
    assert history.visible is True
    assert toggle.text == "Ocultar historial"
    toggle.on_click(None)  # type: ignore[misc]
    assert history.visible is False


def test_seccion_corridas_y_datos_tecnicos_tienen_ids_estables() -> None:
    control = _plan_pago_v2_integral_view(ApiResult(True, data=_plan_data()))
    section = _find_control_by_data(
        control, "seccion-corridas-indexacion", ft.Container
    )
    summary = _find_control_by_data(control, "resumen-corridas", ft.Column)
    technical = _find_control_by_data(control, "tecnico-corrida-10", ft.Container)
    assert "Corridas de indexación" in _texts(section)
    assert "Historial de corridas" not in _texts(section)
    assert "Pendientes" in _texts(summary)
    assert technical.visible is False


def test_codigo_error_tecnico_permanece_oculto_y_es_expandible() -> None:
    control = _plan_pago_v2_integral_view(ApiResult(True, data=_plan_data()))
    summary = _find_control_by_data(control, "resumen-corridas", ft.Column)
    technical = _find_control_by_data(control, "tecnico-corrida-11", ft.Container)
    toggle = _find_control_by_data(control, "toggle-tecnico-corrida-11", ft.TextButton)
    assert "ERR_CAB" not in _texts(summary)
    assert technical.visible is False
    assert "ERR_CAB" in _texts(technical)
    toggle.on_click(None)  # type: ignore[misc]
    assert technical.visible is True
    toggle.on_click(None)  # type: ignore[misc]
    assert technical.visible is False


def test_estado_excepcional_tiene_prioridad_sobre_origen_corrida_posterior() -> None:
    base = {"origen_indexacion": "CORRIDA_POSTERIOR"}
    assert (
        _obligacion_indexacion_label(
            {**base, "estado_indexacion_presentacion": "CON_ERROR"}
        )
        == "Con error"
    )
    assert (
        _obligacion_indexacion_label(
            {**base, "estado_indexacion_presentacion": "EXCLUIDA"}
        )
        == "Excluida"
    )


def test_estado_exitoso_de_corrida_posterior_mantiene_badge_ajustada() -> None:
    assert (
        _obligacion_indexacion_label(
            {
                "estado_indexacion_presentacion": "CON_INDICE_APLICADO",
                "origen_indexacion": "CORRIDA_POSTERIOR",
            }
        )
        == "Ajustada por corrida"
    )


def test_plan_pago_v2_usa_arbol_estatico_sin_expansion_ni_espaciadores_expand() -> None:
    control = _plan_pago_v2_integral_view(ApiResult(True, data=_plan_data()))
    controls = list(_walk(control))
    text = _texts(control)

    assert not any(isinstance(item, ft.ExpansionTile) for item in controls)
    assert not any(
        isinstance(item, ft.Container) and getattr(item, "expand", False)
        for item in controls
    )
    assert "Cuotas" in text
    assert "Total cuota" in text
    assert "Estado obligación" in text
    assert "Estado pago" in text
    assert "Indexación" in text
    assert "Exclusiones" in text
    assert "Errores" in text
    assert "Errores por obligación" not in text
    assert "Datos técnicos" in text


def test_datos_tecnicos_permanecen_en_tarjeta_estatica_accesible() -> None:
    control = _plan_pago_v2_integral_view(ApiResult(True, data=_plan_data()))
    text = _texts(control)

    assert "Datos técnicos" in text
    assert "ID corrida" in text
    assert "Origen técnico" in text


def test_cuota_compacta_muestra_estados_importe_y_composicion_colapsada() -> None:
    control = _plan_pago_v2_integral_view(ApiResult(True, data=_plan_data()))
    text = _texts(control)
    headers = [
        row
        for row in _walk(control)
        if isinstance(row, ft.Row)
        and "N°" in _texts(row)
        and "Vencimiento" in _texts(row)
        and "Total cuota" in _texts(row)
    ]
    assert len(headers) == 1
    assert "Vencimiento" in text
    assert "Total cuota" in text
    assert "Estado obligación" in text
    assert "Estado pago" in text
    assert "Proyectada" in text
    assert "Pendiente" in text
    assert "Proyectada sin índice" in text
    details = _find_control_by_data(control, "composicion-100", ft.Container)
    assert details.visible is False
    assert "CAPITAL_VENTA" in _texts(details)
    assert "AJUSTE_INDEXACION" in _texts(details)


def test_cuota_expande_composicion_localmente_y_vuelve_a_colapsar() -> None:
    control = _plan_pago_v2_integral_view(ApiResult(True, data=_plan_data()))
    button = _find_control_by_data(control, "toggle-composicion-100", ft.IconButton)
    details = _find_control_by_data(control, "composicion-100", ft.Container)
    assert button.icon == ft.Icons.ADD
    assert button.tooltip == "Ver composición"
    assert details.visible is False
    button.on_click(None)  # type: ignore[misc]
    assert button.icon == ft.Icons.REMOVE
    assert button.tooltip == "Ocultar composición"
    assert details.visible is True
    button.on_click(None)  # type: ignore[misc]
    assert button.icon == ft.Icons.ADD
    assert button.tooltip == "Ver composición"
    assert details.visible is False


def test_estado_pago_y_porcentaje_de_ajuste_son_derivados_de_presentacion() -> None:
    assert _estado_pago_label({"estado_obligacion": "CANCELADA"}) == "Pagada"
    assert (
        _estado_pago_label({"estado_obligacion": "PARCIALMENTE_CANCELADA"}) == "Parcial"
    )
    assert _estado_pago_label({"estado_obligacion": "ANULADA"}) == "Anulada"
    assert _estado_pago_label({"estado_obligacion": "REEMPLAZADA"}) == "Reemplazada"
    assert (
        _estado_pago_label({"importe_vigente": "100", "saldo_pendiente": "0"})
        == "Pagada"
    )
    assert (
        _estado_pago_label({"importe_vigente": "100", "saldo_pendiente": "25"})
        == "Parcial"
    )
    assert (
        _estado_pago_label({"importe_vigente": "100", "saldo_pendiente": "100"})
        == "Pendiente"
    )
    assert (
        _porcentaje_ajuste_presentacion(
            {"capital_original": "40000000"},
            {
                "codigo_concepto_financiero": "AJUSTE_INDEXACION",
                "importe_componente": "3152000",
            },
        )
        == "7,88%"
    )
    assert (
        _porcentaje_ajuste_presentacion(
            {"capital_original": "0"},
            {
                "codigo_concepto_financiero": "AJUSTE_INDEXACION",
                "importe_componente": "1",
            },
        )
        == "—"
    )
    assert (
        _porcentaje_ajuste_presentacion(
            {"capital_original": "100"},
            {
                "codigo_concepto_financiero": "CAPITAL_VENTA",
                "importe_componente": "100",
            },
        )
        == "—"
    )


def test_cuotas_aplanadas_tienen_tres_filas_ordenadas_y_no_mutan_datos() -> None:
    data = _three_cuota_plan_data()
    before = deepcopy(data)
    control = _plan_pago_v2_integral_view(ApiResult(True, data=data))
    assert data == before
    headers = [
        row
        for row in _walk(control)
        if isinstance(row, ft.Row)
        and {
            "N°",
            "Vencimiento",
            "Total cuota",
            "Estado obligación",
            "Estado pago",
            "Indexación",
        }.issubset(_texts(row).split("\n"))
    ]
    rows = [
        row
        for row in _walk(control)
        if isinstance(row, ft.Row) and str(row.data or "").startswith("cuota-")
    ]
    assert len(headers) == 1
    assert len(rows) == 3
    assert [row.data for row in rows] == ["cuota-103", "cuota-101", "cuota-102"]
    assert [_texts(row).split("\n")[0] for row in rows] == ["1", "2", "3"]
    assert [
        next(value for value in _texts(row).split("\n") if "/" in value) for row in rows
    ] == ["10/02/2026", "10/03/2026", "10/01/2027"]


def test_cuotas_expandibles_son_independientes() -> None:
    control = _plan_pago_v2_integral_view(
        ApiResult(True, data=_three_cuota_plan_data())
    )
    buttons = {
        item: _find_control_by_data(
            control, f"toggle-composicion-{item}", ft.IconButton
        )
        for item in (101, 102, 103)
    }
    details = {
        item: _find_control_by_data(control, f"composicion-{item}", ft.Container)
        for item in (101, 102, 103)
    }
    assert all(not detail.visible for detail in details.values())
    assert all(
        button.icon == ft.Icons.ADD and button.tooltip == "Ver composición"
        for button in buttons.values()
    )
    buttons[101].on_click(None)  # type: ignore[misc]
    assert (
        details[101].visible and not details[102].visible and not details[103].visible
    )
    assert (
        buttons[101].icon == ft.Icons.REMOVE
        and buttons[101].tooltip == "Ocultar composición"
    )
    buttons[102].on_click(None)  # type: ignore[misc]
    assert details[101].visible and details[102].visible and not details[103].visible
    buttons[101].on_click(None)  # type: ignore[misc]
    assert (
        not details[101].visible and details[102].visible and not details[103].visible
    )
    buttons[103].on_click(None)  # type: ignore[misc]
    assert not details[101].visible and details[102].visible and details[103].visible


def test_cada_toggle_controla_su_detalle_por_id() -> None:
    control = _plan_pago_v2_integral_view(
        ApiResult(True, data=_three_cuota_plan_data())
    )
    details = {
        item: _find_control_by_data(control, f"composicion-{item}", ft.Container)
        for item in (101, 102, 103)
    }
    for obligation_id in (101, 102, 103):
        button = _find_control_by_data(
            control, f"toggle-composicion-{obligation_id}", ft.IconButton
        )
        detail = _find_control_by_data(
            control, f"composicion-{obligation_id}", ft.Container
        )
        before = {item: item_detail.visible for item, item_detail in details.items()}
        button.on_click(None)  # type: ignore[misc]
        assert detail.visible is not before[obligation_id]
        assert all(
            details[item].visible is before[item]
            for item in details
            if item != obligation_id
        )
        button.on_click(None)  # type: ignore[misc]
        assert detail.visible is before[obligation_id]


def test_detalle_expandido_muestra_solo_composiciones() -> None:
    control = _plan_pago_v2_integral_view(
        ApiResult(True, data=_three_cuota_plan_data())
    )
    text = _texts(_find_control_by_data(control, "composicion-103", ft.Container))
    for value in (
        "Composición de la cuota",
        "Concepto",
        "Importe",
        "% ajuste",
        "CAPITAL_VENTA",
        "AJUSTE_INDEXACION",
        "ARS 1.000,00",
        "ARS 100,00",
        "10,00%",
    ):
        assert value in text
    for value in (
        "Configuración del tramo",
        "Referencia original",
        "Método",
        "Índice",
        "Fecha base",
        "Valor base",
        "Número dentro del tramo",
        "Número de obligación",
        "ID obligación",
        "Bloque",
    ):
        assert value not in text


def test_composicion_sin_ajuste_muestra_solo_componentes_reales() -> None:
    text = _texts(
        _find_control_by_data(
            _plan_pago_v2_integral_view(ApiResult(True, data=_three_cuota_plan_data())),
            "composicion-101",
            ft.Container,
        )
    )
    assert "CAPITAL_VENTA" in text and "ARS 1.000,00" in text and "—" in text
    assert "AJUSTE_INDEXACION" not in text


def test_cuota_header_y_filas_comparten_anchos() -> None:
    control = _plan_pago_v2_integral_view(
        ApiResult(True, data=_three_cuota_plan_data())
    )
    header = next(
        row
        for row in _walk(control)
        if isinstance(row, ft.Row) and "N°" in _texts(row) and len(row.controls) == 7
    )
    row = _find_control_by_data(control, "cuota-103", ft.Row)
    assert [cell.width for cell in header.controls] == [
        cell.width for cell in row.controls
    ]


def test_resumen_compacto_expone_solo_metricas_operativas() -> None:
    control = _plan_pago_v2_integral_view(
        ApiResult(True, data=_three_cuota_plan_data())
    )
    text = _texts(_find_control_by_data(control, "plan-pago-v2-resumen", ft.Container))
    for value in (
        "Importe vigente total",
        "Capital total",
        "Ajuste total",
        "Cuotas",
        "Indexadas",
        "Proyectadas sin índice",
    ):
        assert value in text
    for value in (
        "Bloques",
        "Cantidad obligados",
        "Obligaciones múltiples",
        "ID plan",
        "Método",
    ):
        assert value not in text


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


def test_ficha_venta_ordena_secciones_sin_plan_duplicado() -> None:
    api = FakeApi(ApiResult(True, data=_plan_data()))
    control = VentaDetailView(api, lambda *args, **kwargs: None, 371).build()  # type: ignore[arg-type]
    expected = [
        "resumen-venta",
        "objeto-vendido",
        "compradores-venta",
        "plan-pago-v2",
        "origen-venta",
        "detalle-tecnico-venta",
    ]
    sections = [
        item for item in control.controls if getattr(item, "data", None) in expected
    ]
    assert [item.data for item in sections] == expected
    assert all(
        len([item for item in _walk(control) if getattr(item, "data", None) == data])
        == 1
        for data in expected
    )
    assert "Plan de pago / obligaciones" not in _texts(control)
    plan_section = _find_control_by_data(control, "plan-pago-v2", ft.Container)
    assert (
        len(
            [
                item
                for item in _walk(plan_section)
                if isinstance(item, DeferredLoadingContainer)
            ]
        )
        == 1
    )


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
    assert "Corridas de indexación" in text
    assert "Historial de corridas" not in text
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
