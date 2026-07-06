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
        self.datos_principales_calls: list[tuple[int, dict[str, Any], int, str | None]] = []
        self.datos_principales_result = self.update_result
        self.crear_persona_calls: list[dict[str, Any]] = []
        self.registrar_pago_calls: list[dict[str, Any]] = []
        self.crear_contacto_calls: list[tuple[int, dict[str, Any]]] = []
        self.actualizar_contacto_calls: list[tuple[int, int, dict[str, Any], int]] = []
        self.crear_domicilio_calls: list[tuple[int, dict[str, Any]]] = []
        self.actualizar_domicilio_calls: list[tuple[int, int, dict[str, Any], int]] = []
        self.crear_documento_calls: list[tuple[int, dict[str, Any]]] = []
        self.actualizar_documento_calls: list[tuple[int, int, dict[str, Any], int]] = []
        self.crear_documento_result = ApiResult(True, data={"id_persona_documento": 1})
        self.actualizar_documento_result = ApiResult(True, data={"id_persona_documento": 1})

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

    def actualizar_persona_datos_principales(
        self, id_persona: int, payload: dict[str, Any], if_match_version: int, op_id: str | None = None
    ) -> ApiResult:
        self.datos_principales_calls.append((id_persona, payload, if_match_version, op_id))
        return self.update_result

    def crear_persona(self, payload: dict[str, Any], op_id: str | None = None) -> ApiResult:
        self.crear_persona_calls.append(payload)
        return ApiResult(True, data={"id_persona": 999})

    def registrar_pago_persona(self, id_persona: int, **kwargs: Any) -> ApiResult:
        self.registrar_pago_calls.append({"id_persona": id_persona, **kwargs})
        return ApiResult(True, data={"monto_aplicado": kwargs.get("monto", 0), "obligaciones_pagadas": []})

    def crear_persona_contacto(self, id_persona: int, payload: dict[str, Any], op_id: str | None = None) -> ApiResult:
        self.crear_contacto_calls.append((id_persona, payload))
        return ApiResult(True, data={"id_persona_contacto": 1})

    def actualizar_persona_contacto(self, id_persona: int, id_persona_contacto: int, payload: dict[str, Any], if_match_version: int, op_id: str | None = None) -> ApiResult:
        self.actualizar_contacto_calls.append((id_persona, id_persona_contacto, payload, if_match_version))
        return ApiResult(True, data={"id_persona_contacto": id_persona_contacto})

    def crear_persona_domicilio(self, id_persona: int, payload: dict[str, Any], op_id: str | None = None) -> ApiResult:
        self.crear_domicilio_calls.append((id_persona, payload))
        return ApiResult(True, data={"id_persona_domicilio": 1})

    def actualizar_persona_domicilio(self, id_persona: int, id_persona_domicilio: int, payload: dict[str, Any], if_match_version: int, op_id: str | None = None) -> ApiResult:
        self.actualizar_domicilio_calls.append((id_persona, id_persona_domicilio, payload, if_match_version))
        return ApiResult(True, data={"id_persona_domicilio": id_persona_domicilio})

    def crear_persona_documento(self, id_persona: int, payload: dict[str, Any], op_id: str | None = None) -> ApiResult:
        self.crear_documento_calls.append((id_persona, payload))
        return self.crear_documento_result

    def actualizar_persona_documento(self, id_persona: int, id_persona_documento: int, payload: dict[str, Any], if_match_version: int, op_id: str | None = None) -> ApiResult:
        self.actualizar_documento_calls.append((id_persona, id_persona_documento, payload, if_match_version))
        return self.actualizar_documento_result


def _walk(control: object):
    yield control
    if isinstance(control, ft.Control):
        for attr in ("controls", "tabs", "rows", "cells", "columns", "actions"):
            for child in getattr(control, attr, None) or []:
                yield from _walk(child)
        for attr in ("content", "title"):
            child = getattr(control, attr, None)
            if child is not None:
                yield from _walk(child)


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    for item in _walk(control):
        value = getattr(item, "value", None) or getattr(item, "text", None) or getattr(item, "label", None)
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
    assert "Sin teléfonos registrados." in text
    assert "Sin mails registrados." in text
    assert "Sin domicilios registrados." in text
    assert "Sin actividad ni participaciones registradas." in text
    assert "{'" not in text
    assert "[" not in text
    assert "Cliente" not in text


