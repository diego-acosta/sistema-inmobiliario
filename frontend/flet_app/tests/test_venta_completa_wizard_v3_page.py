from __future__ import annotations

from typing import Any

import flet as ft

from app.api_client import ApiResult
from prototypes.venta_completa_wizard_v3_prototype import VentaCompletaWizardV3Prototype


class FakePage:
    def __init__(self) -> None:
        self.controls: list[Any] = []

    def add(self, control: Any) -> None:
        self.controls.append(control)

    def update(self) -> None:
        return None

    def run_thread(self, callback: Any) -> None:
        callback()


class FakeApi:
    def __init__(self) -> None:
        self.buscar_calls: list[dict[str, Any]] = []
        self.crear_persona_calls: list[dict[str, Any]] = []

    def buscar_personas(self, **kwargs: Any) -> ApiResult:
        self.buscar_calls.append(kwargs)
        return ApiResult(
            True,
            data={
                "items": [
                    {
                        "id_persona": 281,
                        "display_name": "Compradora Contextual",
                        "tipo_persona": "FISICA",
                        "documento_principal": "28128128",
                        "cuit_cuil": "20-28128128-1",
                    }
                ]
            },
        )

    def crear_persona(self, payload: dict[str, Any], **kwargs: Any) -> ApiResult:
        self.crear_persona_calls.append({"payload": payload, **kwargs})
        return ApiResult(True, data={"id_persona": 999})


def _walk(control: object):
    yield control
    if isinstance(control, ft.Control):
        for attr in ("controls", "tabs", "rows", "cells", "columns"):
            for child in getattr(control, attr, None) or []:
                yield from _walk(child)
        child = getattr(control, "content", None)
        if child is not None:
            yield from _walk(child)


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    for item in _walk(control):
        value = getattr(item, "value", None) or getattr(item, "text", None)
        if isinstance(value, str):
            values.append(value)
    return values


def _find_button(control: ft.Control, text: str):
    for item in _walk(control):
        if getattr(item, "text", None) == text:
            return item
    raise AssertionError(f"No se encontro boton {text!r}")


def _wizard() -> tuple[VentaCompletaWizardV3Prototype, FakeApi]:
    api = FakeApi()
    wizard = VentaCompletaWizardV3Prototype(FakePage(), api=api)  # type: ignore[arg-type]
    wizard.state.origen = "DIRECTA"
    wizard.state.pantalla_actual = "COMPRADORES"
    wizard.rol_comprador_catalog_loaded = True
    wizard.rol_comprador_data = {"id_rol_participacion": 4, "codigo_rol": "COMPRADOR"}
    return wizard, api


def test_paso_comprador_renderiza_resolver_parte_sin_alta_aislada() -> None:
    wizard, _ = _wizard()

    control = wizard._build_buyers_step()
    text = "\n".join(_texts(control))

    assert "Comprador" in text
    assert "Sin busqueda realizada" in text
    assert "Nueva parte" not in text
    assert "Crear parte" not in text
    assert "Alta persona" not in text
    assert "persona_create" not in text


def test_seleccion_desde_resolver_parte_guarda_comprador_y_payload_usa_id_persona() -> None:
    wizard, api = _wizard()
    control = wizard._build_buyers_step()
    assert wizard.comprador_selector is not None
    wizard.comprador_selector.search.value = "Compradora"

    _find_button(control, "Buscar").on_click(None)
    _find_button(control, "Seleccionar").on_click(None)

    assert wizard.comprador_seleccionado == {
        "id_persona": 281,
        "display_name": "Compradora Contextual",
        "tipo_persona": "FISICA",
        "documento_principal": "28128128",
        "cuit_cuil": "20-28128128-1",
    }

    wizard._add_selected_buyer(None)

    assert api.buscar_calls == [{"q": "Compradora", "limit": 10, "offset": 0}]
    assert api.crear_persona_calls == []
    assert wizard.state.compradores[0].id_persona == 281
    assert wizard.state.compradores[0].display_name == "Compradora Contextual"
    assert wizard.state.compradores[0].tipo_persona == "FISICA"
    assert wizard.state.compradores[0].documento_principal == "28128128"
    assert wizard.state.compradores[0].cuit_cuil == "20-28128128-1"

    wizard.state.codigo_venta = "VD-281"
    wizard.state.moneda = "USD"
    payload = wizard._build_confirm_sale_direct_payload()

    assert payload["compradores"][0]["id_persona"] == 281


def test_validacion_comprador_requiere_seleccion_y_rechaza_sin_id_persona() -> None:
    wizard, _ = _wizard()

    assert wizard._buyers_validation_error(None) == "Agregá al menos un comprador para continuar."

    wizard._on_comprador_selected(
        {
            "display_name": "Sin ID",
            "tipo_persona": "FISICA",
            "documento_principal": "11111111",
            "cuit_cuil": "20-11111111-1",
        }
    )
    wizard._add_selected_buyer(None)

    assert wizard.state.compradores == []
    assert wizard.comprador_error == "id_persona es obligatorio."


def test_regresion_no_navega_ni_crea_persona() -> None:
    wizard, api = _wizard()
    control = wizard._build_buyers_step()
    text = "\n".join(_texts(control))

    assert "persona_create" not in text
    assert "crear_persona" not in text
    assert api.crear_persona_calls == []
