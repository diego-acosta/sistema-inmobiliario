"""Prototipo Flet del wizard venta completa V3 - Pantalla 1: Origen.

Uso:
  cd frontend/flet_app
  python prototypes/venta_completa_wizard_v3_prototype.py

Alcance:
  - Prototipo UI aislado del dominio comercial, sin llamadas a backend.
  - Nueva base de iteracion pantalla por pantalla para venta completa V3.
  - Implementa Pantalla 1 - Origen, Pantalla 1B - Seleccionar reserva y placeholder de Paso 2.
  - No modifica backend, SQL, caja, pagos, recibos ni documental.
  - No pide id_venta, no calcula cronograma local y no implementa objetos todavia.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import flet as ft

from components.search_selector_demo import SearchSelectorDemo, create_search_selector_demo


OrigenVenta = Literal["RESERVA", "DIRECTA"]
PantallaWizard = Literal["ORIGEN", "SELECCIONAR_RESERVA", "OBJETOS_PLACEHOLDER"]


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
        "resumen": "Ejemplo visual para validar estados visibles en el selector.",
    },
]


@dataclass
class WizardVentaCompletaV3State:
    """Estado minimo para Pantalla 1 - Origen y Pantalla 1B.

    La reserva seleccionada guarda los datos necesarios para continuar hacia el
    flujo desde reserva sin pedir campos tecnicos como entradas principales.
    """

    origen: OrigenVenta | None = None
    id_reserva_venta: int | None = None
    version_registro: int | None = None
    texto_visual_reserva: str | None = None
    reserva_demo: dict[str, Any] | None = None
    pantalla_actual: PantallaWizard = "ORIGEN"


class VentaCompletaWizardV3Prototype:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = WizardVentaCompletaV3State()
        self.reserva_selector: SearchSelectorDemo | None = None

    def run(self) -> None:
        self.page.title = "Wizard venta completa V3 - Origen"
        self.page.padding = 0
        self.page.scroll = None
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self._render()

    def _render(self) -> None:
        self.page.controls.clear()
        self.page.add(
            ft.Container(
                expand=True,
                padding=20,
                content=ft.Column(
                    controls=[
                        self._build_header(),
                        self._build_center_area(),
                        self._build_footer(),
                    ],
                    spacing=14,
                    expand=True,
                ),
            )
        )
        self.page.update()

    def _build_center_area(self) -> ft.Control:
        return ft.Row(
            controls=[
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        controls=[self._build_main_content()],
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                ),
                ft.Container(width=300, content=self._build_flow_state_panel()),
            ],
            spacing=16,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _build_footer(self) -> ft.Control:
        return ft.Container(
            padding=12,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=self._build_navigation(),
        )

    def _build_header(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Venta completa V3", size=28, weight=ft.FontWeight.W_700),
                ft.Text(
                    "Prototipo pantalla por pantalla. Esta version inicia solo con el origen de la venta.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
            ],
            spacing=4,
        )

    def _build_main_content(self) -> ft.Control:
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            return self._build_reserva_selection_step()
        if self.state.pantalla_actual == "OBJETOS_PLACEHOLDER":
            return self._build_step_two_placeholder()
        return self._build_origin_step()

    def _build_origin_step(self) -> ft.Control:
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("¿Cómo querés iniciar la venta?", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Elegí una alternativa para definir el contexto inicial.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Row(
                        controls=[
                            self._build_origin_card(
                                origin="RESERVA",
                                title="Desde reserva existente",
                                description="Usar una reserva vigente ya cargada.",
                                icon=ft.Icons.BOOKMARK_OUTLINED,
                            ),
                            self._build_origin_card(
                                origin="DIRECTA",
                                title="Venta directa",
                                description="Crear una venta sin reserva previa.",
                                icon=ft.Icons.ADD_HOME_OUTLINED,
                            ),
                        ],
                        spacing=14,
                    ),
                ],
                spacing=14,
            ),
        )

    def _build_origin_card(self, *, origin: OrigenVenta, title: str, description: str, icon: str) -> ft.Control:
        selected = self.state.origen == origin
        return ft.Container(
            expand=True,
            padding=18,
            border_radius=14,
            border=_border_all(2 if selected else 1, ft.Colors.BLUE_500 if selected else ft.Colors.BLUE_GREY_100),
            bgcolor=ft.Colors.BLUE_50 if selected else ft.Colors.WHITE,
            on_click=lambda _: self._select_origin(origin),
            content=ft.Column(
                controls=[
                    ft.Icon(icon, size=32, color=ft.Colors.BLUE_700 if selected else ft.Colors.BLUE_GREY_500),
                    ft.Text(title, size=18, weight=ft.FontWeight.W_700),
                    ft.Text(description, color=ft.Colors.BLUE_GREY_700),
                ],
                spacing=8,
            ),
        )

    def _build_reserva_selection_step(self) -> ft.Control:
        if self.reserva_selector is None:
            self.reserva_selector = create_search_selector_demo(
                title="Seleccionar reserva",
                placeholder="Codigo, comprador, objeto o estado de reserva",
                selector_kind="reserva",
                records=DEMO_RESERVAS,
                on_selection_change=self._on_reserva_selected,
            )
            self._configure_reserva_selector_scroll()

        controls: list[ft.Control] = [
            ft.Text("Seleccionar reserva", size=24, weight=ft.FontWeight.W_700),
            ft.Text(
                "Elegí una reserva vigente para continuar con la venta desde reserva.",
                color=ft.Colors.BLUE_GREY_700,
            ),
            self.reserva_selector.view(),
            self._build_help_card(
                "En la UI productiva este buscador se conectará al listado real de reservas vigentes.",
                ft.Colors.AMBER_50,
                ft.Colors.AMBER_200,
            ),
        ]
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=14),
        )

    def _configure_reserva_selector_scroll(self) -> None:
        if self.reserva_selector is None:
            return
        self.reserva_selector.results_column.height = 260
        self.reserva_selector.results_column.scroll = ft.ScrollMode.AUTO

    def _build_step_two_placeholder(self) -> ft.Control:
        return ft.Container(
            padding=24,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Paso 2 — Objetos de venta pendiente", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Placeholder tecnico: todavia no se implementa carga de objetos ni datos de pasos posteriores.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                ],
                spacing=8,
            ),
        )

    def _build_flow_state_panel(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Estado del flujo", size=20, weight=ft.FontWeight.W_700),
            _info_row("Origen", self._origin_label()),
        ]
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            controls.append(_info_row("Reserva", self._reservation_status()))
        controls.append(_info_row("Próximo paso", self._next_step_label()))

        return ft.Container(
            padding=16,
            border_radius=14,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=controls,
                spacing=10,
            ),
        )

    def _build_navigation(self) -> ft.Control:
        return ft.Row(
            controls=[
                ft.OutlinedButton(
                    "Anterior",
                    icon=ft.Icons.ARROW_BACK,
                    disabled=self.state.pantalla_actual == "ORIGEN",
                    on_click=self._previous_step,
                ),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Siguiente",
                    icon=ft.Icons.ARROW_FORWARD,
                    disabled=not self._can_advance(),
                    on_click=self._next_step,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _select_origin(self, origin: OrigenVenta) -> None:
        if self.state.origen != origin:
            self.state.id_reserva_venta = None
            self.state.version_registro = None
            self.state.texto_visual_reserva = None
            self.state.reserva_demo = None
            self.reserva_selector = None
        self.state.origen = origin
        self._render()

    def _on_reserva_selected(self, selected: dict[str, Any] | None) -> None:
        if selected is None:
            self.state.id_reserva_venta = None
            self.state.version_registro = None
            self.state.texto_visual_reserva = None
            self.state.reserva_demo = None
            self._render()
            return

        selected_id = selected.get("id_reserva_venta")
        reserva = next((item for item in DEMO_RESERVAS if item.get("id_reserva_venta") == selected_id), None)
        self.state.id_reserva_venta = selected_id
        self.state.version_registro = selected.get("version_registro")
        self.state.texto_visual_reserva = selected.get("texto_visual")
        self.state.reserva_demo = reserva
        self._render()

    def _next_step(self, _: ft.ControlEvent | None = None) -> None:
        if not self._can_advance():
            return
        if self.state.pantalla_actual == "ORIGEN" and self.state.origen == "RESERVA":
            self.state.pantalla_actual = "SELECCIONAR_RESERVA"
        else:
            self.state.pantalla_actual = "OBJETOS_PLACEHOLDER"
        self._render()

    def _previous_step(self, _: ft.ControlEvent | None = None) -> None:
        if self.state.pantalla_actual == "ORIGEN":
            return
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            self.state.pantalla_actual = "ORIGEN"
        elif self.state.origen == "RESERVA":
            self.state.pantalla_actual = "SELECCIONAR_RESERVA"
        else:
            self.state.pantalla_actual = "ORIGEN"
        self._render()

    def _can_advance(self) -> bool:
        if self.state.pantalla_actual == "ORIGEN":
            return self.state.origen is not None
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            return self.state.id_reserva_venta is not None and self.state.version_registro is not None
        return False

    def _origin_label(self) -> str:
        if self.state.origen == "RESERVA":
            return "Desde reserva"
        if self.state.origen == "DIRECTA":
            return "Venta directa"
        return "No seleccionado"

    def _reservation_status(self) -> str:
        return self.state.texto_visual_reserva or "pendiente de selección"

    def _next_step_label(self) -> str:
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            return "cargar objetos de venta"
        if self.state.origen is None:
            return "elegir origen"
        if self.state.origen == "RESERVA":
            return "seleccionar reserva"
        return "cargar objetos de venta"

    def _build_help_card(self, text: str, bgcolor: ft.ColorValue, border_color: ft.ColorValue) -> ft.Control:
        return ft.Container(
            padding=12,
            border_radius=10,
            bgcolor=bgcolor,
            border=_border_all(1, border_color),
            content=ft.Text(text, color=ft.Colors.BLUE_GREY_800),
        )


def _border_all(width: int | float, color: ft.ColorValue) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


def _info_row(label: str, value: Any) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Text(f"{label}:", weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_GREY_700),
            ft.Text(str(value if value not in (None, "") else "-"), color=ft.Colors.BLUE_GREY_900, expand=True),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def main(page: ft.Page) -> None:
    VentaCompletaWizardV3Prototype(page).run()


if hasattr(ft, "run"):
    ft.run(main)
else:
    ft.app(target=main)