def test_ficha_agrupa_actividad_y_resume_estado_financiero_sin_tabla_tecnica() -> None:
    navigations: list[tuple[str, dict[str, Any]]] = []
    api = FakeApi(
        detalle=ApiResult(
            True,
            data={
                "id_persona": 42,
                "display_name": "Ada Lovelace",
                "tipo_persona": "FISICA",
                "estado_persona": "ACTIVA",
                "documentos": [],
                "contactos": [],
                "domicilios": [],
                "participaciones": [
                    {
                        "tipo_relacion": "venta",
                        "codigo_rol": "comprador",
                        "codigo_venta": "VTA-10",
                        "estado_origen": "activa",
                        "id_venta": 10,
                    },
                    {
                        "tipo_relacion": "reserva_venta",
                        "codigo_rol": "interesado",
                        "descripcion_origen": "Reserva lote 4",
                    },
                    {
                        "tipo_relacion": "contrato_alquiler",
                        "codigo_rol": "garante",
                        "codigo_contrato": "ALQ-7",
                        "id_contrato_alquiler": 7,
                    },
                    {"codigo_rol": "referente"},
                ],
                "usos_transversales": {},
            },
        ),
        estado_cuenta=ApiResult(
            True,
            data={
                "resumen": {
                    "saldo_total": 12500,
                    "obligaciones_activas": 3,
                    "fecha_ultimo_pago": "2026-06-20",
                    "mora": 250,
                    "saldo_vencido": 999,
                },
                "grupos_deuda": [],
            },
        ),
    )

    control = ParteDetailPage(
        api, id_persona=42, on_navigate=lambda route, **kwargs: navigations.append((route, kwargs))
    ).build()
    text = "\n".join(_texts(control))

    assert "Ventas (1)" in text
    assert "Reservas (1)" in text
    assert "Contratos locativos (1)" in text
    assert "Otros roles (1)" in text
    assert "VTA-10" in text
    assert "Reserva lote 4" in text
    assert "Referente" in text
    assert "Saldo pendiente" in text
    assert "$ 12.500,00" in text
    assert "Obligaciones activas" in text
    assert "2026-06-20" in text
    assert "Saldo vencido" not in text
    assert "saldo_vencido" not in text
    assert "Pagar" not in text

    buttons = [item for item in _walk(control) if isinstance(item, ft.TextButton)]
    venta_button = next(button for button in buttons if button.text == "Ver" and button.disabled is False)
    venta_button.on_click(None)
    assert navigations == [("venta_detail", {"id_venta": 10})]
    assert any(button.text == "Sin ruta" and button.disabled for button in buttons)


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

    button = _find_button(control, "Editar datos")
    mounted_card = page.basic_data_card
    button.on_click(None)
    dialog = page.active_dialog
    assert dialog is not None and dialog.open is True
    assert page.basic_data_card is mounted_card
    assert mounted_card.height == 265
    assert _find_field(dialog, "Nombre").value == "Ada"
    assert _find_field(dialog, "Apellido").value == "Lovelace"
    assert _find_button(dialog, "Guardar") is not None
    assert _find_button(dialog, "Cancelar") is not None
    edit_text = "\n".join(_texts(dialog))
    assert "Documento de identidad" in edit_text
    assert "Identificación fiscal" in edit_text
    assert "Documentos" not in edit_text
    assert "Contactos" not in edit_text
    assert "Domicilios" not in edit_text

    _find_field(dialog, "Nombre").value = "Augusta Ada"
    _find_field(dialog, "Observaciones").value = "Actualizada"
    _find_button(dialog, "Guardar").on_click(None)

    assert len(api.datos_principales_calls) == 1
    id_persona, payload, if_match_version, op_id = api.datos_principales_calls[0]
    assert id_persona == 42
    assert if_match_version == 7
    assert op_id
    assert payload["persona"] == {
        "tipo_persona": "FISICA",
        "nombre": "Augusta Ada",
        "apellido": "Lovelace",
        "razon_social": None,
        "fecha_nacimiento": "1815-12-10",
        "estado_persona": "ACTIVA",
        "observaciones": "Actualizada",
        "version_registro": 7,
    }
    assert payload["documento_identidad"] is None
    assert payload["identificacion_fiscal"] is None
    assert api.update_calls == []
    assert api.crear_documento_calls == []
    assert api.actualizar_documento_calls == []
    assert api.detalle_ids == [42, 42]
    assert page.data["nombre"] == "Augusta Ada"
    assert page.data["version_registro"] == 8
    assert navigations == [("parte_detail", {"id_persona": 42})]
    assert api.crear_persona_calls == []

    page._open_basic_edit()
    assert _find_field(page.active_dialog, "Nombre").value == "Augusta Ada"

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
    mounted_card = page.basic_data_card
    _find_button(control, "Editar datos").on_click(None)
    assert page.basic_data_card is mounted_card
    dialog = page.active_dialog
    _find_field(dialog, "Nombre").value = "Cambio descartado"
    _find_button(dialog, "Cancelar").on_click(None)

    assert page.active_dialog is not None and page.active_dialog.open is False
    assert page.basic_data_card is mounted_card
    assert mounted_card.height == 265
    read_text = "\n".join(_texts(mounted_card))
    assert "Editar datos principales" not in read_text
    assert "Editar datos" in read_text
    assert "Guardar" not in read_text
    assert "Cancelar" not in read_text
    assert api.update_calls == []
    assert api.datos_principales_calls == []
    assert api.crear_persona_calls == []
    assert api.crear_documento_calls == []
    assert api.actualizar_documento_calls == []


