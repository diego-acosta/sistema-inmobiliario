"""Prototipo Flet del wizard venta completa V3 - Pantalla 2: Objetos de venta.

Uso:
  cd frontend/flet_app
  python prototypes/venta_completa_wizard_v3_prototype.py

Alcance:
  - Prototipo UI aislado del dominio comercial, sin llamadas a backend.
  - Nueva base de iteracion pantalla por pantalla para venta completa V3.
  - Implementa Pantalla 1 - Origen, Pantalla 1B - Seleccionar reserva y Pantalla 2 - Objetos de venta.
  - No modifica backend, SQL, caja, pagos, recibos ni documental.
  - No pide id_venta, no calcula cronograma local y no implementa compradores ni pasos futuros.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

import flet as ft

from components.search_selector_demo import SearchSelectorDemo, create_search_selector_demo


OrigenVenta = Literal["RESERVA", "DIRECTA"]
PantallaWizard = Literal["ORIGEN", "SELECCIONAR_RESERVA", "OBJETOS", "COMPRADORES_PLACEHOLDER"]


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


DEMO_OBJETOS_INMOBILIARIOS: list[dict[str, Any]] = [
    {
        "tipo_objeto": "INMUEBLE",
        "id_inmueble": 501,
        "codigo": "INM-LOTE-12",
        "descripcion": "Lote 12 - Manzana B",
        "estado": "DISPONIBLE",
        "resumen": "Inmueble completo disponible para la operación comercial demo.",
    },
    {
        "tipo_objeto": "INMUEBLE",
        "id_inmueble": 502,
        "codigo": "INM-MACRO-02",
        "descripcion": "Macrolote 2",
        "estado": "DISPONIBLE",
        "resumen": "Macrolote demo para validar carga multiobjeto sin backend.",
    },
    {
        "tipo_objeto": "UNIDAD_FUNCIONAL",
        "id_unidad_funcional": 701,
        "codigo": "UF-3A",
        "descripcion": "Unidad funcional 3A",
        "inmueble_padre": "Edificio Norte",
        "estado": "DISPONIBLE",
        "resumen": "Unidad funcional demo dentro del edificio norte.",
    },
    {
        "tipo_objeto": "UNIDAD_FUNCIONAL",
        "id_unidad_funcional": 702,
        "codigo": "UF-4B",
        "descripcion": "Unidad funcional 4B",
        "inmueble_padre": "Edificio Norte",
        "estado": "RESERVABLE",
        "resumen": "Unidad funcional demo para validar selección por buscador visual.",
    },
]


@dataclass
class ObjetoVentaWizardDraft:
    tipo_objeto: str
    id_inmueble: int | None
    id_unidad_funcional: int | None
    texto_visual: str
    precio_asignado: str


@dataclass
class WizardVentaCompletaV3State:
    """Estado minimo del wizard V3 hasta Pantalla 2 - Objetos de venta.

    Conserva origen/reserva y una lista de objetos comerciales demo con XOR
    visual entre inmueble y unidad funcional, sin persistencia ni backend.
    """

    origen: OrigenVenta | None = None
    id_reserva_venta: int | None = None
    version_registro: int | None = None
    texto_visual_reserva: str | None = None
    reserva_demo: dict[str, Any] | None = None
    objetos: list[ObjetoVentaWizardDraft] = field(default_factory=list)
    pantalla_actual: PantallaWizard = "ORIGEN"


class VentaCompletaWizardV3Prototype:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = WizardVentaCompletaV3State()
        self.reserva_selector: SearchSelectorDemo | None = None
        self.objeto_selector: SearchSelectorDemo | None = None
        self.objeto_seleccionado: dict[str, Any] | None = None
        self.precio_objeto_value = ""
        self.precio_objeto_field = ft.TextField(
            label="Valor asignado al objeto",
            prefix_icon=ft.Icons.ATTACH_MONEY,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_precio_objeto_change,
        )
        self.precio_objeto_error: str | None = None

    def run(self) -> None:
        self.page.title = "Wizard venta completa V3 - Objetos"
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
                    "Prototipo pantalla por pantalla para avanzar el alta de venta completa V3.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
            ],
            spacing=4,
        )

    def _build_main_content(self) -> ft.Control:
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            return self._build_reserva_selection_step()
        if self.state.pantalla_actual == "OBJETOS":
            return self._build_objects_step()
        if self.state.pantalla_actual == "COMPRADORES_PLACEHOLDER":
            return self._build_buyers_placeholder()
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

    def _build_objects_step(self) -> ft.Control:
        if self.objeto_selector is None:
            self.objeto_selector = create_search_selector_demo(
                title="Buscador de objeto inmobiliario",
                placeholder="Código, descripción, tipo o ID técnico del objeto",
                selector_kind="objeto",
                records=DEMO_OBJETOS_INMOBILIARIOS,
                on_selection_change=self._on_objeto_selected,
            )
            self._configure_objeto_selector_scroll()

        controls: list[ft.Control] = [
            ft.Text("Objetos de venta", size=24, weight=ft.FontWeight.W_700),
            ft.Text(
                "Seleccioná los inmuebles o unidades funcionales incluidos en la operación y asigná el valor comercial de cada uno.",
                color=ft.Colors.BLUE_GREY_700,
            ),
            ft.Row(
                controls=[
                    ft.Container(content=self.objeto_selector.view(), expand=True),
                    ft.Container(width=380, content=self._build_objects_side_panel()),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ]

        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=14),
        )

    def _configure_objeto_selector_scroll(self) -> None:
        if self.objeto_selector is None:
            return
        self.objeto_selector.results_column.height = 260
        self.objeto_selector.results_column.scroll = ft.ScrollMode.AUTO

    def _build_objects_side_panel(self) -> ft.Control:
        return ft.Column(
            controls=[
                self._build_selected_object_panel(),
                self._build_help_card(
                    "La validación final de solapamiento entre inmueble completo y unidades funcionales la realiza el backend.",
                    ft.Colors.AMBER_50,
                    ft.Colors.AMBER_200,
                ),
                self._build_added_objects_list(),
                self._build_objects_total_summary(),
            ],
            spacing=12,
        )

    def _build_selected_object_panel(self) -> ft.Control:
        if self.objeto_seleccionado is None:
            panel_content = ft.Column(
                controls=[
                    ft.Text("Objeto seleccionado", size=18, weight=ft.FontWeight.W_700),
                    ft.Container(
                        padding=12,
                        border_radius=10,
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        content=ft.Text(
                            "Seleccioná un inmueble o unidad funcional para asignarle valor.",
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                    ),
                ],
                spacing=10,
            )
        else:
            tipo_objeto = str(self.objeto_seleccionado.get("tipo_objeto") or "-")
            id_label, id_value = _object_id_label_value(self.objeto_seleccionado)
            duplicate = self._is_duplicate_selected_object()
            price_error = self.precio_objeto_error
            panel_content = ft.Column(
                controls=[
                    ft.Text("Objeto seleccionado", size=18, weight=ft.FontWeight.W_700),
                    ft.Text(str(self.objeto_seleccionado.get("texto_visual") or "-"), weight=ft.FontWeight.W_600),
                    ft.Row(
                        controls=[
                            _badge(f"tipo_objeto: {tipo_objeto}", ft.Colors.BLUE_GREY_50, ft.Colors.BLUE_GREY_200),
                            _badge(
                                f"ID técnico secundario ({id_label}): {id_value}",
                                ft.Colors.BLUE_GREY_50,
                                ft.Colors.BLUE_GREY_200,
                            ),
                        ],
                        wrap=True,
                        spacing=8,
                    ),
                    self.precio_objeto_field,
                    ft.Text(
                        price_error or "Ingresá el valor comercial asignado a este objeto.",
                        size=12,
                        color=ft.Colors.RED_700 if price_error else ft.Colors.BLUE_GREY_600,
                    ),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "Agregar a la venta",
                                icon=ft.Icons.ADD,
                                disabled=duplicate,
                                on_click=self._add_selected_object,
                            ),
                            ft.OutlinedButton(
                                "Limpiar selección",
                                icon=ft.Icons.CLOSE,
                                on_click=self._clear_selected_object,
                            ),
                        ],
                        wrap=True,
                        spacing=8,
                    ),
                    ft.Text(
                        "Este objeto ya fue agregado a la venta." if duplicate else "",
                        size=12,
                        color=ft.Colors.RED_700,
                    ),
                ],
                spacing=8,
            )
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.BLUE_50,
            border=_border_all(1, ft.Colors.BLUE_200),
            content=panel_content,
        )

    def _build_added_objects_list(self) -> ft.Control:
        if not self.state.objetos:
            content: ft.Control = ft.Container(
                padding=12,
                border_radius=10,
                bgcolor=ft.Colors.BLUE_GREY_50,
                content=ft.Text("Todavía no agregaste objetos a la venta.", color=ft.Colors.BLUE_GREY_700),
            )
        else:
            content = ft.Container(
                height=240,
                content=ft.Column(
                    controls=[
                        self._build_added_object_row(index, objeto)
                        for index, objeto in enumerate(self.state.objetos)
                    ],
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                ),
            )
        return ft.Container(
            padding=12,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Objetos agregados", size=18, weight=ft.FontWeight.W_700),
                    content,
                ],
                spacing=8,
            ),
        )

    def _build_added_object_row(self, index: int, objeto: ObjetoVentaWizardDraft) -> ft.Control:
        id_label = "id_unidad_funcional" if objeto.tipo_objeto == "UNIDAD_FUNCIONAL" else "id_inmueble"
        id_value = objeto.id_unidad_funcional if objeto.tipo_objeto == "UNIDAD_FUNCIONAL" else objeto.id_inmueble
        return ft.Container(
            padding=12,
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(objeto.texto_visual, weight=ft.FontWeight.W_700),
                            ft.Text(
                                f"Tipo: {objeto.tipo_objeto} — ID técnico secundario ({id_label}): {id_value}",
                                size=12,
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            ft.Text(
                                f"precio_asignado: {_format_money(objeto.precio_asignado)}",
                                size=12,
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.OutlinedButton(
                        "Quitar",
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=lambda _, item_index=index: self._remove_object(item_index),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _build_objects_total_summary(self) -> ft.Control:
        total = self._objects_total()
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.GREEN_50,
            border=_border_all(1, ft.Colors.GREEN_200),
            content=ft.Column(
                controls=[
                    ft.Text("Resumen de objetos", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_900),
                    _info_row("Cantidad de objetos", len(self.state.objetos)),
                    _info_row("Suma precio_asignado", _format_decimal(total)),
                    _info_row("Total de venta derivado de objetos", _format_decimal(total)),
                ],
                spacing=8,
            ),
        )

    def _build_buyers_placeholder(self) -> ft.Control:
        return ft.Container(
            padding=24,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Paso 3 — Compradores pendiente", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Placeholder técnico: todavía no se implementa la carga de compradores.",
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
        if self.state.origen == "RESERVA" or self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            controls.append(_info_row("Reserva", self._reservation_status()))
        controls.extend(
            [
                _info_row("Objetos", len(self.state.objetos)),
                _info_row("Total derivado", _format_decimal(self._objects_total())),
                _info_row("Próximo paso", self._next_step_label()),
            ]
        )

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
        elif self.state.pantalla_actual == "OBJETOS":
            self.state.pantalla_actual = "COMPRADORES_PLACEHOLDER"
        else:
            self.state.pantalla_actual = "OBJETOS"
        self._render()

    def _previous_step(self, _: ft.ControlEvent | None = None) -> None:
        if self.state.pantalla_actual == "ORIGEN":
            return
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            self.state.pantalla_actual = "ORIGEN"
        elif self.state.pantalla_actual == "COMPRADORES_PLACEHOLDER":
            self.state.pantalla_actual = "OBJETOS"
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
        if self.state.pantalla_actual == "OBJETOS":
            return bool(self.state.objetos) and all(
                _parse_decimal(objeto.precio_asignado) is not None for objeto in self.state.objetos
            )
        return False

    def _on_objeto_selected(self, selected: dict[str, Any] | None) -> None:
        self.objeto_seleccionado = selected
        self.precio_objeto_value = ""
        self.precio_objeto_field.value = ""
        self.precio_objeto_error = None
        if self.objeto_selector is not None:
            self.objeto_selector.selected_panel.visible = False
        self._render()

    def _clear_selected_object(self, _: ft.ControlEvent | None = None) -> None:
        self.objeto_seleccionado = None
        self.objeto_selector = None
        self.precio_objeto_value = ""
        self.precio_objeto_field.value = ""
        self.precio_objeto_error = None
        self._render()

    def _on_precio_objeto_change(self, _: ft.ControlEvent) -> None:
        self.precio_objeto_value = str(self.precio_objeto_field.value or "")

    def _selected_price_validation_message(self, *, show_required: bool) -> str | None:
        raw_value = self.precio_objeto_value.strip()
        if not raw_value:
            return "precio_asignado es obligatorio." if show_required else None
        if self._parse_selected_price() is None:
            return "precio_asignado debe ser un decimal finito mayor que cero."
        return None

    def _parse_selected_price(self) -> Decimal | None:
        return _parse_decimal(self.precio_objeto_value)

    def _is_duplicate_selected_object(self) -> bool:
        if self.objeto_seleccionado is None:
            return False
        return any(_same_object_payload(objeto, self.objeto_seleccionado) for objeto in self.state.objetos)

    def _add_selected_object(self, _: ft.ControlEvent | None = None) -> None:
        if self.objeto_seleccionado is None:
            return
        self.precio_objeto_value = str(self.precio_objeto_field.value or self.precio_objeto_value or "")
        self.precio_objeto_error = self._selected_price_validation_message(show_required=True)
        precio = self._parse_selected_price()
        if self.precio_objeto_error is not None or precio is None or self._is_duplicate_selected_object():
            self._render()
            return

        tipo_objeto = str(self.objeto_seleccionado.get("tipo_objeto") or "")
        id_inmueble = self.objeto_seleccionado.get("id_inmueble") if tipo_objeto == "INMUEBLE" else None
        id_unidad_funcional = (
            self.objeto_seleccionado.get("id_unidad_funcional") if tipo_objeto == "UNIDAD_FUNCIONAL" else None
        )
        self.state.objetos.append(
            ObjetoVentaWizardDraft(
                tipo_objeto=tipo_objeto,
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                texto_visual=str(self.objeto_seleccionado.get("texto_visual") or "-"),
                precio_asignado=_format_decimal(precio),
            )
        )
        self.objeto_seleccionado = None
        self.objeto_selector = None
        self.precio_objeto_value = ""
        self.precio_objeto_field.value = ""
        self.precio_objeto_error = None
        self._render()

    def _remove_object(self, index: int) -> None:
        if 0 <= index < len(self.state.objetos):
            self.state.objetos.pop(index)
        self._render()

    def _objects_total(self) -> Decimal:
        total = Decimal("0")
        for objeto in self.state.objetos:
            parsed = _parse_decimal(objeto.precio_asignado)
            if parsed is not None:
                total += parsed
        return total

    def _origin_label(self) -> str:
        if self.state.origen == "RESERVA":
            return "Desde reserva"
        if self.state.origen == "DIRECTA":
            return "Venta directa"
        return "No seleccionado"

    def _reservation_status(self) -> str:
        return self.state.texto_visual_reserva or "pendiente de selección"

    def _next_step_label(self) -> str:
        if self.state.pantalla_actual == "OBJETOS":
            return "cargar compradores" if self._can_advance() else "cargar objetos de venta"
        if self.state.pantalla_actual == "COMPRADORES_PLACEHOLDER":
            return "cargar compradores"
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


def _parse_decimal(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value or "").strip())
        if not parsed.is_finite() or parsed <= 0:
            return None
    except (InvalidOperation, ValueError):
        return None
    return parsed


def _format_decimal(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def _format_money(value: Any) -> str:
    parsed = _parse_decimal(value)
    return _format_decimal(parsed) if parsed is not None else str(value or "-")


def _object_id_label_value(payload: dict[str, Any]) -> tuple[str, Any]:
    if payload.get("tipo_objeto") == "UNIDAD_FUNCIONAL":
        return "id_unidad_funcional", payload.get("id_unidad_funcional")
    return "id_inmueble", payload.get("id_inmueble")


def _same_object_payload(objeto: ObjetoVentaWizardDraft, payload: dict[str, Any]) -> bool:
    return (
        objeto.tipo_objeto == payload.get("tipo_objeto")
        and objeto.id_inmueble == payload.get("id_inmueble")
        and objeto.id_unidad_funcional == payload.get("id_unidad_funcional")
    )


def _badge(text: str, bgcolor: ft.ColorValue, border_color: ft.ColorValue) -> ft.Control:
    return ft.Container(
        padding=ft.Padding(left=8, top=4, right=8, bottom=4),
        border_radius=14,
        bgcolor=bgcolor,
        border=_border_all(1, border_color),
        content=ft.Text(text, size=12, color=ft.Colors.BLUE_GREY_800),
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
