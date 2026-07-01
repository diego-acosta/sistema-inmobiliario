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
        self.documento_calls: list[tuple[int, dict[str, Any], str | None]] = []
        self.contacto_calls: list[tuple[int, dict[str, Any], str | None]] = []
        self.domicilio_calls: list[tuple[int, dict[str, Any], str | None]] = []
        self.documento_result = ApiResult(True, data={"id_persona_documento": 10})
        self.contacto_result = ApiResult(True, data={"id_persona_contacto": 11})
        self.domicilio_result = ApiResult(True, data={"id_persona_domicilio": 12})

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

    def crear_persona_documento(
        self, id_persona: int, payload: dict[str, Any], op_id: str | None = None
    ) -> ApiResult:
        self.documento_calls.append((id_persona, payload, op_id))
        return self.documento_result

    def crear_persona_contacto(
        self, id_persona: int, payload: dict[str, Any], op_id: str | None = None
    ) -> ApiResult:
        self.contacto_calls.append((id_persona, payload, op_id))
        return self.contacto_result

    def crear_persona_domicilio(
        self, id_persona: int, payload: dict[str, Any], op_id: str | None = None
    ) -> ApiResult:
        self.domicilio_calls.append((id_persona, payload, op_id))
        return self.domicilio_result


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

    button = _find_button(control, "Editar datos básicos")
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
    _find_button(control, "Editar datos básicos").on_click(None)
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

    _find_button(control, "Editar datos básicos").on_click(None)
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
    _find_button(control, "Editar datos básicos").on_click(None)
    _find_button(page.edit_panel, "Guardar").on_click(None)
    assert "La persona fue modificada por otro usuario" in page.edit_message.value

    api.update_result = ApiResult(False, status_code=422, error_message="nombre requerido")
    _find_button(page.edit_panel, "Guardar").on_click(None)
    assert "nombre requerido" in page.edit_message.value


def _detalle_asociados() -> dict[str, Any]:
    return {
        "id_persona": 42,
        "display_name": "Ada Lovelace",
        "tipo_persona": "FISICA",
        "nombre": "Ada",
        "apellido": "Lovelace",
        "estado_persona": "ACTIVA",
        "version_registro": 7,
        "documentos": [{"id_persona_documento": 1, "tipo_documento": "DNI", "numero_documento": "123", "pais_emision": "AR", "es_principal": True}],
        "contactos": [{"id_persona_contacto": 2, "tipo_contacto": "EMAIL", "valor_contacto": "ada@example.com", "es_principal": True}],
        "domicilios": [{"id_persona_domicilio": 3, "tipo_domicilio": "REAL", "direccion": "Calle 123", "localidad": "CABA", "provincia": "Buenos Aires", "pais": "AR", "codigo_postal": "1000", "es_principal": True}],
        "participaciones": [],
        "obligaciones_financieras": [],
        "usos_transversales": {},
    }