def test_fallo_documento_tras_guardar_persona_muestra_mensaje_parcial_sin_cerrar_modal() -> None:
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
            "documentos": [
                {
                    "id_persona_documento": 10,
                    "tipo_documento": "DNI",
                    "numero_documento": "12345678",
                    "pais_emision": None,
                    "es_principal": True,
                    "version_registro": 3,
                }
            ],
            "contactos": [],
            "domicilios": [],
            "participaciones": [],
            "obligaciones_financieras": [],
            "usos_transversales": {},
        },
    )
    navigations: list[tuple[str, dict[str, Any]]] = []
    api = FakeApi(detalle=initial)
    api.detalle_results = [initial]
    api.update_result = ApiResult(
        False,
        status_code=500,
        error_message="persona_documento.version_registro stack trace",
    )
    page = ParteDetailPage(
        api,
        id_persona=42,
        on_navigate=lambda route, **kwargs: navigations.append((route, kwargs)),
    )
    control = page.build()

    _find_button(control, "Editar datos").on_click(None)
    dialog = page.active_dialog
    assert dialog is not None
    _find_field(dialog, "Documento de identidad").value = "87654321"
    _find_button(dialog, "Guardar").on_click(None)

    assert len(api.datos_principales_calls) == 1
    assert api.update_calls == []
    assert api.crear_documento_calls == []
    assert api.actualizar_documento_calls == []
    assert api.datos_principales_calls[0][1]["documento_identidad"]["numero_documento"] == "87654321"
    assert api.datos_principales_calls[0][1]["identificacion_fiscal"] is None
    assert page.active_dialog is dialog
    assert dialog.open is True
    assert navigations == []
    assert api.detalle_ids == [42]
    assert page.data["version_registro"] == 7
    message = page.modal_message.value
    assert "persona_documento" not in message
    assert "version_registro" not in message
    assert "stack trace" not in message

    _find_button(dialog, "Guardar").on_click(None)

    assert [call[1]["persona"]["version_registro"] for call in api.datos_principales_calls] == [7, 7]
    assert page.active_dialog is dialog
    assert dialog.open is True
    assert navigations == []



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

    mounted_card = page.basic_data_card
    _find_button(control, "Editar datos").on_click(None)
    assert page.basic_data_card is mounted_card
    dialog = page.active_dialog
    _find_field(dialog, "Nombre").value = "Augusta Ada"
    _find_button(dialog, "Guardar").on_click(None)

    assert api.detalle_ids == [42, 42]
    assert navigations == []
    assert "Los datos se guardaron, pero no se pudo recargar la ficha" in page.modal_message.value


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
    mounted_card = page.basic_data_card
    _find_button(control, "Editar datos").on_click(None)
    assert page.basic_data_card is mounted_card
    dialog = page.active_dialog
    _find_button(dialog, "Guardar").on_click(None)
    assert "Otro usuario modificó estos datos" in page.modal_message.value
    assert "Otro usuario modificó estos datos" in "\n".join(_texts(dialog))

    api.update_result = ApiResult(False, status_code=422, error_message="nombre requerido")
    _find_button(dialog, "Guardar").on_click(None)
    assert "nombre requerido" in page.modal_message.value


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
                        "descripcion_origen": "Venta #15",
                        "id_venta": 15,
                        "estado": "ACTIVA",
                        "fecha_desde": "2022-01-01",
                    },
                    {
                        "tipo_relacion": "reserva_venta",
                        "codigo_rol": "COMPRADOR",
                    },
                    {
                        "tipo_relacion": "contrato_alquiler",
                        "codigo_rol": "LOCATARIO",
                        "id_contrato_alquiler": 3,
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
    assert "Mail" in text
    assert "ada@example.com" in text
    assert "Teléfonos" in text
    assert "+54 299 123" in text
    assert "tipo_contacto" not in text
    assert "fecha_desde" not in text
    assert "fecha_hasta" not in text
    assert "Dirección" in text
    assert "San Martín 123, Neuquén, Neuquén" in text
    assert "tipo_domicilio" not in text
    assert "Participaciones" in text
    assert "Ventas" in text
    assert "Contratos locativos" in text
    assert "Reserva de venta" in text
    assert "Contrato de alquiler" in text
    assert "reserva_venta" not in text
    assert "contrato_alquiler" not in text
    assert "Estado de cuenta resumido" in text
    assert "Sin deuda registrada" in text
    assert "Saldo pendiente" in text
    assert "Obligaciones activas" in text
    assert "Último pago" in text
    assert "Mora" in text
    assert text.rfind("Datos técnicos") > text.rfind("Estado de cuenta resumido")
    assert "ID persona" in text
    assert "Versión" in text
    assert "UID global" in text
    assert "id_persona" not in text
    assert "version_registro" not in text
    assert "uid_global" not in text
    assert _find_button(control, "Editar datos") is not None
    assert api.crear_persona_calls == []
    assert api.update_calls == []
    assert api.registrar_pago_calls == []


def test_datos_principales_muestra_identificacion_fiscal_desde_documentos() -> None:
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
                "documentos": [
                    {
                        "id_persona_documento": 10,
                        "tipo_documento": "DNI",
                        "numero_documento": "12345678",
                        "es_principal": True,
                        "version_registro": 3,
                    },
                    {
                        "id_persona_documento": 11,
                        "tipo_documento": "CUIT",
                        "numero_documento": "20-12345678-9",
                        "es_principal": False,
                        "version_registro": 2,
                    },
                ],
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

    assert "CUIT/CUIL/CDI" in text
    assert "20-12345678-9" in text
    assert "persona_documento" not in text


def test_guardar_identificacion_fiscal_recarga_y_muestra_cuit_actualizado() -> None:
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
            "documentos": [
                {
                    "id_persona_documento": 11,
                    "tipo_documento": "CUIT",
                    "numero_documento": "20-12345678-9",
                    "pais_emision": None,
                    "es_principal": False,
                    "version_registro": 2,
                },
            ],
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
            "version_registro": 8,
            "documentos": [
                {
                    "id_persona_documento": 11,
                    "tipo_documento": "CUIT",
                    "numero_documento": "20-87654321-0",
                    "pais_emision": None,
                    "es_principal": False,
                    "version_registro": 3,
                },
            ],
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

    _find_button(control, "Editar datos").on_click(None)
    dialog = page.active_dialog
    assert dialog is not None
    _find_field(dialog, "Identificación fiscal").value = "20-87654321-0"
    _find_button(dialog, "Guardar").on_click(None)

    assert api.update_calls == []
    assert api.crear_documento_calls == []
    assert api.actualizar_documento_calls == []
    assert api.datos_principales_calls[0][1]["documento_identidad"] is None
    assert api.datos_principales_calls[0][1]["identificacion_fiscal"] == {
        "id_persona_documento": 11,
        "tipo_documento": "CUIT",
        "numero_documento": "20-87654321-0",
        "pais_emision": None,
        "es_principal": False,
        "version_registro": 2,
    }
    assert page.data["documentos"][0]["numero_documento"] == "20-87654321-0"
    assert "20-87654321-0" in "\n".join(_texts(page._datos_base(page.data)))
    assert navigations == [("parte_detail", {"id_persona": 42})]


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

    assert "Estado de cuenta resumido" in text
    assert "Saldo pendiente" in text
    assert "$ 1.000,00" in text
    assert "Pagar" not in text
    assert "Registrar pago" not in text
    assert "Confirmar pago" not in text
    assert api.crear_persona_calls == []
    assert api.update_calls == []
    assert api.registrar_pago_calls == []


def test_ficha_redisenada_usa_grilla_balanceada_para_cards_principales() -> None:
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
                "resumen_financiero": {},
                "obligaciones_financieras": [],
                "usos_transversales": {},
            },
        )
    )

    control = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_: None).build()
    assert isinstance(control, ft.Container)
    assert isinstance(control.content, ft.Column)
    assert control.content.scroll == ft.ScrollMode.AUTO
    rows = [item for item in _walk(control) if isinstance(item, ft.Row)]
    balanced_rows = [row for row in rows if len(getattr(row, "controls", []) or []) == 2]
    root_texts = ["\n".join(_texts(child)) for child in control.content.controls]
    idx_resumen = next(i for i, value in enumerate(root_texts) if "Estado de cuenta resumido" in value)
    idx_tecnicos = next(i for i, value in enumerate(root_texts) if "Datos técnicos" in value)

    assert idx_resumen < idx_tecnicos
    assert getattr(control.content.controls[idx_resumen], "expand", None) is None
    assert getattr(control.content.controls[idx_tecnicos], "expand", None) is None
    assert any([getattr(row.controls[0], "expand", None), getattr(row.controls[1], "expand", None)] == [1, 1] for row in balanced_rows)

    dashboard_cards = [
        item
        for item in _walk(control)
        if isinstance(item, ft.Container) and getattr(item, "height", None)
    ]
    heights = {getattr(item, "height", None) for item in dashboard_cards}
    assert {140, 145, 578}.issubset(heights)

    text = "\n".join(_texts(control))
    assert "Sin teléfonos registrados." in text
    assert "Sin mails registrados." in text
    assert "Sin domicilios registrados." in text
    assert "tipo_contacto" not in text
    assert "tipo_domicilio" not in text


