from __future__ import annotations

from typing import Any

import flet as ft

from app.api_client import ApiResult
from app.components.resolver_parte import ResolverParte


class FakeApi:
    def __init__(self, result: ApiResult) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def buscar_personas(self, **kwargs: Any) -> ApiResult:
        self.calls.append(kwargs)
        return self.result


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


def test_resolver_parte_estado_inicial_no_expone_alta() -> None:
    resolver = ResolverParte(
        FakeApi(ApiResult(True, data={"items": []})), lambda _: None
    )

    control = resolver.build()
    text = "\n".join(_texts(control))

    assert "Sin busqueda realizada" in text
    assert "Nueva parte" not in text
    assert "Crear parte" not in text
    assert "Alta persona" not in text
    assert "persona_create" not in text


def test_resolver_parte_busca_y_selecciona_persona_existente() -> None:
    selected: list[dict[str, Any]] = []
    api = FakeApi(
        ApiResult(
            True,
            data={
                "items": [
                    {
                        "id_persona": 7,
                        "display_name": "Ada Lovelace",
                        "tipo_persona": "FISICA",
                        "documento_principal": "12345678",
                        "cuit_cuil": "20-12345678-9",
                    }
                ]
            },
        )
    )
    resolver = ResolverParte(api, selected.append)
    control = resolver.build()
    resolver.search.value = "Ada"

    _find_button(control, "Buscar").on_click(None)

    assert api.calls == [{"q": "Ada", "limit": 10, "offset": 0}]
    assert "Ada Lovelace" in "\n".join(_texts(control))

    _find_button(control, "Seleccionar").on_click(None)

    assert selected == [
        {
            "id_persona": 7,
            "display_name": "Ada Lovelace",
            "tipo_persona": "FISICA",
            "documento_principal": "12345678",
            "cuit_cuil": "20-12345678-9",
        }
    ]
    assert "Persona seleccionada" in "\n".join(_texts(control))


def test_resolver_parte_normaliza_documento_principal_dict() -> None:
    selected: list[dict[str, Any]] = []
    api = FakeApi(
        ApiResult(
            True,
            data={
                "items": [
                    {
                        "id_persona": 8,
                        "display_name": "Grace Hopper",
                        "tipo_persona": "FISICA",
                        "documento_principal": {
                            "tipo_documento": "DNI",
                            "numero_documento": "12345678",
                        },
                    }
                ]
            },
        )
    )
    resolver = ResolverParte(api, selected.append)
    control = resolver.build()
    resolver.search.value = "Grace"

    _find_button(control, "Buscar").on_click(None)

    text = "\n".join(_texts(control))
    assert "12345678" in text
    assert "numero_documento" not in text
    assert "tipo_documento" not in text

    _find_button(control, "Seleccionar").on_click(None)

    assert selected[0]["documento_principal"] == "12345678"


def test_resolver_parte_muestra_sin_resultados_y_error_api() -> None:
    resolver = ResolverParte(
        FakeApi(ApiResult(True, data={"items": []})), lambda _: None
    )
    control = resolver.build()
    resolver.search.value = "Inexistente"

    _find_button(control, "Buscar").on_click(None)

    assert "Sin resultados" in "\n".join(_texts(control))

    failing = ResolverParte(
        FakeApi(ApiResult(False, error_message="API no disponible")), lambda _: None
    )
    failing_control = failing.build()
    failing.search.value = "Ada"

    _find_button(failing_control, "Buscar").on_click(None)

    assert "API no disponible" in "\n".join(_texts(failing_control))
