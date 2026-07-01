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
        self.detalle_results = [self.detalle]
        self.update_calls: list[tuple[int, dict[str, Any], int, str | None]] = []
        self.update_result = ApiResult(True, data={"id_persona": 42, "version_registro": 8})
        self.crear_persona_calls: list[dict[str, Any]] = []
        self.registrar_pago_calls: list[dict[str, Any]] = []

    def get_personas(self, **_: Any) -> ApiResult:
        return self.personas

    def get_persona_detalle_integral(self, id_persona: int) -> ApiResult:
        self.detalle_ids.append(id_persona)
        if self.detalle_results:
            result = self.detalle_results.pop(0)
            self.detalle = result
            return result
        return self.detalle

    def get_estado_cuenta_persona(self, *_: Any, **__: Any) -> ApiResult:
        return self.estado_cuenta

    def actualizar_persona(
        self, id_persona: int, payload: dict[str, Any], if_match_version: int, op_id: str | None = None
    ) -> ApiResult:
        self.update_calls.append((id_persona, payload, if_match_version, op_id))
        return self.update_result

    def crear_persona(self, payload: dict[str, Any], op_id: str | None = None) -> ApiResult:
        self.crear_persona_calls.append(payload)
        return ApiResult(True, data={"id_persona": 999})

    def registrar_pago_persona(self, id_persona: int, **kwargs: Any) -> ApiResult:
        self.registrar_pago_calls.append({"id_persona": id_persona, **kwargs})
        return ApiResult(True, data={"monto_aplicado": kwargs.get("monto", 0), "obligaciones_pagadas": []})


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
    assert "Datos principales" in text
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


def test_listado_no_expone_alta_aislada_ni_navega_a_persona_create() -> None:
    navigations: list[tuple[str, dict[str, Any]]] = []
    control = PartesListPage(
        FakeApi(),
        on_navigate=lambda route, **kwargs: navigations.append((route, kwargs)),
    ).build()
    text = "\n".join(_texts(control))

    assert "Nueva parte" not in text
    assert "Crear parte" not in text
    assert all(
        getattr(item, "on_click", None) is None
        or getattr(item, "text", None) not in {"Nueva parte", "Crear parte"}
        for item in _walk(control)
    )
    assert navigations == []


def test_shell_no_renderiza_ruta_operativa_persona_create() -> None:
    from app.router import Route
    from app.shell import AppShell

    shell = AppShell.__new__(AppShell)
    shell.navigate = lambda *_args, **_kwargs: None

    control = AppShell._render_route(shell, Route("persona_create"))
    text = "\n".join(_texts(control))

    assert "Sistema Inmobiliario" in text
    assert "Nueva parte" not in text
    assert "Crear parte" not in text


def _find_field(control: ft.Control, label: str) -> ft.TextField:
    for item in _walk(control):
        if isinstance(item, ft.TextField) and item.label == label:
            return item
    raise AssertionError(f"No se encontro campo {label!r}")


def _find_button(control: ft.Control, text: str):
    for item in _walk(control):
        if getattr(item, "text", None) == text:
            return item
    raise AssertionError(f"No se encontro boton {text!r}")


def test_ficha_permite_editar_datos_basicos_y_recarga_visualmente() -> None:
    initial = ApiResult(
        True,
        data={
            "id_persona": 42,
            "display_name": "Ada Lovelace",
            "tipo_persona": "FISICA",
            "nombre": "Ada",
            "apellido": "Lovelace",
            "razon_social": None,
            "estado_persona": "ACTIVA",
            "fecha_nacimiento": "1815-12-10",
            "observaciones": "Original",
            "version_registro": 7,
            "documentos": [],
            "contactos": [],
            "domicilios": [],
            "participaciones": [],
            "obligaciones_financieras": [],
            "usos_transversales": {},
        },
    )
    refreshed = ApiResult(
        True,
        data={
            **initial.data,
            "display_name": "Augusta Ada Lovelace",
            "nombre": "Augusta Ada",
            "observaciones": "Actualizada",
            "version_registro": 8,
        },
    )
    navigations: list[tuple[str, dict[str, Any]]] = []
    api = FakeApi(detalle=initial)
    api.detalle_results = [initial, refreshed]
    page = ParteDetailPage(
        api,
        id_persona=42,
        on_navigate=lambda route, **kwargs: navigations.append((route, kwargs)),
    )
    control = page.build()

    button = _find_button(control, "Editar datos principales")
    button.on_click(None)
    assert page.edit_panel.visible is True
    assert _find_field(page.edit_panel, "Nombre").value == "Ada"
    assert _find_field(page.edit_panel, "Apellido").value == "Lovelace"
    assert "Documentos" not in "\n".join(_texts(page.edit_panel))
    assert "Contactos" not in "\n".join(_texts(page.edit_panel))
    assert "Domicilios" not in "\n".join(_texts(page.edit_panel))

    _find_field(page.edit_panel, "Nombre").value = "Augusta Ada"
    _find_field(page.edit_panel, "Observaciones").value = "Actualizada"
    _find_button(page.edit_panel, "Guardar").on_click(None)

    assert len(api.update_calls) == 1
    id_persona, payload, if_match_version, op_id = api.update_calls[0]
    assert id_persona == 42
    assert if_match_version == 7
    assert op_id
    assert payload == {
        "tipo_persona": "FISICA",
        "nombre": "Augusta Ada",
        "apellido": "Lovelace",
        "razon_social": None,
        "fecha_nacimiento": "1815-12-10",
        "estado_persona": "ACTIVA",
        "observaciones": "Actualizada",
    }
    assert api.detalle_ids == [42, 42]
    assert page.data["nombre"] == "Augusta Ada"
    assert page.data["version_registro"] == 8
    assert navigations == [("parte_detail", {"id_persona": 42})]
    assert api.crear_persona_calls == []

    page._open_basic_edit()
    assert _find_field(page.edit_panel, "Nombre").value == "Augusta Ada"