def test_header_no_contiene_editar_y_accion_esta_en_datos_principales() -> None:
    page = ParteDetailPage(
        FakeApi(
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
                    "resumen_financiero": {},
                    "obligaciones_financieras": [],
                    "usos_transversales": {},
                },
            )
        ),
        id_persona=42,
        on_navigate=lambda *_: None,
    )
    control = page.build()
    header = control.content.controls[0]
    main_row = control.content.controls[1]
    left_column = main_row.controls[0]
    datos_card = left_column.controls[0]

    assert "Editar datos principales" not in "\n".join(_texts(header))
    assert "Editar datos" not in "\n".join(_texts(header))
    assert "Editar datos principales" not in "\n".join(_texts(datos_card))
    assert "Editar datos" in "\n".join(_texts(datos_card))

    mounted_card = page.basic_data_card
    _find_button(datos_card, "Editar datos").on_click(None)
    assert page.active_dialog is not None and page.active_dialog.open is True
    assert page.basic_data_card is mounted_card
    assert mounted_card.height == 265
    assert _find_field(page.active_dialog, "Nombre") is not None


def test_direccion_ocupa_columna_izquierda_y_contactos_quedan_debajo() -> None:
    control = ParteDetailPage(FakeApi(), id_persona=42, on_navigate=lambda *_: None).build()
    main_row = control.content.controls[1]
    left_column = main_row.controls[0]
    participaciones = main_row.controls[1]
    datos_card = left_column.controls[0]
    direccion_card = left_column.controls[1]
    contactos_row = left_column.controls[2]

    assert left_column.expand == 3
    assert left_column.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
    assert "Datos principales" in "\n".join(_texts(datos_card))
    assert "Dirección" in "\n".join(_texts(direccion_card))
    assert direccion_card.height == 145
    assert "Teléfonos" in "\n".join(_texts(contactos_row.controls[0]))
    assert "Mail" in "\n".join(_texts(contactos_row.controls[1]))
    assert "Participaciones" in "\n".join(_texts(participaciones))
    assert participaciones.expand == 2

    icon_names = {getattr(item, "name", None) for item in _walk(control) if isinstance(item, ft.Icon)}
    assert ft.Icons.PERSON_OUTLINED in icon_names
    assert ft.Icons.HOME_OUTLINED in icon_names
    assert ft.Icons.PHONE_OUTLINED in icon_names
    assert ft.Icons.MAIL_OUTLINED in icon_names
    assert ft.Icons.ACCOUNT_TREE_OUTLINED in icon_names
    assert ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED in icon_names
    assert ft.Icons.SETTINGS_OUTLINED in icon_names


