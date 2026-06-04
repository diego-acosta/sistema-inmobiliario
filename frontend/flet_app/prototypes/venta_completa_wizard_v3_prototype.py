"""Prototipo Flet del wizard venta completa V3 - Datos iniciales antes de objetos.

Uso:
  cd frontend/flet_app
  python prototypes/venta_completa_wizard_v3_prototype.py

Alcance:
  - Prototipo UI aislado del dominio comercial, sin llamadas a backend.
  - Nueva base de iteracion pantalla por pantalla para venta completa V3.
  - Implementa Pantalla 1 - Origen, Pantalla 1B - Seleccionar reserva,
    Pantalla 2 - Datos iniciales de venta, Pantalla 3 - Objetos de venta,
    Pantalla 4 - Compradores y Pantalla 5 - Forma de pago.
  - No modifica backend, SQL, caja, pagos, recibos ni documental.
  - Pide moneda antes de cargar precio_asignado por objeto; no pide id_venta,
    no calcula cronograma local, deuda individual por comprador ni implementa datos
    comerciales completos, subwizard de financiacion, cronograma local, plan financiado
    ni cronograma local, interes, indexacion, refuerzos internos, saldo final
    ni revision/confirmacion.
  - Nota compradores: el objetivo final para RESERVA es mostrar y validar
    compradores heredados desde datos reales de reserva; este V3 los deja como
    pendiente visual hasta integrar backend/buscador real. DIRECTA si usa
    buscador de persona y carga manual en estado local demo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

import flet as ft

from components.search_selector_demo import SearchSelectorDemo, create_search_selector_demo


OrigenVenta = Literal["RESERVA", "DIRECTA"]
FormaPagoWizard = Literal["CONTADO", "FINANCIADO"]
PantallaWizard = Literal[
    "ORIGEN",
    "SELECCIONAR_RESERVA",
    "DATOS_INICIALES",
    "OBJETOS",
    "COMPRADORES",
    "FORMA_PAGO",
    "PLAN_ANTICIPO",
    "PLAN_TRAMOS",
    "PLAN_SALDO_PLACEHOLDER",
    "PASO_6_PLACEHOLDER",
]


MONEDAS_DEMO = ["ARS", "USD", "EUR"]


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


DEMO_PERSONAS_COMPRADORAS: list[dict[str, Any]] = [
    {
        "id_persona": 201,
        "codigo_persona": "PER-000201",
        "nombre": "Juan",
        "apellido": "Perez",
        "documento": "DNI 30111222",
        "resumen": "Persona humana disponible para actuar como comprador demo.",
    },
    {
        "id_persona": 202,
        "codigo_persona": "PER-000202",
        "nombre": "Maria",
        "apellido": "Gomez",
        "documento": "DNI 28999888",
        "resumen": "Compradora demo para validar operaciones con mas de una persona.",
    },
    {
        "id_persona": 203,
        "codigo_persona": "PER-000203",
        "nombre": "Sofia",
        "apellido": "Martinez",
        "documento": "DNI 33444555",
        "resumen": "Persona demo con datos visibles sin priorizar el ID tecnico.",
    },
    {
        "id_persona": 204,
        "codigo_persona": "PER-000204",
        "razon_social": "Constructora Rio Sur SA",
        "documento": "CUIT 30-71112223-4",
        "resumen": "Persona juridica demo para validar busqueda por razon social.",
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
class CompradorWizardDraft:
    id_persona: int
    texto_visual: str
    porcentaje_responsabilidad: str
    id_rol_participacion: str


@dataclass
class TramoCuotasWizardDraft:
    importe_total_bloque: str
    cantidad_cuotas: int
    fecha_primer_vencimiento_iso: str
    fecha_primer_vencimiento_display: str
    periodicidad: Literal["MENSUAL"] = "MENSUAL"
    metodo_liquidacion: Literal["SIN_INTERES"] = "SIN_INTERES"


@dataclass
class WizardVentaCompletaV3State:
    """Estado minimo del wizard V3 hasta Pantalla 3 - Compradores.

    Conserva origen/reserva y una lista de objetos comerciales demo con XOR
    visual entre inmueble y unidad funcional, sin persistencia ni backend.
    """

    origen: OrigenVenta | None = None
    id_reserva_venta: int | None = None
    version_registro: int | None = None
    texto_visual_reserva: str | None = None
    reserva_demo: dict[str, Any] | None = None
    moneda: str = "ARS"
    fecha_venta_iso: str = ""
    codigo_venta: str = ""
    observaciones_comerciales: str = ""
    objetos: list[ObjetoVentaWizardDraft] = field(default_factory=list)
    compradores: list[CompradorWizardDraft] = field(default_factory=list)
    forma_pago: FormaPagoWizard | None = None
    fecha_pago_contado_iso: str = ""
    fecha_pago_contado_display: str = ""
    fecha_pago_contado_error: str | None = None
    tiene_anticipo: bool = False
    importe_anticipo: str = ""
    fecha_anticipo_iso: str = ""
    fecha_anticipo_display: str = ""
    fecha_anticipo_error: str | None = None
    importe_anticipo_error: str | None = None
    tramos_cuotas: list[TramoCuotasWizardDraft] = field(default_factory=list)
    tramo_capital_value: str = ""
    tramo_cantidad_cuotas_value: str = ""
    tramo_fecha_display: str = ""
    tramo_fecha_iso: str = ""
    tramo_capital_error: str | None = None
    tramo_cantidad_error: str | None = None
    tramo_fecha_error: str | None = None
    pantalla_actual: PantallaWizard = "ORIGEN"


class VentaCompletaWizardV3Prototype:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = WizardVentaCompletaV3State()
        self.reserva_selector: SearchSelectorDemo | None = None
        self.objeto_selector: SearchSelectorDemo | None = None
        self.comprador_selector: SearchSelectorDemo | None = None
        self.objeto_seleccionado: dict[str, Any] | None = None
        self.comprador_seleccionado: dict[str, Any] | None = None
        self.precio_objeto_value = ""
        self.moneda_selector_width = 220
        self.fecha_venta_display_value = ""
        self.fecha_venta_error: str | None = None
        self.fecha_venta_field = ft.TextField(
            label="Fecha de venta",
            hint_text="DD/MM/AAAA",
            width=220,
            on_change=self._on_fecha_venta_change,
        )
        self.fecha_venta_feedback = ft.Text(
            "Formato: DD/MM/AAAA",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.codigo_venta_field = ft.TextField(
            label="Código de venta (si corresponde)",
            width=280,
            on_change=self._on_codigo_venta_change,
        )
        self.observaciones_field = ft.TextField(
            label="Observaciones comerciales opcionales",
            multiline=True,
            min_lines=3,
            max_lines=5,
            on_change=self._on_observaciones_change,
        )
        self.precio_objeto_field = ft.TextField(
            label=f"Valor asignado al objeto ({self.state.moneda})",
            prefix_icon=ft.Icons.ATTACH_MONEY,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_precio_objeto_change,
        )
        self.precio_objeto_error: str | None = None
        self.porcentaje_comprador_value = ""
        self.porcentaje_comprador_field = ft.TextField(
            label="Responsabilidad pactada (%)",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_porcentaje_comprador_change,
        )
        self.rol_comprador_value = ""
        self.rol_comprador_field = ft.TextField(
            label="ID rol comprador backend",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_rol_comprador_change,
        )
        self.comprador_error: str | None = None
        self.fecha_pago_contado_field = ft.TextField(
            label="Fecha de pago / vencimiento",
            hint_text="DD/MM/AAAA",
            width=240,
            on_change=self._on_fecha_pago_contado_change,
        )
        self.fecha_pago_contado_feedback = ft.Text(
            "Formato: DD/MM/AAAA",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.importe_anticipo_field = ft.TextField(
            label="Importe anticipo",
            prefix_icon=ft.Icons.ATTACH_MONEY,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_importe_anticipo_change,
        )
        self.importe_anticipo_feedback = ft.Text(
            "Ingresá un importe mayor que 0 y menor o igual al total derivado.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.fecha_anticipo_field = ft.TextField(
            label="Fecha vencimiento anticipo",
            hint_text="DD/MM/AAAA",
            width=240,
            on_change=self._on_fecha_anticipo_change,
        )
        self.fecha_anticipo_feedback = ft.Text(
            "Formato: DD/MM/AAAA",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.tramo_capital_field = ft.TextField(
            label="Capital del tramo",
            prefix_icon=ft.Icons.ATTACH_MONEY,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_tramo_capital_change,
        )
        self.tramo_capital_feedback = ft.Text(
            "Podés asignar todo el capital restante o un valor menor.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.tramo_cantidad_field = ft.TextField(
            label="Cantidad total de cuotas",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_tramo_cantidad_change,
        )
        self.tramo_cantidad_feedback = ft.Text(
            "Ingresá un número entero mayor que 0.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.tramo_fecha_field = ft.TextField(
            label="Primer vencimiento",
            hint_text="DD/MM/AAAA",
            width=240,
            on_change=self._on_tramo_fecha_change,
        )
        self.tramo_fecha_feedback = ft.Text(
            "Formato: DD/MM/AAAA",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.anticipo_actual_summary_value = ft.Text(color=ft.Colors.BLUE_GREY_900, expand=True)
        self.capital_pendiente_summary_value = ft.Text(color=ft.Colors.BLUE_GREY_900, expand=True)
        self.next_button: ft.ElevatedButton | None = None

    def run(self) -> None:
        self.page.title = "Wizard venta completa V3 - Datos iniciales"
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
        if self.state.pantalla_actual == "DATOS_INICIALES":
            return self._build_initial_sale_data_step()
        if self.state.pantalla_actual == "OBJETOS":
            return self._build_objects_step()
        if self.state.pantalla_actual == "COMPRADORES":
            return self._build_buyers_step()
        if self.state.pantalla_actual == "FORMA_PAGO":
            return self._build_payment_method_step()
        if self.state.pantalla_actual == "PLAN_ANTICIPO":
            return self._build_financed_plan_advance_step()
        if self.state.pantalla_actual == "PLAN_TRAMOS":
            return self._build_financed_plan_installments_step()
        if self.state.pantalla_actual in {"PLAN_SALDO_PLACEHOLDER", "PASO_6_PLACEHOLDER"}:
            return self._build_step_6_placeholder()
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

    def _build_initial_sale_data_step(self) -> ft.Control:
        currency_locked = self._currency_locked_by_objects()
        self.fecha_venta_field.value = self._date_display_value()
        self._sync_fecha_venta_feedback()
        self.codigo_venta_field.value = self.state.codigo_venta
        self.observaciones_field.value = self.state.observaciones_comerciales
        currency_help = (
            "La moneda no puede cambiarse porque ya hay objetos cargados. Para cambiarla, primero quitá los objetos de venta."
            if currency_locked
            else "Los valores asignados a los objetos se cargarán en esta moneda."
        )
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Datos iniciales de venta", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Definí la moneda antes de cargar objetos para que cada precio_asignado tenga contexto comercial.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Row(
                        controls=[
                            self._build_currency_selector(currency_locked),
                            ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            self.fecha_venta_field,
                                            ft.IconButton(
                                                icon=ft.Icons.CALENDAR_MONTH,
                                                tooltip="Seleccionar fecha",
                                                on_click=self._open_fecha_venta_picker,
                                            ),
                                        ],
                                        wrap=True,
                                        spacing=8,
                                    ),
                                    self.fecha_venta_feedback,
                                ],
                                spacing=4,
                            ),
                            self.codigo_venta_field,
                        ],
                        wrap=True,
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    self._build_help_card(
                        currency_help,
                        ft.Colors.AMBER_50 if currency_locked else ft.Colors.BLUE_50,
                        ft.Colors.AMBER_200 if currency_locked else ft.Colors.BLUE_200,
                    ),
                    self.observaciones_field,
                    self._build_help_card(
                        "La moneda se conservará para el payload futuro de generar_venta, condiciones_comerciales y plan_pago_v2. La fecha se muestra como DD/MM/AAAA y se conserva internamente como YYYY-MM-DD. No se implementan forma de pago, plan ni cronograma local en este prototipo.",
                        ft.Colors.AMBER_50,
                        ft.Colors.AMBER_200,
                    ),
                ],
                spacing=14,
            ),
        )

    def _build_objects_step(self) -> ft.Control:
        if not self._has_valid_currency():
            return ft.Container(
                padding=18,
                border_radius=14,
                bgcolor=ft.Colors.RED_50,
                border=_border_all(1, ft.Colors.RED_200),
                content=ft.Column(
                    controls=[
                        ft.Text("Objetos de venta bloqueado", size=24, weight=ft.FontWeight.W_700),
                        ft.Text(
                            "Seleccioná una moneda válida en Datos iniciales de venta antes de cargar objetos.",
                            color=ft.Colors.RED_800,
                        ),
                    ],
                    spacing=10,
                ),
            )
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
                f"Seleccioná los inmuebles o unidades funcionales incluidos en la operación y asigná el valor comercial de cada uno en {self._currency_label()}.",
                color=ft.Colors.BLUE_GREY_700,
            ),
            self._build_help_card(
                "Los valores asignados a los objetos se cargarán en esta moneda.",
                ft.Colors.BLUE_50,
                ft.Colors.BLUE_200,
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
        controls: list[ft.Control] = []
        if self.objeto_seleccionado is not None:
            controls.extend(
                [
                    self._build_selected_object_panel(),
                    self._build_help_card(
                        "La validación final de solapamiento entre inmueble completo y unidades funcionales la realiza el backend.",
                        ft.Colors.AMBER_50,
                        ft.Colors.AMBER_200,
                    ),
                ]
            )
        controls.extend([self._build_added_objects_list(), self._build_objects_total_summary()])
        return ft.Column(controls=controls, spacing=12)

    def _build_selected_object_panel(self) -> ft.Control:
        if self.objeto_seleccionado is None:
            return ft.Container()

        tipo_objeto = str(self.objeto_seleccionado.get("tipo_objeto") or "-")
        id_label, id_value = _object_id_label_value(self.objeto_seleccionado)
        duplicate = self._is_duplicate_selected_object()
        price_error = self.precio_objeto_error
        self.precio_objeto_field.label = f"Valor asignado al objeto ({self._currency_label()})"
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
                                f"precio_asignado ({self._currency_label()}): {_format_money(objeto.precio_asignado)}",
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
                    ft.Text(
                        f"Total derivado: {self._format_money_with_currency(total)}",
                        size=16,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.GREEN_900,
                    ),
                    _info_row("Cantidad de objetos", len(self.state.objetos)),
                    _info_row("Suma precio_asignado", self._format_money_with_currency(total)),
                    _info_row("Total derivado", self._format_money_with_currency(total)),
                ],
                spacing=8,
            ),
        )

    def _build_buyers_step(self) -> ft.Control:
        if self.state.origen == "RESERVA":
            return self._build_reserva_buyers_info_step()

        if self.comprador_selector is None:
            self.comprador_selector = create_search_selector_demo(
                title="Buscador de comprador/persona",
                placeholder="Nombre, documento, código o dato visible del comprador",
                selector_kind="persona",
                records=DEMO_PERSONAS_COMPRADORAS,
                on_selection_change=self._on_comprador_selected,
            )
            self._configure_comprador_selector_scroll()

        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Compradores", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Seleccioná los compradores de la operación y definí la responsabilidad pactada de cada uno.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Row(
                        controls=[
                            ft.Container(content=self.comprador_selector.view(), expand=True),
                            ft.Container(width=380, content=self._build_buyers_side_panel()),
                        ],
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ],
                spacing=14,
            ),
        )

    def _build_reserva_buyers_info_step(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Compradores de la reserva", size=24, weight=ft.FontWeight.W_700),
            ft.Text("Los compradores se heredan de la reserva seleccionada.", color=ft.Colors.BLUE_GREY_700),
            self._build_reserva_selected_card(),
            self._build_inherited_buyers_pending_card(),
            self._build_help_card(
                "No se cargarán compradores manuales, no se pedirá id_rol_participacion y no se enviarán compradores en el payload futuro para ventas desde reserva.",
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

    def _build_reserva_selected_card(self) -> ft.Control:
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Reserva seleccionada", size=18, weight=ft.FontWeight.W_700),
                    ft.Text(self.state.texto_visual_reserva or "Reserva pendiente", weight=ft.FontWeight.W_600),
                    _info_row("id_reserva_venta", self.state.id_reserva_venta),
                    _info_row("version_registro", self.state.version_registro),
                ],
                spacing=6,
            ),
        )

    def _build_inherited_buyers_pending_card(self) -> ft.Control:
        reserva_comprador = ""
        if self.state.reserva_demo is not None:
            reserva_comprador = str(self.state.reserva_demo.get("comprador") or "").strip()
        pending_controls: list[ft.Control] = [
            ft.Text("Compradores heredados", size=18, weight=ft.FontWeight.W_700),
            ft.Container(
                padding=12,
                border_radius=10,
                bgcolor=ft.Colors.BLUE_GREY_50,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            reserva_comprador or "Pendiente de datos reales de compradores de la reserva.",
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            "Pendiente/demo: la reserva demo solo expone un texto de comprador, no una lista validable de personas.",
                            size=12,
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                    ],
                    spacing=4,
                ),
            ),
            ft.Text(
                "En la integración productiva se mostrarán aquí los compradores precargados de la reserva y se validarán antes de confirmar.",
                size=12,
                color=ft.Colors.BLUE_GREY_700,
            ),
        ]
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=pending_controls, spacing=8),
        )

    def _configure_comprador_selector_scroll(self) -> None:
        if self.comprador_selector is None:
            return
        self.comprador_selector.results_column.height = 260
        self.comprador_selector.results_column.scroll = ft.ScrollMode.AUTO

    def _build_buyers_side_panel(self) -> ft.Control:
        controls: list[ft.Control] = []
        if self.comprador_seleccionado is not None:
            controls.append(self._build_selected_buyer_panel())
        controls.extend([self._build_added_buyers_list(), self._build_buyers_summary()])
        return ft.Column(controls=controls, spacing=12)

    def _build_selected_buyer_panel(self) -> ft.Control:
        if self.comprador_seleccionado is None:
            return ft.Container()

        duplicate = self._is_duplicate_selected_buyer()
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.BLUE_50,
            border=_border_all(1, ft.Colors.BLUE_200),
            content=ft.Column(
                controls=[
                    ft.Text("Comprador seleccionado", size=18, weight=ft.FontWeight.W_700),
                    ft.Text(str(self.comprador_seleccionado.get("texto_visual") or "-"), weight=ft.FontWeight.W_600),
                    _badge(
                        f"ID técnico secundario (id_persona): {self.comprador_seleccionado.get('id_persona') or '-'}",
                        ft.Colors.BLUE_GREY_50,
                        ft.Colors.BLUE_GREY_200,
                    ),
                    self.porcentaje_comprador_field,
                    ft.Text(
                        "Si es el único comprador, este campo puede quedar vacío y se asumirá 100%.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_600,
                    ),
                    self.rol_comprador_field,
                    ft.Text("Debe corresponder al rol COMPRADOR.", size=12, color=ft.Colors.BLUE_GREY_600),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "Agregar comprador",
                                icon=ft.Icons.PERSON_ADD_ALT_1,
                                disabled=duplicate,
                                on_click=self._add_selected_buyer,
                            ),
                            ft.OutlinedButton(
                                "Limpiar selección",
                                icon=ft.Icons.CLOSE,
                                on_click=self._clear_selected_buyer,
                            ),
                        ],
                        wrap=True,
                        spacing=8,
                    ),
                    ft.Text(
                        self.comprador_error or ("Este comprador ya fue agregado." if duplicate else ""),
                        size=12,
                        color=ft.Colors.RED_700,
                    ),
                ],
                spacing=8,
            ),
        )

    def _build_added_buyers_list(self) -> ft.Control:
        if not self.state.compradores:
            content: ft.Control = ft.Container(
                padding=12,
                border_radius=10,
                bgcolor=ft.Colors.BLUE_GREY_50,
                content=ft.Text("Todavía no agregaste compradores a la venta.", color=ft.Colors.BLUE_GREY_700),
            )
        else:
            content = ft.Container(
                height=240,
                content=ft.Column(
                    controls=[self._build_added_buyer_row(index, comprador) for index, comprador in enumerate(self.state.compradores)],
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
                controls=[ft.Text("Compradores agregados", size=18, weight=ft.FontWeight.W_700), content],
                spacing=8,
            ),
        )

    def _build_added_buyer_row(self, index: int, comprador: CompradorWizardDraft) -> ft.Control:
        porcentaje = comprador.porcentaje_responsabilidad or "vacío (se asumirá 100% si es único comprador)"
        return ft.Container(
            padding=12,
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(comprador.texto_visual, weight=ft.FontWeight.W_700),
                            ft.Text(f"id_persona: {comprador.id_persona}", size=12, color=ft.Colors.BLUE_GREY_700),
                            ft.Text(
                                f"id_rol_participacion: {comprador.id_rol_participacion}",
                                size=12,
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            ft.Text(
                                f"porcentaje_responsabilidad: {porcentaje}",
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
                        on_click=lambda _, item_index=index: self._remove_buyer(item_index),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _build_buyers_summary(self) -> ft.Control:
        total = self._buyers_responsibility_total()
        validation_error = self._buyers_validation_error(total)
        has_error = validation_error is not None
        controls: list[ft.Control] = [
            ft.Text(
                "Resumen de compradores",
                size=18,
                weight=ft.FontWeight.W_700,
                color=ft.Colors.RED_900 if has_error else ft.Colors.GREEN_900,
            ),
            _info_row("Cantidad de compradores", len(self.state.compradores)),
            _info_row("Suma de responsabilidad", self._buyers_responsibility_total_label(total)),
            _info_row("Estado", self._buyers_responsibility_status(total)),
        ]
        if validation_error is not None:
            controls.append(
                ft.Container(
                    padding=10,
                    border_radius=8,
                    bgcolor=ft.Colors.RED_50,
                    border=_border_all(1, ft.Colors.RED_200),
                    content=ft.Text(validation_error, color=ft.Colors.RED_800, weight=ft.FontWeight.W_600),
                )
            )
        controls.append(
            ft.OutlinedButton(
                "Distribuir en partes iguales",
                icon=ft.Icons.CALL_SPLIT,
                disabled=not self.state.compradores,
                on_click=self._distribute_buyers_equally,
            )
        )
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.RED_50 if has_error else ft.Colors.GREEN_50,
            border=_border_all(1, ft.Colors.RED_200 if has_error else ft.Colors.GREEN_200),
            content=ft.Column(controls=controls, spacing=8),
        )

    def _build_payment_method_step(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Forma de pago", size=24, weight=ft.FontWeight.W_700),
            ft.Text(
                "Elegí cómo se pagará la operación. El total surge de los objetos seleccionados.",
                color=ft.Colors.BLUE_GREY_700,
            ),
            self._build_payment_total_card(),
            ft.Row(
                controls=[
                    self._build_payment_method_card(
                        payment_method="CONTADO",
                        title="Contado",
                        description="El total se paga en una única obligación.",
                        icon=ft.Icons.PAYMENTS_OUTLINED,
                    ),
                    self._build_payment_method_card(
                        payment_method="FINANCIADO",
                        title="Financiado",
                        description="El total se estructura en anticipo, cuotas, refuerzos y/o saldo.",
                        icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                    ),
                ],
                spacing=14,
            ),
        ]
        if self.state.forma_pago == "CONTADO":
            controls.append(self._build_cash_payment_data_section())
        elif self.state.forma_pago == "FINANCIADO":
            controls.append(
                self._build_help_card(
                    "El plan se cargará en el siguiente paso.",
                    ft.Colors.BLUE_50,
                    ft.Colors.BLUE_200,
                )
            )

        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=14),
        )

    def _build_payment_total_card(self) -> ft.Control:
        total = self._objects_total()
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.GREEN_50,
            border=_border_all(1, ft.Colors.GREEN_200),
            content=ft.Column(
                controls=[
                    ft.Text("Total derivado de la venta", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_900),
                    _info_row("Moneda seleccionada", self._currency_label()),
                    _info_row("Total de venta derivado de objetos", self._format_money_with_currency(total)),
                ],
                spacing=8,
            ),
        )

    def _build_payment_method_card(
        self,
        *,
        payment_method: FormaPagoWizard,
        title: str,
        description: str,
        icon: str,
    ) -> ft.Control:
        selected = self.state.forma_pago == payment_method
        return ft.Container(
            expand=True,
            padding=18,
            border_radius=14,
            border=_border_all(2 if selected else 1, ft.Colors.BLUE_500 if selected else ft.Colors.BLUE_GREY_100),
            bgcolor=ft.Colors.BLUE_50 if selected else ft.Colors.WHITE,
            on_click=lambda _, selected_method=payment_method: self._select_payment_method(selected_method),
            content=ft.Column(
                controls=[
                    ft.Icon(icon, size=32, color=ft.Colors.BLUE_700 if selected else ft.Colors.BLUE_GREY_500),
                    ft.Text(title, size=18, weight=ft.FontWeight.W_700),
                    ft.Text(description, color=ft.Colors.BLUE_GREY_700),
                ],
                spacing=8,
            ),
        )

    def _build_cash_payment_data_section(self) -> ft.Control:
        self.fecha_pago_contado_field.value = self._cash_payment_date_display_value()
        self._sync_fecha_pago_contado_feedback()
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Datos de pago contado", size=18, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Construcción futura: tipo_pago CONTADO, monto_total_plan igual al total derivado y bloque único CONTADO con fecha de vencimiento.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Row(
                        controls=[
                            self.fecha_pago_contado_field,
                            ft.IconButton(
                                icon=ft.Icons.CALENDAR_MONTH,
                                tooltip="Abrir calendario",
                                on_click=self._open_fecha_pago_contado_picker,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    self.fecha_pago_contado_feedback,
                    _info_row("Monto total plan futuro", self._format_money_with_currency(self._objects_total())),
                ],
                spacing=8,
            ),
        )

    def _build_financed_plan_advance_step(self) -> ft.Control:
        self._validate_advance_state()
        self.importe_anticipo_field.value = self.state.importe_anticipo
        self.fecha_anticipo_field.value = self._advance_date_display_value()
        self._sync_importe_anticipo_feedback()
        self._sync_fecha_anticipo_feedback()
        total = self._objects_total()
        advance = self._valid_advance_amount_or_zero()
        pending = total - advance
        controls: list[ft.Control] = [
            ft.Text("Plan de pago — Anticipo", size=24, weight=ft.FontWeight.W_700),
            ft.Text(
                "Definí si la operación tendrá anticipo. El saldo restante se asignará luego a cuotas, refuerzos o saldo final.",
                color=ft.Colors.BLUE_GREY_700,
            ),
            self._build_advance_summary_card(total, advance, pending),
            ft.Text("¿Tiene anticipo?", size=16, weight=ft.FontWeight.W_700),
            ft.Row(
                controls=[
                    self._build_advance_toggle_card(has_advance=False, label="No"),
                    self._build_advance_toggle_card(has_advance=True, label="Sí"),
                ],
                spacing=12,
            ),
        ]
        if self.state.tiene_anticipo:
            controls.append(self._build_advance_form_section())
        else:
            controls.append(
                self._build_help_card(
                    "Todo el total quedará pendiente para cuotas, refuerzos o saldo final.",
                    ft.Colors.BLUE_50,
                    ft.Colors.BLUE_200,
                )
            )

        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=14),
        )

    def _build_advance_summary_card(self, total: Decimal, advance: Decimal, pending: Decimal) -> ft.Control:
        self.anticipo_actual_summary_value.value = self._format_money_with_currency(advance)
        self.capital_pendiente_summary_value.value = self._format_money_with_currency(pending)
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.GREEN_50,
            border=_border_all(1, ft.Colors.GREEN_200),
            content=ft.Column(
                controls=[
                    ft.Text("Resumen visual del plan", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_900),
                    _info_row("Total de venta derivado de objetos", self._format_money_with_currency(total)),
                    _info_row_control("Anticipo actual", self.anticipo_actual_summary_value),
                    _info_row_control("Capital pendiente después de anticipo", self.capital_pendiente_summary_value),
                ],
                spacing=8,
            ),
        )

    def _build_advance_toggle_card(self, *, has_advance: bool, label: str) -> ft.Control:
        selected = self.state.tiene_anticipo == has_advance
        return ft.Container(
            width=140,
            padding=14,
            border_radius=12,
            border=_border_all(2 if selected else 1, ft.Colors.BLUE_500 if selected else ft.Colors.BLUE_GREY_100),
            bgcolor=ft.Colors.BLUE_50 if selected else ft.Colors.WHITE,
            on_click=lambda _, selected_value=has_advance: self._select_tiene_anticipo(selected_value),
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                        color=ft.Colors.BLUE_700 if selected else ft.Colors.BLUE_GREY_500,
                    ),
                    ft.Text(label, weight=ft.FontWeight.W_700),
                ],
                spacing=8,
            ),
        )

    def _build_advance_form_section(self) -> ft.Control:
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Datos del anticipo", size=18, weight=ft.FontWeight.W_700),
                    self.importe_anticipo_field,
                    self.importe_anticipo_feedback,
                    ft.Row(
                        controls=[
                            self.fecha_anticipo_field,
                            ft.IconButton(
                                icon=ft.Icons.CALENDAR_MONTH,
                                tooltip="Abrir calendario",
                                on_click=self._open_fecha_anticipo_picker,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    self.fecha_anticipo_feedback,
                    ft.Text(
                        "El anticipo se incluirá como bloque ANTICIPO del Plan Pago V2.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                ],
                spacing=8,
            ),
        )


    def _build_financed_plan_installments_step(self) -> ft.Control:
        self._sync_installment_form_controls()
        capital_base = self._capital_pending_after_advance()
        capital_assigned = self._capital_assigned_to_installments()
        capital_remaining = self._capital_remaining_for_installments()
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Plan de pago — Tramos de cuotas", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Asigná el capital pendiente a uno o más tramos de cuotas. El plan no calcula cronograma local; solo prepara los datos para Plan Pago V2.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    self._build_installments_top_summary(capital_base, capital_assigned, capital_remaining),
                    self._build_installment_form_section(),
                    self._build_added_installments_list(),
                    self._build_installments_bottom_summary(capital_base, capital_assigned, capital_remaining),
                ],
                spacing=14,
            ),
        )

    def _build_installments_top_summary(
        self,
        capital_base: Decimal,
        capital_assigned: Decimal,
        capital_remaining: Decimal,
    ) -> ft.Control:
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.GREEN_50,
            border=_border_all(1, ft.Colors.GREEN_200),
            content=ft.Column(
                controls=[
                    ft.Text("Resumen de capital", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_900),
                    _info_row("Total derivado de objetos", self._format_money_with_currency(self._objects_total())),
                    _info_row("Anticipo", self._format_money_with_currency(self._valid_advance_amount_or_zero())),
                    _info_row("Capital pendiente para asignar a tramos", self._format_money_with_currency(capital_base)),
                    _info_row("Capital ya asignado a tramos", self._format_money_with_currency(capital_assigned)),
                    _info_row("Capital restante", self._format_money_with_currency(capital_remaining)),
                ],
                spacing=8,
            ),
        )

    def _build_installment_form_section(self) -> ft.Control:
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Crear tramo", size=18, weight=ft.FontWeight.W_700),
                    self.tramo_capital_field,
                    self.tramo_capital_feedback,
                    self.tramo_cantidad_field,
                    self.tramo_cantidad_feedback,
                    ft.Row(
                        controls=[
                            self.tramo_fecha_field,
                            ft.IconButton(
                                icon=ft.Icons.CALENDAR_MONTH,
                                tooltip="Abrir calendario",
                                on_click=self._open_tramo_fecha_picker,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    self.tramo_fecha_feedback,
                    _info_row("Periodicidad", "MENSUAL"),
                    _info_row("Método", "Cuotas fijas / sin interés"),
                    ft.ElevatedButton(
                        "Agregar tramo",
                        icon=ft.Icons.ADD,
                        on_click=self._add_installment_block,
                    ),
                    ft.Text(
                        "Construcción futura del bloque: tipo_bloque TRAMO_CUOTAS, importe_total_bloque, cantidad_cuotas, fecha_primer_vencimiento, periodicidad MENSUAL y metodo_liquidacion SIN_INTERES.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                ],
                spacing=8,
            ),
        )

    def _build_added_installments_list(self) -> ft.Control:
        if not self.state.tramos_cuotas:
            content: ft.Control = ft.Container(
                padding=12,
                border_radius=10,
                bgcolor=ft.Colors.BLUE_GREY_50,
                content=ft.Text("Todavía no agregaste tramos de cuotas.", color=ft.Colors.BLUE_GREY_700),
            )
        else:
            content = ft.Container(
                height=260,
                content=ft.Column(
                    controls=[
                        self._build_added_installment_row(index, tramo)
                        for index, tramo in enumerate(self.state.tramos_cuotas)
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
                controls=[ft.Text("Tramos agregados", size=18, weight=ft.FontWeight.W_700), content],
                spacing=8,
            ),
        )

    def _build_added_installment_row(self, index: int, tramo: TramoCuotasWizardDraft) -> ft.Control:
        return ft.Container(
            padding=12,
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(f"Tramo {index + 1}", weight=ft.FontWeight.W_700),
                            ft.Text(
                                f"Capital del tramo: {self._format_money_with_currency(_parse_decimal(tramo.importe_total_bloque) or Decimal('0'))}",
                                size=12,
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            ft.Text(f"Cantidad de cuotas: {tramo.cantidad_cuotas}", size=12, color=ft.Colors.BLUE_GREY_700),
                            ft.Text(
                                f"Primer vencimiento: {tramo.fecha_primer_vencimiento_display}",
                                size=12,
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            ft.Text(f"Periodicidad: {tramo.periodicidad}", size=12, color=ft.Colors.BLUE_GREY_700),
                            ft.Text(f"Método: {tramo.metodo_liquidacion}", size=12, color=ft.Colors.BLUE_GREY_700),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.OutlinedButton(
                        "Quitar",
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=lambda _, item_index=index: self._remove_installment_block(item_index),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _build_installments_bottom_summary(
        self,
        capital_base: Decimal,
        capital_assigned: Decimal,
        capital_remaining: Decimal,
    ) -> ft.Control:
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.BLUE_50,
            border=_border_all(1, ft.Colors.BLUE_200),
            content=ft.Column(
                controls=[
                    ft.Text("Resumen de tramos", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_900),
                    _info_row("Capital base", self._format_money_with_currency(capital_base)),
                    _info_row("Capital asignado", self._format_money_with_currency(capital_assigned)),
                    _info_row("Capital restante", self._format_money_with_currency(capital_remaining)),
                    _info_row("Cantidad de tramos", len(self.state.tramos_cuotas)),
                    _info_row("Cantidad estimada de obligaciones", self._installments_obligations_count()),
                ],
                spacing=8,
            ),
        )

    def _build_step_6_placeholder(self) -> ft.Control:
        if self.state.pantalla_actual == "PLAN_SALDO_PLACEHOLDER":
            title = "Pantalla 6C — Saldo final pendiente"
            description = "Placeholder futuro: acá se cargará saldo final o revisión pendiente sin calcular cronograma local."
        elif self.state.forma_pago == "FINANCIADO":
            title = "Paso 6 — Plan de pago pendiente"
            description = "Placeholder futuro: acá se continuará el subwizard de financiación sin calcular cronograma local."
        else:
            title = "Paso 6 — Revisión de venta pendiente"
            description = "Placeholder futuro: acá se revisará la venta contado antes de confirmar, sin mostrar payload final."
        return ft.Container(
            padding=24,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=self._build_step_6_placeholder_rows(title, description),
                spacing=8,
            ),
        )

    def _build_step_6_placeholder_rows(self, title: str, description: str) -> list[ft.Control]:
        controls: list[ft.Control] = [
            ft.Text(title, size=24, weight=ft.FontWeight.W_700),
            ft.Text(description, color=ft.Colors.BLUE_GREY_700),
            _info_row("Forma de pago", self._payment_method_status()),
            _info_row("Moneda definida", self._currency_label()),
            _info_row("Total derivado desde objetos", self._format_money_with_currency(self._objects_total())),
        ]
        if self.state.forma_pago == "FINANCIADO":
            controls.extend(
                [
                    _info_row("Anticipo", self._advance_status()),
                    _info_row("Capital pendiente después de anticipo", self._format_money_with_currency(self._capital_pending_after_advance())),
                    _info_row("Tramos", len(self.state.tramos_cuotas)),
                    _info_row("Capital asignado", self._format_money_with_currency(self._capital_assigned_to_installments())),
                    _info_row("Capital restante", self._format_money_with_currency(self._capital_remaining_for_installments())),
                ]
            )
        return controls

    def _build_flow_state_panel(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Estado del flujo", size=20, weight=ft.FontWeight.W_700),
            _info_row("Origen", self._origin_label()),
        ]
        if self.state.origen == "RESERVA" or self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            controls.append(_info_row("Reserva", self._reservation_status()))
        controls.extend(
            [
                _info_row("Moneda", self._currency_label()),
                _info_row("Objetos", len(self.state.objetos)),
                _info_row("Total derivado", self._format_money_with_currency(self._objects_total())),
                _info_row("Compradores", self._buyers_flow_status()),
                _info_row("Forma de pago", self._payment_method_status()),
            ]
        )
        if self.state.forma_pago == "FINANCIADO":
            controls.extend(
                [
                    _info_row("Anticipo", self._advance_status()),
                    _info_row(
                        "Capital pendiente después de anticipo",
                        self._format_money_with_currency(self._capital_pending_after_advance()),
                    ),
                    _info_row("Tramos", len(self.state.tramos_cuotas)),
                    _info_row("Capital asignado", self._format_money_with_currency(self._capital_assigned_to_installments())),
                    _info_row("Capital restante", self._format_money_with_currency(self._capital_remaining_for_installments())),
                ]
            )
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
        self.next_button = ft.ElevatedButton(
            "Siguiente",
            icon=ft.Icons.ARROW_FORWARD,
            disabled=not self._can_advance(),
            on_click=self._next_step,
        )
        return ft.Row(
            controls=[
                ft.OutlinedButton(
                    "Anterior",
                    icon=ft.Icons.ARROW_BACK,
                    disabled=self.state.pantalla_actual == "ORIGEN",
                    on_click=self._previous_step,
                ),
                ft.Container(expand=True),
                self.next_button,
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
            self.state.compradores.clear()
            self.comprador_selector = None
            self.comprador_seleccionado = None
        self.state.origen = origin
        self._render()

    def _build_currency_selector(self, currency_locked: bool) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Moneda", size=12, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_GREY_700),
                ft.Row(
                    controls=[self._build_currency_card(moneda, currency_locked) for moneda in MONEDAS_DEMO],
                    spacing=8,
                    wrap=True,
                ),
            ],
            spacing=6,
            width=self.moneda_selector_width,
        )

    def _build_currency_card(self, moneda: str, currency_locked: bool) -> ft.Control:
        selected = self.state.moneda == moneda
        if selected:
            bgcolor = ft.Colors.BLUE_600 if not currency_locked else ft.Colors.BLUE_GREY_400
            border_color = ft.Colors.BLUE_700 if not currency_locked else ft.Colors.BLUE_GREY_500
            text_color = ft.Colors.WHITE
        else:
            bgcolor = ft.Colors.BLUE_GREY_50 if currency_locked else ft.Colors.WHITE
            border_color = ft.Colors.BLUE_GREY_100 if currency_locked else ft.Colors.BLUE_200
            text_color = ft.Colors.BLUE_GREY_500 if currency_locked else ft.Colors.BLUE_700
        return ft.Container(
            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
            border_radius=10,
            bgcolor=bgcolor,
            border=_border_all(2 if selected else 1, border_color),
            on_click=None if currency_locked else lambda _, selected_moneda=moneda: self._select_moneda(selected_moneda),
            content=ft.Text(moneda, weight=ft.FontWeight.W_700, color=text_color),
        )

    def _select_moneda(self, moneda: str) -> None:
        selected_currency = str(moneda or "").strip().upper()
        if selected_currency not in MONEDAS_DEMO or self._currency_locked_by_objects():
            self._render()
            return
        self.state.moneda = selected_currency
        self.precio_objeto_field.label = f"Valor asignado al objeto ({self._currency_label()})"
        self._render()

    def _on_fecha_venta_change(self, event: ft.ControlEvent) -> None:
        raw_value = str(event.control.value or "")
        self.fecha_venta_display_value = raw_value
        if not raw_value.strip():
            self.state.fecha_venta_iso = ""
            self.fecha_venta_error = None
        else:
            parsed_date = _parse_date_ar(raw_value)
            if parsed_date is None:
                self.fecha_venta_error = "Fecha inválida. Usá formato DD/MM/AAAA."
            else:
                self.state.fecha_venta_iso = parsed_date
                self.fecha_venta_display_value = _format_date_ar(parsed_date)
                event.control.value = self.fecha_venta_display_value
                self.fecha_venta_error = None
        self._sync_fecha_venta_feedback()
        self._refresh_navigation_controls()
        self.page.update()

    def _open_fecha_venta_picker(self, _: ft.ControlEvent | None = None) -> None:
        if not hasattr(ft, "DatePicker"):
            if self.fecha_venta_error is None:
                self.fecha_venta_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.fecha_venta_feedback.color = ft.Colors.AMBER_800
            self._refresh_navigation_controls()
            self.page.update()
            return
        selected_date = _date_from_iso(self.state.fecha_venta_iso) or date.today()
        try:
            picker = ft.DatePicker(
                value=selected_date,
                first_date=date(1900, 1, 1),
                last_date=date(2100, 12, 31),
            )
            picker.on_change = self._on_fecha_picker_change
            self.page.overlay.append(picker)
            picker.open = True
            self.page.update()
        except Exception:
            if self.fecha_venta_error is None:
                self.fecha_venta_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.fecha_venta_feedback.color = ft.Colors.AMBER_800
            self._refresh_navigation_controls()
            self.page.update()

    def _on_fecha_picker_change(self, event: ft.ControlEvent) -> None:
        selected_date = getattr(event.control, "value", None)
        if selected_date is None:
            return
        if isinstance(selected_date, datetime):
            selected_date = selected_date.date()
        if isinstance(selected_date, date):
            self.state.fecha_venta_iso = selected_date.isoformat()
            self.fecha_venta_display_value = _format_date_ar(self.state.fecha_venta_iso)
            self.fecha_venta_field.value = self.fecha_venta_display_value
            self.fecha_venta_error = None
            self._sync_fecha_venta_feedback()
            self._refresh_navigation_controls()
            self.page.update()

    def _on_codigo_venta_change(self, event: ft.ControlEvent) -> None:
        self.state.codigo_venta = str(event.control.value or "")

    def _on_observaciones_change(self, event: ft.ControlEvent) -> None:
        self.state.observaciones_comerciales = str(event.control.value or "")

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
        elif self.state.pantalla_actual in {"ORIGEN", "SELECCIONAR_RESERVA"}:
            self.state.pantalla_actual = "DATOS_INICIALES"
        elif self.state.pantalla_actual == "DATOS_INICIALES":
            self.state.pantalla_actual = "OBJETOS"
        elif self.state.pantalla_actual == "OBJETOS":
            self.state.pantalla_actual = "COMPRADORES"
        elif self.state.pantalla_actual == "COMPRADORES":
            self.state.pantalla_actual = "FORMA_PAGO"
        elif self.state.pantalla_actual == "FORMA_PAGO":
            if self.state.forma_pago == "FINANCIADO":
                self.state.pantalla_actual = "PLAN_ANTICIPO"
            else:
                self.state.pantalla_actual = "PASO_6_PLACEHOLDER"
        elif self.state.pantalla_actual == "PLAN_ANTICIPO":
            self.state.pantalla_actual = "PLAN_TRAMOS"
        elif self.state.pantalla_actual == "PLAN_TRAMOS":
            self.state.pantalla_actual = "PLAN_SALDO_PLACEHOLDER"
        self._render()

    def _previous_step(self, _: ft.ControlEvent | None = None) -> None:
        if self.state.pantalla_actual == "ORIGEN":
            return
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            self.state.pantalla_actual = "ORIGEN"
        elif self.state.pantalla_actual == "PLAN_TRAMOS":
            self.state.pantalla_actual = "PLAN_ANTICIPO"
        elif self.state.pantalla_actual == "PLAN_SALDO_PLACEHOLDER":
            self.state.pantalla_actual = "PLAN_TRAMOS"
        elif self.state.pantalla_actual in {"PLAN_ANTICIPO", "PASO_6_PLACEHOLDER"}:
            self.state.pantalla_actual = "FORMA_PAGO"
        elif self.state.pantalla_actual == "FORMA_PAGO":
            self.state.pantalla_actual = "COMPRADORES"
        elif self.state.pantalla_actual == "COMPRADORES":
            self.state.pantalla_actual = "OBJETOS"
        elif self.state.pantalla_actual == "OBJETOS":
            self.state.pantalla_actual = "DATOS_INICIALES"
        elif self.state.pantalla_actual == "DATOS_INICIALES" and self.state.origen == "RESERVA":
            self.state.pantalla_actual = "SELECCIONAR_RESERVA"
        else:
            self.state.pantalla_actual = "ORIGEN"
        self._render()

    def _can_advance(self) -> bool:
        if self.state.pantalla_actual == "ORIGEN":
            return self.state.origen is not None
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            return self.state.id_reserva_venta is not None and self.state.version_registro is not None
        if self.state.pantalla_actual == "DATOS_INICIALES":
            return self._has_valid_currency() and self.fecha_venta_error is None
        if self.state.pantalla_actual == "OBJETOS":
            if not self._has_valid_currency():
                return False
            return bool(self.state.objetos) and all(
                _parse_decimal(objeto.precio_asignado) is not None for objeto in self.state.objetos
            )
        if self.state.pantalla_actual == "COMPRADORES":
            if self.state.origen == "RESERVA":
                return True
            return self._buyers_are_valid()
        if self.state.pantalla_actual == "FORMA_PAGO":
            if self.state.forma_pago == "FINANCIADO":
                return True
            if self.state.forma_pago == "CONTADO":
                return bool(self.state.fecha_pago_contado_iso) and self.state.fecha_pago_contado_error is None
            return False
        if self.state.pantalla_actual == "PLAN_ANTICIPO":
            return self._advance_is_valid()
        if self.state.pantalla_actual == "PLAN_TRAMOS":
            return self._installments_are_complete()
        return False

    def _date_display_value(self) -> str:
        if self.fecha_venta_error is not None:
            return self.fecha_venta_display_value
        return _format_date_ar(self.state.fecha_venta_iso)

    def _sync_fecha_venta_feedback(self) -> None:
        if self.fecha_venta_error is not None:
            self.fecha_venta_feedback.value = self.fecha_venta_error
            self.fecha_venta_feedback.color = ft.Colors.RED_700
            return
        self.fecha_venta_feedback.value = "Formato: DD/MM/AAAA"
        self.fecha_venta_feedback.color = ft.Colors.BLUE_GREY_600

    def _refresh_navigation_controls(self) -> None:
        if self.next_button is not None:
            self.next_button.disabled = not self._can_advance()

    def _select_payment_method(self, payment_method: FormaPagoWizard) -> None:
        if payment_method not in {"CONTADO", "FINANCIADO"}:
            return
        self.state.forma_pago = payment_method
        if payment_method == "FINANCIADO":
            self.state.fecha_pago_contado_iso = ""
            self.state.fecha_pago_contado_display = ""
            self.state.fecha_pago_contado_error = None
            self.fecha_pago_contado_field.value = ""
        if payment_method == "CONTADO":
            self._clear_advance_state()
        self._render()

    def _clear_advance_state(self) -> None:
        self.state.tiene_anticipo = False
        self.state.importe_anticipo = ""
        self.state.fecha_anticipo_iso = ""
        self.state.fecha_anticipo_display = ""
        self.state.fecha_anticipo_error = None
        self.state.importe_anticipo_error = None
        self.importe_anticipo_field.value = ""
        self.fecha_anticipo_field.value = ""
        self.state.tramos_cuotas.clear()
        self._clear_installment_form_state()

    def _cash_payment_date_display_value(self) -> str:
        if self.state.fecha_pago_contado_error is not None:
            return self.state.fecha_pago_contado_display
        return _format_date_ar(self.state.fecha_pago_contado_iso)

    def _on_fecha_pago_contado_change(self, event: ft.ControlEvent) -> None:
        raw_value = str(event.control.value or "")
        self.state.fecha_pago_contado_display = raw_value
        if not raw_value.strip():
            self.state.fecha_pago_contado_iso = ""
            self.state.fecha_pago_contado_error = None
        else:
            parsed_date = _parse_date_ar(raw_value)
            if parsed_date is None:
                self.state.fecha_pago_contado_error = "Fecha inválida. Usá formato DD/MM/AAAA."
            else:
                self.state.fecha_pago_contado_iso = parsed_date
                self.state.fecha_pago_contado_display = _format_date_ar(parsed_date)
                event.control.value = self.state.fecha_pago_contado_display
                self.state.fecha_pago_contado_error = None
        self._sync_fecha_pago_contado_feedback()
        self._refresh_navigation_controls()
        self.page.update()

    def _open_fecha_pago_contado_picker(self, _: ft.ControlEvent | None = None) -> None:
        if not hasattr(ft, "DatePicker"):
            if self.state.fecha_pago_contado_error is None:
                self.fecha_pago_contado_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.fecha_pago_contado_feedback.color = ft.Colors.AMBER_800
            self._refresh_navigation_controls()
            self.page.update()
            return
        selected_date = _date_from_iso(self.state.fecha_pago_contado_iso) or date.today()
        try:
            picker = ft.DatePicker(
                value=selected_date,
                first_date=date(1900, 1, 1),
                last_date=date(2100, 12, 31),
            )
            picker.on_change = self._on_fecha_pago_contado_picker_change
            self.page.overlay.append(picker)
            picker.open = True
            self.page.update()
        except Exception:
            if self.state.fecha_pago_contado_error is None:
                self.fecha_pago_contado_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.fecha_pago_contado_feedback.color = ft.Colors.AMBER_800
            self._refresh_navigation_controls()
            self.page.update()

    def _on_fecha_pago_contado_picker_change(self, event: ft.ControlEvent) -> None:
        selected_date = getattr(event.control, "value", None)
        if selected_date is None:
            return
        if isinstance(selected_date, datetime):
            selected_date = selected_date.date()
        if isinstance(selected_date, date):
            self.state.fecha_pago_contado_iso = selected_date.isoformat()
            self.state.fecha_pago_contado_display = _format_date_ar(self.state.fecha_pago_contado_iso)
            self.fecha_pago_contado_field.value = self.state.fecha_pago_contado_display
            self.state.fecha_pago_contado_error = None
            self._sync_fecha_pago_contado_feedback()
            self._refresh_navigation_controls()
            self.page.update()

    def _sync_fecha_pago_contado_feedback(self) -> None:
        if self.state.fecha_pago_contado_error is not None:
            self.fecha_pago_contado_feedback.value = self.state.fecha_pago_contado_error
            self.fecha_pago_contado_feedback.color = ft.Colors.RED_700
            return
        self.fecha_pago_contado_feedback.value = "Formato: DD/MM/AAAA"
        self.fecha_pago_contado_feedback.color = ft.Colors.BLUE_GREY_600

    def _select_tiene_anticipo(self, has_advance: bool) -> None:
        self.state.tiene_anticipo = has_advance
        if not has_advance:
            self.state.importe_anticipo_error = None
            self.state.fecha_anticipo_error = None
        else:
            self._validate_advance_state()
        self._render()

    def _on_importe_anticipo_change(self, event: ft.ControlEvent) -> None:
        self.state.importe_anticipo = str(event.control.value or "")
        self._validate_advance_amount()
        self._sync_importe_anticipo_feedback()
        self._sync_advance_visual_amounts()
        self._refresh_navigation_controls()
        self.page.update()

    def _on_fecha_anticipo_change(self, event: ft.ControlEvent) -> None:
        raw_value = str(event.control.value or "")
        self.state.fecha_anticipo_display = raw_value
        if not raw_value.strip():
            self.state.fecha_anticipo_iso = ""
            self.state.fecha_anticipo_error = "La fecha vencimiento anticipo es requerida."
        else:
            parsed_date = _parse_date_ar_strict(raw_value)
            if parsed_date is None:
                self.state.fecha_anticipo_iso = ""
                self.state.fecha_anticipo_error = "Fecha inválida. Usá formato DD/MM/AAAA."
            else:
                self.state.fecha_anticipo_iso = parsed_date
                self.state.fecha_anticipo_display = _format_date_ar(parsed_date)
                event.control.value = self.state.fecha_anticipo_display
                self.state.fecha_anticipo_error = None
        self._sync_fecha_anticipo_feedback()
        self._refresh_navigation_controls()
        self.page.update()

    def _open_fecha_anticipo_picker(self, _: ft.ControlEvent | None = None) -> None:
        if not hasattr(ft, "DatePicker"):
            if self.state.fecha_anticipo_error is None:
                self.fecha_anticipo_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.fecha_anticipo_feedback.color = ft.Colors.AMBER_800
            self._refresh_navigation_controls()
            self.page.update()
            return
        selected_date = _date_from_iso(self.state.fecha_anticipo_iso) or date.today()
        try:
            picker = ft.DatePicker(
                value=selected_date,
                first_date=date(1900, 1, 1),
                last_date=date(2100, 12, 31),
            )
            picker.on_change = self._on_fecha_anticipo_picker_change
            self.page.overlay.append(picker)
            picker.open = True
            self.page.update()
        except Exception:
            if self.state.fecha_anticipo_error is None:
                self.fecha_anticipo_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.fecha_anticipo_feedback.color = ft.Colors.AMBER_800
            self._refresh_navigation_controls()
            self.page.update()

    def _on_fecha_anticipo_picker_change(self, event: ft.ControlEvent) -> None:
        selected_date = getattr(event.control, "value", None)
        if selected_date is None:
            return
        if isinstance(selected_date, datetime):
            selected_date = selected_date.date()
        if isinstance(selected_date, date):
            self.state.fecha_anticipo_iso = selected_date.isoformat()
            self.state.fecha_anticipo_display = _format_date_ar(self.state.fecha_anticipo_iso)
            self.fecha_anticipo_field.value = self.state.fecha_anticipo_display
            self.state.fecha_anticipo_error = None
            self._sync_fecha_anticipo_feedback()
            self._refresh_navigation_controls()
            self.page.update()

    def _advance_date_display_value(self) -> str:
        if self.state.fecha_anticipo_error is not None:
            return self.state.fecha_anticipo_display
        return _format_date_ar(self.state.fecha_anticipo_iso)

    def _validate_advance_state(self) -> None:
        if not self.state.tiene_anticipo:
            self.state.importe_anticipo_error = None
            self.state.fecha_anticipo_error = None
            return
        self._validate_advance_amount()
        if not self.state.fecha_anticipo_display.strip() and not self.state.fecha_anticipo_iso:
            self.state.fecha_anticipo_error = "La fecha vencimiento anticipo es requerida."
        elif self.state.fecha_anticipo_display.strip() and _parse_date_ar_strict(self.state.fecha_anticipo_display) is None:
            self.state.fecha_anticipo_error = "Fecha inválida. Usá formato DD/MM/AAAA."

    def _validate_advance_amount(self) -> Decimal | None:
        if not self.state.tiene_anticipo:
            self.state.importe_anticipo_error = None
            return None
        raw_value = self.state.importe_anticipo.strip()
        total = self._objects_total()
        if not raw_value:
            self.state.importe_anticipo_error = "El importe anticipo es requerido."
            return None
        parsed = _parse_decimal(raw_value)
        if parsed is None:
            self.state.importe_anticipo_error = "El importe debe ser un número finito mayor que 0."
            return None
        if parsed > total:
            self.state.importe_anticipo_error = "El importe anticipo no puede superar el total derivado."
            return None
        self.state.importe_anticipo_error = None
        return parsed

    def _advance_is_valid(self) -> bool:
        self._validate_advance_state()
        if not self.state.tiene_anticipo:
            return True
        return (
            self.state.importe_anticipo_error is None
            and self.state.fecha_anticipo_error is None
            and self._validate_advance_amount() is not None
            and bool(self.state.fecha_anticipo_iso)
        )

    def _valid_advance_amount_or_zero(self) -> Decimal:
        if not self.state.tiene_anticipo:
            return Decimal("0")
        parsed = _parse_decimal(self.state.importe_anticipo)
        if parsed is None or parsed > self._objects_total():
            return Decimal("0")
        return parsed

    def _capital_pending_after_advance(self) -> Decimal:
        return self._objects_total() - self._valid_advance_amount_or_zero()

    def _advance_status(self) -> str:
        if not self.state.tiene_anticipo:
            return "No"
        parsed = _parse_decimal(self.state.importe_anticipo)
        if parsed is None:
            return "importe pendiente"
        return self._format_money_with_currency(parsed)

    def _sync_importe_anticipo_feedback(self) -> None:
        if self.state.importe_anticipo_error is not None:
            self.importe_anticipo_feedback.value = self.state.importe_anticipo_error
            self.importe_anticipo_feedback.color = ft.Colors.RED_700
            return
        self.importe_anticipo_feedback.value = "Ingresá un importe mayor que 0 y menor o igual al total derivado."
        self.importe_anticipo_feedback.color = ft.Colors.BLUE_GREY_600

    def _sync_advance_visual_amounts(self) -> None:
        advance = self._valid_advance_amount_or_zero()
        pending = self._objects_total() - advance
        self.anticipo_actual_summary_value.value = self._format_money_with_currency(advance)
        self.capital_pendiente_summary_value.value = self._format_money_with_currency(pending)

    def _sync_fecha_anticipo_feedback(self) -> None:
        if self.state.fecha_anticipo_error is not None:
            self.fecha_anticipo_feedback.value = self.state.fecha_anticipo_error
            self.fecha_anticipo_feedback.color = ft.Colors.RED_700
            return
        self.fecha_anticipo_feedback.value = "Formato: DD/MM/AAAA"
        self.fecha_anticipo_feedback.color = ft.Colors.BLUE_GREY_600


    def _sync_installment_form_controls(self) -> None:
        remaining = self._capital_remaining_for_installments()
        self.tramo_capital_field.value = self.state.tramo_capital_value
        self.tramo_capital_field.hint_text = self._format_money_with_currency(remaining)
        self.tramo_cantidad_field.value = self.state.tramo_cantidad_cuotas_value
        self.tramo_fecha_field.value = self._installment_date_display_value()
        self._sync_tramo_capital_feedback()
        self._sync_tramo_cantidad_feedback()
        self._sync_tramo_fecha_feedback()

    def _on_tramo_capital_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_capital_value = str(event.control.value or "")
        self.state.tramo_capital_error = None

    def _on_tramo_cantidad_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_cantidad_cuotas_value = str(event.control.value or "")
        self.state.tramo_cantidad_error = None

    def _on_tramo_fecha_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_fecha_display = str(event.control.value or "")
        self.state.tramo_fecha_iso = ""
        self.state.tramo_fecha_error = None

    def _open_tramo_fecha_picker(self, _: ft.ControlEvent | None = None) -> None:
        if not hasattr(ft, "DatePicker"):
            if self.state.tramo_fecha_error is None:
                self.tramo_fecha_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.tramo_fecha_feedback.color = ft.Colors.AMBER_800
            self.page.update()
            return
        selected_date = _date_from_iso(self.state.tramo_fecha_iso) or date.today()
        try:
            picker = ft.DatePicker(
                value=selected_date,
                first_date=date(1900, 1, 1),
                last_date=date(2100, 12, 31),
            )
            picker.on_change = self._on_tramo_fecha_picker_change
            self.page.overlay.append(picker)
            picker.open = True
            self.page.update()
        except Exception:
            if self.state.tramo_fecha_error is None:
                self.tramo_fecha_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.tramo_fecha_feedback.color = ft.Colors.AMBER_800
            self.page.update()

    def _on_tramo_fecha_picker_change(self, event: ft.ControlEvent) -> None:
        selected_date = getattr(event.control, "value", None)
        if selected_date is None:
            return
        if isinstance(selected_date, datetime):
            selected_date = selected_date.date()
        if isinstance(selected_date, date):
            self.state.tramo_fecha_iso = selected_date.isoformat()
            self.state.tramo_fecha_display = _format_date_ar(self.state.tramo_fecha_iso)
            self.tramo_fecha_field.value = self.state.tramo_fecha_display
            self.state.tramo_fecha_error = None
            self._sync_tramo_fecha_feedback()
            self.page.update()

    def _add_installment_block(self, _: ft.ControlEvent | None = None) -> None:
        capital = self._validate_installment_capital()
        quantity = self._validate_installment_quantity()
        due_date_iso = self._validate_installment_date()
        if capital is None or quantity is None or due_date_iso is None:
            self._render()
            return
        self.state.tramos_cuotas.append(
            TramoCuotasWizardDraft(
                importe_total_bloque=_format_decimal(capital),
                cantidad_cuotas=quantity,
                fecha_primer_vencimiento_iso=due_date_iso,
                fecha_primer_vencimiento_display=_format_date_ar(due_date_iso),
            )
        )
        self._clear_installment_form_state()
        self._render()

    def _remove_installment_block(self, index: int) -> None:
        if 0 <= index < len(self.state.tramos_cuotas):
            self.state.tramos_cuotas.pop(index)
            self._clear_installment_errors()
            self._render()

    def _validate_installment_capital(self) -> Decimal | None:
        raw_value = self.state.tramo_capital_value.strip()
        if not raw_value:
            self.state.tramo_capital_error = "El capital del tramo es requerido."
            return None
        parsed = _parse_decimal(raw_value)
        if parsed is None:
            self.state.tramo_capital_error = "El capital del tramo debe ser un número finito mayor que 0."
            return None
        remaining = self._capital_remaining_for_installments()
        if parsed > remaining:
            self.state.tramo_capital_error = "El capital del tramo no puede superar el capital restante."
            return None
        self.state.tramo_capital_error = None
        return parsed

    def _validate_installment_quantity(self) -> int | None:
        raw_value = self.state.tramo_cantidad_cuotas_value.strip()
        if not raw_value:
            self.state.tramo_cantidad_error = "La cantidad total de cuotas es requerida."
            return None
        try:
            quantity = int(raw_value)
        except ValueError:
            self.state.tramo_cantidad_error = "La cantidad total de cuotas debe ser un entero mayor que 0."
            return None
        if str(quantity) != raw_value or quantity <= 0:
            self.state.tramo_cantidad_error = "La cantidad total de cuotas debe ser un entero mayor que 0."
            return None
        self.state.tramo_cantidad_error = None
        return quantity

    def _validate_installment_date(self) -> str | None:
        raw_value = self.state.tramo_fecha_display.strip()
        if not raw_value:
            self.state.tramo_fecha_error = "El primer vencimiento es requerido."
            return None
        parsed_date = _parse_date_ar_strict(raw_value)
        if parsed_date is None:
            self.state.tramo_fecha_error = "Fecha inválida. Usá formato DD/MM/AAAA."
            self.state.tramo_fecha_iso = ""
            return None
        self.state.tramo_fecha_iso = parsed_date
        self.state.tramo_fecha_display = _format_date_ar(parsed_date)
        self.state.tramo_fecha_error = None
        return parsed_date

    def _clear_installment_form_state(self) -> None:
        self.state.tramo_capital_value = ""
        self.state.tramo_cantidad_cuotas_value = ""
        self.state.tramo_fecha_display = ""
        self.state.tramo_fecha_iso = ""
        self._clear_installment_errors()
        self.tramo_capital_field.value = ""
        self.tramo_cantidad_field.value = ""
        self.tramo_fecha_field.value = ""

    def _clear_installment_errors(self) -> None:
        self.state.tramo_capital_error = None
        self.state.tramo_cantidad_error = None
        self.state.tramo_fecha_error = None

    def _installment_date_display_value(self) -> str:
        if self.state.tramo_fecha_error is not None:
            return self.state.tramo_fecha_display
        return self.state.tramo_fecha_display or _format_date_ar(self.state.tramo_fecha_iso)

    def _sync_tramo_capital_feedback(self) -> None:
        if self.state.tramo_capital_error is not None:
            self.tramo_capital_feedback.value = self.state.tramo_capital_error
            self.tramo_capital_feedback.color = ft.Colors.RED_700
            return
        self.tramo_capital_feedback.value = "Podés asignar todo el capital restante o un valor menor."
        self.tramo_capital_feedback.color = ft.Colors.BLUE_GREY_600

    def _sync_tramo_cantidad_feedback(self) -> None:
        if self.state.tramo_cantidad_error is not None:
            self.tramo_cantidad_feedback.value = self.state.tramo_cantidad_error
            self.tramo_cantidad_feedback.color = ft.Colors.RED_700
            return
        self.tramo_cantidad_feedback.value = "Ingresá un número entero mayor que 0."
        self.tramo_cantidad_feedback.color = ft.Colors.BLUE_GREY_600

    def _sync_tramo_fecha_feedback(self) -> None:
        if self.state.tramo_fecha_error is not None:
            self.tramo_fecha_feedback.value = self.state.tramo_fecha_error
            self.tramo_fecha_feedback.color = ft.Colors.RED_700
            return
        self.tramo_fecha_feedback.value = "Formato: DD/MM/AAAA"
        self.tramo_fecha_feedback.color = ft.Colors.BLUE_GREY_600

    def _capital_assigned_to_installments(self) -> Decimal:
        total = Decimal("0")
        for tramo in self.state.tramos_cuotas:
            parsed = _parse_decimal(tramo.importe_total_bloque)
            if parsed is not None:
                total += parsed
        return total

    def _capital_remaining_for_installments(self) -> Decimal:
        return self._capital_pending_after_advance() - self._capital_assigned_to_installments()

    def _installments_obligations_count(self) -> int:
        return sum(tramo.cantidad_cuotas for tramo in self.state.tramos_cuotas)

    def _installments_are_complete(self) -> bool:
        return bool(self.state.tramos_cuotas) and self._capital_remaining_for_installments() == Decimal("0")

    def _currency_locked_by_objects(self) -> bool:
        return bool(self.state.objetos)

    def _has_valid_currency(self) -> bool:
        return self.state.moneda.strip().upper() in MONEDAS_DEMO

    def _currency_label(self) -> str:
        return self.state.moneda.strip().upper() or "sin moneda"

    def _format_money_with_currency(self, value: Decimal) -> str:
        return f"{self._currency_label()} {_format_decimal(value)}"

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

    def _on_comprador_selected(self, selected: dict[str, Any] | None) -> None:
        self.comprador_seleccionado = selected
        self.porcentaje_comprador_value = ""
        self.porcentaje_comprador_field.value = ""
        self.rol_comprador_value = ""
        self.rol_comprador_field.value = ""
        self.comprador_error = None
        if self.comprador_selector is not None:
            self.comprador_selector.selected_panel.visible = False
        self._render()

    def _clear_selected_buyer(self, _: ft.ControlEvent | None = None) -> None:
        self.comprador_seleccionado = None
        self.comprador_selector = None
        self.porcentaje_comprador_value = ""
        self.porcentaje_comprador_field.value = ""
        self.rol_comprador_value = ""
        self.rol_comprador_field.value = ""
        self.comprador_error = None
        self._render()

    def _on_porcentaje_comprador_change(self, _: ft.ControlEvent) -> None:
        self.porcentaje_comprador_value = str(self.porcentaje_comprador_field.value or "")

    def _on_rol_comprador_change(self, _: ft.ControlEvent) -> None:
        self.rol_comprador_value = str(self.rol_comprador_field.value or "")

    def _selected_buyer_validation_message(self) -> str | None:
        if self.comprador_seleccionado is None or self.comprador_seleccionado.get("id_persona") is None:
            return "id_persona es obligatorio."
        if self._is_duplicate_selected_buyer():
            return "No se puede duplicar id_persona."
        porcentaje_raw = self.porcentaje_comprador_value.strip()
        if porcentaje_raw and _parse_percentage(porcentaje_raw) is None:
            return "porcentaje_responsabilidad debe ser mayor que 0 y menor o igual que 100."
        if not self.rol_comprador_value.strip():
            return "id_rol_participacion es obligatorio y debe corresponder al rol COMPRADOR."
        if not self.rol_comprador_value.strip().isdigit():
            return "id_rol_participacion debe ser un ID numerico de backend."
        return None

    def _is_duplicate_selected_buyer(self) -> bool:
        if self.comprador_seleccionado is None:
            return False
        selected_id = self.comprador_seleccionado.get("id_persona")
        return any(comprador.id_persona == selected_id for comprador in self.state.compradores)

    def _add_selected_buyer(self, _: ft.ControlEvent | None = None) -> None:
        if self.comprador_seleccionado is None:
            return
        self.porcentaje_comprador_value = str(
            self.porcentaje_comprador_field.value or self.porcentaje_comprador_value or ""
        )
        self.rol_comprador_value = str(self.rol_comprador_field.value or self.rol_comprador_value or "")
        self.comprador_error = self._selected_buyer_validation_message()
        if self.comprador_error is not None:
            self._render()
            return

        porcentaje = self.porcentaje_comprador_value.strip()
        parsed_percentage = _parse_percentage(porcentaje) if porcentaje else None
        self.state.compradores.append(
            CompradorWizardDraft(
                id_persona=int(self.comprador_seleccionado.get("id_persona")),
                texto_visual=str(self.comprador_seleccionado.get("texto_visual") or "-"),
                porcentaje_responsabilidad=_format_decimal(parsed_percentage) if parsed_percentage is not None else "",
                id_rol_participacion=self.rol_comprador_value.strip(),
            )
        )
        self.comprador_seleccionado = None
        self.comprador_selector = None
        self.porcentaje_comprador_value = ""
        self.porcentaje_comprador_field.value = ""
        self.rol_comprador_value = ""
        self.rol_comprador_field.value = ""
        self.comprador_error = None
        self._render()

    def _remove_buyer(self, index: int) -> None:
        if 0 <= index < len(self.state.compradores):
            self.state.compradores.pop(index)
        self._render()

    def _distribute_buyers_equally(self, _: ft.ControlEvent | None = None) -> None:
        if not self.state.compradores:
            return
        base = Decimal("100") / Decimal(len(self.state.compradores))
        accumulated = Decimal("0")
        for index, comprador in enumerate(self.state.compradores):
            if index == len(self.state.compradores) - 1:
                percentage = Decimal("100") - accumulated
            else:
                percentage = base.quantize(Decimal("0.01"))
                accumulated += percentage
            comprador.porcentaje_responsabilidad = _format_decimal(percentage)
        self._render()

    def _objects_total(self) -> Decimal:
        total = Decimal("0")
        for objeto in self.state.objetos:
            parsed = _parse_decimal(objeto.precio_asignado)
            if parsed is not None:
                total += parsed
        return total

    def _buyers_responsibility_total(self) -> Decimal | None:
        total = Decimal("0")
        has_percentage = False
        for comprador in self.state.compradores:
            if not comprador.porcentaje_responsabilidad.strip():
                continue
            parsed = _parse_percentage(comprador.porcentaje_responsabilidad)
            if parsed is None:
                return None
            has_percentage = True
            total += parsed
        if len(self.state.compradores) == 1 and not has_percentage:
            return Decimal("100")
        return total

    def _buyers_responsibility_total_label(self, total: Decimal | None) -> str:
        if total is None:
            return "inválida"
        return f"{_format_decimal(total)}%"

    def _buyers_responsibility_status(self, total: Decimal | None) -> str:
        validation_error = self._buyers_validation_error(total)
        if validation_error is not None:
            return "Responsabilidad inválida."
        if len(self.state.compradores) == 1 and not self.state.compradores[0].porcentaje_responsabilidad.strip():
            return "Se asumirá 100%."
        if self.state.compradores:
            return "Responsabilidad válida. Se puede continuar."
        return "Compradores requeridos para venta directa."

    def _buyers_validation_error(self, total: Decimal | None = None) -> str | None:
        if self.state.origen == "RESERVA":
            return None
        if self.state.origen != "DIRECTA" or not self.state.compradores:
            return "Agregá al menos un comprador para continuar con una venta directa."

        seen_ids: set[int] = set()
        for comprador in self.state.compradores:
            if comprador.id_persona in seen_ids:
                return "No se puede duplicar id_persona entre compradores."
            seen_ids.add(comprador.id_persona)
            if not comprador.id_rol_participacion.strip():
                return "Todos los compradores deben tener id_rol_participacion del rol COMPRADOR."
            percentage_raw = comprador.porcentaje_responsabilidad.strip()
            if len(self.state.compradores) > 1 and not percentage_raw:
                return "Con más de un comprador, todos deben informar porcentaje_responsabilidad."
            if percentage_raw and _parse_percentage(percentage_raw) is None:
                return "Cada porcentaje_responsabilidad debe ser mayor que 0 y menor o igual que 100."

        if len(self.state.compradores) == 1:
            percentage_raw = self.state.compradores[0].porcentaje_responsabilidad.strip()
            if not percentage_raw:
                return None
            parsed = _parse_percentage(percentage_raw)
            if parsed is None:
                return "El porcentaje del comprador debe ser mayor que 0 y menor o igual que 100."
            if _format_decimal(parsed) != "100.00":
                return "Si hay un único comprador, el porcentaje informado debe ser 100.00 o quedar vacío para asumir 100%."
            return None

        total = self._buyers_responsibility_total() if total is None else total
        if total is None:
            return "La suma de responsabilidad no se puede calcular por porcentajes inválidos."
        if _format_decimal(total) != "100.00":
            return f"La suma de responsabilidad debe ser exactamente 100.00%; actual: {_format_decimal(total)}%."
        return None

    def _buyers_are_valid(self) -> bool:
        return self._buyers_validation_error() is None

    def _origin_label(self) -> str:
        if self.state.origen == "RESERVA":
            return "Desde reserva"
        if self.state.origen == "DIRECTA":
            return "Venta directa"
        return "No seleccionado"

    def _reservation_status(self) -> str:
        return self.state.texto_visual_reserva or "pendiente de selección"

    def _buyers_flow_status(self) -> str:
        if self.state.origen == "RESERVA":
            return "heredados de reserva"
        return str(len(self.state.compradores))

    def _payment_method_status(self) -> str:
        if self.state.forma_pago == "CONTADO":
            return "contado"
        if self.state.forma_pago == "FINANCIADO":
            return "financiado"
        return "pendiente"

    def _next_step_label(self) -> str:
        if self.state.pantalla_actual == "DATOS_INICIALES":
            return "cargar objetos de venta" if self._can_advance() else "seleccionar moneda"
        if self.state.pantalla_actual == "OBJETOS":
            return "cargar compradores" if self._can_advance() else "cargar objetos de venta"
        if self.state.pantalla_actual == "COMPRADORES":
            return "elegir forma de pago" if self._can_advance() else "cargar compradores"
        if self.state.pantalla_actual == "FORMA_PAGO":
            if self.state.forma_pago == "CONTADO":
                return "revisar venta" if self._can_advance() else "cargar fecha de pago contado"
            if self.state.forma_pago == "FINANCIADO":
                return "cargar anticipo"
            return "elegir forma de pago"
        if self.state.pantalla_actual == "PLAN_ANTICIPO":
            return "cargar tramos de cuotas" if self._can_advance() else "completar anticipo"
        if self.state.pantalla_actual == "PLAN_TRAMOS":
            return "cargar saldo final / revisión pendiente" if self._can_advance() else "cargar tramos de cuotas"
        if self.state.pantalla_actual in {"PLAN_SALDO_PLACEHOLDER", "PASO_6_PLACEHOLDER"}:
            return "pendiente"
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            return "cargar datos iniciales"
        if self.state.origen is None:
            return "elegir origen"
        if self.state.origen == "RESERVA":
            return "seleccionar reserva"
        return "cargar datos iniciales"

    def _build_help_card(self, text: str, bgcolor: ft.ColorValue, border_color: ft.ColorValue) -> ft.Control:
        return ft.Container(
            padding=12,
            border_radius=10,
            bgcolor=bgcolor,
            border=_border_all(1, border_color),
            content=ft.Text(text, color=ft.Colors.BLUE_GREY_800),
        )


def _format_date_ar(iso_date: str | None) -> str:
    text = str(iso_date or "").strip()
    if not text:
        return ""
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return text


def _parse_date_ar(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return datetime.strptime(text, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _parse_date_ar_strict(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) != 10 or text[2] != "/" or text[5] != "/":
        return None
    day, month, year = text[:2], text[3:5], text[6:]
    if not (day.isdigit() and month.isdigit() and year.isdigit()):
        return None
    return _parse_date_ar(text)


def _date_from_iso(iso_date: str | None) -> date | None:
    text = str(iso_date or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value or "").strip())
        if not parsed.is_finite() or parsed <= 0:
            return None
    except (InvalidOperation, ValueError):
        return None
    return parsed


def _parse_percentage(value: Any) -> Decimal | None:
    parsed = _parse_decimal(value)
    if parsed is None or parsed > Decimal("100"):
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
    return _info_row_control(
        label,
        ft.Text(str(value if value not in (None, "") else "-"), color=ft.Colors.BLUE_GREY_900, expand=True),
    )


def _info_row_control(label: str, value_control: ft.Control) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Text(f"{label}:", weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_GREY_700),
            value_control,
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
