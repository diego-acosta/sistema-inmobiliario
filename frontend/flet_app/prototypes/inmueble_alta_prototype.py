"""Prototipo Flet aislado para alta real de inmuebles.

Uso:
  cd frontend/flet_app
  python prototypes/inmueble_alta_prototype.py

Prueba inline sin backend:
  cd frontend/flet_app
  python prototypes/inmueble_alta_prototype.py --self-test

Alcance:
  - Pantalla aislada para validar el alta contra POST /api/v1/inmuebles.
  - Permite cargar opcionalmente el dato catastral/registral inicial.
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
ESTADOS_DATO_CATASTRAL = ("ACTIVO", "INACTIVO", "HISTORICO")


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


def validate_dato_catastral_form(values: dict[str, str | None]) -> list[str]:
    errors: list[str] = []
    for field_name, label in (
        ("superficie_titulo", "Superficie título"),
        ("superficie_mensura", "Superficie mensura"),
    ):
        error = _validate_positive_decimal(values.get(field_name), label)
        if error:
            errors.append(error)
    return errors


def has_dato_catastral_util(values: dict[str, str | None]) -> bool:
    useful_fields = (
        "nomenclatura_catastral",
        "partida_inmobiliaria",
        "matricula",
        "folio_real",
        "circunscripcion",
        "seccion",
        "manzana",
        "lote",
        "parcela",
        "superficie_titulo",
        "superficie_mensura",
        "medidas",
        "situacion_posesoria",
        "situacion_dominial",
        "observaciones",
    )
    return any(_clean_text(values.get(field_name)) for field_name in useful_fields)


def has_manzana_o_lote(values: dict[str, str | None]) -> bool:
    return bool(_clean_text(values.get("manzana")) or _clean_text(values.get("lote")))


def should_create_dato_catastral(
    cargar_dato_catastral: bool, values: dict[str, str | None]
) -> bool:
    return bool(cargar_dato_catastral or has_manzana_o_lote(values))


def build_dato_catastral_payload(values: dict[str, str | None]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "estado_dato": _clean_text(values.get("estado_dato")) or "ACTIVO"
    }
    optional_text_fields = (
        "nomenclatura_catastral",
        "partida_inmobiliaria",
        "matricula",
        "folio_real",
        "circunscripcion",
        "seccion",
        "manzana",
        "lote",
        "parcela",
        "medidas",
        "situacion_posesoria",
        "situacion_dominial",
        "observaciones",
    )
    for field_name in optional_text_fields:
        clean_value = _clean_text(values.get(field_name))
        if clean_value:
            payload[field_name] = clean_value

    for field_name in ("superficie_titulo", "superficie_mensura"):
        clean_value = _clean_text(values.get(field_name))
        if clean_value:
            payload[field_name] = str(Decimal(clean_value))

    return payload


def _safe_border(width: int, color: str) -> ft.Border | None:
    border_all = getattr(ft.border, "all", None)
    if callable(border_all):
        return border_all(width, color)

    border_cls = getattr(ft, "Border", None)
    border_side_cls = getattr(ft, "BorderSide", None)
    if border_cls is None or border_side_cls is None:
        return None

    side = border_side_cls(width, color)
    return border_cls(left=side, top=side, right=side, bottom=side)


def format_api_error(result: ApiResult) -> str:
    parts = []
    if result.status_code is not None:
        parts.append(f"status_code={result.status_code}")
    if result.error_code:
        parts.append(f"error_code={result.error_code}")
    if result.error_message:
        parts.append(f"error_message={result.error_message}")
    if result.error_details:
        details = json.dumps(result.error_details, ensure_ascii=False, default=str)
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
        self.cargar_dato_catastral = ft.Checkbox(
            label="Cargar datos catastrales/registrales ahora",
            value=False,
        )
        self.nomenclatura_catastral = ft.TextField(label="Nomenclatura catastral")
        self.partida_inmobiliaria = ft.TextField(label="Partida inmobiliaria")
        self.matricula = ft.TextField(label="Matrícula")
        self.folio_real = ft.TextField(label="Folio real")
        self.circunscripcion = ft.TextField(label="Circunscripción")
        self.seccion = ft.TextField(label="Sección")
        self.manzana = ft.TextField(label="Manzana")
        self.lote = ft.TextField(label="Lote")
        self.parcela = ft.TextField(label="Parcela")
        self.superficie_titulo = ft.TextField(
            label="Superficie título", hint_text="Ej.: 120.50"
        )
        self.superficie_mensura = ft.TextField(
            label="Superficie mensura", hint_text="Ej.: 120.50"
        )
        self.medidas = ft.TextField(label="Medidas")
        self.situacion_posesoria = ft.TextField(label="Situación posesoria")
        self.situacion_dominial = ft.TextField(label="Situación dominial")
        self.estado_dato = ft.Dropdown(
            label="Estado dato",
            value="ACTIVO",
            options=[ft.dropdown.Option(value) for value in ESTADOS_DATO_CATASTRAL],
        )
        self.observaciones_catastrales = ft.TextField(
            label="Observaciones catastrales/registrales",
            multiline=True,
            min_lines=2,
            max_lines=4,
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
                                "Datos básicos del inmueble",
                                size=18,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                "El alta crea el inmueble sin disponibilidad ni ocupación inicial.",
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            self.codigo_inmueble,
                            self.nombre_inmueble,
                            ft.Row([self.superficie, self.id_desarrollo], wrap=True),
                            ft.Row([self.manzana, self.lote], wrap=True),
                            ft.Text(
                                "Manzana y lote se guardan como dato catastral asociado.",
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            ft.Row(
                                [self.estado_administrativo, self.estado_juridico],
                                wrap=True,
                            ),
                            self.observaciones,
                            ft.Divider(),
                            ft.Text(
                                "Datos catastrales y registrales",
                                size=18,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                "Se cargan como subrecurso opcional después de crear el inmueble. No incluye linderos.",
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            self.cargar_dato_catastral,
                            ft.Row(
                                [
                                    self.nomenclatura_catastral,
                                    self.partida_inmobiliaria,
                                ],
                                wrap=True,
                            ),
                            ft.Row([self.matricula, self.folio_real], wrap=True),
                            ft.Row(
                                [self.circunscripcion, self.seccion],
                                wrap=True,
                            ),
                            ft.Row([self.parcela, self.estado_dato], wrap=True),
                            ft.Row(
                                [self.superficie_titulo, self.superficie_mensura],
                                wrap=True,
                            ),
                            self.medidas,
                            ft.Row(
                                [self.situacion_posesoria, self.situacion_dominial],
                                wrap=True,
                            ),
                            self.observaciones_catastrales,
                            ft.Row([self.save_button, self.clear_button], spacing=10),
                            self.message,
                            self.result_details,
                        ],
                        spacing=12,
                    ),
                    bgcolor=ft.Colors.WHITE,
                    padding=20,
                    border_radius=8,
                    border=_safe_border(1, ft.Colors.BLUE_GREY_100),
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

    def _current_dato_catastral_values(self) -> dict[str, str | None]:
        return {
            "nomenclatura_catastral": self.nomenclatura_catastral.value,
            "partida_inmobiliaria": self.partida_inmobiliaria.value,
            "matricula": self.matricula.value,
            "folio_real": self.folio_real.value,
            "circunscripcion": self.circunscripcion.value,
            "seccion": self.seccion.value,
            "manzana": self.manzana.value,
            "lote": self.lote.value,
            "parcela": self.parcela.value,
            "superficie_titulo": self.superficie_titulo.value,
            "superficie_mensura": self.superficie_mensura.value,
            "medidas": self.medidas.value,
            "situacion_posesoria": self.situacion_posesoria.value,
            "situacion_dominial": self.situacion_dominial.value,
            "estado_dato": self.estado_dato.value,
            "observaciones": self.observaciones_catastrales.value,
        }

    def _save(self, _event: ft.ControlEvent) -> None:
        values = self._current_values()
        errors = validate_form(values)
        dato_values = self._current_dato_catastral_values()
        should_create_dato = should_create_dato_catastral(
            bool(self.cargar_dato_catastral.value), dato_values
        )
        if should_create_dato:
            errors.extend(validate_dato_catastral_form(dato_values))
        if self.cargar_dato_catastral.value and not has_dato_catastral_util(dato_values):
            errors.append(
                "Cargá al menos un dato catastral/registral o desactivá la opción."
            )
        if errors:
            self._show_message("\n".join(errors), success=False)
            self.page.update()
            return

        inmueble_payload = build_inmueble_payload(values)
        dato_payload = (
            build_dato_catastral_payload(dato_values) if should_create_dato else None
        )
        self.save_button.disabled = True
        self.page.update()
        inmueble_result = self.api_client.crear_inmueble(inmueble_payload)
        dato_result: ApiResult | None = None
        if inmueble_result.success and dato_payload is not None:
            id_inmueble = (inmueble_result.data or {}).get("id_inmueble")
            if id_inmueble is None:
                dato_result = ApiResult(
                    success=False,
                    error_message="El backend no devolvió id_inmueble para asociar el dato catastral/registral.",
                )
            else:
                dato_result = self.api_client.crear_dato_catastral_registral_inmueble(
                    int(id_inmueble), dato_payload
                )
        self.save_button.disabled = False

        if inmueble_result.success:
            self._show_success(
                inmueble_payload,
                inmueble_result.data or {},
                dato_payload,
                dato_result,
            )
        else:
            self._show_message(format_api_error(inmueble_result), success=False)
            self._show_technical_details(
                inmueble_payload, inmueble_result, dato_payload, dato_result
            )
        self.page.update()

    def _show_success(
        self,
        inmueble_payload: dict[str, Any],
        data: dict[str, Any],
        dato_payload: dict[str, Any] | None,
        dato_result: ApiResult | None,
    ) -> None:
        messages = ["Inmueble creado correctamente"]
        if dato_payload is not None:
            if dato_result and dato_result.success:
                if set(dato_payload) <= {"estado_dato", "manzana", "lote"} and (
                    "manzana" in dato_payload or "lote" in dato_payload
                ):
                    messages.append("Datos de manzana/lote guardados correctamente")
                else:
                    messages.append(
                        "Datos catastrales/registrales creados correctamente"
                    )
            else:
                messages.append(
                    "El inmueble fue creado, pero no se pudieron guardar los datos catastrales/registrales"
                )
                if dato_result is not None:
                    messages.append(format_api_error(dato_result))
        self._show_message(
            "\n".join(messages), success=not (dato_result and not dato_result.success)
        )
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
        rows.append(ft.Divider())
        rows.append(ft.Text("Modo técnico", weight=ft.FontWeight.W_700))
        rows.extend(
            self._technical_rows(inmueble_payload, data, dato_payload, dato_result)
        )
        self.result_details.controls = rows
        self.result_details.visible = bool(rows)

    def _show_technical_details(
        self,
        inmueble_payload: dict[str, Any],
        inmueble_result: ApiResult,
        dato_payload: dict[str, Any] | None,
        dato_result: ApiResult | None,
    ) -> None:
        self.result_details.controls = [
            ft.Text("Modo técnico", weight=ft.FontWeight.W_700),
            *self._technical_rows(
                inmueble_payload, inmueble_result, dato_payload, dato_result
            ),
        ]
        self.result_details.visible = True

    def _technical_rows(
        self,
        inmueble_payload: dict[str, Any],
        inmueble_response: dict[str, Any] | ApiResult,
        dato_payload: dict[str, Any] | None,
        dato_result: ApiResult | None,
    ) -> list[ft.Control]:
        inmueble_data = (
            inmueble_response
            if isinstance(inmueble_response, dict)
            else inmueble_response.data
        )
        backend_errors = []
        if isinstance(inmueble_response, ApiResult) and not inmueble_response.success:
            backend_errors.append(format_api_error(inmueble_response))
        if dato_result is not None and not dato_result.success:
            backend_errors.append(format_api_error(dato_result))
        return [
            ft.Text(
                "Manzana/lote no van en payload inmueble; "
                "sí van en payload catastral asociado."
            ),
            ft.Text("payload inmueble enviado:"),
            ft.Text(
                json.dumps(inmueble_payload, ensure_ascii=False, indent=2, default=str),
                selectable=True,
            ),
            ft.Text("response inmueble:"),
            ft.Text(
                json.dumps(inmueble_data, ensure_ascii=False, indent=2, default=str),
                selectable=True,
            ),
            ft.Text("payload catastral enviado:"),
            ft.Text(
                json.dumps(dato_payload, ensure_ascii=False, indent=2, default=str),
                selectable=True,
            ),
            ft.Text("response catastral:"),
            ft.Text(
                json.dumps(
                    dato_result.data if dato_result else None,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                selectable=True,
            ),
            ft.Text("errores backend:"),
            ft.Text(
                "\n".join(backend_errors) or "Sin errores backend.", selectable=True
            ),
        ]

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
            self.nomenclatura_catastral,
            self.partida_inmobiliaria,
            self.matricula,
            self.folio_real,
            self.circunscripcion,
            self.seccion,
            self.manzana,
            self.lote,
            self.parcela,
            self.superficie_titulo,
            self.superficie_mensura,
            self.medidas,
            self.situacion_posesoria,
            self.situacion_dominial,
            self.observaciones_catastrales,
        ):
            control.value = ""
        self.cargar_dato_catastral.value = False
        self.estado_administrativo.value = "ACTIVO"
        self.estado_juridico.value = "REGULAR"
        self.estado_dato.value = "ACTIVO"
        self.message.visible = False
        self.result_details.visible = False
        self.page.update()


def _run_self_test() -> None:
    minimum = build_inmueble_payload(
        {
            "codigo_inmueble": "  INM-FLET-999  ",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "nombre_inmueble": "",
            "superficie": "",
            "id_desarrollo": "",
            "observaciones": "",
            "manzana": "M99",
            "lote": "L99",
        }
    )
    assert "manzana" not in minimum
    assert "lote" not in minimum
    assert minimum == {
        "codigo_inmueble": "INM-FLET-999",
        "estado_administrativo": "ACTIVO",
        "estado_juridico": "REGULAR",
    }
    complete = build_inmueble_payload(
        {
            "codigo_inmueble": "INM-FLET-998",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "OBSERVADO",
            "nombre_inmueble": " Casa piloto Flet ",
            "superficie": "120.50",
            "id_desarrollo": "1",
            "observaciones": " Alta desde prototipo Flet ",
        }
    )
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
    dato_payload = build_dato_catastral_payload(
        {
            "nomenclatura_catastral": " NC-1 ",
            "partida_inmobiliaria": "",
            "matricula": " MAT-1 ",
            "folio_real": "",
            "circunscripcion": "",
            "seccion": "",
            "manzana": " M1 ",
            "lote": " L1 ",
            "parcela": " P1 ",
            "superficie_titulo": "100.25",
            "superficie_mensura": "",
            "medidas": "",
            "situacion_posesoria": "",
            "situacion_dominial": "",
            "estado_dato": "ACTIVO",
            "observaciones": " Obs ",
        }
    )
    assert dato_payload == {
        "estado_dato": "ACTIVO",
        "nomenclatura_catastral": "NC-1",
        "matricula": "MAT-1",
        "manzana": "M1",
        "lote": "L1",
        "parcela": "P1",
        "observaciones": "Obs",
        "superficie_titulo": "100.25",
    }
    assert has_dato_catastral_util({"manzana": "M1", "lote": ""})
    assert has_dato_catastral_util({"manzana": "", "lote": "L1"})
    assert not has_dato_catastral_util(
        {"manzana": "", "lote": "", "estado_dato": "ACTIVO"}
    )
    assert has_manzana_o_lote({"manzana": "M1", "lote": ""})
    assert not has_manzana_o_lote({"manzana": "", "lote": ""})
    assert should_create_dato_catastral(False, {"manzana": "M1", "lote": ""})
    assert not should_create_dato_catastral(False, {"manzana": "", "lote": ""})
    assert should_create_dato_catastral(True, {"manzana": "", "lote": ""})
    dato_solo_manzana_lote = build_dato_catastral_payload(
        {"manzana": " M2 ", "lote": " L2 ", "estado_dato": ""}
    )
    assert dato_solo_manzana_lote == {
        "estado_dato": "ACTIVO",
        "manzana": "M2",
        "lote": "L2",
    }
    assert validate_dato_catastral_form({"superficie_titulo": "0"})
    assert validate_dato_catastral_form({"superficie_mensura": "-1"})
    _safe_border(1, ft.Colors.BLUE_GREY_100)
    prototype = InmuebleAltaPrototype(page=object())  # type: ignore[arg-type]
    assert prototype._build_layout() is not None

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

    DummyClient(base_url="http://testserver").crear_inmueble(
        minimum, op_id="not-a-uuid"
    )
    assert captured["path"] == "/api/v1/inmuebles"
    assert "If-Match-Version" not in captured["headers"]
    assert set(captured["headers"]) == {
        "X-Op-Id",
        "X-Usuario-Id",
        "X-Sucursal-Id",
        "X-Instalacion-Id",
    }
    assert captured["json"] == minimum

    DummyClient(base_url="http://testserver").crear_dato_catastral_registral_inmueble(
        10, dato_payload, op_id="not-a-uuid"
    )
    assert captured["path"] == "/api/v1/inmuebles/10/datos-catastrales-registrales"
    assert "If-Match-Version" not in captured["headers"]
    assert set(captured["headers"]) == {
        "X-Op-Id",
        "X-Usuario-Id",
        "X-Sucursal-Id",
        "X-Instalacion-Id",
    }
    assert captured["json"] == dato_payload
    assert "linderos" not in captured["json"]
    print("self-test ok")


def main(page: ft.Page) -> None:
    InmuebleAltaPrototype(page).run()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _run_self_test()
    else:
        ft.app(target=main)