def test_participaciones_muestran_tablas_por_ventas_y_alquileres_con_accion_ver() -> None:
    navigations: list[tuple[str, dict[str, Any]]] = []
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
                "participaciones": [
                    {"tipo_relacion": "venta", "codigo_rol": "COMPRADOR", "id_venta": 22, "codigo_origen": "V-22"},
                    {"tipo_relacion": "contrato_alquiler", "codigo_rol": "LOCATARIO", "id_contrato_alquiler": 33, "codigo_origen": "C-33"},
                    {"tipo_relacion": "reserva_venta", "codigo_rol": "COMPRADOR", "codigo_origen": "R-1"},
                ],
                "resumen_financiero": {},
                "obligaciones_financieras": [],
                "usos_transversales": {},
            },
        )
    )

    control = ParteDetailPage(
        api,
        id_persona=42,
        on_navigate=lambda route, **kwargs: navigations.append((route, kwargs)),
    ).build()
    text = "\n".join(_texts(control))

    assert "Ventas" in text
    assert "Contratos locativos" in text
    assert "Venta" in text
    assert "Reserva de venta" in text
    assert "Contrato de alquiler" in text
    assert "reserva_venta" not in text
    assert "contrato_alquiler" not in text
    participaciones_card = control.content.controls[1].controls[1]
    participaciones_text = "\n".join(_texts(participaciones_card))
    assert "Venta" in participaciones_text
    assert "V-22" in participaciones_text
    assert "Rol" not in participaciones_text
    assert "COMPRADOR" not in participaciones_text
    assert ft.Icons.SELL_OUTLINED in {getattr(item, "name", None) for item in _walk(participaciones_card) if isinstance(item, ft.Icon)}
    participacion_rows = [
        item
        for item in _walk(participaciones_card)
        if isinstance(item, ft.Container)
        and isinstance(getattr(item, "content", None), ft.Row)
        and any(getattr(child, "text", None) in {"Ver", "Sin ruta"} for child in item.content.controls)
    ]
    assert len(participacion_rows) == 3
    assert all(row.content.controls[-1].text in {"Ver", "Sin ruta"} for row in participacion_rows)

    ver_buttons = [item for item in _walk(control) if getattr(item, "text", None) == "Ver"]
    assert len(ver_buttons) >= 2
    disabled = [item for item in _walk(control) if getattr(item, "text", None) == "Sin ruta"]
    assert disabled and all(getattr(button, "disabled", False) for button in disabled)

    ver_buttons[0].on_click(None)
    ver_buttons[1].on_click(None)
    assert ("venta_detail", {"id_venta": 22}) in navigations
    assert ("contrato_detail", {"id_contrato_alquiler": 33}) in navigations
    assert api.crear_persona_calls == []
    assert api.update_calls == []
    assert api.registrar_pago_calls == []