def test_ficha_renderiza_y_crea_documento_contacto_domicilio() -> None:
    initial = ApiResult(True, data=_detalle_asociados())
    refreshed = ApiResult(True, data={**_detalle_asociados(), "version_registro": 8})
    api = FakeApi(detalle=initial)
    api.detalle_results = [initial, refreshed, refreshed, refreshed]
    navigations: list[tuple[str, dict[str, Any]]] = []
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda r, **kw: navigations.append((r, kw)))
    control = page.build()
    text = "\n".join(_texts(control))
    assert "DNI" in text
    assert "ada@example.com" in text
    assert "Calle 123" in text
    assert "Agregar documento" in text
    assert "Agregar contacto" in text
    assert "Agregar domicilio" in text
    associated_text = "\n".join(_texts(page.associated_panel)).lower()
    assert "venta" not in associated_text
    assert "locativo" not in associated_text
    assert "financiero" not in associated_text

    _find_button(control, "Agregar documento").on_click(None)
    documento_op_id = page.associated_op_id
    assert documento_op_id
    assert page.associated_kind == "documento"
    _find_field(page.associated_panel, "Tipo de documento").value = "PASAPORTE"
    _find_field(page.associated_panel, "Número de documento").value = "ABC123"
    _find_field(page.associated_panel, "País de emisión").value = "AR"
    page.associated_principal.value = True
    _find_button(page.associated_panel, "Guardar").on_click(None)
    assert api.documento_calls[0][0] == 42
    assert api.documento_calls[0][1]["tipo_documento"] == "PASAPORTE"
    assert api.documento_calls[0][1]["numero_documento"] == "ABC123"
    assert api.documento_calls[0][1]["pais_emision"] == "AR"
    assert api.documento_calls[0][1]["es_principal"] is True
    assert api.documento_calls[0][2] == documento_op_id
    assert page.associated_op_id is None
    assert page.associated_kind is None

    _find_button(control, "Agregar contacto").on_click(None)
    _find_button(page.associated_panel, "Cancelar").on_click(None)
    assert api.contacto_calls == []

    _find_button(control, "Agregar contacto").on_click(None)
    contacto_op_id = page.associated_op_id
    assert contacto_op_id
    assert contacto_op_id != documento_op_id
    _find_field(page.associated_panel, "Tipo de contacto").value = "EMAIL"
    _find_field(page.associated_panel, "Valor de contacto").value = "grace@example.com"
    _find_button(page.associated_panel, "Guardar").on_click(None)
    assert api.contacto_calls[0][1]["tipo_contacto"] == "EMAIL"
    assert api.contacto_calls[0][1]["valor_contacto"] == "grace@example.com"
    assert api.contacto_calls[0][2] == contacto_op_id

    _find_button(control, "Agregar domicilio").on_click(None)
    domicilio_op_id = page.associated_op_id
    assert domicilio_op_id
    assert domicilio_op_id not in {documento_op_id, contacto_op_id}
    _find_field(page.associated_panel, "Tipo de domicilio").value = "REAL"
    _find_field(page.associated_panel, "Dirección").value = "Av Siempre Viva 742"
    _find_field(page.associated_panel, "Localidad").value = "CABA"
    _find_button(page.associated_panel, "Guardar").on_click(None)
    assert api.domicilio_calls[0][1]["tipo_domicilio"] == "REAL"
    assert api.domicilio_calls[0][1]["direccion"] == "Av Siempre Viva 742"
    assert api.domicilio_calls[0][1]["localidad"] == "CABA"
    assert api.domicilio_calls[0][2] == domicilio_op_id
    assert navigations == [("parte_detail", {"id_persona": 42})] * 3
    assert api.detalle_ids == [42, 42, 42, 42]
    assert api.crear_persona_calls == []


def test_error_al_crear_documento_muestra_mensaje_claro() -> None:
    api = FakeApi(detalle=ApiResult(True, data=_detalle_asociados()))
    api.documento_result = ApiResult(False, error_message="Documento duplicado", status_code=400)
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_args, **_kwargs: None)
    control = page.build()

    _find_button(control, "Agregar documento").on_click(None)
    _find_field(page.associated_panel, "Tipo de documento").value = "DNI"
    _find_field(page.associated_panel, "Número de documento").value = "123"
    _find_button(page.associated_panel, "Guardar").on_click(None)

    assert "Documento duplicado" in page.associated_message.value
    assert page.associated_message.visible is True


def test_recarga_fallida_post_alta_muestra_mensaje_claro() -> None:
    api = FakeApi(detalle=ApiResult(True, data=_detalle_asociados()))
    api.detalle_results = [ApiResult(True, data=_detalle_asociados()), ApiResult(False, error_message="down")]
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_args, **_kwargs: None)
    control = page.build()

    _find_button(control, "Agregar contacto").on_click(None)
    _find_field(page.associated_panel, "Valor de contacto").value = "ada@example.com"
    _find_button(page.associated_panel, "Guardar").on_click(None)

    assert "El dato se guardó, pero no se pudo recargar la ficha" in page.associated_message.value
    assert api.contacto_calls


