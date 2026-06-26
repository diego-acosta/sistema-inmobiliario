from __future__ import annotations

from typing import Any

import flet as ft

from app.api_client import ApiResult
from app.pages.parte_detail_page import ParteDetailPage
from app.pages.partes_list_page import PartesListPage


class FakeApi:
    def __init__(
        self,
        *,
        personas: ApiResult | None = None,
        detalle: ApiResult | None = None,
        estado_cuenta: ApiResult | None = None,
    ) -> None:
        self.personas = personas or ApiResult(True, data={"items": [], "total": 0})
        self.detalle = detalle or ApiResult(True, data={})
        self.estado_cuenta = estado_cuenta or ApiResult(
            True,
            data={"resumen": {"saldo_total": 0}, "grupos_deuda": []},
        )
        self.detalle_ids: list[int] = []

    def get_personas(self, **_: Any) -> ApiResult:
        return self.personas

    def get_persona_detalle_integral(self, id_persona: int) -> ApiResult:
        self.detalle_ids.append(id_persona)
        return self.detalle

    def get_estado_cuenta_persona(self, *_: Any, **__: Any) -> ApiResult:
        return self.estado_cuenta


def _walk(control: object):
    yield control
    if isinstance(control, ft.Control):
        for attr in ("controls", "tabs", "rows", "cells", "columns"):
            for child in getattr(control, attr, None) or []:
                yield from _walk(child)
        for attr in ("content",):
            child = getattr(control, attr, None)
            if child is not None:
                yield from _walk(child)


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    for item in _walk(control):
        value = getattr(item, "value", None) or getattr(item, "text", None)
        if isinstance(value, str):
            values.append(value)
    return values


def _find_text_button(control: ft.Control, text: str) -> ft.TextButton:
    for item in _walk(control):
        if isinstance(item, ft.TextButton) and item.text == text:
            return item
    raise AssertionError(f"No se encontro boton {text!r}")


def test_listado_muestra_abrir_ficha_y_navega_a_parte_detail() -> None:
    navigations: list[tuple[str, dict[str, Any]]] = []
    api = FakeApi(
        personas=ApiResult(
            True,
            data={
                "items": [
                    {
                        "id_persona": 42,
                        "display_name": "Ada Lovelace",
                        "tipo_persona": "FISICA",
                        "estado_persona": "ACTIVA",
                    }
                ],
                "total": 1,
            },
        )
    )

    control = PartesListPage(
        api, on_navigate=lambda route, **kwargs: navigations.append((route, kwargs))
    ).build()

    button = _find_text_button(control, "Abrir ficha")
    assert button.disabled is False
    button.on_click(None)
    assert navigations == [("parte_detail", {"id_persona": 42})]


def test_ficha_renderiza_datos_reales_y_secciones_vacias_sin_crudos() -> None:
    api = FakeApi(
        detalle=ApiResult(
            True,
            data={
                "display_name": "Ada Lovelace",
                "tipo_persona": "FISICA",
                "estado_persona": "ACTIVA",
                "cuit_cuil": "20-12345678-9",
                "documentos": [],
                "contactos": [],
                "domicilios": [],
                "participaciones": [],
                "obligaciones_financieras": [],
                "usos_transversales": {},
            },
        )
    )

    control = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_: None).build()
    text = "\n".join(_texts(control))

    assert api.detalle_ids == [42]
    assert "Ada Lovelace" in text
    assert "20-12345678-9" in text
    assert "Sin documentos registrados." in text
    assert "Sin contactos registrados." in text
    assert "Sin domicilios registrados." in text
    assert "Sin roles ni participaciones." in text
    assert "{'" not in text
    assert "[" not in text
    assert "Cliente" not in text


def test_ficha_muestra_error_de_carga_amigable() -> None:
    api = FakeApi(detalle=ApiResult(False, error_message="No se pudo cargar la ficha."))

    control = ParteDetailPage(api, id_persona=99, on_navigate=lambda *_: None).build()
    text = "\n".join(_texts(control))

    assert "Volver al listado" in text
    assert "No se pudo cargar la ficha." in text
    assert "{'" not in text