def test_participaciones_ocultan_secciones_sin_datos_por_tipo() -> None:
    ventas_only = ParteDetailPage(
        FakeApi(
            detalle=ApiResult(
                True,
                data={
                    "display_name": "Ada Lovelace",
                    "estado_persona": "ACTIVA",
                    "participaciones": [{"tipo_relacion": "venta", "codigo_rol": "COMPRADOR", "id_venta": 1}],
                },
            )
        ),
        id_persona=42,
        on_navigate=lambda *_: None,
    ).build()
    ventas_text = "\n".join(_texts(ventas_only))
    assert "Ventas" in ventas_text
    assert "Contratos locativos" not in ventas_text

    alquileres_only = ParteDetailPage(
        FakeApi(
            detalle=ApiResult(
                True,
                data={
                    "display_name": "Ada Lovelace",
                    "estado_persona": "ACTIVA",
                    "participaciones": [{"tipo_relacion": "contrato_alquiler", "codigo_rol": "LOCATARIO", "id_contrato_alquiler": 1}],
                },
            )
        ),
        id_persona=42,
        on_navigate=lambda *_: None,
    ).build()
    alquileres_text = "\n".join(_texts(alquileres_only))
    assert "Contratos locativos" in alquileres_text
    assert "Ventas" not in alquileres_text

    empty = ParteDetailPage(FakeApi(), id_persona=42, on_navigate=lambda *_: None).build()
    assert "Sin actividad ni participaciones registradas." in "\n".join(_texts(empty))


def _detalle_contactos_domicilios() -> dict[str, Any]:
    return {
        "display_name": "Ada Lovelace",
        "estado_persona": "ACTIVA",
        "contactos": [
            {"id_persona_contacto": 10, "tipo_contacto": "TELEFONO", "valor_contacto": "+54 299", "es_principal": True, "observaciones": "Laboral", "version_registro": 3},
            {"id_persona_contacto": 11, "tipo_contacto": "EMAIL", "valor_contacto": "ada@example.com", "es_principal": False, "observaciones": "Personal", "version_registro": 4},
        ],
        "domicilios": [
            {"id_persona_domicilio": 20, "tipo_domicilio": "REAL", "direccion": "San Martín 123", "localidad": "Neuquén", "es_principal": True, "observaciones": "Casa familiar", "version_registro": 5},
        ],
        "participaciones": [],
    }