def test_cancelar_edicion_no_llama_api_ni_cambia_estado() -> None:
    api = FakeApi(
        detalle=ApiResult(
            True,
            data={
                "id_persona": 42,
                "display_name": "Ada Lovelace",
                "tipo_persona": "FISICA",
                "nombre": "Ada",
                "apellido": "Lovelace",
                "estado_persona": "ACTIVA",
                "version_registro": 7,
                "documentos": [],
                "contactos": [],
                "domicilios": [],
                "participaciones": [],
                "obligaciones_financieras": [],
                "usos_transversales": {},
            },
        )
    )
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_: None)
    control = page.build()
    _find_button(control, "Editar datos principales").on_click(None)
    _find_field(page.edit_panel, "Nombre").value = "Cambio descartado"
    _find_button(page.edit_panel, "Cancelar").on_click(None)

    assert page.edit_panel.visible is False
    assert api.update_calls == []
    assert api.crear_persona_calls == []



def test_guardado_exitoso_con_fallo_de_recarga_muestra_error_y_no_navega() -> None:
    initial = ApiResult(
        True,
        data={
            "id_persona": 42,
            "display_name": "Ada Lovelace",
            "tipo_persona": "FISICA",
            "nombre": "Ada",
            "apellido": "Lovelace",
            "estado_persona": "ACTIVA",
            "version_registro": 7,
            "documentos": [],
            "contactos": [],
            "domicilios": [],
            "participaciones": [],
            "obligaciones_financieras": [],
            "usos_transversales": {},
        },
    )
    api = FakeApi(detalle=initial)
    api.detalle_results = [
        initial,
        ApiResult(False, error_message="No se pudo refrescar"),
    ]
    navigations: list[tuple[str, dict[str, Any]]] = []
    page = ParteDetailPage(
        api,
        id_persona=42,
        on_navigate=lambda route, **kwargs: navigations.append((route, kwargs)),
    )
    control = page.build()

    _find_button(control, "Editar datos principales").on_click(None)
    _find_field(page.edit_panel, "Nombre").value = "Augusta Ada"
    _find_button(page.edit_panel, "Guardar").on_click(None)

    assert api.detalle_ids == [42, 42]
    assert navigations == []
    assert "Los datos se guardaron, pero no se pudo recargar la ficha" in page.edit_message.value


def test_error_concurrencia_y_validacion_muestran_mensaje_claro() -> None:
    api = FakeApi(
        detalle=ApiResult(
            True,
            data={
                "id_persona": 42,
                "display_name": "Ada Lovelace",
                "tipo_persona": "FISICA",
                "nombre": "Ada",
                "apellido": "Lovelace",
                "estado_persona": "ACTIVA",
                "version_registro": 7,
                "documentos": [],
                "contactos": [],
                "domicilios": [],
                "participaciones": [],
                "obligaciones_financieras": [],
                "usos_transversales": {},
            },
        )
    )
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_: None)
    control = page.build()
    api.update_result = ApiResult(False, status_code=409, error_code="CONCURRENCY_ERROR")
    _find_button(control, "Editar datos principales").on_click(None)
    _find_button(page.edit_panel, "Guardar").on_click(None)
    assert "La persona fue modificada por otro usuario" in page.edit_message.value

    api.update_result = ApiResult(False, status_code=422, error_message="nombre requerido")
    _find_button(page.edit_panel, "Guardar").on_click(None)
    assert "nombre requerido" in page.edit_message.value


