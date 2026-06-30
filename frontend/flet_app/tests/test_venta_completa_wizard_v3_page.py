from __future__ import annotations

from typing import Any

import flet as ft

from app.api_client import ApiResult
from prototypes.venta_completa_wizard_v3_prototype import (
    CompradorWizardDraft,
    ObjetoVentaWizardDraft,
    VentaCompletaWizardV3Prototype,
)


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


def _prepare_review_ready_wizard(wizard: VentaCompletaWizardV3Prototype) -> None:
    wizard.state.pantalla_actual = "REVISION_GENERAL"
    wizard.state.codigo_venta = "VD-CTX-001"
    wizard.state.fecha_venta_iso = "2026-05-22"
    wizard.fecha_venta_error = None
    wizard.state.moneda = "USD"
    wizard.state.forma_pago = "CONTADO"
    wizard.state.fecha_pago_contado_iso = "2026-05-22"
    wizard.state.fecha_pago_contado_error = None
    wizard.state.preview_data = {"ok": True}
    wizard.state.preview_stale = False
    wizard.state.objetos = [
        ObjetoVentaWizardDraft(
            tipo_objeto="INMUEBLE",
            id_inmueble=10,
            id_unidad_funcional=None,
            texto_visual="Inmueble 10",
            precio_asignado="1000.00",
            persisted=True,
        )
    ]


def _contextual_buyer() -> CompradorWizardDraft:
    return CompradorWizardDraft(
        id_persona=None,
        texto_visual="Juan Pérez (se creará en esta venta)",
        porcentaje_responsabilidad="",
        id_rol_participacion="4",
        source="contextual_venta",
        persisted=False,
        datos_persona={
            "tipo_persona": "FISICA",
            "nombre": "Juan",
            "apellido": "Pérez",
            "razon_social": None,
            "cuit_cuil": None,
            "documento_principal": {
                "tipo_documento": "DNI",
                "numero_documento": "12345678",
            },
        },
    )


def test_comprador_contextual_no_bloquea_confirmacion_y_payload_usa_datos_persona() -> None:
    wizard, api = _wizard()
    _prepare_review_ready_wizard(wizard)
    wizard.state.compradores = [_contextual_buyer()]

    assert wizard._non_persisted_confirmation_errors() == []
    assert wizard._has_only_persisted_confirmation_records()
    assert wizard._can_confirm_sale()

    payload = wizard._build_confirm_sale_direct_payload()
    comprador_payload = payload["compradores"][0]

    assert "id_persona" not in comprador_payload
    assert comprador_payload["datos_persona"]["documento_principal"]["numero_documento"] == "12345678"
    assert api.crear_persona_calls == []


def test_comprador_manual_no_persistido_sigue_bloqueando_confirmacion() -> None:
    wizard, _ = _wizard()
    _prepare_review_ready_wizard(wizard)
    wizard.state.compradores = [
        CompradorWizardDraft(
            id_persona=None,
            texto_visual="Comprador manual no soportado",
            porcentaje_responsabilidad="",
            id_rol_participacion="4",
            source="manual",
            persisted=False,
        )
    ]

    assert wizard._non_persisted_confirmation_errors() == [
        "Compradores no persistidos: Comprador manual no soportado"
    ]
    assert not wizard._can_confirm_sale()


def test_accion_crear_comprador_en_venta_abre_ficha_contextual_y_conserva_estado() -> None:
    wizard, api = _wizard()
    wizard.state.codigo_venta = "VD-293"
    wizard.state.objetos = [
        ObjetoVentaWizardDraft(
            tipo_objeto="INMUEBLE",
            id_inmueble=293,
            id_unidad_funcional=None,
            texto_visual="Inmueble 293",
            precio_asignado="5000.00",
            persisted=True,
        )
    ]

    control = wizard._build_buyers_step()
    _find_button(control, "Crear comprador en esta venta").on_click(None)

    assert wizard.state.pantalla_actual == "COMPRADOR_CONTEXTUAL"
    assert wizard.state.codigo_venta == "VD-293"
    assert wizard.state.objetos[0].id_inmueble == 293
    assert wizard.state.compradores == []
    text = "\n".join(_texts(wizard._build_contextual_buyer_full_step()))
    assert "Crear comprador para esta venta" in text
    assert "Guardar y volver a la venta" in text
    assert "Cancelar y volver" in text
    assert "return_to=venta_completa_wizard_v3" in text
    assert "persona_create" not in text
    assert api.crear_persona_calls == []