def test_ficha_contactos_domicilios_muestra_acciones_y_no_escribe_al_renderizar() -> None:
    api = FakeApi(detalle=ApiResult(True, data=_detalle_contactos_domicilios()))
    control = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_args, **_kwargs: None).build()
    text = "\n".join(_texts(control))
    assert "Agregar teléfono" in text
    assert "Agregar mail" in text
    assert "Agregar dirección" in text
    assert "Editar" in text
    assert "Principal · San Martín 123, Neuquén" in text
    assert "Principal · +54 299" in text
    assert "Secundario · ada@example.com" in text
    assert "Principal · San Martín 123, Neuquén · Casa familiar" in text
    assert "Principal · +54 299 · Laboral" in text
    assert "Secundario · ada@example.com · Personal" in text
    assert "tipo_contacto" not in text
    assert "tipo_domicilio" not in text
    assert "fecha_desde" not in text
    assert "fecha_hasta" not in text
    assert api.crear_contacto_calls == []
    assert api.actualizar_contacto_calls == []
    assert api.crear_domicilio_calls == []

    compact_rows = [
        item
        for item in _walk(control)
        if isinstance(item, ft.Container)
        and isinstance(getattr(item, "content", None), ft.Row)
        and any(
            (getattr(child, "value", None) or getattr(child, "text", "")).startswith(
                ("Principal ·", "Secundario ·")
            )
            for child in item.content.controls
        )
        and any(getattr(child, "text", None) == "Editar" for child in item.content.controls)
    ]
    assert len(compact_rows) == 3
    assert all(row.content.controls[-1].text == "Editar" for row in compact_rows)


def test_agregar_contactos_y_domicilio_abre_modal_sin_navegar_y_guarda() -> None:
    navigations: list[tuple[str, dict[str, Any]]] = []
    api = FakeApi(detalle=ApiResult(True, data=_detalle_contactos_domicilios()))
    api.detalle_results = [api.detalle, api.detalle, api.detalle, api.detalle]
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda route, **kwargs: navigations.append((route, kwargs)))
    control = page.build()

    _find_button(control, "Agregar teléfono").on_click(None)
    assert navigations == []
    assert page.active_dialog is not None
    telefono_text = "\n".join(_texts(page.active_dialog))
    assert "Agregar teléfono" in telefono_text
    assert "Teléfono" in telefono_text
    assert "Observaciones" in telefono_text
    assert "Principal" in telefono_text
    assert "Guardar" in telefono_text
    assert "Cancelar" in telefono_text
    _find_button(page.active_dialog, "Guardar").on_click(None)
    assert "Ingresá un teléfono." in "\n".join(_texts(page.active_dialog))
    page.modal_fields["valor_contacto"].value = "+54 11 5555"
    _find_button(page.active_dialog, "Guardar").on_click(None)
    assert api.crear_contacto_calls[-1][1]["tipo_contacto"] == "TELEFONO"
    assert api.detalle_ids.count(42) >= 2
    assert navigations[-1] == ("parte_detail", {"id_persona": 42})

    navigations.clear()
    _find_button(control, "Agregar mail").on_click(None)
    assert navigations == []
    assert page.active_dialog is not None
    mail_text = "\n".join(_texts(page.active_dialog))
    assert "Agregar mail" in mail_text
    assert "Mail" in mail_text
    page.modal_fields["valor_contacto"].value = "invalido"
    _find_button(page.active_dialog, "Guardar").on_click(None)
    assert "Ingresá un mail válido." in "\n".join(_texts(page.active_dialog))
    page.modal_fields["valor_contacto"].value = "nueva@example.com"
    _find_button(page.active_dialog, "Guardar").on_click(None)
    assert api.crear_contacto_calls[-1][1]["tipo_contacto"] == "EMAIL"

    navigations.clear()
    _find_button(control, "Agregar dirección").on_click(None)
    assert navigations == []
    assert page.active_dialog is not None
    direccion_text = "\n".join(_texts(page.active_dialog))
    assert "Agregar dirección" in direccion_text
    assert "Calle / dirección" in direccion_text
    assert "Localidad" in direccion_text
    _find_button(page.active_dialog, "Guardar").on_click(None)
    assert "Ingresá al menos calle/dirección o localidad." in "\n".join(_texts(page.active_dialog))
    page.modal_fields["direccion"].value = "Belgrano 456"
    _find_button(page.active_dialog, "Guardar").on_click(None)
    assert api.crear_domicilio_calls[-1][1]["direccion"] == "Belgrano 456"


def test_cancelar_modal_cierra_sin_api_ni_navegacion() -> None:
    navigations: list[tuple[str, dict[str, Any]]] = []
    api = FakeApi(detalle=ApiResult(True, data=_detalle_contactos_domicilios()))
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda route, **kwargs: navigations.append((route, kwargs)))
    control = page.build()

    before = len(api.crear_contacto_calls) + len(api.crear_domicilio_calls)
    _find_button(control, "Agregar teléfono").on_click(None)
    assert page.active_dialog is not None
    _find_button(page.active_dialog, "Cancelar").on_click(None)
    after = len(api.crear_contacto_calls) + len(api.crear_domicilio_calls)
    assert after == before
    assert page.active_modal_kind is None
    assert navigations == []


