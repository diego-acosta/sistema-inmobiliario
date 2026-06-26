from typing import Any

import flet as ft

from app.api_client import ApiClient
from app.components.entity_table import entity_table
from app.components.error_state import error_state


class PartesListPage:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.q = ft.TextField(label="Buscar", width=280)
        self.tipo_persona = ft.TextField(label="Tipo", width=160)
        self.estado_persona = ft.TextField(label="Estado", width=160)
        self.limit = 20
        self.offset = 0
        self.total = 0
        self.results = ft.Column(spacing=12, expand=True)
        self.page_info = ft.Text("")

    def build(self) -> ft.Control:
        self._load()
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Partes", size=28, weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        ft.FilledButton(
                            "Nueva persona",
                            icon=ft.Icons.PERSON_ADD,
                            on_click=lambda _: self.on_navigate("persona_create"),
                        ),
                    ]
                ),
                ft.Row(
                    controls=[
                        self.q,
                        self.tipo_persona,
                        self.estado_persona,
                        ft.ElevatedButton("Buscar", on_click=self._on_search),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                self.results,
            ],
            spacing=16,
            expand=True,
        )

    def _on_search(self, _) -> None:
        self.offset = 0
        self._load()
        self.results.update()

    def _load(self) -> None:
        result = self.api.get_personas(
            q=self.q.value,
            tipo_persona=self.tipo_persona.value,
            estado_persona=self.estado_persona.value,
            limit=self.limit,
            offset=self.offset,
        )
        self.results.controls.clear()

        if not result.success:
            self.results.controls.append(error_state(result.error_message or "Error"))
            return

        data = result.data or {}
        if not isinstance(data, dict):
            self.results.controls.append(
                error_state("El listado de partes devolvio un formato inesperado.")
            )
            return

        raw_items = data.get("items", [])
        items = (
            [item for item in raw_items if isinstance(item, dict)]
            if isinstance(raw_items, list)
            else []
        )
        self.total = self._safe_int(data.get("total"))

        if not items:
            self.results.controls.append(
                ft.Container(
                    content=ft.Text("No hay partes para los filtros indicados."),
                    padding=16,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                    border_radius=6,
                )
            )
        else:
            self.results.controls.append(
                entity_table(
                    columns=[
                        ("Nombre", "display_name"),
                        ("Tipo", "tipo_persona"),
                        ("Estado", "estado_persona"),
                        ("CUIT/CUIL", "cuit_cuil"),
                        ("Documento", "documento_principal"),
                        ("Contacto", "contacto_principal"),
                    ],
                    rows=items,
                    actions=self._row_actions,
                )
            )

        self.results.controls.append(self._pagination())

    def _row_actions(self, row: dict[str, Any]) -> list[ft.Control]:
        id_persona = row.get("id_persona")
        return [
            ft.TextButton(
                "Abrir ficha",
                disabled=id_persona is None,
                on_click=(
                    lambda _, id_persona=id_persona: self.on_navigate(
                        "parte_detail",
                        id_persona=id_persona,
                    )
                )
                if id_persona is not None
                else None,
            )
        ]

    def _pagination(self) -> ft.Control:
        start = self.offset + 1 if self.total else 0
        end = min(self.offset + self.limit, self.total)
        self.page_info.value = f"{start}-{end} de {self.total}"
        return ft.Row(
            controls=[
                ft.OutlinedButton(
                    "Anterior",
                    disabled=self.offset <= 0,
                    on_click=self._previous,
                ),
                self.page_info,
                ft.OutlinedButton(
                    "Siguiente",
                    disabled=self.offset + self.limit >= self.total,
                    on_click=self._next,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _safe_int(self, value: object) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _previous(self, _) -> None:
        self.offset = max(0, self.offset - self.limit)
        self._load()
        self.results.update()

    def _next(self, _) -> None:
        self.offset += self.limit
        self._load()
        self.results.update()


class PersonaCreateView:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate

    def build(self) -> ft.Control:
        return PersonaCreateForm(
            self.api,
            on_close=lambda: self.on_navigate("partes"),
            on_created=lambda id_persona: self.on_navigate(
                "parte_detail", id_persona=id_persona
            ),
        ).build()


class PersonaCreateForm:
    def __init__(self, api: ApiClient, on_close, on_created) -> None:
        self.api = api
        self.on_close = on_close
        self.on_created = on_created
        self.tipo_persona = ft.Dropdown(
            label="Tipo de persona",
            width=220,
            value="FISICA",
            options=[ft.dropdown.Option("FISICA"), ft.dropdown.Option("JURIDICA")],
        )
        self.nombre = ft.TextField(label="Nombre", width=260)
        self.apellido = ft.TextField(label="Apellido", width=260)
        self.razon_social = ft.TextField(label="Razón social", width=360)
        self.fecha_nacimiento = ft.TextField(label="Fecha (AAAA-MM-DD)", width=190)
        self.estado_persona = ft.Dropdown(
            label="Estado",
            width=180,
            value="ACTIVA",
            options=[ft.dropdown.Option("ACTIVA"), ft.dropdown.Option("INACTIVA")],
        )
        self.observaciones = ft.TextField(
            label="Observaciones", multiline=True, min_lines=2, max_lines=4
        )
        self.message = ft.Text("")
        self.submit_button = ft.FilledButton("Crear persona", on_click=self._submit)
        self.clear_button = ft.OutlinedButton("Limpiar", on_click=self._clear_form)

    def build(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Nueva persona", size=28, weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        ft.TextButton("Volver", on_click=lambda _: self.on_close()),
                    ]
                ),
                ft.Text(
                    "Alta básica del dominio Personas. Documentos y contactos se cargan fuera de este formulario.",
                    color=ft.Colors.BLUE_GREY_600,
                ),
                ft.Row(
                    controls=[
                        self.tipo_persona,
                        self.estado_persona,
                        self.fecha_nacimiento,
                    ],
                    wrap=True,
                    spacing=12,
                ),
                ft.Row(
                    controls=[self.nombre, self.apellido, self.razon_social],
                    wrap=True,
                    spacing=12,
                ),
                self.observaciones,
                self.message,
                ft.Row(controls=[self.submit_button, self.clear_button], spacing=12),
            ],
            spacing=16,
            expand=True,
        )

    def _values(self) -> dict[str, str | None]:
        return {
            "tipo_persona": self.tipo_persona.value,
            "nombre": self.nombre.value,
            "apellido": self.apellido.value,
            "razon_social": self.razon_social.value,
            "fecha_nacimiento": self.fecha_nacimiento.value,
            "estado_persona": self.estado_persona.value,
            "observaciones": self.observaciones.value,
        }

    def _submit(self, _) -> None:
        from app.persona_alta_helpers import build_persona_payload, validate_persona_form

        errors = validate_persona_form(self._values())
        if errors:
            self._set_message("No se pudo crear: " + " ".join(errors), is_error=True)
            return

        result = self.api.crear_persona(build_persona_payload(self._values()))
        if not result.success:
            self._set_message(
                result.error_message or "No se pudo crear la persona.", is_error=True
            )
            return

        data = result.data if isinstance(result.data, dict) else {}
        id_persona = data.get("id_persona")
        self._set_message(f"Persona creada correctamente. ID: {id_persona}")
        self.clear_button.text = "Nueva alta"

    def _clear_form(self, _=None) -> None:
        self.tipo_persona.value = "FISICA"
        self.nombre.value = ""
        self.apellido.value = ""
        self.razon_social.value = ""
        self.fecha_nacimiento.value = ""
        self.estado_persona.value = "ACTIVA"
        self.observaciones.value = ""
        self.message.value = ""
        self.clear_button.text = "Limpiar"

    def _set_message(self, text: str, *, is_error: bool = False) -> None:
        self.message.value = text
        self.message.color = ft.Colors.RED_700 if is_error else ft.Colors.GREEN_700