def test_documento_reutiliza_op_id_si_create_falla_y_cancelar_limpia_estado() -> None:
    api = FakeApi(detalle=ApiResult(True, data=_detalle_asociados()))
    api.documento_result = ApiResult(False, error_message="Documento duplicado", status_code=400)
    page = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_args, **_kwargs: None)
    control = page.build()

    _find_button(control, "Agregar documento").on_click(None)
    first_op_id = page.associated_op_id
    assert first_op_id
    assert page.associated_kind == "documento"
    _find_field(page.associated_panel, "Tipo de documento").value = "DNI"
    _find_field(page.associated_panel, "Número de documento").value = "123"

    _find_button(page.associated_panel, "Guardar").on_click(None)
    _find_button(page.associated_panel, "Guardar").on_click(None)

    assert [call[2] for call in api.documento_calls] == [first_op_id, first_op_id]
    assert page.associated_op_id == first_op_id
    assert page.associated_kind == "documento"

    _find_button(page.associated_panel, "Cancelar").on_click(None)
    assert page.associated_op_id is None
    assert page.associated_kind is None
    assert page.associated_fields == {}
    assert page.associated_panel.visible is False

    _find_button(control, "Agregar documento").on_click(None)
    assert page.associated_op_id
    assert page.associated_op_id != first_op_id
    assert page.associated_kind == "documento"


def test_documento_reutiliza_op_id_si_recarga_falla_y_exito_limpia_estado() -> None:
    api = FakeApi(detalle=ApiResult(True, data=_detalle_asociados()))
    api.detalle_results = [
        ApiResult(True, data=_detalle_asociados()),
        ApiResult(False, error_message="down"),
        ApiResult(True, data={**_detalle_asociados(), "version_registro": 8}),
    ]
    navigations: list[tuple[str, dict[str, Any]]] = []
    page = ParteDetailPage(
        api,
        id_persona=42,
        on_navigate=lambda route, **kwargs: navigations.append((route, kwargs)),
    )
    control = page.build()

    _find_button(control, "Agregar documento").on_click(None)
    first_op_id = page.associated_op_id
    assert first_op_id
    _find_field(page.associated_panel, "Tipo de documento").value = "DNI"
    _find_field(page.associated_panel, "Número de documento").value = "123"

    _find_button(page.associated_panel, "Guardar").on_click(None)
    assert "El dato se guardó, pero no se pudo recargar la ficha" in page.associated_message.value
    assert page.associated_op_id == first_op_id

    _find_button(page.associated_panel, "Guardar").on_click(None)

    assert [call[2] for call in api.documento_calls] == [first_op_id, first_op_id]
    assert page.associated_op_id is None
    assert page.associated_kind is None
    assert navigations == [("parte_detail", {"id_persona": 42})]


def test_contacto_y_domicilio_reutilizan_op_id_en_retry_con_error() -> None:
    for kind, button_text, field_label, calls_attr, result_attr in [
        ("contacto", "Agregar contacto", "Valor de contacto", "contacto_calls", "contacto_result"),
        ("domicilio", "Agregar domicilio", "Dirección", "domicilio_calls", "domicilio_result"),
    ]:
        api = FakeApi(detalle=ApiResult(True, data=_detalle_asociados()))
        setattr(api, result_attr, ApiResult(False, error_message="error", status_code=400))
        page = ParteDetailPage(api, id_persona=42, on_navigate=lambda *_args, **_kwargs: None)
        control = page.build()

        _find_button(control, button_text).on_click(None)
        first_op_id = page.associated_op_id
        assert first_op_id
        assert page.associated_kind == kind
        _find_field(page.associated_panel, field_label).value = "valor"

        _find_button(page.associated_panel, "Guardar").on_click(None)
        _find_button(page.associated_panel, "Guardar").on_click(None)

        calls = getattr(api, calls_attr)
        assert [call[2] for call in calls] == [first_op_id, first_op_id]
        assert page.associated_op_id == first_op_id