def test_editar_contactos_y_domicilio_abre_modal_precarga_y_guarda_version() -> None:
    navigations: list[tuple[str, dict[str, Any]]] = []
    api = FakeApi(detalle=ApiResult(True, data=_detalle_contactos_domicilios()))
    api.detalle_results = [api.detalle, api.detalle, api.detalle, api.detalle]
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda route, **kwargs: navigations.append((route, kwargs)))
    control = page.build()

    edit_buttons = [item for item in _walk(control) if getattr(item, "text", None) == "Editar"]
    edit_buttons[1].on_click(None)
    assert navigations == []
    assert page.active_dialog is not None
    assert page.modal_fields["valor_contacto"].value == "+54 299"
    assert "Editar teléfono" in "\n".join(_texts(page.active_dialog))
    page.modal_fields["valor_contacto"].value = "+54 299 999"
    _find_button(page.active_dialog, "Guardar").on_click(None)
    assert api.actualizar_contacto_calls[-1] == (42, 10, {"tipo_contacto": "TELEFONO", "valor_contacto": "+54 299 999", "es_principal": True, "observaciones": "Laboral"}, 3)

    navigations.clear()
    edit_buttons[2].on_click(None)
    assert navigations == []
    assert page.modal_fields["valor_contacto"].value == "ada@example.com"
    assert "Editar mail" in "\n".join(_texts(page.active_dialog))
    _find_button(page.active_dialog, "Guardar").on_click(None)
    assert api.actualizar_contacto_calls[-1][2]["tipo_contacto"] == "EMAIL"
    assert api.actualizar_contacto_calls[-1][3] == 4

    navigations.clear()
    edit_buttons[0].on_click(None)
    assert navigations == []
    assert page.modal_fields["direccion"].value == "San Martín 123"
    assert page.modal_fields["localidad"].value == "Neuquén"
    assert "Editar dirección" in "\n".join(_texts(page.active_dialog))
    page.modal_fields["localidad"].value = "Neuquén Capital"
    _find_button(page.active_dialog, "Guardar").on_click(None)
    assert api.actualizar_domicilio_calls[-1][0:2] == (42, 20)
    assert api.actualizar_domicilio_calls[-1][3] == 5


def test_editar_contacto_sin_version_muestra_mensaje_amigable_sin_api() -> None:
    api = FakeApi(
        detalle=ApiResult(
            True,
            data={
                "display_name": "Ada Lovelace",
                "estado_persona": "ACTIVA",
                "contactos": [
                    {"id_persona_contacto": 10, "tipo_contacto": "TELEFONO", "valor_contacto": "+54 299", "es_principal": True},
                ],
                "domicilios": [],
                "participaciones": [],
            },
        )
    )
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_args, **_kwargs: None)
    control = page.build()

    _find_button(control, "Editar").on_click(None)
    page.modal_fields["valor_contacto"].value = "+54 299 999"
    _find_button(page.active_dialog, "Guardar").on_click(None)

    text = "\n".join(_texts(page.active_dialog))
    assert "No se pudo editar este dato. Recargá la ficha e intentá nuevamente." in text
    assert "version_registro" not in text
    assert "If-Match-Version" not in text
    assert "CORE-EF" not in text
    assert api.actualizar_contacto_calls == []


def test_editar_domicilio_sin_version_muestra_mensaje_amigable_sin_api() -> None:
    api = FakeApi(
        detalle=ApiResult(
            True,
            data={
                "display_name": "Ada Lovelace",
                "estado_persona": "ACTIVA",
                "contactos": [],
                "domicilios": [
                    {"id_persona_domicilio": 20, "tipo_domicilio": "REAL", "direccion": "San Martín 123", "localidad": "Neuquén", "es_principal": True},
                ],
                "participaciones": [],
            },
        )
    )
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_args, **_kwargs: None)
    control = page.build()

    _find_button(control, "Editar").on_click(None)
    page.modal_fields["localidad"].value = "Neuquén Capital"
    _find_button(page.active_dialog, "Guardar").on_click(None)

    text = "\n".join(_texts(page.active_dialog))
    assert "No se pudo editar este dato. Recargá la ficha e intentá nuevamente." in text
    assert "version_registro" not in text
    assert "If-Match-Version" not in text
    assert "CORE-EF" not in text
    assert api.actualizar_domicilio_calls == []
