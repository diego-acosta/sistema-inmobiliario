from __future__ import annotations

from collections.abc import Callable
from typing import Any

import flet as ft

from app.api_client import ApiClient
from app.components.error_state import error_state


class ResolverParte:
    """Componente reutilizable para resolver una Persona/Parte existente.

    Este componente solo consulta y selecciona personas ya existentes. No crea,
    no navega a altas y no implementa alta contextual.
    """

    def __init__(
        self,
        api: ApiClient,
        on_selected: Callable[[dict[str, Any]], None],
        titulo: str = "Resolver parte",
        placeholder: str = "Buscar por nombre, documento o CUIT/CUIL",
        limit: int = 10,
    ) -> None:
        self.api = api
        self.on_selected = on_selected
        self.titulo = titulo
        self.placeholder = placeholder
        self.limit = limit
        self._has_searched = False
        self._selected: dict[str, Any] | None = None

        self.search = ft.TextField(
            label="Buscar",
            hint_text=placeholder,
            expand=True,
            on_submit=self._on_search,
        )
        self.status = ft.Column(spacing=8)
        self.results = ft.Column(spacing=8)
        self.root = ft.Column(spacing=12)

    def build(self) -> ft.Control:
        self._render_idle()
        self.root.controls = [
            ft.Text(self.titulo, size=18, weight=ft.FontWeight.W_600),
            ft.Row(
                controls=[
                    self.search,
                    ft.ElevatedButton(
                        "Buscar",
                        icon=ft.Icons.SEARCH,
                        on_click=self._on_search,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            self.status,
            self.results,
        ]
        return self.root

    def _on_search(self, _) -> None:
        query = (self.search.value or "").strip()
        self._selected = None
        self._has_searched = bool(query)
        self.results.controls.clear()

        if not query:
            self._render_idle()
            self._safe_update()
            return

        self._render_loading()
        self._safe_update()

        result = self.api.buscar_personas(q=query, limit=self.limit, offset=0)
        self.results.controls.clear()

        if not result.success:
            self.status.controls = [
                error_state(result.error_message or "No se pudo buscar personas.")
            ]
            self._safe_update()
            return

        items = self._extract_items(result.data)
        if not items:
            self.status.controls = [
                self._message(
                    "Sin resultados",
                    "No se encontraron personas existentes para la busqueda indicada.",
                )
            ]
            self._safe_update()
            return

        self.status.controls = [ft.Text(f"{len(items)} resultado(s) encontrado(s).")]
        self.results.controls = [self._result_card(item) for item in items]
        self._safe_update()

    def _select(self, persona: dict[str, Any]) -> None:
        self._selected = self._selection_payload(persona)
        self.status.controls = [
            self._message(
                "Persona seleccionada",
                self._selected.get("display_name") or "Persona existente seleccionada.",
            )
        ]
        self.on_selected(dict(self._selected))
        self._safe_update()

    def _result_card(self, persona: dict[str, Any]) -> ft.Control:
        payload = self._selection_payload(persona)
        display = payload.get("display_name") or "Sin nombre visible"
        chips = [
            value
            for value in (
                payload.get("tipo_persona"),
                payload.get("documento_principal"),
                payload.get("cuit_cuil"),
            )
            if value
        ]
        id_persona = payload.get("id_persona")
        return ft.Container(
            padding=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(str(display), weight=ft.FontWeight.W_600),
                            ft.Text(
                                " · ".join(str(chip) for chip in chips)
                                or "Sin datos identificatorios adicionales"
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.OutlinedButton(
                        "Seleccionar",
                        disabled=id_persona is None,
                        on_click=lambda _, persona=persona: self._select(persona),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _render_idle(self) -> None:
        if self._has_searched:
            return
        self.status.controls = [
            self._message(
                "Sin busqueda realizada",
                (
                    "Ingrese un nombre, documento o CUIT/CUIL para buscar "
                    "una persona existente."
                ),
            )
        ]
        self.results.controls.clear()

    def _render_loading(self) -> None:
        self.status.controls = [
            ft.Row(
                controls=[
                    ft.ProgressRing(width=18, height=18),
                    ft.Text("Buscando personas..."),
                ],
                spacing=8,
            )
        ]

    def _extract_items(self, data: Any) -> list[dict[str, Any]]:
        raw_items = data.get("items", []) if isinstance(data, dict) else data
        if not isinstance(raw_items, list):
            return []
        return [item for item in raw_items if isinstance(item, dict)]

    def _selection_payload(self, persona: dict[str, Any]) -> dict[str, Any]:
        return {
            "id_persona": persona.get("id_persona"),
            "display_name": (
                persona.get("display_name")
                or persona.get("nombre_visible")
                or persona.get("nombre")
            ),
            "tipo_persona": persona.get("tipo_persona"),
            "documento_principal": persona.get("documento_principal")
            or persona.get("documento"),
            "cuit_cuil": persona.get("cuit_cuil")
            or persona.get("cuit")
            or persona.get("cuil"),
        }

    def _message(self, title: str, body: str) -> ft.Control:
        return ft.Container(
            padding=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
            content=ft.Column(
                controls=[
                    ft.Text(title, weight=ft.FontWeight.W_600),
                    ft.Text(body),
                ],
                spacing=4,
            ),
        )

    def _safe_update(self) -> None:
        if getattr(self.root, "page", None) is not None:
            self.root.update()