def test_ficha_redisenada_renderiza_bloques_administrativos_sin_campos_tecnicos_crudos() -> None:
    api = FakeApi(
        detalle=ApiResult(
            True,
            data={
                "id_persona": 42,
                "display_name": "Ada Lovelace",
                "tipo_persona": "FISICA",
                "nombre": "Ada",
                "apellido": "Lovelace",
                "razon_social": None,
                "estado_persona": "ACTIVA",
                "cuit_cuil": "20-12345678-9",
                "fecha_nacimiento": "1815-12-10",
                "observaciones": "Matemática",
                "version_registro": 7,
                "uid_global": "uid-ada",
                "updated_at": "2026-06-01T10:00:00",
                "documentos": [
                    {"tipo_documento": "DNI", "numero_documento": "12345678", "es_principal": True}
                ],
                "contactos": [
                    {
                        "tipo_contacto": "EMAIL",
                        "valor_contacto": "ada@example.com",
                        "es_principal": True,
                        "fecha_desde": "2020-01-01",
                        "fecha_hasta": "2021-01-01",
                    },
                    {"tipo_contacto": "TELEFONO", "valor_contacto": "+54 299 123", "es_principal": False},
                ],
                "domicilios": [
                    {
                        "tipo_domicilio": "REAL",
                        "calle": "San Martín 123",
                        "localidad": "Neuquén",
                        "provincia": "Neuquén",
                        "es_principal": True,
                        "fecha_desde": "2020-01-01",
                        "fecha_hasta": "2021-01-01",
                    }
                ],
                "participaciones": [
                    {
                        "tipo_relacion": "venta",
                        "codigo_rol": "COMPRADOR",
                        "descripcion_origen": "Reserva #15",
                        "lote": "Lote 12",
                        "fecha_desde": "2022-01-01",
                    }
                ],
                "resumen_financiero": {
                    "saldo_pendiente_total": 1500,
                    "cantidad_obligaciones": 2,
                    "fecha_ultimo_pago": "2026-05-20",
                    "mora_calculada": 100,
                },
                "obligaciones_financieras": [],
                "usos_transversales": {},
            },
        )
    )

    control = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_: None).build()
    text = "\n".join(_texts(control))

    assert "Ada Lovelace" in text
    assert "ACTIVA" in text
    assert "FISICA" in text
    assert "12345678" in text
    assert "Datos principales" in text
    assert "Documento de identidad" in text
    assert "CUIT/CUIL/CDI" in text
    assert "20-12345678-9" in text
    assert "Contactos" in text
    assert "Emails" in text
    assert "ada@example.com" in text
    assert "Teléfonos" in text
    assert "+54 299 123" in text
    assert "tipo_contacto" not in text
    assert "fecha_desde" not in text
    assert "fecha_hasta" not in text
    assert "Direcciones" in text
    assert "San Martín 123, Neuquén, Neuquén" in text
    assert "tipo_domicilio" not in text
    assert "Participaciones" in text
    assert "Ventas" in text
    assert "Comprador en Reserva #15 — Lote 12" in text
    assert "Estado financiero" in text
    assert "Estado de cuenta" in text
    assert "Saldo pendiente" in text
    assert "Obligaciones activas" in text
    assert "Último pago" in text
    assert "Mora" in text
    assert text.rfind("Datos técnicos") > text.rfind("Estado financiero")
    assert "id_persona" in text
    assert "version_registro" in text
    assert _find_button(control, "Editar datos principales") is not None
    assert api.crear_persona_calls == []
    assert api.update_calls == []
    assert api.registrar_pago_calls == []


def test_ficha_redisenada_preserva_estado_de_cuenta_y_panel_de_pago(monkeypatch) -> None:
    monkeypatch.setattr(ft.Control, "update", lambda self: None)
    api = FakeApi(
        detalle=ApiResult(
            True,
            data={
                "id_persona": 42,
                "display_name": "Ada Lovelace",
                "tipo_persona": "FISICA",
                "estado_persona": "ACTIVA",
                "version_registro": 7,
                "documentos": [],
                "contactos": [],
                "domicilios": [],
                "participaciones": [],
                "resumen_financiero": {"saldo_pendiente_total": 1000, "cantidad_obligaciones": 1},
                "obligaciones_financieras": [],
                "usos_transversales": {},
            },
        ),
        estado_cuenta=ApiResult(
            True,
            data={
                "resumen": {"saldo_total": 1000},
                "grupos_deuda": [],
                "obligaciones": [
                    {
                        "id_obligacion_financiera": 77,
                        "tipo_origen": "venta",
                        "fecha_vencimiento": "2026-07-10",
                        "estado_obligacion": "PENDIENTE",
                        "saldo_pendiente": 1000,
                        "total_con_mora": 1100,
                        "mora_calculada": 100,
                    }
                ],
            },
        ),
    )

    control = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_: None).build()
    text = "\n".join(_texts(control))

    assert "Estado de cuenta" in text
    assert "Conceptos a pagar" in text
    pagar = _find_button(control, "Pagar")
    pagar.on_click(None)

    updated_text = "\n".join(_texts(control))
    assert "Registrar pago" in updated_text
    assert "Confirmar pago" in updated_text
    assert api.crear_persona_calls == []
    assert api.update_calls == []
    assert api.registrar_pago_calls == []