def test_cancelar_ficha_contextual_vuelve_sin_agregar_comprador() -> None:
    wizard, _ = _wizard()
    wizard.state.pantalla_actual = "COMPRADOR_CONTEXTUAL"
    wizard.contextual_buyer_nombre_field.value = "Ana"

    wizard._cancel_contextual_buyer_full_step(None)

    assert wizard.state.pantalla_actual == "COMPRADORES"
    assert wizard.state.compradores == []
    assert wizard.contextual_buyer_nombre_field.value == "Ana"


def test_guardar_ficha_contextual_completa_vuelve_agrega_comprador_y_marca_preview_stale() -> None:
    wizard, api = _wizard()
    wizard.state.pantalla_actual = "COMPRADOR_CONTEXTUAL"
    wizard.state.preview_data = {"ok": True}
    wizard.state.preview_stale = False
    wizard.contextual_buyer_nombre_field.value = "Ana"
    wizard.contextual_buyer_apellido_field.value = "García"
    wizard.contextual_buyer_cuit_field.value = "27-12345678-9"
    wizard.contextual_buyer_doc_numero_field.value = "12345678"
    wizard.contextual_buyer_email_field.value = "ana@example.com"
    wizard.contextual_buyer_telefono_field.value = "+54 11 5555-5555"
    wizard.contextual_buyer_domicilio_calle_field.value = "Av. Siempre Viva"
    wizard.contextual_buyer_domicilio_numero_field.value = "742"
    wizard.contextual_buyer_domicilio_localidad_field.value = "CABA"
    wizard.contextual_buyer_domicilio_provincia_field.value = "Buenos Aires"
    wizard.contextual_buyer_observaciones_field.value = "Observación contextual"

    wizard._add_contextual_buyer(None)

    assert wizard.state.pantalla_actual == "COMPRADORES"
    assert len(wizard.state.compradores) == 1
    comprador = wizard.state.compradores[0]
    assert comprador.source == "contextual_venta"
    assert comprador.persisted is False
    assert comprador.id_persona is None
    assert comprador.id_rol_participacion == "4"
    assert comprador.texto_visual == "Ana García (se creará en esta venta)"
    assert comprador.datos_persona is not None
    assert comprador.datos_persona == {
        "tipo_persona": "FISICA",
        "nombre": "Ana",
        "apellido": "García",
        "razon_social": None,
        "cuit_cuil": "27-12345678-9",
        "documento_principal": {"tipo_documento": "DNI", "numero_documento": "12345678"},
    }
    assert "contactos" not in comprador.datos_persona
    assert "domicilios" not in comprador.datos_persona
    assert "observaciones" not in comprador.datos_persona
    assert comprador.ficha_persona_contextual is not None
    assert comprador.ficha_persona_contextual["contactos"] == [
        {"tipo_contacto": "EMAIL", "valor": "ana@example.com", "principal": True},
        {"tipo_contacto": "TELEFONO", "valor": "+54 11 5555-5555", "principal": False},
    ]
    assert comprador.ficha_persona_contextual["domicilios"][0]["calle"] == "Av. Siempre Viva"
    assert comprador.ficha_persona_contextual["observaciones"] == "Observación contextual"
    assert wizard.state.preview_stale is True
    assert api.crear_persona_calls == []

    payload = wizard._build_confirm_sale_direct_payload()
    comprador_payload = payload["compradores"][0]
    assert "id_persona" not in comprador_payload
    assert comprador_payload["datos_persona"] == comprador.datos_persona
    assert "contactos" not in comprador_payload["datos_persona"]
    assert "domicilios" not in comprador_payload["datos_persona"]
    assert "observaciones" not in comprador_payload["datos_persona"]


def test_comprador_existente_sigue_funcionando_con_ficha_contextual_disponible() -> None:
    wizard, api = _wizard()
    control = wizard._build_buyers_step()
    assert "Crear comprador en esta venta" in "\n".join(_texts(control))
    wizard.comprador_selector.search.value = "Compradora"

    _find_button(control, "Buscar").on_click(None)
    _find_button(control, "Seleccionar").on_click(None)
    wizard._add_selected_buyer(None)

    assert wizard.state.compradores[0].id_persona == 281
    assert wizard.state.compradores[0].datos_persona is None
    assert api.crear_persona_calls == []
