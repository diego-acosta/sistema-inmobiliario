"""Prototipo Flet aislado para alta real de inmuebles.

Uso:
  cd frontend/flet_app
  python prototypes/inmueble_alta_prototype.py

Prueba inline sin backend:
  cd frontend/flet_app
  python prototypes/inmueble_alta_prototype.py --self-test

Alcance:
  - Pantalla aislada para validar el alta contra POST /api/v1/inmuebles.
  - No integra el listado productivo de inmuebles.
  - No modifica backend, SQL, ventas, reservas ni financiero.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
APP_ROOT = CURRENT_DIR.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import flet as ft

from app.api_client import ApiClient, ApiResult


ESTADOS_ADMINISTRATIVOS = ("ACTIVO", "INACTIVO")
ESTADOS_JURIDICOS = ("REGULAR", "OBSERVADO")


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _validate_positive_decimal(value: str | None, field_label: str) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return f"{field_label} debe ser un decimal positivo."
    if number <= 0:
        return f"{field_label} debe ser un decimal positivo."
    return None


def _validate_positive_int(value: str | None, field_label: str) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        number = int(text)
    except ValueError:
        return f"{field_label} debe ser un entero positivo."
    if number <= 0:
        return f"{field_label} debe ser un entero positivo."
    return None


def validate_form(values: dict[str, str | None]) -> list[str]:
    errors: list[str] = []
    if not _clean_text(values.get("codigo_inmueble")):
        errors.append("Código de inmueble es requerido.")
    if not _clean_text(values.get("estado_administrativo")):
        errors.append("Estado administrativo es requerido.")
    if not _clean_text(values.get("estado_juridico")):
        errors.append("Estado jurídico es requerido.")

    superficie_error = _validate_positive_decimal(
        values.get("superficie"), "Superficie"
    )
    if superficie_error:
        errors.append(superficie_error)
    desarrollo_error = _validate_positive_int(
        values.get("id_desarrollo"), "ID desarrollo"
    )
    if desarrollo_error:
        errors.append(desarrollo_error)
    return errors


def build_inmueble_payload(values: dict[str, str | None]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "codigo_inmueble": _clean_text(values.get("codigo_inmueble")),
        "estado_administrativo": _clean_text(values.get("estado_administrativo")),
        "estado_juridico": _clean_text(values.get("estado_juridico")),
    }
    optional_text_fields = ("nombre_inmueble", "observaciones")
    for field_name in optional_text_fields:
        clean_value = _clean_text(values.get(field_name))
        if clean_value:
            payload[field_name] = clean_value

    superficie = _clean_text(values.get("superficie"))
    if superficie:
        payload["superficie"] = str(Decimal(superficie))

    id_desarrollo = _clean_text(values.get("id_desarrollo"))
    if id_desarrollo:
        payload["id_desarrollo"] = int(id_desarrollo)

    return payload


def format_api_error(result: ApiResult) -> str:
    parts = []
    if result.status_code is not None:
        parts.append(f"status_code={result.status_code}")
    if result.error_code:
        parts.append(f"error_code={result.error_code}")
    if result.error_message:
        parts.append(f"error_message={result.error_message}")
    if result.error_details:
        details = json.dumps(
            result.error_details, ensure_ascii=False, default=str
        )
        parts.append("error_details=" + details)
    return " | ".join(parts) or "No se pudo crear el inmueble."


class InmuebleAltaPrototype:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.api_client = ApiClient()
        self.codigo_inmueble = ft.TextField(
            label="Código de inmueble *",
            hint_text="Ej.: INM-FLET-001",
            autofocus=True,
        )
        self.nombre_inmueble = ft.TextField(label="Nombre")
        self.superficie = ft.TextField(label="Superficie", hint_text="Ej.: 120.50")
        self.estado_administrativo = ft.Dropdown(
            label="Estado administrativo *",
            value="ACTIVO",
            options=[ft.dropdown.Option(value) for value in ESTADOS_ADMINISTRATIVOS],
        )
        self.estado_juridico = ft.Dropdown(
            label="Estado jurídico *",
            value="REGULAR",
            options=[ft.dropdown.Option(value) for value in ESTADOS_JURIDICOS],
        )
        self.id_desarrollo = ft.TextField(label="ID desarrollo", hint_text="Opcional")
        self.observaciones = ft.TextField(
            label="Observaciones", multiline=True, min_lines=2, max_lines=4
        )
        self.message = ft.Container(visible=False)
        self.result_details = ft.Column(spacing=4, visible=False)
        self.save_button = ft.FilledButton(
            "Guardar inmueble", icon=ft.Icons.SAVE, on_click=self._save
        )
        self.clear_button = ft.OutlinedButton(
            "Limpiar", icon=ft.Icons.CLEAR, on_click=self._clear
        )

    def run(self) -> None:
        self.page.title = "Alta de inmueble"
        self.page.padding = 24
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.add(self._build_layout())

    def _build_layout(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Alta de inmueble", size=28, weight=ft.FontWeight.W_700),
                ft.Text(
                    "Prototipo aislado para validar el alta real contra el backend existente.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Datos del inmueble",
                                size=18,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                "El alta crea solo el inmueble. No genera disponibilidad ni ocupación inicial.",
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            self.codigo_inmueble,
                            self.nombre_inmueble,
                            ft.Row([self.superficie, self.id_desarrollo], wrap=True),
                            ft.Row([self.estado_administrativo, self.estado_juridico], wrap=True),
                            self.observaciones,
                            ft.Row([self.save_button, self.clear_button], spacing=10),
                            self.message,
                            self.result_details,
                        ],
                        spacing=12,
                    ),
                    bgcolor=ft.Colors.WHITE,
                    padding=20,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                ),
            ],
            spacing=14,
        )

    def _current_values(self) -> dict[str, str | None]:
        return {
            "codigo_inmueble": self.codigo_inmueble.value,
            "nombre_inmueble": self.nombre_inmueble.value,
            "superficie": self.superficie.value,
            "estado_administrativo": self.estado_administrativo.value,
            "estado_juridico": self.estado_juridico.value,
            "id_desarrollo": self.id_desarrollo.value,
            "observaciones": self.observaciones.value,
        }

    def _save(self, _event: ft.ControlEvent) -> None:
        values = self._current_values()
        errors = validate_form(values)
        if errors:
            self._show_message("\n".join(errors), success=False)
            self.page.update()
            return

        self.save_button.disabled = True
        self.page.update()
        result = self.api_client.crear_inmueble(build_inmueble_payload(values))
        self.save_button.disabled = False
        if result.success:
            self._show_success(result.data or {})
        else:
            self._show_message(format_api_error(result), success=False)
        self.page.update()

    def _show_success(self, data: dict[str, Any]) -> None:
        self._show_message("Inmueble creado correctamente.", success=True)
        rows: list[ft.Control] = []
        for label, key in (
            ("ID inmueble", "id_inmueble"),
            ("Código", "codigo_inmueble"),
            ("Estado administrativo", "estado_administrativo"),
            ("Estado jurídico", "estado_juridico"),
            ("Versión registro", "version_registro"),
        ):
            if data.get(key) is not None:
                rows.append(ft.Text(f"{label}: {data.get(key)}"))
        if data.get("uid_global") is not None:
            rows.append(ft.Divider())
            rows.append(ft.Text("Sección técnica", weight=ft.FontWeight.W_700))
            rows.append(
                ft.Text(f"uid_global: {data.get('uid_global')}", selectable=True)
            )
        self.result_details.controls = rows
        self.result_details.visible = bool(rows)

    def _show_message(self, text: str, *, success: bool) -> None:
        self.message.content = ft.Text(
            text, color=ft.Colors.GREEN_800 if success else ft.Colors.RED_800
        )
        self.message.bgcolor = ft.Colors.GREEN_50 if success else ft.Colors.RED_50
        self.message.padding = 12
        self.message.border_radius = 6
        self.message.visible = True
        if not success:
            self.result_details.visible = False

    def _clear(self, _event: ft.ControlEvent | None = None) -> None:
        for control in (
            self.codigo_inmueble,
            self.nombre_inmueble,
            self.superficie,
            self.id_desarrollo,
            self.observaciones,
        ):
            control.value = ""
        self.estado_administrativo.value = "ACTIVO"
        self.estado_juridico.value = "REGULAR"
        self.message.visible = False
        self.result_details.visible = False
        self.page.update()


def _run_self_test() -> None:
    minimum = build_inmueble_payload({
        "codigo_inmueble": "  INM-FLET-999  ",
        "estado_administrativo": "ACTIVO",
        "estado_juridico": "REGULAR",
        "nombre_inmueble": "",
        "superficie": "",
        "id_desarrollo": "",
        "observaciones": "",
    })
    assert minimum == {
        "codigo_inmueble": "INM-FLET-999",
        "estado_administrativo": "ACTIVO",
        "estado_juridico": "REGULAR",
    }
    complete = build_inmueble_payload({
        "codigo_inmueble": "INM-FLET-998",
        "estado_administrativo": "ACTIVO",
        "estado_juridico": "OBSERVADO",
        "nombre_inmueble": " Casa piloto Flet ",
        "superficie": "120.50",
        "id_desarrollo": "1",
        "observaciones": " Alta desde prototipo Flet ",
    })
    assert complete["id_desarrollo"] == 1
    assert complete["superficie"] == "120.50"
    assert validate_form(
        {
            "codigo_inmueble": "A",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "superficie": "-1",
        }
    )
    assert validate_form(
        {
            "codigo_inmueble": "A",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "id_desarrollo": "0",
        }
    )

    captured: dict[str, Any] = {}

    class DummyClient(ApiClient):
        def _post(
            self,
            path: str,
            json: dict[str, Any] | None = None,
            params: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
        ) -> ApiResult:
            captured["path"] = path
            captured["headers"] = headers or {}
            captured["json"] = json or {}
            return ApiResult(success=True, data={})

    DummyClient(base_url="http://testserver").crear_inmueble(minimum, op_id="not-a-uuid")
    assert captured["path"] == "/api/v1/inmuebles"
    assert "If-Match-Version" not in captured["headers"]
    assert set(captured["headers"]) == {
        "X-Op-Id",
        "X-Usuario-Id",
        "X-Sucursal-Id",
        "X-Instalacion-Id",
    }
    assert captured["json"] == minimum
    print("self-test ok")


def main(page: ft.Page) -> None:
    InmuebleAltaPrototype(page).run()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _run_self_test()
    else:
        ft.app(target=main)
