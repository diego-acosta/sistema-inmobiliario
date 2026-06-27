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
