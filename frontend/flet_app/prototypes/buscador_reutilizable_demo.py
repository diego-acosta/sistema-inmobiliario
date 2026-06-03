"""Pantalla demo de buscadores reutilizables para futuros wizards Flet.

Uso:
  cd frontend/flet_app
  python prototypes/buscador_reutilizable_demo.py

Alcance:
  - Prototipo UI aislado con datos demo en memoria.
  - No llama endpoints reales, no modifica backend ni SQL.
  - Muestra el payload simple que cada buscador devolveria al wizard futuro.
"""

from __future__ import annotations

import json
from typing import Any

import flet as ft

from components.search_selector_demo import create_search_selector_demo


def _border_all(width: int | float, color: ft.ColorValue) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


DEMO_RESERVAS: list[dict[str, Any]] = [
    {
        "id_reserva_venta": 101,
        "codigo_reserva": "RV-000123",
        "estado": "VIGENTE",
        "comprador": "Juan Perez",
        "objeto": "Lote 12 - Manzana B",
        "version_registro": 7,
        "resumen": "Reserva vigente por lote disponible para venta completa.",
    },
    {
        "id_reserva_venta": 102,
        "codigo_reserva": "RV-000124",
        "estado": "VIGENTE",
        "comprador": "Maria Gomez",
        "objeto": "UF 3A - Edificio Norte",
        "version_registro": 4,
        "resumen": "Reserva de unidad funcional en edificio norte.",
    },
    {
        "id_reserva_venta": 103,
        "codigo_reserva": "RV-000118",
        "estado": "A_REVISAR",
        "comprador": "Constructora Rio Sur SA",
        "objeto": "Macrolote 2",
        "version_registro": 11,
        "resumen": "Ejemplo no principal para validar estados visibles.",
    },
]

DEMO_OBJETOS: list[dict[str, Any]] = [
    {
        "tipo_objeto": "INMUEBLE",
        "id_inmueble": 501,
        "id_unidad_funcional": None,
        "codigo": "LT-12-MB",
        "descripcion": "Lote 12 - Manzana B",
        "estado": "Disponible",
        "resumen": "Lote individual apto para venta directa o desde reserva.",
    },
    {
        "tipo_objeto": "UNIDAD_FUNCIONAL",
        "id_inmueble": 601,
        "id_unidad_funcional": 701,
        "codigo": "UF-3A",
        "descripcion": "Departamento 3A",
        "estado": "Disponible",
        "inmueble_padre": "Edificio Norte",
        "resumen": "Unidad funcional dentro de Edificio Norte.",
    },
    {
        "tipo_objeto": "INMUEBLE",
        "id_inmueble": 502,
        "id_unidad_funcional": None,
        "codigo": "ML-02",
        "descripcion": "Macrolote 2",
        "estado": "Reservado",
        "resumen": "Objeto visible para validar busqueda por disponibilidad.",
    },
]

DEMO_PERSONAS: list[dict[str, Any]] = [
    {
        "id_persona": 201,
        "codigo_persona": "PER-000201",
        "nombre": "Juan",
        "apellido": "Perez",
        "documento": "DNI 12.345.678",
        "resumen": "Comprador persona humana con documento visible.",
    },
    {
        "id_persona": 202,
        "codigo_persona": "PER-000202",
        "nombre": "Maria",
        "apellido": "Gomez",
        "documento": "DNI 23.456.789",
        "resumen": "Compradora persona humana para reserva vigente.",
    },
    {
        "id_persona": 203,
        "codigo_persona": "PER-000203",
        "razon_social": "Constructora Rio Sur SA",
        "documento": "CUIT 30-12345678-9",
        "resumen": "Comprador persona juridica con razon social.",
    },
]


class BuscadorReutilizableDemo:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.current_selection: dict[str, Any] = {
            "reserva": None,
            "objeto_inmobiliario": None,
            "comprador": None,
        }
        self.selection_json = ft.Text(selectable=True)

        self.reserva_selector = create_search_selector_demo(
            title="Buscar reserva",
            placeholder="Codigo, comprador, objeto o estado de reserva",
            selector_kind="reserva",
            records=DEMO_RESERVAS,
            on_selection_change=lambda selected: self._update_selection("reserva", selected),
        )
        self.objeto_selector = create_search_selector_demo(
            title="Buscar objeto inmobiliario",
            placeholder="Codigo, descripcion, inmueble padre o disponibilidad",
            selector_kind="objeto",
            records=DEMO_OBJETOS,
            on_selection_change=lambda selected: self._update_selection("objeto_inmobiliario", selected),
        )
        self.comprador_selector = create_search_selector_demo(
            title="Buscar comprador",
            placeholder="Codigo, nombre, razon social o documento",
            selector_kind="persona",
            records=DEMO_PERSONAS,
            on_selection_change=lambda selected: self._update_selection("comprador", selected),
        )

    def run(self) -> None:
        self.page.title = "Buscador reutilizable demo"
        self.page.padding = 20
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.add(self._build_layout())
        self._refresh_selection_panel()

    def _build_layout(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Buscador reutilizable para wizards", size=28, weight=ft.FontWeight.W_700),
                        ft.Text(
                            "Demo UI con datos en memoria: seleccion de reserva, objeto inmobiliario y comprador.",
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                        ft.Text(
                            "No llama endpoints reales; el objetivo es reemplazar inputs manuales crudos por seleccion visual.",
                            size=12,
                            color=ft.Colors.BLUE_GREY_600,
                        ),
                    ],
                    spacing=4,
                ),
                self.reserva_selector.view(),
                self.objeto_selector.view(),
                self.comprador_selector.view(),
                self._build_selection_panel(),
            ],
            spacing=14,
            expand=True,
        )

    def _build_selection_panel(self) -> ft.Control:
        return ft.Container(
            padding=16,
            border_radius=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            bgcolor=ft.Colors.BLUE_GREY_50,
            content=ft.Column(
                controls=[
                    ft.Text("Selecciones actuales", size=20, weight=ft.FontWeight.W_700),
                    self.selection_json,
                ],
                spacing=8,
            ),
        )

    def _update_selection(self, key: str, selected: dict[str, Any] | None) -> None:
        self.current_selection[key] = selected
        self._refresh_selection_panel()
        self.selection_json.update()

    def _refresh_selection_panel(self) -> None:
        self.selection_json.value = json.dumps(self.current_selection, indent=2, ensure_ascii=False)


def main(page: ft.Page) -> None:
    BuscadorReutilizableDemo(page).run()


if hasattr(ft, "run"):
    ft.run(main)
else:
    ft.app(target=main)
