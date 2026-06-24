"""Prototipo Flet del wizard venta completa V3 - Datos iniciales antes de objetos.

Uso:
  cd frontend/flet_app
  python prototypes/venta_completa_wizard_v3_prototype.py

Alcance:
  - Prototipo UI aislado del dominio comercial, con preview real read-like de Plan Pago V2 sin id_venta.
  - Nueva base de iteracion pantalla por pantalla para venta completa V3.
  - Implementa Pantalla 1 - Origen, Pantalla 1B - Seleccionar reserva,
    Pantalla 2 - Datos iniciales de venta, Pantalla 3 - Objetos de venta,
    Pantalla 4 - Compradores, Pantalla 5 - Forma de pago y avance UI de
    Plan Pago V2 con anticipo, tramos con método de liquidación y resumen
    del plan financiado.
  - No modifica backend, SQL, caja, pagos, recibos ni documental.
  - Pide moneda antes de cargar precio_asignado por objeto; no pide id_venta,
    no calcula cronograma local, deuda individual por comprador ni implementa datos
    comerciales completos, cronograma definitivo, interés/indexación local.
    Incluye preview backend sin venta persistida, confirmación real de venta directa
    al final del flujo y draft UI de refuerzos internos
    dentro de tramos sin calcular importes financieros definitivos.
  - El frontend comercial no calcula resultados financieros definitivos: interés,
    indexación y cronograma se delegarán al preview backend de Plan Pago V2.
    La versión productiva debe mostrar esos resultados cuando integre esa simulación.
  - Nota compradores: el objetivo final para RESERVA es mostrar y validar
    compradores heredados desde datos reales de reserva; este V3 los deja como
    pendiente visual hasta integrar backend/buscador real. DIRECTA usa personas
    reales del backend o modo tecnico/dev explicito con IDs ya persistidos.
  - Los objetos de venta se agregan exclusivamente desde registros reales del
    backend; no existe fallback tecnico/dev por ID para inmuebles o unidades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys
from typing import Any, Callable, Literal
from uuid import uuid4

import flet as ft

PROTOTYPES_DIR = Path(__file__).resolve().parent
FLET_APP_ROOT = PROTOTYPES_DIR.parent
for import_path in (str(FLET_APP_ROOT), str(PROTOTYPES_DIR)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from app.api_client import ApiClient, ApiResult
from app.components.loading_state import loading_state, safe_update
from components.search_selector_demo import (
    SearchSelectorDemo,
    create_search_selector_demo,
    is_object_selectable,
    object_selection_warning,
)


OrigenVenta = Literal["RESERVA", "DIRECTA"]
FormaPagoWizard = Literal["CONTADO", "FINANCIADO"]
MetodoLiquidacionTramoWizard = Literal["SIN_INTERES", "INTERES_DIRECTO", "INDEXACION"]
PantallaWizard = Literal[
    "ORIGEN",
    "SELECCIONAR_RESERVA",
    "DATOS_INICIALES",
    "OBJETOS",
    "COMPRADORES",
    "FORMA_PAGO",
    "PLAN_ANTICIPO",
    "PLAN_TRAMOS",
    "PLAN_TRAMO_FORM",
    "PLAN_RESUMEN",
    "PREVIEW_PLAN_PAGO",
    "REVISION_GENERAL",
    "VENTA_CONFIRMADA",
]


MONEDAS_PERMITIDAS = ["ARS", "USD", "EUR"]
MONEY_DECIMAL_QUANTUM = Decimal("0.01")
MONEY_PRECISION_ERROR = "El importe debe tener como máximo 2 decimales."
VENTA_SELECTOR_CONFLICT_STATES = {"activa", "confirmada", "en_proceso", "finalizada"}
VENTA_SELECTOR_BLOCK_REASON = "Ya participa en una venta vigente"
VENTA_SELECTOR_RELATED_BLOCK_REASON = "Tiene una venta vigente relacionada"
VENTA_SELECTOR_ALREADY_ADDED_REASON = "Ya fue agregado a esta venta"
WIZARD_VISIBLE_STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Origen", ("ORIGEN", "SELECCIONAR_RESERVA")),
    ("Datos", ("DATOS_INICIALES",)),
    ("Objetos", ("OBJETOS",)),
    ("Compradores", ("COMPRADORES",)),
    ("Pago", ("FORMA_PAGO",)),
    (
        "Plan",
        ("PLAN_ANTICIPO", "PLAN_TRAMOS", "PLAN_TRAMO_FORM", "PLAN_RESUMEN"),
    ),
    ("Revisión", ("PREVIEW_PLAN_PAGO", "REVISION_GENERAL")),
    ("Confirmación", ("VENTA_CONFIRMADA",)),
)


@dataclass
class ObjetoVentaWizardDraft:
    tipo_objeto: str
    id_inmueble: int | None
    id_unidad_funcional: int | None
    texto_visual: str
    precio_asignado: str
    source: str = "manual"
    persisted: bool = False
    heredado_reserva: bool = False


@dataclass
class CompradorWizardDraft:
    id_persona: int
    texto_visual: str
    porcentaje_responsabilidad: str
    id_rol_participacion: str
    source: str = "manual"
    persisted: bool = False
    heredado_reserva: bool = False


@dataclass
class CuotaRefuerzoWizardDraft:
    numero_cuota: int
    etiqueta: str
    unidades_refuerzo: str = "1.00"


@dataclass
class TramoCuotasWizardDraft:
    importe_total_bloque: str
    cantidad_cuotas: int
    fecha_primer_vencimiento_iso: str
    fecha_primer_vencimiento_display: str
    periodicidad: Literal["MENSUAL"] = "MENSUAL"
    metodo_liquidacion: MetodoLiquidacionTramoWizard = "SIN_INTERES"
    tasa_interes_directo_periodica: str | None = None
    cantidad_periodos: str | None = None
    id_indice_financiero: str | None = None
    codigo_indice_visual: str | None = None
    fecha_base_indice_iso: str | None = None
    fecha_base_indice_display: str | None = None
    valor_base_indice: str | None = None
    cuotas_refuerzo: list[CuotaRefuerzoWizardDraft] = field(default_factory=list)


@dataclass
class WizardVentaCompletaV3State:
    """Estado minimo del wizard V3 hasta Pantalla 3 - Compradores.

    Conserva origen/reserva y listas seleccionadas desde backend real.
    """

    origen: OrigenVenta | None = None
    id_reserva_venta: int | None = None
    version_registro: int | None = None
    texto_visual_reserva: str | None = None
    reserva_visible_data: dict[str, Any] = field(default_factory=dict)
    reserva_detalle_error: str | None = None
    reserva_detalle_loaded: bool = False
    reserva_detalle_source: str = "listado_parcial"
    reserva_detalle_participaciones_count: int = 0
    reserva_detalle_objetos_count: int = 0
    reserva_detalle_conversion_warning: str | None = None
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
    tramo_metodo_liquidacion: MetodoLiquidacionTramoWizard = "SIN_INTERES"
    tramo_tasa_interes_value: str = ""
    tramo_id_indice_financiero_value: str = ""
    tramo_codigo_indice_visual_value: str = ""
    tramo_fecha_base_indice_display: str = ""
    tramo_fecha_base_indice_iso: str = ""
    tramo_valor_base_indice_value: str = ""
    tramo_usa_refuerzos: bool = False
    refuerzo_cantidad_value: str = ""
    refuerzo_cantidad_error: str | None = None
    refuerzo_numero_cuota_value: str = ""
    refuerzo_etiqueta_value: str = ""
    refuerzo_numero_error: str | None = None
    tramo_cuotas_refuerzo_draft: list[CuotaRefuerzoWizardDraft] = field(default_factory=list)
    tramo_capital_error: str | None = None
    tramo_cantidad_error: str | None = None
    tramo_fecha_error: str | None = None
    tramo_tasa_interes_error: str | None = None
    tramo_id_indice_financiero_error: str | None = None
    tramo_fecha_base_indice_error: str | None = None
    tramo_valor_base_indice_error: str | None = None
    preview_loading: bool = False
    preview_data: dict[str, Any] | None = None
    preview_error: str | None = None
    preview_status_code: int | None = None
    preview_stale: bool = True
    preview_obligaciones_page: int = 1
    preview_obligaciones_page_size: int = 8
    confirm_loading: bool = False
    confirm_data: dict[str, Any] | None = None
    confirm_error: str | None = None
    confirm_status_code: int | None = None
    confirm_op_id: str | None = None
    confirm_payload_signature: str | None = None
    confirm_payload: dict[str, Any] | None = None
    confirm_endpoint: str | None = None
    confirm_error_details: Any = None
    detalle_venta_loading: bool = False
    detalle_venta_data: dict[str, Any] | None = None
    detalle_venta_error: str | None = None
    detalle_venta_status_code: int | None = None
    detalle_venta_requested_id: int | None = None
    detalle_cuotas_page: int = 1
    detalle_cuotas_page_size: int = 10
    mostrar_datos_tecnicos: bool = False
    pantalla_actual: PantallaWizard = "ORIGEN"


class VentaCompletaWizardV3Prototype:
    def __init__(
        self,
        page: ft.Page,
        *,
        api: ApiClient | None = None,
        embedded: bool = False,
        on_close: Callable[[], None] | None = None,
        on_confirmed: Callable[[int | None], None] | None = None,
    ) -> None:
        self.page = page
        self.embedded = embedded
        self.on_close = on_close
        self.on_confirmed = on_confirmed
        self.root = ft.Container(expand=True)
        self.state = WizardVentaCompletaV3State()
        self.api = api or ApiClient(timeout=20.0)
        self.reserva_selector: SearchSelectorDemo | None = None
        self.objeto_selector: SearchSelectorDemo | None = None
        self.comprador_selector: SearchSelectorDemo | None = None
        self.objeto_seleccionado: dict[str, Any] | None = None
        self.comprador_seleccionado: dict[str, Any] | None = None
        self.backend_reservation_records: list[dict[str, Any]] = []
        self.backend_reservation_error: str | None = None
        self.backend_reservations_loaded = False
        self.backend_reservations_loading = False
        self.backend_object_records: list[dict[str, Any]] = []
        self.backend_object_error: str | None = None
        self.backend_objects_loaded = False
        self.backend_objects_loading = False
        self.backend_buyer_records: list[dict[str, Any]] = []
        self.backend_buyer_error: str | None = None
        self.backend_buyers_loaded = False
        self.backend_buyers_loading = False
        self.rol_comprador_catalog_loaded = False
        self.rol_comprador_loading = False
        self.reserva_select_loading = False
        self.object_select_loading = False
        self.buyer_select_loading = False
        self.reserva_select_error: str | None = None
        self.object_select_error: str | None = None
        self.buyer_select_error: str | None = None
        self.rol_comprador_catalog_error: str | None = None
        self.rol_comprador_manual_fallback_enabled = False
        self.rol_comprador_data: dict[str, Any] | None = None
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
            keyboard_type=ft.KeyboardType.TEXT,
            on_change=self._on_precio_objeto_change,
            on_blur=self._on_precio_objeto_commit,
            on_submit=self._on_precio_objeto_commit,
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
            label="ID rol comprador backend (fallback técnico/dev)",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_rol_comprador_change,
        )
        self.comprador_error: str | None = None
        self.manual_buyer_id_value = ""
        self.manual_buyer_text_value = ""
        self.manual_buyer_role_value = ""
        self.manual_buyer_percentage_value = ""
        self.manual_buyer_error: str | None = None
        self.manual_buyer_id_field = ft.TextField(
            label="id_persona persistido",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_manual_buyer_id_change,
        )
        self.manual_buyer_text_field = ft.TextField(
            label="Texto visual comprador",
            on_change=self._on_manual_buyer_text_change,
        )
        self.manual_buyer_role_field = ft.TextField(
            label="id_rol_participacion persistido",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_manual_buyer_role_change,
        )
        self.manual_buyer_percentage_field = ft.TextField(
            label="Responsabilidad pactada (%)",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_manual_buyer_percentage_change,
        )
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
            keyboard_type=ft.KeyboardType.TEXT,
            on_change=self._on_importe_anticipo_change,
            on_blur=self._on_importe_anticipo_commit,
            on_submit=self._on_importe_anticipo_commit,
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
            keyboard_type=ft.KeyboardType.TEXT,
            on_change=self._on_tramo_capital_change,
            on_blur=self._on_tramo_capital_commit,
            on_submit=self._on_tramo_capital_commit,
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
        self.tramo_tasa_interes_field = ft.TextField(
            label="Tasa periódica (%)",
            hint_text="Ej: 6 para 6%",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_tramo_tasa_interes_change,
        )
        self.tramo_tasa_interes_feedback = ft.Text(
            "Ingresá un porcentaje mayor que 0. Ej: 6 para 6%.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.tramo_codigo_indice_visual_field = ft.TextField(
            label="Código/índice visual",
            on_change=self._on_tramo_codigo_indice_visual_change,
        )
        self.tramo_codigo_indice_visual_feedback = ft.Text(
            "Opcional. Se usa solo para identificar el índice en pantalla.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.tramo_id_indice_financiero_field = ft.TextField(
            label="ID índice financiero backend",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_tramo_id_indice_financiero_change,
        )
        self.tramo_id_indice_financiero_feedback = ft.Text(
            "Ingresá el identificador numérico del índice financiero.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.tramo_fecha_base_indice_field = ft.TextField(
            label="Fecha base índice",
            hint_text="DD/MM/AAAA",
            width=240,
            on_change=self._on_tramo_fecha_base_indice_change,
        )
        self.tramo_fecha_base_indice_feedback = ft.Text(
            "Formato: DD/MM/AAAA",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.tramo_valor_base_indice_field = ft.TextField(
            label="Valor base índice",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_tramo_valor_base_indice_change,
        )
        self.tramo_valor_base_indice_feedback = ft.Text(
            "Ingresá un valor numérico mayor que 0.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.refuerzo_cantidad_field = ft.TextField(
            label="Cantidad de cuotas refuerzo",
            width=240,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_refuerzo_cantidad_change,
            on_blur=self._on_refuerzo_cantidad_commit,
            on_submit=self._on_refuerzo_cantidad_commit,
        )
        self.refuerzo_cantidad_feedback = ft.Text(
            "Definí primero cuántos refuerzos tendrá el tramo.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.refuerzo_numero_feedback = ft.Text(
            "Definí primero una cantidad válida de refuerzos.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
        )
        self.anticipo_actual_summary_value = ft.Text(color=ft.Colors.BLUE_GREY_900, expand=True)
        self.capital_pendiente_summary_value = ft.Text(color=ft.Colors.BLUE_GREY_900, expand=True)
        self.tramo_cuota_estimada_feedback = ft.Text(
            color=ft.Colors.BLUE_GREY_800,
            selectable=True,
        )
        self.next_button: ft.Button | None = None

    def run(self) -> None:
        self.page.title = "Wizard venta completa V3 - Datos iniciales"
        self.page.padding = 0
        self.page.scroll = None
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self._render()

    def build(self) -> ft.Control:
        self._render(update=False)
        return self.root

    def _render(self, *, update: bool = True) -> None:
        content = ft.Container(
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
        if self.embedded:
            self.root.content = content
            if update:
                safe_update(self.root)
            return
        self.page.controls.clear()
        self.page.add(content)
        if update:
            self.page.update()

    def _build_center_area(self) -> ft.Control:
        return ft.Row(
            controls=[
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        controls=[
                            self._build_stepper_bar(),
                            self._build_main_content(),
                        ],
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                ),
                ft.Container(width=300, content=self._build_flow_state_panel()),
            ],
            spacing=16,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _on_toggle_technical_data(self, event: ft.ControlEvent) -> None:
        self.state.mostrar_datos_tecnicos = bool(event.control.value)
        self._render()

    def _technical_text(self, value: str) -> ft.Control | None:
        if not self.state.mostrar_datos_tecnicos:
            return None
        return ft.Text(value, size=12, color=ft.Colors.BLUE_GREY_600, selectable=True)

    def _technical_chip(self, value: str, *, persisted: bool | None = None) -> ft.Control | None:
        if not self.state.mostrar_datos_tecnicos:
            return None
        bgcolor = ft.Colors.BLUE_GREY_50
        border_color = ft.Colors.BLUE_GREY_200
        if persisted is not None:
            bgcolor = ft.Colors.GREEN_50 if persisted else ft.Colors.AMBER_50
            border_color = ft.Colors.GREEN_200 if persisted else ft.Colors.AMBER_200
        return _badge(value, bgcolor, border_color)

    def _technical_controls(self, controls: list[ft.Control | None]) -> list[ft.Control]:
        if not self.state.mostrar_datos_tecnicos:
            return []
        return [control for control in controls if control is not None]

    @staticmethod
    def _object_type_label(tipo_objeto: str) -> str:
        labels = {
            "INMUEBLE": "Inmueble",
            "UNIDAD_FUNCIONAL": "Unidad funcional",
        }
        return labels.get(str(tipo_objeto or "").upper(), str(tipo_objeto or "-"))

    @staticmethod
    def _friendly_status_label(value: Any) -> str:
        return str(value or "").strip().replace("_", " ").upper() or "-"

    def _status_badge(self, value: Any) -> ft.Control | None:
        label = self._friendly_status_label(value)
        if label == "-":
            return None
        is_ok = label in {"DISPONIBLE", "DISPONIBLE PARA VENTA", "ACTIVA", "ACTIVO"}
        return _badge(
            label,
            ft.Colors.GREEN_50 if is_ok else ft.Colors.AMBER_50,
            ft.Colors.GREEN_200 if is_ok else ft.Colors.AMBER_200,
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
        header_actions: list[ft.Control] = []
        if self.embedded and self.on_close is not None and self.state.pantalla_actual != "VENTA_CONFIRMADA":
            header_actions.append(
                ft.OutlinedButton(
                    "Volver a ventas",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda _: self.on_close(),
                )
            )
        return ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Venta completa V3", size=28, weight=ft.FontWeight.W_700),
                        ft.Text(
                            "Prototipo pantalla por pantalla para avanzar el alta de venta completa V3.",
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
                *header_actions,
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _wizard_step_items(self) -> list[str]:
        return [label for label, _ in WIZARD_VISIBLE_STEPS]

    def _wizard_step_index(self) -> int:
        for index, (_, internal_screens) in enumerate(WIZARD_VISIBLE_STEPS):
            if self.state.pantalla_actual in internal_screens:
                return index
        return 0

    def _build_stepper_bar(self) -> ft.Control:
        current_index = self._wizard_step_index()
        step_controls: list[ft.Control] = []
        step_labels = self._wizard_step_items()

        for index, label in enumerate(step_labels):
            is_completed = index < current_index
            is_current = index == current_index
            circle_bgcolor = (
                ft.Colors.GREEN_100
                if is_completed
                else ft.Colors.BLUE_100 if is_current else ft.Colors.WHITE
            )
            circle_border = (
                ft.Colors.GREEN_400
                if is_completed
                else ft.Colors.BLUE_500 if is_current else ft.Colors.BLUE_GREY_200
            )
            circle_color = (
                ft.Colors.GREEN_800
                if is_completed
                else ft.Colors.BLUE_800 if is_current else ft.Colors.BLUE_GREY_500
            )
            circle_text = "✓" if is_completed else str(index + 1)

            step_controls.append(
                ft.Container(
                    width=88,
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                width=28,
                                height=28,
                                border_radius=14,
                                alignment=ft.Alignment(0, 0),
                                bgcolor=circle_bgcolor,
                                border=_border_all(1.5, circle_border),
                                content=ft.Text(
                                    circle_text,
                                    size=13,
                                    weight=ft.FontWeight.W_700,
                                    color=circle_color,
                                ),
                            ),
                            ft.Text(
                                label,
                                size=11,
                                weight=ft.FontWeight.W_700
                                if is_current
                                else ft.FontWeight.W_500,
                                color=ft.Colors.BLUE_800
                                if is_current
                                else ft.Colors.BLUE_GREY_700,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

            if index < len(step_labels) - 1:
                line_color = (
                    ft.Colors.BLUE_300
                    if index < current_index
                    else ft.Colors.BLUE_GREY_200
                )
                step_controls.append(
                    ft.Container(
                        expand=True,
                        padding=ft.Padding(left=0, top=13, right=0, bottom=0),
                        content=ft.Container(
                            height=2,
                            bgcolor=line_color,
                            border_radius=2,
                        ),
                    )
                )

        return ft.Container(
            padding=ft.Padding(left=14, top=10, right=14, bottom=10),
            border_radius=14,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Progreso de la venta",
                        size=12,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Row(
                        controls=step_controls,
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ],
                spacing=8,
            ),
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
        if self.state.pantalla_actual == "PLAN_TRAMO_FORM":
            return self._build_financed_plan_installment_form_step()
        if self.state.pantalla_actual == "PLAN_RESUMEN":
            return self._build_financed_plan_summary_step()
        if self.state.pantalla_actual == "PREVIEW_PLAN_PAGO":
            return self._build_plan_payment_preview_step()
        if self.state.pantalla_actual == "REVISION_GENERAL":
            return self._build_general_review_step()
        if self.state.pantalla_actual == "VENTA_CONFIRMADA":
            return self._build_confirmed_sale_step()
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
                        "Elegí una alternativa para definir el contexto inicial. Venta directa permite crear una venta nueva; desde reserva permite seleccionar una reserva real read-only.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Row(
                        controls=[
                            self._build_origin_card(
                                origin="RESERVA",
                                title="Desde reserva existente",
                                description="Buscar y seleccionar una reserva real del backend antes de continuar.",
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
        if self.reserva_select_loading:
            return self._build_deferred_step_loading("Cargando reserva seleccionada...")
        if not self.backend_reservations_loaded:
            self._start_deferred_load(
                self._load_backend_reservation_records_if_needed,
                "backend_reservations_loading",
            )
            return self._build_deferred_step_loading("Cargando reservas disponibles...")
        if self.reserva_selector is None:
            self.reserva_selector = create_search_selector_demo(
                title="Reservas reales",
                placeholder="Buscar por código, estado, objeto o comprador",
                records=self._backend_reservation_selector_records(),
                selector_kind="reserva",
                on_selection_change=self._request_reserva_selected,
                show_technical_details=self.state.mostrar_datos_tecnicos,
            )
            self._configure_reserva_selector_scroll()
        else:
            self.reserva_selector.set_show_technical_details(self.state.mostrar_datos_tecnicos)

        controls: list[ft.Control] = [
            ft.Text("Seleccionar reserva", size=24, weight=ft.FontWeight.W_700),
            ft.Text(
                "Buscá y seleccioná una reserva real del backend. Esta etapa es read-only: no confirma venta ni modifica la reserva.",
                color=ft.Colors.BLUE_GREY_700,
                weight=ft.FontWeight.W_600,
            ),
            *([self._build_help_card(self.backend_reservation_error, ft.Colors.AMBER_50, ft.Colors.AMBER_200)] if self.backend_reservation_error else []),
            *([self._build_help_card(self.reserva_select_error, ft.Colors.RED_50, ft.Colors.RED_200)] if self.reserva_select_error else []),
            self.reserva_selector.view(),
            self._build_reserva_selected_card(),
            *([self._build_help_card(self._reservation_state_warning() or "", ft.Colors.AMBER_50, ft.Colors.AMBER_200)] if self._reservation_state_warning() else []),
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

    def _start_deferred_load(
        self,
        loader: Callable[[], None],
        loading_attr: str,
    ) -> None:
        if getattr(self, loading_attr, False):
            return
        setattr(self, loading_attr, True)
        self.page.run_thread(lambda: self._run_deferred_load(loader, loading_attr))

    def _run_deferred_load(self, loader: Callable[[], None], loading_attr: str) -> None:
        try:
            loader()
        finally:
            setattr(self, loading_attr, False)
            self._render()

    def _build_deferred_step_loading(self, message: str) -> ft.Control:
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=loading_state(message),
        )

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
                        "Definí la moneda antes de cargar objetos para que todos los valores de esta venta queden en la misma moneda.",
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
                        "La moneda se aplicará a todos los valores cargados en esta venta.",
                        ft.Colors.BLUE_50,
                        ft.Colors.BLUE_200,
                    ),
                    *self._technical_controls([
                        self._build_help_card(
                            "Detalle técnico: la moneda se conserva para generar_venta, condiciones_comerciales y plan_pago_v2. La fecha se muestra como DD/MM/AAAA y se conserva internamente como YYYY-MM-DD.",
                            ft.Colors.AMBER_50,
                            ft.Colors.AMBER_200,
                        )
                    ]),
                ],
                spacing=14,
            ),
        )

    def _load_backend_reservation_records_if_needed(self) -> None:
        if self.backend_reservations_loaded:
            return
        self.backend_reservations_loaded = True
        result = self.api.get_reservas_venta(limit=50)
        if result.success:
            self.backend_reservation_records = [self._backend_reserva_record(item) for item in self._api_items(result.data)]
            self.backend_reservation_error = None if self.backend_reservation_records else "No se encontraron reservas disponibles."
            return
        self.backend_reservation_records = []
        self.backend_reservation_error = self._backend_selector_error("reservas de venta", result)

    def _load_backend_object_records_if_needed(self) -> None:
        if self.backend_objects_loaded:
            return
        self.backend_objects_loaded = True
        records: list[dict[str, Any]] = []
        errors: list[str] = []

        inmuebles_result = self.api.listar_inmuebles(limit=50)
        if inmuebles_result.success:
            records.extend(self._backend_inmueble_record(item) for item in self._api_items(inmuebles_result.data))
        else:
            errors.append(self._backend_selector_error("inmuebles", inmuebles_result))

        unidades_result = self.api.listar_unidades_funcionales(limit=50)
        if unidades_result.success:
            records.extend(self._backend_unidad_funcional_record(item) for item in self._api_items(unidades_result.data))
        else:
            errors.append(self._backend_selector_error("unidades funcionales", unidades_result))

        self.backend_object_records = self._enrich_object_records_with_venta_conflicts(records)
        if errors:
            self.backend_object_error = " ".join(errors)
        elif not records:
            self.backend_object_error = "No se encontraron objetos disponibles. Cargá inmuebles o unidades funcionales antes de continuar."
        else:
            self.backend_object_error = None

    def _load_rol_comprador_if_needed(self) -> None:
        if self.rol_comprador_catalog_loaded:
            return
        self.rol_comprador_catalog_loaded = True
        result = self.api.listar_roles_participacion(codigo="COMPRADOR")
        if not result.success:
            self.rol_comprador_data = None
            self.rol_comprador_manual_fallback_enabled = True
            self.rol_comprador_catalog_error = self._backend_selector_error(
                "rol COMPRADOR", result
            )
            return

        roles = self._api_items(result.data)
        if not roles:
            self.rol_comprador_data = None
            self.rol_comprador_manual_fallback_enabled = False
            self.rol_comprador_catalog_error = "No se encontró el rol comprador en el sistema."
            return

        self.rol_comprador_data = roles[0]
        self.rol_comprador_value = str(roles[0].get("id_rol_participacion") or "")
        self.rol_comprador_field.value = self.rol_comprador_value
        self.rol_comprador_catalog_error = None
        self.rol_comprador_manual_fallback_enabled = False

    def _rol_comprador_id_resuelto(self) -> str:
        if self.rol_comprador_data is not None:
            return str(self.rol_comprador_data.get("id_rol_participacion") or "")
        if self.rol_comprador_manual_fallback_enabled:
            return self.rol_comprador_value.strip()
        return ""

    def _load_backend_buyer_records_if_needed(self) -> None:
        if self.backend_buyers_loaded:
            return
        self.backend_buyers_loaded = True
        result = self.api.buscar_personas(limit=50)
        if result.success:
            self.backend_buyer_records = [self._backend_persona_record(item) for item in self._api_items(result.data)]
            self.backend_buyer_error = (
                None
                if self.backend_buyer_records
                else "No se encontraron personas disponibles."
            )
            return
        self.backend_buyer_records = []
        self.backend_buyer_error = self._backend_selector_error("personas", result)

    def _backend_reservation_selector_records(self) -> list[dict[str, Any]]:
        self._load_backend_reservation_records_if_needed()
        return list(self.backend_reservation_records)

    def _backend_object_selector_records(self) -> list[dict[str, Any]]:
        self._load_backend_object_records_if_needed()
        return self._mark_current_sale_objects_in_selector_records(self.backend_object_records)

    def _backend_buyer_selector_records(self) -> list[dict[str, Any]]:
        self._load_backend_buyer_records_if_needed()
        return list(self.backend_buyer_records)

    @staticmethod
    def _api_items(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            items = data.get("items")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
            nested_data = data.get("data")
            if isinstance(nested_data, list):
                return [item for item in nested_data if isinstance(item, dict)]
            if isinstance(nested_data, dict):
                nested_items = nested_data.get("items")
                if isinstance(nested_items, list):
                    return [item for item in nested_items if isinstance(item, dict)]
        return []


    @staticmethod
    def _first_present_field(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            value = item.get(key)
            if value not in (None, "", []):
                return value
        return None

    @staticmethod
    def _visible_join(value: Any) -> str:
        if value in (None, "", []):
            return ""
        if isinstance(value, (str, int, float, bool, Decimal)):
            return str(value).strip()
        if isinstance(value, list):
            return ", ".join(part for part in (VentaCompletaWizardV3Prototype._visible_join(entry) for entry in value) if part)
        if isinstance(value, dict):
            nombre = VentaCompletaWizardV3Prototype._visible_join(value.get("nombre"))
            apellido = VentaCompletaWizardV3Prototype._visible_join(value.get("apellido"))
            nombre_apellido = " ".join(part for part in [nombre, apellido] if part)
            codigo_objeto = (
                VentaCompletaWizardV3Prototype._visible_join(value.get("codigo_inmueble"))
                or VentaCompletaWizardV3Prototype._visible_join(value.get("codigo_unidad_funcional"))
            )
            descripcion_objeto = (
                VentaCompletaWizardV3Prototype._visible_join(value.get("descripcion"))
                or VentaCompletaWizardV3Prototype._visible_join(value.get("observaciones"))
            )
            if codigo_objeto and descripcion_objeto:
                return " — ".join([codigo_objeto, descripcion_objeto])
            for key in ("texto_visual", "display_name", "nombre_completo", "razon_social"):
                text = VentaCompletaWizardV3Prototype._visible_join(value.get(key))
                if text:
                    return text
            if nombre_apellido:
                return nombre_apellido
            for key in (
                "codigo_reserva",
                "codigo_inmueble",
                "codigo_unidad_funcional",
                "codigo",
                "descripcion",
                "observaciones",
            ):
                text = VentaCompletaWizardV3Prototype._visible_join(value.get(key))
                if text:
                    return text
            return ""
        return ""

    @staticmethod
    def _visible_date(value: Any) -> str:
        text = VentaCompletaWizardV3Prototype._visible_join(value)
        if not text:
            return ""
        date_part = text[:10]
        if len(date_part) == 10 and date_part[4] == "-" and date_part[7] == "-":
            year, month, day = date_part.split("-")
            return f"{day}/{month}/{year}"
        return text

    def _backend_reserva_record(self, item: dict[str, Any]) -> dict[str, Any]:
        codigo = self._visible_join(VentaCompletaWizardV3Prototype._first_present_field(item, ("codigo_reserva", "codigo", "numero_reserva")))
        estado = self._visible_join(VentaCompletaWizardV3Prototype._first_present_field(item, ("estado", "estado_reserva")))
        fecha = self._visible_date(VentaCompletaWizardV3Prototype._first_present_field(item, ("fecha", "fecha_reserva", "fecha_alta", "created_at")))
        vencimiento = self._visible_date(VentaCompletaWizardV3Prototype._first_present_field(item, ("vencimiento", "fecha_vencimiento", "fecha_vencimiento_reserva", "fecha_hasta")))
        objetos = self._visible_join(VentaCompletaWizardV3Prototype._first_present_field(item, ("objetos", "objeto", "inmuebles", "unidades_funcionales")))
        compradores = self._visible_join(VentaCompletaWizardV3Prototype._first_present_field(item, ("compradores", "comprador", "reservantes", "reservante", "cliente")))
        moneda = self._visible_join(VentaCompletaWizardV3Prototype._first_present_field(item, ("moneda", "codigo_moneda")))
        importe = self._visible_join(VentaCompletaWizardV3Prototype._first_present_field(item, ("importe", "precio_reservado", "importe_reserva", "precio_total", "monto")))
        return {
            "id_reserva_venta": VentaCompletaWizardV3Prototype._first_present_field(item, ("id_reserva_venta", "id_reserva", "id")),
            "version_registro": item.get("version_registro"),
            "codigo_reserva": codigo,
            "estado": estado,
            "fecha": fecha,
            "vencimiento": vencimiento,
            "objeto": objetos,
            "comprador": compradores,
            "moneda": moneda,
            "importe": importe,
            "resumen": " — ".join(str(v) for v in (compradores, objetos) if v),
            "source": "backend",
            "persisted": True,
            "raw": item,
        }

    @staticmethod
    def _backend_selector_error(label: str, result: ApiResult) -> str:
        parts = [f"No se pudieron cargar {label} disponibles desde el sistema."]
        if result.status_code is not None:
            parts.append(f"HTTP {result.status_code}.")
        if result.error_code:
            parts.append(f"{result.error_code}.")
        if result.error_message:
            parts.append(result.error_message)
        return " ".join(parts)

    @staticmethod
    def _venta_conflict_from_item(item: dict[str, Any]) -> dict[str, Any] | None:
        for key in ("venta_conflictiva", "venta_vigente", "venta_actual"):
            value = item.get(key)
            if isinstance(value, dict) and value:
                return value
        for key in ("tiene_venta_vigente", "venta_vigente", "con_venta_vigente"):
            if item.get(key) is True:
                return {"motivo": VENTA_SELECTOR_BLOCK_REASON}
        return None

    @staticmethod
    def _venta_is_selector_conflict(venta: dict[str, Any]) -> bool:
        if venta.get("deleted_at") not in (None, ""):
            return False
        estado = str(venta.get("estado_venta") or venta.get("estado") or "").strip().lower()
        return estado in VENTA_SELECTOR_CONFLICT_STATES

    def _enrich_object_records_with_venta_conflicts(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for record in records:
            next_record = dict(record)
            conflict = self._venta_conflict_from_item(next_record)
            if conflict is not None:
                next_record["venta_vigente"] = True
                next_record["venta_conflictiva"] = conflict
                next_record["motivo_bloqueo"] = VENTA_SELECTOR_BLOCK_REASON
            enriched.append(next_record)

        # Prototipo frontend: GET /api/v1/ventas no acepta filtro batch por muchos
        # objetos; se consulta una pagina razonable por estado vigente y se indexa
        # localmente para evitar una llamada por inmueble/UF del selector.
        conflict_index = self._build_selector_venta_conflict_index(enriched)
        return self._apply_selector_venta_conflict_index(enriched, conflict_index)

    def _fetch_selector_active_ventas(self) -> list[dict[str, Any]]:
        ventas: list[dict[str, Any]] = []
        limit = 100
        max_pages_per_state = 5
        for estado in sorted(VENTA_SELECTOR_CONFLICT_STATES):
            offset = 0
            for _ in range(max_pages_per_state):
                result = self.api.get_ventas(estado_venta=estado, limit=limit, offset=offset)
                if not result.success:
                    break
                ventas.extend(self._api_items(result.data))
                total = result.data.get("total") if isinstance(result.data, dict) else None
                offset += limit
                if not isinstance(total, int) or offset >= total:
                    break
        return ventas

    @staticmethod
    def _venta_conflict_summary(venta: dict[str, Any], objeto: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "id_venta": venta.get("id_venta"),
            "codigo_venta": venta.get("codigo_venta"),
            "estado_venta": venta.get("estado_venta"),
            "id_inmueble": objeto.get("id_inmueble") if isinstance(objeto, dict) else None,
            "id_unidad_funcional": objeto.get("id_unidad_funcional") if isinstance(objeto, dict) else None,
        }

    def _build_selector_venta_conflict_index(self, records: list[dict[str, Any]]) -> dict[str, dict[int, dict[str, Any]]]:
        direct_inmuebles: dict[int, dict[str, Any]] = {}
        direct_unidades: dict[int, dict[str, Any]] = {}
        for venta in self._fetch_selector_active_ventas():
            if not self._venta_is_selector_conflict(venta):
                continue
            for objeto in self._as_list(venta.get("objetos_resumen") or venta.get("objetos")):
                if not isinstance(objeto, dict):
                    continue
                id_inmueble = _safe_int(objeto.get("id_inmueble"))
                id_unidad = _safe_int(objeto.get("id_unidad_funcional"))
                summary = self._venta_conflict_summary(venta, objeto)
                if id_inmueble is not None:
                    direct_inmuebles.setdefault(id_inmueble, summary)
                if id_unidad is not None:
                    direct_unidades.setdefault(id_unidad, summary)
        return {"inmuebles": direct_inmuebles, "unidades": direct_unidades}

    def _apply_selector_venta_conflict_index(
        self,
        records: list[dict[str, Any]],
        conflict_index: dict[str, dict[int, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        direct_inmuebles = conflict_index.get("inmuebles", {})
        direct_unidades = conflict_index.get("unidades", {})
        unidades_by_parent: dict[int, list[int]] = {}
        for record in records:
            if str(record.get("tipo_objeto") or "").upper() != "UNIDAD_FUNCIONAL":
                continue
            id_parent = _safe_int(record.get("id_inmueble") or record.get("inmueble_padre_id"))
            id_unidad = _safe_int(record.get("id_unidad_funcional"))
            if id_parent is not None and id_unidad is not None:
                unidades_by_parent.setdefault(id_parent, []).append(id_unidad)

        indexed: list[dict[str, Any]] = []
        for record in records:
            next_record = dict(record)
            tipo_objeto = str(next_record.get("tipo_objeto") or "").upper()
            id_inmueble = _safe_int(next_record.get("id_inmueble"))
            id_unidad = _safe_int(next_record.get("id_unidad_funcional"))
            if tipo_objeto == "INMUEBLE" and id_inmueble is not None:
                direct = direct_inmuebles.get(id_inmueble)
                if direct is not None and not next_record.get("motivo_bloqueo"):
                    next_record["venta_vigente"] = True
                    next_record["venta_conflictiva"] = direct
                    next_record["motivo_bloqueo"] = VENTA_SELECTOR_BLOCK_REASON
                elif not next_record.get("motivo_bloqueo"):
                    for child_id in unidades_by_parent.get(id_inmueble, []):
                        related = direct_unidades.get(child_id)
                        if related is not None:
                            next_record["venta_conflictiva_jerarquica"] = related
                            next_record["motivo_bloqueo"] = VENTA_SELECTOR_RELATED_BLOCK_REASON
                            break
            elif tipo_objeto == "UNIDAD_FUNCIONAL" and id_unidad is not None:
                direct = direct_unidades.get(id_unidad)
                if direct is not None and not next_record.get("motivo_bloqueo"):
                    next_record["venta_vigente"] = True
                    next_record["venta_conflictiva"] = direct
                    next_record["motivo_bloqueo"] = VENTA_SELECTOR_BLOCK_REASON
                elif not next_record.get("motivo_bloqueo"):
                    parent_id = _safe_int(next_record.get("id_inmueble") or next_record.get("inmueble_padre_id"))
                    related = direct_inmuebles.get(parent_id) if parent_id is not None else None
                    if related is not None:
                        next_record["venta_conflictiva_jerarquica"] = related
                        next_record["motivo_bloqueo"] = VENTA_SELECTOR_RELATED_BLOCK_REASON
            indexed.append(next_record)
        return indexed

    @staticmethod
    def _object_record_key(record: dict[str, Any]) -> tuple[str, int] | None:
        tipo_objeto = str(record.get("tipo_objeto") or "").upper()
        if tipo_objeto == "UNIDAD_FUNCIONAL":
            id_unidad = _safe_int(record.get("id_unidad_funcional"))
            return ("UNIDAD_FUNCIONAL", id_unidad) if id_unidad is not None else None
        if tipo_objeto == "INMUEBLE":
            id_inmueble = _safe_int(record.get("id_inmueble"))
            return ("INMUEBLE", id_inmueble) if id_inmueble is not None else None
        return None

    def _current_sale_object_keys(self) -> set[tuple[str, int]]:
        keys: set[tuple[str, int]] = set()
        for objeto in self.state.objetos:
            if objeto.tipo_objeto == "UNIDAD_FUNCIONAL" and objeto.id_unidad_funcional is not None:
                keys.add(("UNIDAD_FUNCIONAL", int(objeto.id_unidad_funcional)))
            elif objeto.tipo_objeto == "INMUEBLE" and objeto.id_inmueble is not None:
                keys.add(("INMUEBLE", int(objeto.id_inmueble)))
        return keys

    def _mark_current_sale_objects_in_selector_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        current_keys = self._current_sale_object_keys()
        marked: list[dict[str, Any]] = []
        for record in records:
            next_record = dict(record)
            if self._object_record_key(next_record) in current_keys:
                next_record["agregado_en_venta_actual"] = True
                if not next_record.get("motivo_bloqueo"):
                    next_record["motivo_bloqueo"] = VENTA_SELECTOR_ALREADY_ADDED_REASON
            else:
                next_record["agregado_en_venta_actual"] = False
            marked.append(next_record)
        return marked

    @staticmethod
    def _availability_label(value: Any) -> str:
        if isinstance(value, dict):
            return str(
                value.get("estado_disponibilidad")
                or value.get("estado")
                or value.get("codigo")
                or ""
            ).strip()
        return str(value or "").strip()

    def _backend_inmueble_record(self, item: dict[str, Any]) -> dict[str, Any]:
        codigo = str(item.get("codigo_inmueble") or item.get("codigo") or item.get("id_inmueble") or "").strip()
        descripcion = str(item.get("nombre_inmueble") or item.get("nombre") or item.get("descripcion") or "Inmueble").strip()
        disponibilidad = self._availability_label(item.get("disponibilidad_actual"))
        venta_conflictiva = self._venta_conflict_from_item(item)
        return {
            "tipo_objeto": "INMUEBLE",
            "id_inmueble": item.get("id_inmueble"),
            "codigo": codigo,
            "descripcion": descripcion,
            "estado": disponibilidad,
            "estado_administrativo": item.get("estado_administrativo") or "",
            "ocupacion_actual": item.get("ocupacion_actual"),
            "venta_vigente": bool(venta_conflictiva),
            "venta_conflictiva": venta_conflictiva,
            "motivo_bloqueo": VENTA_SELECTOR_BLOCK_REASON if venta_conflictiva else "",
            "resumen": str(item.get("direccion") or item.get("ubicacion") or item.get("observaciones") or "Inmueble."),
            "source": "backend",
            "persisted": True,
        }

    def _backend_unidad_funcional_record(self, item: dict[str, Any]) -> dict[str, Any]:
        codigo = str(item.get("codigo_unidad_funcional") or item.get("codigo_unidad") or item.get("id_unidad_funcional") or "").strip()
        descripcion = str(item.get("nombre_unidad") or item.get("nombre") or item.get("descripcion") or "Unidad funcional").strip()
        inmueble = item.get("inmueble") if isinstance(item.get("inmueble"), dict) else {}
        disponibilidad = self._availability_label(item.get("disponibilidad_actual"))
        venta_conflictiva = self._venta_conflict_from_item(item)
        return {
            "tipo_objeto": "UNIDAD_FUNCIONAL",
            "id_unidad_funcional": item.get("id_unidad_funcional"),
            "id_inmueble": item.get("id_inmueble") or inmueble.get("id_inmueble"),
            "codigo": codigo,
            "descripcion": descripcion,
            "inmueble_padre": inmueble.get("codigo_inmueble") or inmueble.get("nombre_inmueble") or item.get("id_inmueble"),
            "estado": disponibilidad,
            "estado_operativo": item.get("estado_operativo") or "",
            "estado_administrativo": item.get("estado_administrativo") or "",
            "ocupacion_actual": item.get("ocupacion_actual"),
            "venta_vigente": bool(venta_conflictiva),
            "venta_conflictiva": venta_conflictiva,
            "motivo_bloqueo": VENTA_SELECTOR_BLOCK_REASON if venta_conflictiva else "",
            "resumen": str(item.get("observaciones") or "Unidad funcional."),
            "source": "backend",
            "persisted": True,
        }

    @staticmethod
    def _backend_persona_record(item: dict[str, Any]) -> dict[str, Any]:
        documento = item.get("documento_principal") if isinstance(item.get("documento_principal"), dict) else {}
        document_label = " ".join(
            part
            for part in [str(documento.get("tipo_documento") or "").strip(), str(documento.get("numero_documento") or "").strip()]
            if part
        )
        return {
            "id_persona": item.get("id_persona"),
            "codigo_persona": str(item.get("id_persona") or ""),
            "nombre": item.get("display_name") or item.get("nombre"),
            "apellido": None if item.get("display_name") else item.get("apellido"),
            "razon_social": item.get("razon_social"),
            "documento": document_label or item.get("cuit_cuil") or "",
            "estado": item.get("estado_persona") or "activa",
            "resumen": f"Persona {(item.get('estado_persona') or 'activa').lower()}",
            "source": "backend",
            "persisted": True,
        }

    def _build_objects_step(self) -> ft.Control:
        if self.state.origen == "RESERVA":
            controls: list[ft.Control] = [
                ft.Text("Objetos de venta", size=24, weight=ft.FontWeight.W_700),
                ft.Text("Los objetos provienen de la reserva seleccionada. No se puede cambiar el objeto, pero sí completar el valor comercial si falta.", color=ft.Colors.BLUE_GREY_700),
                self._build_help_card(
                    "Los objetos provienen de la reserva seleccionada. No se puede cambiar el objeto, pero sí completar el valor comercial si falta.",
                    ft.Colors.AMBER_50,
                    ft.Colors.AMBER_200,
                ),
                *([] if self.state.objetos else [self._build_help_card("La reserva seleccionada no informa objetos. No se inventan datos y el avance queda sujeto a las validaciones existentes.", ft.Colors.RED_50, ft.Colors.RED_200)]),
                self._build_added_objects_list(),
                self._build_objects_total_summary(),
            ]
            return ft.Container(
                padding=18,
                border_radius=14,
                bgcolor=ft.Colors.WHITE,
                border=_border_all(1, ft.Colors.BLUE_GREY_100),
                content=ft.Column(controls=controls, spacing=14),
            )
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
        if self.object_select_loading:
            return self._build_deferred_step_loading("Cargando objeto seleccionado...")
        if not self.backend_objects_loaded:
            self._start_deferred_load(
                self._load_backend_object_records_if_needed,
                "backend_objects_loading",
            )
            return self._build_deferred_step_loading("Cargando inmuebles disponibles...")
        if self.objeto_selector is None:
            self.objeto_selector = create_search_selector_demo(
                title="Buscador de objeto inmobiliario real",
                placeholder="Código, descripción o tipo del objeto",
                selector_kind="objeto",
                records=self._backend_object_selector_records(),
                on_selection_change=self._request_objeto_selected,
                show_technical_details=self.state.mostrar_datos_tecnicos,
            )
            self._configure_objeto_selector_scroll()
        else:
            self.objeto_selector.set_records(self._backend_object_selector_records())
        self.objeto_selector.set_show_technical_details(self.state.mostrar_datos_tecnicos)

        controls: list[ft.Control] = [
            ft.Text("Objetos de venta", size=24, weight=ft.FontWeight.W_700),
            ft.Text(
                f"Seleccioná los inmuebles o unidades funcionales incluidos en la operación y asigná el valor comercial de cada uno en {self._currency_label()}.",
                color=ft.Colors.BLUE_GREY_700,
            ),
            self._build_help_card(
                "El buscador muestra inmuebles y unidades funcionales disponibles y no disponibles. Solo los objetos DISPONIBLES pueden seleccionarse; si la disponibilidad no está informada, la UI permite continuar y el backend validará al confirmar.",
                ft.Colors.BLUE_50,
                ft.Colors.BLUE_200,
            ),
            *(
                [self._build_help_card(self.backend_object_error, ft.Colors.AMBER_50, ft.Colors.AMBER_200)]
                if self.backend_object_error is not None
                else []
            ),
            *(
                [self._build_help_card(self.object_select_error, ft.Colors.RED_50, ft.Colors.RED_200)]
                if self.object_select_error is not None
                else []
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
                        "La validación final de solapamiento entre inmueble completo y unidades funcionales se realiza al confirmar.",
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
        status_badge = self._status_badge(self.objeto_seleccionado.get("estado"))
        is_selectable = is_object_selectable(
            self.objeto_seleccionado.get("estado"),
            self.objeto_seleccionado.get("ocupacion_actual"),
            self.objeto_seleccionado.get("venta_vigente") or self.objeto_seleccionado.get("venta_conflictiva") or self.objeto_seleccionado.get("venta_conflictiva_jerarquica"),
            self.objeto_seleccionado.get("motivo_bloqueo"),
        )
        availability_warning = object_selection_warning(
            self.objeto_seleccionado.get("estado"),
            self.objeto_seleccionado.get("ocupacion_actual"),
            self.objeto_seleccionado.get("venta_vigente") or self.objeto_seleccionado.get("venta_conflictiva") or self.objeto_seleccionado.get("venta_conflictiva_jerarquica"),
            self.objeto_seleccionado.get("motivo_bloqueo"),
        )
        panel_content = ft.Column(
            controls=[
                ft.Text("Objeto seleccionado", size=18, weight=ft.FontWeight.W_700),
                ft.Text(str(self.objeto_seleccionado.get("texto_visual") or "-"), weight=ft.FontWeight.W_600),
                ft.Row(
                    controls=[
                        _badge(f"Tipo: {self._object_type_label(tipo_objeto)}", ft.Colors.BLUE_GREY_50, ft.Colors.BLUE_GREY_200),
                        *([status_badge] if status_badge is not None else []),
                        *self._technical_controls([
                            self._technical_chip(f"ID técnico secundario ({id_label}): {id_value}"),
                            self._technical_chip(
                                self._record_source_label(
                                    str(self.objeto_seleccionado.get("source") or "backend"),
                                    bool(self.objeto_seleccionado.get("persisted", False)),
                                ),
                                persisted=bool(self.objeto_seleccionado.get("persisted", False)),
                            ),
                            *(
                                [self._technical_chip(f"estado_administrativo: {self.objeto_seleccionado.get('estado_administrativo')}")]
                                if self.objeto_seleccionado.get("estado_administrativo")
                                else []
                            ),
                            *(
                                [self._technical_chip(f"ocupacion_actual: {self.objeto_seleccionado.get('ocupacion_actual')}")]
                                if self.objeto_seleccionado.get("ocupacion_actual")
                                else []
                            ),
                            self._technical_chip(f"venta_vigente: {bool(self.objeto_seleccionado.get('venta_vigente') or self.objeto_seleccionado.get('venta_conflictiva'))}"),
                            self._technical_chip(f"agregado_en_venta_actual: {bool(self.objeto_seleccionado.get('agregado_en_venta_actual'))}"),
                            *(
                                [self._technical_chip(f"venta_conflictiva_jerarquica: {self.objeto_seleccionado.get('venta_conflictiva_jerarquica')}")]
                                if self.objeto_seleccionado.get("venta_conflictiva_jerarquica")
                                else []
                            ),
                            *(
                                [self._technical_chip(f"venta_conflictiva: {self.objeto_seleccionado.get('venta_conflictiva')}")]
                                if self.objeto_seleccionado.get("venta_conflictiva")
                                else []
                            ),
                            *(
                                [self._technical_chip(f"motivo_bloqueo: {self.objeto_seleccionado.get('motivo_bloqueo')}")]
                                if self.objeto_seleccionado.get("motivo_bloqueo")
                                else []
                            ),
                        ]),
                    ],
                    wrap=True,
                    spacing=8,
                ),
                *(
                    [
                        ft.Text(
                            availability_warning or "",
                            size=12,
                            color=ft.Colors.AMBER_900 if is_selectable else ft.Colors.RED_700,
                        )
                    ]
                    if availability_warning is not None
                    else []
                ),
                self.precio_objeto_field,
                ft.Text(
                    price_error or "Ingresá el valor comercial asignado a este objeto.",
                    size=12,
                    color=ft.Colors.RED_700 if price_error else ft.Colors.BLUE_GREY_600,
                ),
                ft.Row(
                    controls=[
                        ft.Button(
                            "Agregar a la venta",
                            icon=ft.Icons.ADD,
                            disabled=duplicate or not is_selectable,
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
                    "Este objeto ya fue agregado a la venta." if duplicate else "El objeto no está disponible para esta venta." if not is_selectable else "",
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
                            ft.Row(
                                controls=[
                                    _badge(
                                        f"Tipo: {self._object_type_label(objeto.tipo_objeto)}",
                                        ft.Colors.BLUE_GREY_50,
                                        ft.Colors.BLUE_GREY_200,
                                    ),
                                    *([] if objeto.heredado_reserva else [
                                        _badge(
                                            f"Precio: {self._format_money_with_currency(_parse_money_decimal(objeto.precio_asignado) or Decimal('0'))}",
                                            ft.Colors.GREEN_50,
                                            ft.Colors.GREEN_200,
                                        )
                                    ]),
                                ],
                                spacing=8,
                                wrap=True,
                            ),
                            *([self._build_reservation_object_price_field(index, objeto)] if objeto.heredado_reserva else []),
                            *self._technical_controls([
                                self._technical_text(f"ID técnico secundario ({id_label}): {id_value}"),
                                self._technical_text(f"Origen dato: {self._record_source_label(objeto.source, objeto.persisted)}"),
                                self._technical_text(f"heredado_reserva: {objeto.heredado_reserva}"),
                            ]),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.OutlinedButton(
                        "Quitar",
                        icon=ft.Icons.DELETE_OUTLINE,
                        disabled=objeto.heredado_reserva,
                        on_click=lambda _, item_index=index: self._remove_object(item_index),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )

    def _build_reservation_object_price_field(self, index: int, objeto: ObjetoVentaWizardDraft) -> ft.Control:
        parsed = _parse_money_decimal(objeto.precio_asignado)
        has_error = parsed is None
        return ft.Column(
            controls=[
                ft.TextField(
                    label=f"Valor comercial asignado ({self._currency_label()})",
                    value=objeto.precio_asignado,
                    dense=True,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    on_change=lambda event, item_index=index: self._on_reservation_object_price_change(item_index, event),
                    on_blur=lambda event, item_index=index: self._on_reservation_object_price_blur(item_index, event),
                ),
                ft.Text(
                    "Completá un precio válido para avanzar." if has_error else "Precio editable; el objeto heredado no se puede cambiar ni quitar.",
                    size=12,
                    color=ft.Colors.RED_700 if has_error else ft.Colors.BLUE_GREY_600,
                ),
            ],
            spacing=4,
            tight=True,
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
                    _info_row("Suma de precios asignados", self._format_money_with_currency(total)),
                    _info_row("Total derivado", self._format_money_with_currency(total)),
                ],
                spacing=8,
            ),
        )

    def _build_buyers_step(self) -> ft.Control:
        if self.state.origen == "RESERVA":
            return self._build_reserva_buyers_info_step()

        if self.buyer_select_loading:
            return self._build_deferred_step_loading("Cargando comprador seleccionado...")

        if not self.rol_comprador_catalog_loaded:
            self._start_deferred_load(
                self._load_rol_comprador_if_needed,
                "rol_comprador_loading",
            )
            return self._build_deferred_step_loading("Cargando partes...")

        if not self.backend_buyers_loaded:
            self._start_deferred_load(
                self._load_backend_buyer_records_if_needed,
                "backend_buyers_loading",
            )
            return self._build_deferred_step_loading("Buscando compradores...")

        if self.comprador_selector is None:
            self.comprador_selector = create_search_selector_demo(
                title="Buscador de persona real",
                placeholder="Nombre, documento, código o dato visible del comprador",
                selector_kind="persona",
                records=self._backend_buyer_selector_records(),
                on_selection_change=self._request_comprador_selected,
                show_technical_details=self.state.mostrar_datos_tecnicos,
            )
            self._configure_comprador_selector_scroll()
        self.comprador_selector.set_show_technical_details(self.state.mostrar_datos_tecnicos)

        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Compradores", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Seleccioná personas disponibles y definí la responsabilidad pactada de cada comprador.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    self._build_help_card(
                        "El buscador muestra personas disponibles para operar. Si no aparecen resultados, cargá las personas antes de continuar.",
                        ft.Colors.BLUE_50,
                        ft.Colors.BLUE_200,
                    ),
                    self._build_rol_comprador_status_card(),
                    *(
                        [self._build_help_card(self.backend_buyer_error, ft.Colors.AMBER_50, ft.Colors.AMBER_200)]
                        if self.backend_buyer_error is not None
                        else []
                    ),
                    *(
                        [self._build_help_card(self.buyer_select_error, ft.Colors.RED_50, ft.Colors.RED_200)]
                        if self.buyer_select_error is not None
                        else []
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
            ft.Text("Los compradores provienen de la reserva seleccionada. La edición queda bloqueada en esta etapa.", color=ft.Colors.BLUE_GREY_700),
            self._build_reserva_selected_card(),
            self._build_help_card(
                "Los compradores provienen de la reserva seleccionada. La edición queda bloqueada en esta etapa.",
                ft.Colors.AMBER_50,
                ft.Colors.AMBER_200,
            ),
            *([] if self.state.compradores else [self._build_help_card(self._reservation_buyers_missing_message(), ft.Colors.RED_50, ft.Colors.RED_200)]),
            self._build_added_buyers_list(),
            self._build_buyers_summary(),
        ]
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=14),
        )

    def _build_reserva_selected_card(self) -> ft.Control:
        data = self.state.reserva_visible_data
        controls: list[ft.Control] = [
            ft.Text("Reserva seleccionada", size=18, weight=ft.FontWeight.W_700),
        ]
        if not self.state.id_reserva_venta:
            controls.append(ft.Text("Seleccioná una reserva real para continuar.", color=ft.Colors.BLUE_GREY_700))
        else:
            controls.extend([
                *([self._build_help_card(str(data.get("detalle_warning")), ft.Colors.AMBER_50, ft.Colors.AMBER_200)] if data.get("detalle_warning") else []),
                *([self._build_help_card(str(data.get("compradores_warning")), ft.Colors.AMBER_50, ft.Colors.AMBER_200)] if data.get("compradores_warning") else []),
                _info_row("Código", data.get("codigo") or "No informado"),
                _info_row("Estado", data.get("estado") or "No informado"),
                _info_row("Fecha", data.get("fecha") or "No informado"),
                _info_row("Vencimiento", data.get("vencimiento") or "No informado"),
                _info_row("Objeto/s", data.get("objetos") or "No informado"),
                _info_row("Comprador/es", data.get("compradores") or "No informado"),
                _info_row("Moneda", data.get("moneda") or "No informado"),
                _info_row("Importe / precio", data.get("importe") or "No informado"),
                *self._technical_controls([
                    _info_row("id_reserva_venta", self.state.id_reserva_venta),
                    _info_row("version_registro", self.state.version_registro if self.state.version_registro is not None else "No informado"),
                    _info_row("detalle reserva cargado", "sí" if self.state.reserva_detalle_loaded else "no"),
                    _info_row("fuente precarga", self.state.reserva_detalle_source),
                    _info_row("cantidad objetos detalle", self.state.reserva_detalle_objetos_count),
                    _info_row("cantidad participaciones detalle", self.state.reserva_detalle_participaciones_count),
                    _info_row("error detalle", self.state.reserva_detalle_error or "sin error"),
                ]),
            ])
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.GREEN_50 if self.state.id_reserva_venta else ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.GREEN_200 if self.state.id_reserva_venta else ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=6),
        )

    def _build_inherited_buyers_pending_card(self) -> ft.Control:
        pending_controls: list[ft.Control] = [
            ft.Text("Compradores heredados", size=18, weight=ft.FontWeight.W_700),
            ft.Container(
                padding=12,
                border_radius=10,
                bgcolor=ft.Colors.BLUE_GREY_50,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Pendiente de datos reales de compradores de la reserva.",
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            "La reserva, los objetos y los compradores heredados se mantienen read-only; la confirmación usa el backend real.",
                            size=12,
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                    ],
                    spacing=4,
                ),
            ),
            ft.Text(
                "Cuando exista la integración de reservas, se mostrarán aquí los compradores precargados y se validarán antes de confirmar.",
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
        if self.rol_comprador_manual_fallback_enabled:
            controls.append(self._build_manual_buyer_persisted_panel())
        controls.extend([self._build_added_buyers_list(), self._build_buyers_summary()])
        return ft.Column(controls=controls, spacing=12)

    def _build_rol_comprador_status_card(self) -> ft.Control:
        if self.rol_comprador_data is not None:
            return self._build_help_card(
                "Rol comprador asignado automáticamente." + (f" id_rol_participacion={self._rol_comprador_id_resuelto()}." if self.state.mostrar_datos_tecnicos else ""),
                ft.Colors.GREEN_50,
                ft.Colors.GREEN_200,
            )
        if self.rol_comprador_catalog_error is not None:
            return self._build_help_card(
                self.rol_comprador_catalog_error,
                ft.Colors.RED_50
                if not self.rol_comprador_manual_fallback_enabled
                else ft.Colors.AMBER_50,
                ft.Colors.RED_200
                if not self.rol_comprador_manual_fallback_enabled
                else ft.Colors.AMBER_200,
            )
        return self._build_help_card(
            "Resolviendo rol comprador desde el sistema.",
            ft.Colors.BLUE_50,
            ft.Colors.BLUE_200,
        )

    def _build_manual_buyer_persisted_panel(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Modo técnico/dev: comprador persistido", size=18, weight=ft.FontWeight.W_700),
            ft.Text(
                "Fallback explícito: usá esta carga solo si falló la carga del catálogo de roles.",
                size=12,
                color=ft.Colors.BLUE_GREY_700,
            ),
            self.manual_buyer_id_field,
            self.manual_buyer_text_field,
            self.manual_buyer_role_field,
            self.manual_buyer_percentage_field,
            ft.Text(
                "Si es el único comprador, el porcentaje puede quedar vacío y se asumirá 100%.",
                size=12,
                color=ft.Colors.BLUE_GREY_600,
            ),
        ]
        if self.manual_buyer_error is not None:
            controls.append(ft.Text(self.manual_buyer_error, size=12, color=ft.Colors.RED_700))
        controls.append(
            ft.Button(
                "Agregar comprador persistido",
                icon=ft.Icons.PERSON_ADD_ALT_1,
                on_click=self._add_manual_persisted_buyer,
            )
        )
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.TEAL_50,
            border=_border_all(1, ft.Colors.TEAL_200),
            content=ft.Column(controls=controls, spacing=8),
        )

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
                    ft.Row(
                        controls=[
                            _badge("Rol: COMPRADOR", ft.Colors.GREEN_50, ft.Colors.GREEN_200),
                            *self._technical_controls([
                                self._technical_chip(f"ID técnico secundario (id_persona): {self.comprador_seleccionado.get('id_persona') or '-'}"),
                                self._technical_chip(
                                    self._record_source_label(
                                        str(self.comprador_seleccionado.get("source") or "backend"),
                                        bool(self.comprador_seleccionado.get("persisted", False)),
                                    ),
                                    persisted=bool(self.comprador_seleccionado.get("persisted", False)),
                                ),
                            ]),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    self.porcentaje_comprador_field,
                    ft.Text(
                        "Si es el único comprador, se asumirá 100%.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_600,
                    ),
                    *self._technical_controls([_info_row("id_rol_participacion", self._rol_comprador_id_resuelto() or "pendiente")]),
                    ft.Row(
                        controls=[
                            ft.Button(
                                "Agregar comprador",
                                icon=ft.Icons.PERSON_ADD_ALT_1,
                                disabled=duplicate or not self._rol_comprador_id_resuelto(),
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
        porcentaje = (
            f"Responsabilidad: {comprador.porcentaje_responsabilidad}%"
            if comprador.porcentaje_responsabilidad
            else "Se asumirá 100% por ser único comprador"
        )
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
                            ft.Row(
                                controls=[
                                    _badge("Rol: COMPRADOR", ft.Colors.GREEN_50, ft.Colors.GREEN_200),
                                    ft.Text(
                                        porcentaje,
                                        size=12,
                                        color=ft.Colors.BLUE_GREY_700,
                                    ),
                                ],
                                spacing=8,
                                wrap=True,
                            ),
                            *self._technical_controls([
                                self._technical_text(f"id_persona: {comprador.id_persona}"),
                                self._technical_text(f"id_rol_participacion: {comprador.id_rol_participacion}"),
                                self._technical_text(f"Origen dato: {self._record_source_label(comprador.source, comprador.persisted)}"),
                                self._technical_text(f"heredado_reserva: {comprador.heredado_reserva}"),
                            ]),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.OutlinedButton(
                        "Quitar",
                        icon=ft.Icons.DELETE_OUTLINE,
                        disabled=comprador.heredado_reserva,
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
                    self._build_plan_preview_status_section(),
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
                "Definí si la operación tendrá anticipo. El saldo restante se asignará luego a tramos de cuotas y refuerzos internos.",
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
                    "Todo el total quedará pendiente para tramos de cuotas y refuerzos internos.",
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
                        "El anticipo se incluirá en el plan de pago de la venta.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                ],
                spacing=8,
            ),
        )


    def _build_financed_plan_installments_step(self) -> ft.Control:
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
                        "Un tramo es un grupo de cuotas con las mismas condiciones. Podés financiar todo el saldo en un solo tramo o en varios tramos diferentes.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Text(
                        "La pantalla de tramos mantiene el resumen/listado; la actualización se define al cargar cada tramo.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Text(
                        "El plan se cargará en el siguiente paso. Los datos serán validados al confirmar la venta.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_600,
                    ),
                    self._build_installments_top_summary(capital_base, capital_assigned, capital_remaining),
                    self._build_added_installments_list(),
                    self._build_add_installment_button(),
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
                    _info_row("Capital pendiente después de anticipo", self._format_money_with_currency(capital_base)),
                    _info_row("Capital asignado a tramos", self._format_money_with_currency(capital_assigned)),
                    _info_row("Capital restante", self._format_money_with_currency(capital_remaining)),
                    *(
                        [
                            ft.Text(
                                "Todavía queda capital por financiar. Agregá otro tramo o ajustá los tramos existentes hasta cubrir todo el capital pendiente.",
                                size=12,
                                color=ft.Colors.BLUE_GREY_700,
                            )
                        ]
                        if capital_remaining > Decimal("0")
                        else []
                    ),
                ],
                spacing=8,
            ),
        )


    def _build_add_installment_button(self) -> ft.Control:
        return ft.Row(
            controls=[
                ft.Button(
                    "Agregar tramo",
                    icon=ft.Icons.ADD,
                    on_click=self._open_installment_form_step,
                ),
            ],
        )

    def _build_financed_plan_installment_form_step(self) -> ft.Control:
        self._sync_installment_form_controls()
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Cargar tramo de cuotas", size=24, weight=ft.FontWeight.W_700),
                    _info_row(
                        "Capital disponible para asignar",
                        self._format_money_with_currency(self._capital_remaining_for_installments()),
                    ),
                    self._build_installment_form_section(),
                ],
                spacing=14,
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
                    ft.Row(
                        controls=[
                            self._build_installment_basic_fields_section(),
                            self._build_installment_liquidation_section(),
                        ],
                        spacing=12,
                        run_spacing=12,
                        wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Row(
                        controls=[
                            ft.Button(
                                "Guardar tramo",
                                icon=ft.Icons.SAVE,
                                on_click=self._add_installment_block,
                            ),
                            ft.OutlinedButton(
                                "Cancelar",
                                icon=ft.Icons.CLOSE,
                                on_click=self._cancel_installment_form_step,
                            ),
                        ],
                        wrap=True,
                        spacing=8,
                    ),
                ],
                spacing=10,
            ),
        )

    def _build_installment_basic_fields_section(self) -> ft.Control:
        return ft.Container(
            width=360,
            padding=12,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Datos del tramo", size=18, weight=ft.FontWeight.W_700),
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
                    self._build_installment_estimate_card(),
                ],
                spacing=8,
                tight=True,
            ),
        )


    def _build_installment_estimate_card(self) -> ft.Control:
        self._sync_installment_estimate_feedback()
        return ft.Container(
            padding=12,
            border_radius=10,
            bgcolor=ft.Colors.BLUE_50,
            border=_border_all(1, ft.Colors.BLUE_200),
            content=ft.Column(
                controls=[
                    ft.Text("Estimación visual de cuota", weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_900),
                    self.tramo_cuota_estimada_feedback,
                    ft.Text(
                        "Estimación visual. El cálculo definitivo se validará al confirmar la venta.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                ],
                spacing=6,
                tight=True,
            ),
        )

    def _build_installment_liquidation_section(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Método de financiación", size=18, weight=ft.FontWeight.W_700),
            ft.Text(
                "Elegí cómo se liquidará este tramo. El cálculo definitivo se validará al confirmar la venta.",
                size=12,
                color=ft.Colors.BLUE_GREY_700,
            ),
            ft.Row(
                controls=[
                    self._build_liquidation_method_card(
                        method="SIN_INTERES",
                        title="Cuotas fijas / sin interés",
                        description="Todas las cuotas del tramo mantienen el mismo capital base.",
                        icon=ft.Icons.LOCK_OUTLINE,
                    ),
                    self._build_liquidation_method_card(
                        method="INTERES_DIRECTO",
                        title="Interés directo",
                        description="Captura la tasa para calcular las cuotas más adelante.",
                        icon=ft.Icons.PERCENT,
                    ),
                    self._build_liquidation_method_card(
                        method="INDEXACION",
                        title="Indexado por índice",
                        description="Actualiza las cuotas usando un índice financiero publicado.",
                        icon=ft.Icons.TRENDING_UP,
                    ),
                ],
                spacing=10,
                wrap=True,
            ),
        ]
        if self.state.tramo_metodo_liquidacion == "INTERES_DIRECTO":
            controls.extend(
                [
                    self._build_help_card(
                        "Cargá la tasa como porcentaje visible. El cálculo final se validará al confirmar la venta.",
                        ft.Colors.BLUE_50,
                        ft.Colors.BLUE_100,
                    ),
                    self.tramo_tasa_interes_field,
                    self.tramo_tasa_interes_feedback,
                    ft.Text(
                        "Ej: ingresá 6 para 6%. La tasa se aplicará por cada período/cuota del tramo.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                ]
            )
        if self.state.tramo_metodo_liquidacion == "INDEXACION":
            controls.extend(
                [
                    self._build_help_card(
                        "Defaults futuros: POR_COEFICIENTE, CAPITAL_INICIAL_BLOQUE, DEFINITIVA, ERROR_SI_NO_EXISTE, conserva capital original y genera ajuste por diferencia.",
                        ft.Colors.BLUE_50,
                        ft.Colors.BLUE_100,
                    ),
                    self.tramo_codigo_indice_visual_field,
                    self.tramo_codigo_indice_visual_feedback,
                    self.tramo_id_indice_financiero_field,
                    self.tramo_id_indice_financiero_feedback,
                    ft.Row(
                        controls=[
                            self.tramo_fecha_base_indice_field,
                            ft.IconButton(
                                icon=ft.Icons.CALENDAR_MONTH,
                                tooltip="Abrir calendario",
                                on_click=self._open_tramo_fecha_base_indice_picker,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    self.tramo_fecha_base_indice_feedback,
                    self.tramo_valor_base_indice_field,
                    self.tramo_valor_base_indice_feedback,
                ]
            )
        controls.append(self._build_installment_reinforcement_method_controls())
        return ft.Container(
            width=760,
            padding=12,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=8, tight=True),
        )

    def _build_installment_reinforcement_method_controls(self) -> ft.Control:
        if self.state.tramo_metodo_liquidacion == "INTERES_DIRECTO":
            return ft.Text(
                "Las cuotas refuerzo no están disponibles para interés directo.",
                size=12,
                color=ft.Colors.BLUE_GREY_600,
            )
        if not self.state.tramo_usa_refuerzos:
            return ft.Row(
                controls=[
                    ft.OutlinedButton(
                        "Agregar cuotas refuerzo",
                        icon=ft.Icons.ADD,
                        on_click=lambda _: self._select_installment_reinforcements_usage(True),
                    )
                ],
                wrap=True,
            )
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Cuotas refuerzo", size=16, weight=ft.FontWeight.W_700),
                        ft.OutlinedButton(
                            "Quitar refuerzos",
                            icon=ft.Icons.CLOSE,
                            on_click=lambda _: self._select_installment_reinforcements_usage(False),
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    "Las cuotas refuerzo forman parte de la cantidad total de cuotas. No agregan cuotas por fuera del tramo.",
                    size=12,
                    color=ft.Colors.BLUE_GREY_700,
                ),
                self._build_installment_reinforcement_two_column_layout(),
            ],
            spacing=8,
            tight=True,
        )

    def _build_liquidation_method_card(
        self,
        *,
        method: MetodoLiquidacionTramoWizard,
        title: str,
        description: str,
        icon: str,
    ) -> ft.Control:
        selected = self.state.tramo_metodo_liquidacion == method
        return ft.Container(
            width=220,
            padding=12,
            border_radius=12,
            border=_border_all(2 if selected else 1, ft.Colors.BLUE_500 if selected else ft.Colors.BLUE_GREY_100),
            bgcolor=ft.Colors.BLUE_50 if selected else ft.Colors.WHITE,
            on_click=lambda _, selected_method=method: self._select_installment_liquidation_method(selected_method),
            content=ft.Column(
                controls=[
                    ft.Icon(icon, size=24, color=ft.Colors.BLUE_700 if selected else ft.Colors.BLUE_GREY_500),
                    ft.Text(title, weight=ft.FontWeight.W_700),
                    ft.Text(description, size=12, color=ft.Colors.BLUE_GREY_700),
                ],
                spacing=6,
            ),
        )

    def _build_installment_reinforcement_two_column_layout(self) -> ft.Control:
        reinforcement_count = self._current_reinforcement_count_or_none()
        columns: list[ft.Control] = [self._build_installment_reinforcement_left_column(reinforcement_count)]
        if reinforcement_count is not None:
            columns.append(self._build_installment_reinforcement_right_column(reinforcement_count))
        return ft.Row(
            controls=columns,
            spacing=12,
            run_spacing=12,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _build_installment_reinforcement_left_column(self, reinforcement_count: int | None) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Column(
                controls=[self.refuerzo_cantidad_field, self.refuerzo_cantidad_feedback],
                spacing=4,
                tight=True,
            ),
        ]
        if reinforcement_count is None:
            controls.append(
                ft.Text(
                    "Ingresá una cantidad válida de refuerzos para habilitar la selección de cuotas posibles.",
                    size=12,
                    color=ft.Colors.BLUE_GREY_700,
                )
            )
        else:
            controls.append(self._build_installment_reinforcements_summary(reinforcement_count))
        return ft.Column(controls=controls, width=360, spacing=8, tight=True)

    def _build_installment_reinforcement_right_column(self, reinforcement_count: int) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text(
                    "Asigná cada refuerzo a una posición válida de la duración efectiva.",
                    size=12,
                    color=ft.Colors.BLUE_GREY_700,
                ),
                self._build_installment_reinforcement_position_picker(reinforcement_count),
                self.refuerzo_numero_feedback,
                self._build_installment_reinforcement_selection_status(reinforcement_count),
            ],
            width=520,
            spacing=8,
            tight=True,
        )

    def _build_installment_reinforcement_position_picker(self, reinforcement_count: int) -> ft.Control:
        effective_duration = self._effective_duration_for_reinforcements(reinforcement_count)
        return ft.Row(
            controls=[self._build_reinforcement_position_button(number, reinforcement_count) for number in range(1, effective_duration + 1)],
            spacing=8,
            run_spacing=8,
            wrap=True,
        )

    def _build_reinforcement_position_button(self, number: int, reinforcement_count: int) -> ft.Control:
        selected = any(item.numero_cuota == number for item in self.state.tramo_cuotas_refuerzo_draft)
        selection_full = len(self.state.tramo_cuotas_refuerzo_draft) >= reinforcement_count
        blocked = selection_full and not selected
        return ft.Container(
            padding=10,
            border_radius=10,
            border=_border_all(2 if selected else 1, ft.Colors.BLUE_500 if selected else ft.Colors.BLUE_GREY_100),
            bgcolor=ft.Colors.BLUE_50 if selected else ft.Colors.BLUE_GREY_100 if blocked else ft.Colors.WHITE,
            on_click=lambda _, selected_number=number: self._toggle_installment_reinforcement_position(selected_number),
            content=ft.Text(
                f"cuota {number}",
                weight=ft.FontWeight.W_700 if selected else ft.FontWeight.W_400,
                color=ft.Colors.BLUE_900 if selected else ft.Colors.BLUE_GREY_600 if blocked else ft.Colors.BLUE_GREY_900,
            ),
        )

    def _build_installment_reinforcement_selection_status(self, reinforcement_count: int) -> ft.Control:
        missing_count = max(reinforcement_count - len(self.state.tramo_cuotas_refuerzo_draft), 0)
        return ft.Column(
            controls=[
                ft.Text(
                    f"Seleccionadas: {self._selected_reinforcement_numbers_text()}",
                    size=12,
                    color=ft.Colors.BLUE_GREY_700,
                ),
                ft.Text(
                    f"Faltan seleccionar: {missing_count}",
                    size=12,
                    color=ft.Colors.BLUE_GREY_700,
                ),
            ],
            spacing=4,
            tight=True,
        )

    def _build_installment_reinforcements_list(self) -> ft.Control:
        if not self.state.tramo_cuotas_refuerzo_draft:
            return ft.Text("Todavía no agregaste cuotas refuerzo.", size=12, color=ft.Colors.BLUE_GREY_700)
        return ft.Column(
            controls=[
                self._build_installment_reinforcement_row(index, reinforcement)
                for index, reinforcement in enumerate(self.state.tramo_cuotas_refuerzo_draft)
            ],
            spacing=6,
        )

    def _build_installment_reinforcement_row(self, index: int, reinforcement: CuotaRefuerzoWizardDraft) -> ft.Control:
        label_parts = [f"Refuerzo en cuota {reinforcement.numero_cuota}"]
        if reinforcement.etiqueta:
            label_parts.append(reinforcement.etiqueta)
        return ft.Container(
            padding=10,
            border_radius=10,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Row(
                controls=[
                    ft.Text(" — ".join(label_parts), expand=True),
                    ft.OutlinedButton(
                        "Quitar",
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=lambda _, item_index=index: self._remove_installment_reinforcement(item_index),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _build_installment_reinforcements_summary(self, reinforcement_count: int) -> ft.Control:
        quantity = self._current_installment_quantity_or_zero()
        effective_duration = max(quantity - reinforcement_count, 0)
        return ft.Container(
            padding=10,
            border_radius=10,
            bgcolor=ft.Colors.GREEN_50,
            border=_border_all(1, ft.Colors.GREEN_200),
            content=ft.Column(
                controls=[
                    _info_row("Cantidad total de cuotas", quantity),
                    _info_row("Cuotas refuerzo", reinforcement_count),
                    _info_row("Duración efectiva estimada", f"{effective_duration} vencimientos"),
                    _info_row("Posiciones válidas", f"1 a {effective_duration}"),
                    ft.Text(
                        f"El total de cuotas del tramo sigue siendo {quantity}.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                ],
                spacing=6,
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
                                f"Capital del tramo: {self._format_money_with_currency(_parse_money_decimal(tramo.importe_total_bloque) or Decimal('0'))}",
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
                            ft.Text(
                                f"Método: {self._installment_liquidation_label(tramo.metodo_liquidacion)}",
                                size=12,
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            *(
                                [
                                    ft.Text(
                                        self._installment_liquidation_secondary_text(tramo),
                                        size=12,
                                        color=ft.Colors.BLUE_GREY_700,
                                    )
                                ]
                                if self._installment_liquidation_secondary_text(tramo)
                                else []
                            ),
                            *(
                                [
                                    ft.Text(
                                        self._installment_reinforcements_list_text(tramo),
                                        size=12,
                                        color=ft.Colors.BLUE_GREY_700,
                                    ),
                                    ft.Text(
                                        self._installment_reinforcements_duration_text(tramo),
                                        size=12,
                                        color=ft.Colors.BLUE_GREY_700,
                                    ),
                                ]
                                if tramo.cuotas_refuerzo
                                else []
                            ),
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
                    *(
                        [
                            ft.Text(
                                "Todavía queda capital por financiar. Agregá otro tramo o ajustá los tramos existentes hasta cubrir todo el capital pendiente.",
                                size=12,
                                color=ft.Colors.BLUE_GREY_700,
                            )
                        ]
                        if capital_remaining > Decimal("0")
                        else []
                    ),
                ],
                spacing=8,
            ),
        )

    def _build_financed_plan_summary_step(self) -> ft.Control:
        difference = self._financed_plan_difference()
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Resumen del plan financiado", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Revisá la estructura financiera cargada antes de pasar a la revisión general de la venta.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    self._build_financed_plan_general_summary_card(),
                    self._build_financed_plan_advance_summary_card(),
                    self._build_financed_plan_installments_summary_cards(),
                    self._build_financed_plan_validation_panel(difference),
                    self._build_plan_preview_status_section(),
                    ft.Text(
                        "Al presionar Siguiente se calculará una vista previa obligatoria. El cálculo definitivo se validará al confirmar la venta.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_600,
                    ),
                ],
                spacing=14,
            ),
        )

    def _build_financed_plan_general_summary_card(self) -> ft.Control:
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.BLUE_50,
            border=_border_all(1, ft.Colors.BLUE_200),
            content=ft.Column(
                controls=[
                    ft.Text("Resumen general", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_900),
                    _info_row("Total de venta derivado de objetos", self._format_money_with_currency(self._objects_total())),
                    _info_row("Anticipo", self._format_money_with_currency(self._valid_advance_amount_or_zero())),
                    _info_row("Capital financiado en tramos", self._format_money_with_currency(self._capital_assigned_to_installments())),
                    _info_row("Total asignado", self._format_money_with_currency(self._financed_plan_total_assigned())),
                    _info_row("Diferencia", self._format_money_with_currency(self._financed_plan_difference())),
                ],
                spacing=8,
            ),
        )

    def _build_financed_plan_advance_summary_card(self) -> ft.Control:
        controls: list[ft.Control] = [ft.Text("Anticipo", size=18, weight=ft.FontWeight.W_700)]
        if self.state.tiene_anticipo:
            controls.extend(
                [
                    _info_row("Importe", self._format_money_with_currency(self._valid_advance_amount_or_zero())),
                    _info_row("Vencimiento", self.state.fecha_anticipo_display or _format_date_ar(self.state.fecha_anticipo_iso)),
                ]
            )
        else:
            controls.append(ft.Text("Sin anticipo", color=ft.Colors.BLUE_GREY_700))
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=8),
        )

    def _build_financed_plan_installments_summary_cards(self) -> ft.Control:
        if not self.state.tramos_cuotas:
            content: ft.Control = ft.Text("Sin tramos cargados.", color=ft.Colors.BLUE_GREY_700)
        else:
            content = ft.Column(
                controls=[
                    self._build_financed_plan_installment_summary_card(index, tramo)
                    for index, tramo in enumerate(self.state.tramos_cuotas)
                ],
                spacing=10,
            )
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[ft.Text("Tramos", size=18, weight=ft.FontWeight.W_700), content],
                spacing=10,
            ),
        )

    def _build_financed_plan_installment_summary_card(self, index: int, tramo: TramoCuotasWizardDraft) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text(f"Tramo {index + 1}", weight=ft.FontWeight.W_700),
            _info_row("Capital del tramo", self._format_money_with_currency(_parse_money_decimal(tramo.importe_total_bloque) or Decimal("0"))),
            _info_row("Cantidad total de cuotas", tramo.cantidad_cuotas),
            _info_row("Primer vencimiento", tramo.fecha_primer_vencimiento_display),
            _info_row("Periodicidad", tramo.periodicidad),
            _info_row("Método", self._installment_liquidation_label(tramo.metodo_liquidacion)),
        ]
        if tramo.metodo_liquidacion == "INTERES_DIRECTO":
            controls.extend(
                [
                    _info_row("Tasa periódica (%)", self._format_rate_decimal_as_percentage(tramo.tasa_interes_directo_periodica)),
                    _info_row("Períodos derivados", tramo.cantidad_periodos or tramo.cantidad_cuotas),
                ]
            )
        if tramo.metodo_liquidacion == "INDEXACION":
            controls.extend(
                [
                    _info_row("Índice visual o ID índice", tramo.codigo_indice_visual or f"ID {tramo.id_indice_financiero or '-'}"),
                    _info_row("Fecha base", tramo.fecha_base_indice_display or "-"),
                    _info_row("Valor base", tramo.valor_base_indice or "-"),
                ]
            )
        if tramo.cuotas_refuerzo:
            controls.extend(
                [
                    _info_row("Refuerzos", self._installment_reinforcements_list_text(tramo)),
                    _info_row("Duración efectiva", self._installment_reinforcements_duration_value(tramo)),
                ]
            )
        else:
            controls.append(ft.Text("Sin cuotas refuerzo.", color=ft.Colors.BLUE_GREY_700))
        return ft.Container(
            padding=12,
            border_radius=10,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=6),
        )

    def _build_financed_plan_validation_panel(self, difference: Decimal) -> ft.Control:
        complete = difference == Decimal("0")
        if complete:
            bgcolor = ft.Colors.GREEN_50
            border_color = ft.Colors.GREEN_300
            title = "Plan financiero completo."
            detail = "La diferencia es 0; podés pasar a la revisión general de la venta."
            text_color = ft.Colors.GREEN_900
        else:
            bgcolor = ft.Colors.AMBER_50
            border_color = ft.Colors.AMBER_300
            title = "El plan no cubre el total de venta."
            detail = f"Diferencia: {self._format_money_with_currency(difference)}. Ajustá anticipo o tramos para continuar."
            text_color = ft.Colors.AMBER_900
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=bgcolor,
            border=_border_all(1, border_color),
            content=ft.Column(
                controls=[
                    ft.Text(title, size=18, weight=ft.FontWeight.W_700, color=text_color),
                    ft.Text(detail, color=text_color),
                ],
                spacing=6,
            ),
        )

    def _build_general_review_step(self) -> ft.Control:
        errors = self._general_review_errors()
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text("Revisión general de venta", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Revisá los datos principales de la operación antes de confirmar la venta.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    self._build_review_origin_section(),
                    self._build_review_initial_data_section(),
                    self._build_review_objects_section(),
                    self._build_review_buyers_section(),
                    self._build_review_payment_section(),
                    self._build_review_validation_panel(errors),
                    self._build_confirm_status_panel(),
                    ft.Text(
                        "La venta se crea recién al presionar Confirmar venta. La vista previa anterior no confirma la operación.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_600,
                    ),
                ],
                spacing=14,
            ),
        )

    def _build_review_origin_section(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("1. Origen", size=18, weight=ft.FontWeight.W_700),
            _info_row("Origen", self._origin_label()),
        ]
        if self.state.origen == "RESERVA":
            controls.extend(
                [
                    _info_row("Reserva seleccionada", self.state.texto_visual_reserva or "Reserva pendiente"),
                    *self._technical_controls([
                        _info_row("id_reserva_venta", self.state.id_reserva_venta),
                        _info_row("version_registro", self.state.version_registro),
                    ]),
                ]
            )
        return self._build_review_section_container(controls)

    def _build_review_initial_data_section(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("2. Datos iniciales", size=18, weight=ft.FontWeight.W_700),
            _info_row("Código de venta", self.state.codigo_venta or "Sin código informado"),
            _info_row("Fecha de venta", _format_date_ar(self.state.fecha_venta_iso) or "Fecha pendiente"),
            _info_row("Moneda", self._currency_label()),
        ]
        if self.state.observaciones_comerciales.strip():
            controls.append(_info_row("Observaciones comerciales", self.state.observaciones_comerciales.strip()))
        return self._build_review_section_container(controls)

    def _build_review_objects_section(self) -> ft.Control:
        object_controls: list[ft.Control] = []
        for index, objeto in enumerate(self.state.objetos):
            id_label = "id_unidad_funcional" if objeto.tipo_objeto == "UNIDAD_FUNCIONAL" else "id_inmueble"
            technical_id = objeto.id_unidad_funcional if objeto.tipo_objeto == "UNIDAD_FUNCIONAL" else objeto.id_inmueble
            object_controls.append(
                ft.Container(
                    padding=12,
                    border_radius=10,
                    bgcolor=ft.Colors.BLUE_GREY_50,
                    border=_border_all(1, ft.Colors.BLUE_GREY_100),
                    content=ft.Column(
                        controls=[
                            ft.Text(f"Objeto {index + 1}: {objeto.texto_visual}", weight=ft.FontWeight.W_700),
                            _info_row("Tipo", self._object_type_label(objeto.tipo_objeto)),
                            _info_row("Precio asignado", self._format_money_with_currency(_parse_money_decimal(objeto.precio_asignado) or Decimal("0"))),
                            *self._technical_controls([
                                _info_row(id_label, technical_id),
                                _info_row("Origen dato", self._record_source_label(objeto.source, objeto.persisted)),
                            ]),
                        ],
                        spacing=5,
                    ),
                )
            )
        if not object_controls:
            object_controls.append(ft.Text("No hay objetos de venta cargados.", color=ft.Colors.RED_700))
        controls: list[ft.Control] = [
            ft.Text("3. Objetos de venta", size=18, weight=ft.FontWeight.W_700),
            ft.Column(controls=object_controls, spacing=8),
            _info_row("Cantidad de objetos", len(self.state.objetos)),
            _info_row("Total derivado de objetos", self._format_money_with_currency(self._objects_total())),
        ]
        return self._build_review_section_container(controls)

    def _build_review_buyers_section(self) -> ft.Control:
        controls: list[ft.Control] = [ft.Text("4. Compradores", size=18, weight=ft.FontWeight.W_700)]
        if self.state.origen == "RESERVA":
            controls.append(ft.Text("Los compradores heredados de la reserva se muestran read-only y se usan como fuente de negocio del backend.", color=ft.Colors.BLUE_GREY_800))
            if self.state.texto_visual_reserva:
                controls.append(_info_row("Reserva", self.state.texto_visual_reserva))
        buyer_controls: list[ft.Control] = []
        for index, comprador in enumerate(self.state.compradores):
                buyer_controls.append(
                    ft.Container(
                        padding=12,
                        border_radius=10,
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border=_border_all(1, ft.Colors.BLUE_GREY_100),
                        content=ft.Column(
                            controls=[
                                ft.Text(f"Comprador {index + 1}: {comprador.texto_visual}", weight=ft.FontWeight.W_700),
                                _info_row("Responsabilidad", (comprador.porcentaje_responsabilidad + "%") if comprador.porcentaje_responsabilidad else "100%"),
                                *self._technical_controls([
                                    _info_row("id_persona", comprador.id_persona),
                                    _info_row("id_rol_participacion", comprador.id_rol_participacion),
                                    _info_row("Origen dato", self._record_source_label(comprador.source, comprador.persisted)),
                                ]),
                            ],
                            spacing=5,
                        ),
                    )
                )
        if buyer_controls:
            controls.append(ft.Column(controls=buyer_controls, spacing=8))
        elif self.state.origen == "RESERVA":
            controls.append(ft.Text("La reserva seleccionada no devolvió compradores heredados.", color=ft.Colors.RED_700))
        else:
            controls.append(ft.Text("No hay compradores manuales cargados.", color=ft.Colors.RED_700))
        if self.state.origen == "DIRECTA":
            controls.append(_info_row("Suma de responsabilidad", self._buyers_responsibility_total_label(self._buyers_responsibility_total())))
        return self._build_review_section_container(controls)

    def _build_review_payment_section(self) -> ft.Control:
        controls: list[ft.Control] = [ft.Text("5. Forma de pago", size=18, weight=ft.FontWeight.W_700)]
        if self.state.forma_pago == "CONTADO":
            controls.extend(
                [
                    _info_row("Forma de pago", "Contado"),
                    _info_row("Total a pagar", self._format_money_with_currency(self._objects_total())),
                    _info_row("Fecha de pago / vencimiento", self.state.fecha_pago_contado_display or _format_date_ar(self.state.fecha_pago_contado_iso)),
                    self._build_help_card(
                        "El plan de pago fue calculado previamente. La venta todavía no fue confirmada.",
                        ft.Colors.BLUE_50,
                        ft.Colors.BLUE_200,
                    ),
                ]
            )
        elif self.state.forma_pago == "FINANCIADO":
            difference = self._financed_plan_difference()
            controls.extend(
                [
                    _info_row("Forma de pago", "Financiado"),
                    _info_row("Anticipo", self._format_money_with_currency(self._valid_advance_amount_or_zero())),
                    _info_row("Tramos", len(self.state.tramos_cuotas)),
                    _info_row("Total asignado", self._format_money_with_currency(self._financed_plan_total_assigned())),
                    _info_row("Diferencia", self._format_money_with_currency(difference)),
                    self._build_financed_plan_general_summary_card(),
                    self._build_financed_plan_advance_summary_card(),
                    self._build_financed_plan_installments_summary_cards(),
                    self._build_financed_plan_validation_panel(difference),
                    self._build_help_card(
                        "El plan de pago fue calculado previamente. La venta todavía no fue confirmada.",
                        ft.Colors.BLUE_50,
                        ft.Colors.BLUE_200,
                    ),
                ]
            )
        else:
            controls.append(ft.Text("Forma de pago pendiente.", color=ft.Colors.RED_700))
        return self._build_review_section_container(controls)


    def _build_plan_preview_status_section(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Vista previa del plan de pago", size=18, weight=ft.FontWeight.W_700),
            ft.Text(
                "Al presionar Siguiente se calcula una vista previa. No confirma la venta ni genera obligaciones reales.",
                size=12,
                color=ft.Colors.BLUE_GREY_700,
            ),
        ]
        if self.state.preview_loading:
            controls.append(
                ft.Row(
                    controls=[ft.ProgressRing(width=18, height=18), ft.Text("Cargando preview de plan de pago...")],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        if self.state.preview_error is not None:
            controls.append(self._build_help_card(self.state.preview_error, ft.Colors.RED_50, ft.Colors.RED_200))
        elif self.state.preview_data is not None and self.state.preview_stale:
            controls.append(self._build_help_card("El preview anterior quedó desactualizado. Presioná Siguiente desde esta pantalla para recalcularlo antes de revisar la venta.", ft.Colors.AMBER_50, ft.Colors.AMBER_200))
        else:
            controls.append(
                ft.Text(
                    "El preview es obligatorio para avanzar a la revisión general.",
                    color=ft.Colors.BLUE_GREY_700,
                )
            )
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=10),
        )

    def _build_plan_payment_preview_step(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Preview del plan de pago", size=24, weight=ft.FontWeight.W_700),
        ]
        if self.state.preview_loading:
            controls.append(
                ft.Row(
                    controls=[ft.ProgressRing(width=18, height=18), ft.Text("Cargando preview de plan de pago...")],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        if self.state.preview_error is not None:
            controls.append(self._build_help_card(self.state.preview_error, ft.Colors.RED_50, ft.Colors.RED_200))
        if self.state.preview_stale:
            controls.append(
                self._build_help_card(
                    "Este preview está desactualizado porque cambió el plan o sus datos base. Volvé con Anterior y presioná Siguiente desde la edición del plan para recalcularlo.",
                    ft.Colors.AMBER_50,
                    ft.Colors.AMBER_200,
                )
            )
        if self.state.preview_data is not None:
            controls.extend(self._build_plan_preview_result_controls(self.state.preview_data))
        else:
            controls.append(
                ft.Text(
                    "Todavía no hay vista previa calculada. Volvé a la edición del plan y avanzá con Siguiente para calcularla.",
                    color=ft.Colors.BLUE_GREY_700,
                )
            )
        return ft.Container(
            padding=18,
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=14),
        )

    def _build_plan_preview_result_controls(self, data: dict[str, Any]) -> list[ft.Control]:
        obligaciones = data.get("obligaciones") if isinstance(data.get("obligaciones"), list) else []
        summary = self._build_plan_preview_compact_summary(data, len(obligaciones))
        obligations_control = self._build_plan_preview_obligations_table(obligaciones)
        return [
            summary,
            ft.Column(
                controls=[
                    ft.Text("Obligaciones simuladas", weight=ft.FontWeight.W_700),
                    obligations_control,
                ],
                spacing=8,
            ),
        ]


    def _build_plan_preview_compact_summary(self, data: dict[str, Any], obligations_count: int) -> ft.Control:
        columns = [
            ("Total calculado", self._format_preview_financial_total(data.get("total_calculado"))),
            ("Total con interés", self._format_preview_financial_total(data.get("total_con_interes"))),
            ("Total con indexación", self._format_preview_financial_total(data.get("total_con_indexacion"))),
            ("Obligaciones simuladas", str(obligations_count)),
        ]
        adjustment = data.get("total_ajuste_indexacion")
        if adjustment not in (None, ""):
            columns.insert(3, ("Ajuste por indexación", self._format_preview_financial_total(adjustment)))
        return ft.Container(
            padding=12,
            border_radius=10,
            bgcolor=ft.Colors.GREEN_50,
            border=_border_all(1, ft.Colors.GREEN_200),
            content=ft.Column(
                controls=[
                    ft.Text("Resultado de la vista previa", weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_900),
                    ft.DataTable(
                        heading_row_height=34,
                        data_row_min_height=38,
                        data_row_max_height=44,
                        column_spacing=18,
                        columns=[ft.DataColumn(ft.Text(label, weight=ft.FontWeight.W_700)) for label, _ in columns],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(value, selectable=True, color=ft.Colors.GREEN_900))
                                    for _, value in columns
                                ]
                            )
                        ],
                    ),
                    *self._technical_controls([
                        ft.Text("Datos técnicos del payload", size=12, color=ft.Colors.BLUE_GREY_700),
                        _info_row("Status HTTP", self.state.preview_status_code or "-"),
                        _info_row("total_calculado", data.get("total_calculado") or "-"),
                        _info_row("total_con_interes", data.get("total_con_interes") or "-"),
                        _info_row("total_ajuste_indexacion", data.get("total_ajuste_indexacion") or "0.00"),
                        _info_row("total_con_indexacion", data.get("total_con_indexacion") or "-"),
                    ]),
                ],
                spacing=8,
                tight=True,
            ),
        )

    def _format_preview_financial_total(self, value: Any) -> str:
        if value in (None, ""):
            return "-"
        parsed = _parse_money_decimal(str(value))
        if parsed is None:
            return str(value or "-")
        return self._format_money_with_currency(parsed)

    def _build_plan_preview_obligations_table(self, obligaciones: list[Any]) -> ft.Control:
        valid_obligations = [obligacion for obligacion in obligaciones if isinstance(obligacion, dict)]
        if not valid_obligations:
            return ft.Text("El preview no devolvió obligaciones simuladas.", color=ft.Colors.BLUE_GREY_700)

        page_size = self.state.preview_obligaciones_page_size
        total = len(valid_obligations)
        total_pages = max(1, (total + page_size - 1) // page_size)
        self.state.preview_obligaciones_page = min(max(1, self.state.preview_obligaciones_page), total_pages)
        current_page = self.state.preview_obligaciones_page
        start_index = (current_page - 1) * page_size
        end_index = min(start_index + page_size, total)
        rows: list[ft.DataRow] = []
        for absolute_index, obligacion in enumerate(valid_obligations[start_index:end_index], start=start_index):
            item_type = str(obligacion.get("tipo_item_cronograma") or "-")
            obligation_label = str(obligacion.get("etiqueta_obligacion") or "").strip()
            has_accumulated_reinforcement = self._preview_obligation_has_accumulated_reinforcement(obligation_label)
            is_reinforcement = item_type == "REFUERZO" or has_accumulated_reinforcement
            type_cell = self._build_preview_obligation_type_cell(
                item_type=item_type,
                obligation_label=obligation_label,
                has_accumulated_reinforcement=has_accumulated_reinforcement,
            )
            rows.append(
                ft.DataRow(
                    color=ft.Colors.AMBER_50 if is_reinforcement else None,
                    cells=[
                        ft.DataCell(self._preview_obligation_table_cell(str(absolute_index + 1), width=56)),
                        ft.DataCell(
                            self._preview_obligation_table_cell(
                                _format_date_ar(str(obligacion.get("fecha_vencimiento") or "")) or "-",
                                width=170,
                            )
                        ),
                        ft.DataCell(self._preview_obligation_table_cell(type_cell, width=260)),
                        ft.DataCell(
                            self._preview_obligation_table_cell(
                                str(obligacion.get("numero_cuota_asociada") or "-"),
                                width=110,
                            )
                        ),
                        ft.DataCell(
                            self._preview_obligation_table_cell(
                                self._format_preview_obligation_amount(obligacion.get("importe_total")),
                                width=220,
                                alignment=ft.Alignment(1, 0),
                            )
                        ),
                    ],
                )
            )

        return ft.Container(
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
            padding=8,
            content=ft.Column(
                controls=[
                    ft.Text(f"Obligaciones {start_index + 1} a {end_index} de {total}", size=12, color=ft.Colors.BLUE_GREY_700),
                    ft.Row(
                        controls=[
                            ft.Container(
                                expand=True,
                                content=ft.DataTable(
                                    column_spacing=18,
                                    horizontal_margin=12,
                                    columns=[
                                        ft.DataColumn(self._preview_obligation_table_header("#", width=56)),
                                        ft.DataColumn(self._preview_obligation_table_header("Fecha vencimiento", width=170)),
                                        ft.DataColumn(self._preview_obligation_table_header("Tipo", width=260)),
                                        ft.DataColumn(self._preview_obligation_table_header("Cuota", width=110)),
                                        ft.DataColumn(
                                            self._preview_obligation_table_header(
                                                "Importe",
                                                width=220,
                                                alignment=ft.Alignment(1, 0),
                                            )
                                        ),
                                    ],
                                    rows=rows,
                                ),
                            )
                        ],
                        expand=True,
                    ),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton("Anterior", on_click=self._on_preview_obligations_previous_page, disabled=current_page <= 1),
                            ft.Text(f"Página {current_page} de {total_pages}", color=ft.Colors.BLUE_GREY_800),
                            ft.OutlinedButton("Siguiente", on_click=self._on_preview_obligations_next_page, disabled=current_page >= total_pages),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
        )


    @staticmethod
    def _preview_obligation_table_header(
        label: str,
        *,
        width: int,
        alignment: ft.Alignment = ft.Alignment(-1, 0),
    ) -> ft.Control:
        return ft.Container(
            width=width,
            alignment=alignment,
            content=ft.Text(label, weight=ft.FontWeight.W_700),
        )

    @staticmethod
    def _preview_obligation_table_cell(
        content: str | ft.Control,
        *,
        width: int,
        alignment: ft.Alignment = ft.Alignment(-1, 0),
    ) -> ft.Control:
        if isinstance(content, str):
            inner: ft.Control = ft.Text(content, selectable=True)
        else:
            inner = content
        return ft.Container(width=width, alignment=alignment, content=inner)

    def _on_preview_obligations_previous_page(self, _: ft.ControlEvent | None = None) -> None:
        self.state.preview_obligaciones_page = max(1, self.state.preview_obligaciones_page - 1)
        self._render()

    def _on_preview_obligations_next_page(self, _: ft.ControlEvent | None = None) -> None:
        self.state.preview_obligaciones_page += 1
        self._render()

    def _build_preview_obligation_type_cell(
        self,
        *,
        item_type: str,
        obligation_label: str,
        has_accumulated_reinforcement: bool,
    ) -> ft.Control:
        type_label = self._preview_obligation_type_label(item_type)
        if has_accumulated_reinforcement and item_type == "CUOTA":
            type_label = "Cuota reforzada"
        is_reinforcement = item_type == "REFUERZO" or has_accumulated_reinforcement
        controls: list[ft.Control] = [
            ft.Text(
                type_label,
                weight=ft.FontWeight.W_700 if is_reinforcement else None,
                color=ft.Colors.AMBER_900 if is_reinforcement else ft.Colors.BLUE_GREY_900,
            )
        ]
        if obligation_label and has_accumulated_reinforcement:
            controls.append(ft.Text(obligation_label, size=11, color=ft.Colors.AMBER_900))
        elif obligation_label and item_type == "REFUERZO":
            controls.append(ft.Text(obligation_label, size=11, color=ft.Colors.AMBER_900))
        return ft.Column(controls=controls, spacing=2)

    @staticmethod
    def _preview_obligation_has_accumulated_reinforcement(obligation_label: str) -> bool:
        return "refuerzo" in obligation_label.lower()

    def _format_preview_obligation_amount(self, value: Any) -> str:
        parsed = _parse_money_decimal(str(value or ""))
        if parsed is None:
            return str(value or "-")
        return self._format_money_with_currency(parsed)

    @staticmethod
    def _preview_obligation_type_label(item_type: str) -> str:
        labels = {
            "ANTICIPO": "Anticipo",
            "CUOTA": "Cuota",
            "REFUERZO": "Refuerzo",
            "SALDO": "Saldo",
        }
        return labels.get(item_type, item_type or "-")

    def _request_plan_payment_preview_before_next(self, target_screen: PantallaWizard) -> None:
        if self.state.preview_loading:
            return
        validation_error = self._preview_local_validation_error()
        if validation_error is not None:
            self.state.preview_error = validation_error
            self.state.preview_status_code = None
            self.state.preview_loading = False
            self._render()
            return
        payload = self._build_plan_payment_preview_payload()
        self.state.preview_loading = True
        self.state.preview_error = None
        self._render()
        self.page.run_thread(
            lambda: self._run_plan_payment_preview_request(payload, target_screen)
        )

    def _run_plan_payment_preview_request(
        self, payload: dict[str, Any], target_screen: PantallaWizard
    ) -> None:
        result = self.api.preview_plan_pago_venta_v2_sin_venta(payload)
        self.state.preview_loading = False
        self.state.preview_status_code = result.status_code
        if result.success and isinstance(result.data, dict):
            self.state.preview_data = result.data
            self.state.preview_error = None
            self.state.preview_stale = False
            self.state.pantalla_actual = target_screen
            self._render()
            return
        self.state.preview_error = self._preview_error_message(result)
        self._render()

    def _preview_error_message(self, result: ApiResult) -> str:
        parts = ["No se pudo obtener el preview del plan."]
        if result.status_code is not None:
            parts.append(f"HTTP {result.status_code}.")
        if result.error_code:
            parts.append(f"{result.error_code}.")
        if result.error_message:
            parts.append(result.error_message)
        return " ".join(parts)

    def _preview_local_validation_error(self) -> str | None:
        if not self.state.objetos or self._objects_total() <= Decimal("0"):
            return "Cargá objetos de venta con total mayor que 0 antes de calcular el preview del plan."
        if self.state.forma_pago not in {"CONTADO", "FINANCIADO"}:
            return "Elegí una forma de pago antes de calcular el preview del plan."
        if self.state.forma_pago == "CONTADO":
            if not self.state.fecha_pago_contado_iso or self.state.fecha_pago_contado_error is not None:
                return "Para contado, cargá una fecha de pago / vencimiento válida."
            return None
        if self.state.tiene_anticipo and not self._advance_is_valid():
            return "Completá un anticipo válido o marcá Sin anticipo antes de calcular el preview."
        if not self.state.tramos_cuotas:
            return "Para financiado, cargá al menos un tramo de cuotas antes de calcular el preview."
        if self._financed_plan_difference() != Decimal("0"):
            return "El plan financiado debe cubrir exactamente el capital pendiente; la diferencia debe ser 0."
        return None

    def _build_plan_payment_preview_payload(self) -> dict[str, Any]:
        total = _format_decimal(self._objects_total())
        if self.state.forma_pago == "CONTADO":
            return {
                "tipo_pago": "CONTADO",
                "monto_total_plan": total,
                "moneda": self._currency_label(),
                "bloques": [
                    {
                        "tipo_bloque": "CONTADO",
                        "importe_total_bloque": total,
                        "fecha_vencimiento": self.state.fecha_pago_contado_iso,
                    }
                ],
                "observaciones": self.state.observaciones_comerciales.strip() or None,
            }
        bloques: list[dict[str, Any]] = []
        advance = self._valid_advance_amount_or_zero()
        if self.state.tiene_anticipo and advance > Decimal("0"):
            bloques.append(
                {
                    "tipo_bloque": "ANTICIPO",
                    "importe_total_bloque": _format_decimal(advance),
                    "fecha_vencimiento": self.state.fecha_anticipo_iso,
                }
            )
        for tramo in self.state.tramos_cuotas:
            block: dict[str, Any] = {
                "tipo_bloque": "TRAMO_CUOTAS",
                "importe_total_bloque": tramo.importe_total_bloque,
                "cantidad_cuotas": tramo.cantidad_cuotas,
                "fecha_primer_vencimiento": tramo.fecha_primer_vencimiento_iso,
                "periodicidad": tramo.periodicidad,
                "metodo_liquidacion": tramo.metodo_liquidacion,
            }
            if tramo.metodo_liquidacion == "INTERES_DIRECTO":
                block.update(
                    {
                        "tasa_interes_directo_periodica": tramo.tasa_interes_directo_periodica,
                        "cantidad_periodos": int(tramo.cantidad_periodos or tramo.cantidad_cuotas),
                        "base_calculo_interes": "CAPITAL_INICIAL_BLOQUE",
                    }
                )
            if tramo.metodo_liquidacion == "INDEXACION":
                block.update(
                    {
                        "id_indice_financiero": int(tramo.id_indice_financiero or "0"),
                        "fecha_base_indice": tramo.fecha_base_indice_iso,
                        "valor_base_indice": tramo.valor_base_indice,
                        "modo_indexacion": "POR_COEFICIENTE",
                        "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
                        "tipo_generacion_indexada": "DEFINITIVA",
                        "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
                        "conserva_capital_original": True,
                        "genera_ajuste_por_diferencia": True,
                    }
                )
            if tramo.cuotas_refuerzo:
                block["cuotas_refuerzo"] = [
                    {
                        "numero_cuota": refuerzo.numero_cuota,
                        "etiqueta": refuerzo.etiqueta,
                        "unidades_refuerzo": refuerzo.unidades_refuerzo,
                    }
                    for refuerzo in tramo.cuotas_refuerzo
                ]
            bloques.append(block)
        return {
            "tipo_pago": "FINANCIADO",
            "monto_total_plan": total,
            "moneda": self._currency_label(),
            "bloques": bloques,
            "observaciones": self.state.observaciones_comerciales.strip() or None,
        }

    def _build_confirm_sale_payload(self) -> dict[str, Any]:
        if self.state.origen == "RESERVA":
            return self._build_confirm_sale_from_reservation_payload()
        return self._build_confirm_sale_direct_payload()

    def _build_confirm_sale_from_reservation_payload(self) -> dict[str, Any]:
        total_decimal = self._objects_total()
        total = _format_decimal(total_decimal)
        condiciones = self._build_confirm_sale_commercial_conditions(total_decimal)
        condiciones["objetos"] = [
            {
                "id_inmueble": objeto.id_inmueble,
                "id_unidad_funcional": objeto.id_unidad_funcional,
                "precio_asignado": objeto.precio_asignado,
            }
            for objeto in self.state.objetos
        ]
        return {
            "generar_venta": {
                "codigo_venta": self.state.codigo_venta.strip(),
                "fecha_venta": f"{self.state.fecha_venta_iso}T00:00:00",
                "monto_total": total,
                "observaciones": self.state.observaciones_comerciales.strip() or None,
            },
            "condiciones_comerciales": condiciones,
            "plan_pago_v2": self._build_plan_payment_preview_payload(),
            "confirmacion": {
                "observaciones": self.state.observaciones_comerciales.strip() or None,
            },
        }

    def _build_confirm_sale_direct_payload(self) -> dict[str, Any]:
        total_decimal = self._objects_total()
        total = _format_decimal(total_decimal)
        plan_pago_v2 = self._build_plan_payment_preview_payload()
        condiciones = self._build_confirm_sale_commercial_conditions(total_decimal)
        return {
            "generar_venta": {
                "codigo_venta": self.state.codigo_venta.strip(),
                "fecha_venta": f"{self.state.fecha_venta_iso}T00:00:00",
                "monto_total": total,
                "observaciones": self.state.observaciones_comerciales.strip() or None,
            },
            "objetos": [
                {
                    "id_inmueble": objeto.id_inmueble,
                    "id_unidad_funcional": objeto.id_unidad_funcional,
                    "precio_asignado": objeto.precio_asignado,
                    "observaciones": objeto.texto_visual,
                }
                for objeto in self.state.objetos
            ],
            "compradores": [
                {
                    "id_persona": comprador.id_persona,
                    "id_rol_participacion": int(comprador.id_rol_participacion),
                    "porcentaje_responsabilidad": comprador.porcentaje_responsabilidad.strip() or "100.00",
                    "fecha_desde": self.state.fecha_venta_iso,
                    "fecha_hasta": None,
                    "observaciones": comprador.texto_visual,
                }
                for comprador in self.state.compradores
            ],
            "condiciones_comerciales": condiciones,
            "plan_pago_v2": plan_pago_v2,
            "confirmacion": {
                "observaciones": self.state.observaciones_comerciales.strip() or None,
            },
        }

    def _confirm_payload_signature(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _ensure_confirm_op_id_for_payload(self, payload: dict[str, Any]) -> str:
        signature = self._confirm_payload_signature(payload)
        if self.state.confirm_op_id is None or self.state.confirm_payload_signature != signature:
            self.state.confirm_op_id = str(uuid4())
            self.state.confirm_payload_signature = signature
        return self.state.confirm_op_id

    def _build_confirm_sale_commercial_conditions(self, total_decimal: Decimal) -> dict[str, Any]:
        total = _format_decimal(total_decimal)
        if self.state.forma_pago == "CONTADO":
            return {
                "monto_total": total,
                "tipo_plan_financiero": "CONTADO",
                "moneda": self._currency_label(),
                "importe_anticipo": None,
                "fecha_vencimiento_anticipo": None,
                "importe_saldo": None,
                "fecha_vencimiento_saldo": None,
                "cuotas": [],
            }

        return {
            "monto_total": total,
            "tipo_plan_financiero": "CUOTAS_FIJAS",
            "moneda": self._currency_label(),
            "importe_anticipo": None,
            "fecha_vencimiento_anticipo": None,
            "importe_saldo": None,
            "fecha_vencimiento_saldo": None,
            "cuotas": self._build_legacy_fixed_installments_for_conditions(),
        }

    def _build_legacy_fixed_installments_for_conditions(self) -> list[dict[str, Any]]:
        cuotas: list[dict[str, Any]] = []
        next_number = 1
        advance = self._valid_advance_amount_or_zero()
        if self.state.tiene_anticipo and advance > Decimal("0"):
            cuotas.append(
                {
                    "numero_cuota": next_number,
                    "importe_cuota": _format_decimal(advance),
                    "fecha_vencimiento": self.state.fecha_anticipo_iso,
                    "moneda": self._currency_label(),
                    "observaciones": "Compatibilidad legacy de condiciones comerciales: anticipo reflejado como cuota fija; Plan Pago V2 define el cronograma real.",
                }
            )
            next_number += 1
        for tramo in self.state.tramos_cuotas:
            block_total = Decimal(str(tramo.importe_total_bloque))
            base_amount = (block_total / Decimal(tramo.cantidad_cuotas)).quantize(MONEY_DECIMAL_QUANTUM)
            accumulated = Decimal("0")
            first_due_date = _date_from_iso(tramo.fecha_primer_vencimiento_iso)
            for index in range(tramo.cantidad_cuotas):
                if index == tramo.cantidad_cuotas - 1:
                    amount = (block_total - accumulated).quantize(MONEY_DECIMAL_QUANTUM)
                else:
                    amount = base_amount
                    accumulated += amount
                due_date = _add_months(first_due_date, index).isoformat() if first_due_date is not None else tramo.fecha_primer_vencimiento_iso
                cuotas.append(
                    {
                        "numero_cuota": next_number,
                        "importe_cuota": _format_decimal(amount),
                        "fecha_vencimiento": due_date,
                        "moneda": self._currency_label(),
                        "observaciones": "Compatibilidad legacy de condiciones comerciales; Plan Pago V2 define el cronograma real.",
                    }
                )
                next_number += 1
        return cuotas

    def _confirm_sale(self, _: ft.ControlEvent | None = None) -> None:
        if self.state.confirm_loading:
            return
        if not self._can_confirm_sale():
            persisted_errors = self._non_persisted_confirmation_errors()
            if persisted_errors:
                self.state.confirm_error = "La confirmación requiere objetos y compradores válidos. Activá datos técnicos para ver el detalle de persistencia."
            else:
                self.state.confirm_error = "No se puede confirmar: resolvé validaciones y recalculá el preview si está desactualizado."
            self._render()
            return

        payload = self._build_confirm_sale_payload()
        confirm_op_id = self._ensure_confirm_op_id_for_payload(payload)
        self.state.confirm_loading = True
        self.state.confirm_data = None
        self.state.confirm_error = None
        self.state.confirm_status_code = None
        self.state.confirm_payload = payload
        self.state.confirm_error_details = None
        if self.state.origen == "RESERVA":
            self.state.confirm_endpoint = f"POST /api/v1/reservas-venta/{self.state.id_reserva_venta}/confirmar-venta-completa"
        else:
            self.state.confirm_endpoint = "POST /api/v1/ventas/directa/confirmar-venta-completa"
        self._render()
        self.page.run_thread(
            lambda: self._run_confirm_sale_request(payload, confirm_op_id)
        )

    def _run_confirm_sale_request(
        self,
        payload: dict[str, Any],
        confirm_op_id: str,
    ) -> None:
        if self.state.origen == "RESERVA":
            result = self.api.confirmar_venta_completa_desde_reserva(
                int(self.state.id_reserva_venta or 0),
                int(self.state.version_registro or 0),
                payload,
                op_id=confirm_op_id,
            )
        else:
            result = self.api.confirmar_venta_directa_completa(payload, op_id=confirm_op_id)
        self.state.confirm_loading = False
        self.state.confirm_status_code = result.status_code
        if result.success and isinstance(result.data, dict):
            self.state.confirm_data = result.data
            self.state.confirm_error = None
            self.state.detalle_venta_data = None
            self.state.detalle_venta_error = None
            self.state.detalle_venta_status_code = None
            self.state.detalle_venta_requested_id = None
            self.state.pantalla_actual = "VENTA_CONFIRMADA"
            if self.on_confirmed is not None:
                self.on_confirmed(self._confirmed_sale_id())
            self._load_confirmed_sale_detail(force=True)
            return
        self.state.confirm_error_details = result.error_details
        self.state.confirm_error = self._confirm_error_message(result)
        self._render()


    def _confirmed_sale_id(self) -> int | None:
        data = self.state.confirm_data or {}
        venta = data.get("venta") if isinstance(data.get("venta"), dict) else {}
        id_venta = venta.get("id_venta")
        try:
            return int(id_venta)
        except (TypeError, ValueError):
            return None

    def _load_confirmed_sale_detail(self, _: Any = None, *, force: bool = True) -> None:
        id_venta = self._confirmed_sale_id()
        if id_venta is None:
            self.state.detalle_venta_data = None
            self.state.detalle_venta_error = "No hay id_venta confirmado para consultar detalle."
            self.state.detalle_venta_requested_id = None
            self._render()
            return
        if not force and self.state.detalle_venta_requested_id == id_venta:
            return

        self.state.detalle_venta_requested_id = id_venta
        self.state.detalle_cuotas_page = 1
        self.state.detalle_venta_loading = True
        self.state.detalle_venta_error = None
        self.state.detalle_venta_status_code = None
        self._render()
        result = self.api.get_venta_detalle_integral(id_venta)
        self.state.detalle_venta_loading = False
        self.state.detalle_venta_status_code = result.status_code
        if result.success and isinstance(result.data, dict):
            self.state.detalle_venta_data = result.data
            self.state.detalle_venta_error = None
            self._render()
            return
        self.state.detalle_venta_data = None
        parts = ["No se pudo cargar el detalle integral de venta."]
        if result.status_code is not None:
            parts.append(f"HTTP {result.status_code}.")
        if result.error_code:
            parts.append(f"error_code={result.error_code}.")
        if result.error_message:
            parts.append(f"error_message={result.error_message}")
        self.state.detalle_venta_error = " ".join(parts)
        self._render()

    def _restart_wizard(self, _: Any = None) -> None:
        self.state = WizardVentaCompletaV3State()
        self.reserva_selector = None
        self.objeto_selector = None
        self.comprador_selector = None
        self._clear_object_selection_state()
        self._clear_buyer_selection_state()
        self.fecha_venta_display_value = ""
        self.fecha_venta_error = None
        self.fecha_venta_field.value = ""
        self.codigo_venta_field.value = ""
        self.observaciones_field.value = ""
        self.fecha_pago_contado_field.value = ""
        self.importe_anticipo_field.value = ""
        self.fecha_anticipo_field.value = ""
        self.backend_reservation_records = []
        self.backend_reservation_error = None
        self.backend_reservations_loaded = False
        self.backend_reservations_loading = False
        self.backend_object_records = []
        self.backend_object_error = None
        self.backend_objects_loaded = False
        self.backend_objects_loading = False
        self.backend_buyer_records = []
        self.backend_buyer_error = None
        self.backend_buyers_loaded = False
        self.backend_buyers_loading = False
        self.rol_comprador_data = None
        self.rol_comprador_catalog_loaded = False
        self.rol_comprador_loading = False
        self.reserva_select_loading = False
        self.object_select_loading = False
        self.buyer_select_loading = False
        self.reserva_select_error = None
        self.object_select_error = None
        self.buyer_select_error = None
        self.rol_comprador_catalog_error = None
        self.rol_comprador_manual_fallback_enabled = False
        self._render()

    def _clear_object_selection_state(self) -> None:
        self.objeto_seleccionado = None
        self.precio_objeto_value = ""
        self.precio_objeto_error = None
        self.precio_objeto_field.value = ""
        if self.objeto_selector is not None:
            self.objeto_selector.selected_panel.visible = False

    def _clear_buyer_selection_state(self) -> None:
        self.comprador_seleccionado = None
        self.porcentaje_comprador_value = ""
        self.porcentaje_comprador_field.value = ""
        self.rol_comprador_value = ""
        self.rol_comprador_field.value = ""
        self.comprador_error = None
        self.manual_buyer_id_value = ""
        self.manual_buyer_text_value = ""
        self.manual_buyer_role_value = ""
        self.manual_buyer_percentage_value = ""
        self.manual_buyer_error = None
        self.manual_buyer_id_field.value = ""
        self.manual_buyer_text_field.value = ""
        self.manual_buyer_role_field.value = ""
        self.manual_buyer_percentage_field.value = ""
        if self.comprador_selector is not None:
            self.comprador_selector.selected_panel.visible = False

    def _build_confirmed_sale_detail_controls(self) -> list[ft.Control]:
        if self.state.detalle_venta_loading:
            return [ft.Text("Cargando detalle integral...", color=ft.Colors.BLUE_GREY_700)]
        if self.state.detalle_venta_error:
            return [
                ft.Container(
                    padding=12,
                    border_radius=10,
                    bgcolor=ft.Colors.RED_50,
                    border=_border_all(1, ft.Colors.RED_200),
                    content=ft.Row(
                        controls=[
                            ft.Text(self.state.detalle_venta_error, color=ft.Colors.RED_800, expand=True),
                            ft.TextButton("Reintentar carga", icon=ft.Icons.REFRESH, on_click=self._load_confirmed_sale_detail),
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                )
            ]
        detalle = self.state.detalle_venta_data
        if not detalle:
            return [ft.Text("Detalle integral pendiente de carga automática.", color=ft.Colors.BLUE_GREY_700)]

        venta = detalle.get("venta") if isinstance(detalle.get("venta"), dict) else detalle
        objetos = self._as_list(detalle.get("objetos_vendidos") or detalle.get("objetos"))
        compradores = self._as_list(detalle.get("compradores"))
        plan = detalle.get("plan_pago_v2") if isinstance(detalle.get("plan_pago_v2"), dict) else {}
        resumen_plan = plan.get("resumen_financiero") if isinstance(plan.get("resumen_financiero"), dict) else {}
        bloques = self._as_list(plan.get("bloques"))
        obligaciones_plan = [ob for bloque in bloques if isinstance(bloque, dict) for ob in self._as_list(bloque.get("obligaciones"))]
        obligaciones = self._as_list(detalle.get("obligaciones_financieras") or detalle.get("obligaciones") or obligaciones_plan)
        moneda = venta.get("moneda") or plan.get("moneda") or detalle.get("moneda")
        impacto = detalle.get("impacto_activo") or detalle.get("impactos_activo") or detalle.get("impactos_activos")
        estado_venta = venta.get("estado_venta") or venta.get("estado")
        estado_plan = plan.get("estado_plan_pago") or plan.get("estado")
        precio_venta = self._first_present(venta.get("monto_total"), venta.get("precio_total"), detalle.get("precio_total"))
        anticipo_obligacion, cuotas_obligaciones = self._split_advance_and_installment_obligations(obligaciones)
        anticipo_importe = self._obligation_amount(anticipo_obligacion) if anticipo_obligacion is not None else None
        total_obligaciones = self._first_present(resumen_plan.get("saldo_total"), plan.get("saldo_total"), self._sum_obligations_amount(obligaciones))
        total_cuotas_obligaciones = self._sum_obligations_amount(cuotas_obligaciones)
        saldo_financiado = self._subtract_money_values(precio_venta, anticipo_importe)
        interes_total = self._subtract_money_values(total_obligaciones, precio_venta)
        confirmed_payment_method = self._confirmed_payment_method_label(venta, plan, detalle, cuotas_obligaciones)

        sale_summary_items = [
            ("Código de venta", venta.get("codigo_venta") or venta.get("codigo") or f"Venta {venta.get('id_venta') or '-'}"),
            ("Estado", self._status_badge(str(estado_venta or "-"))),
            ("Fecha", _format_date_ar(venta.get("fecha_venta")) or venta.get("fecha_venta")),
            ("Moneda", moneda),
            ("Total venta", self._detail_money(precio_venta, moneda)),
            ("Forma de pago", confirmed_payment_method),
        ]
        plan_summary_items: list[tuple[str, Any]] = []

        return [
            ft.Container(
                padding=16,
                border_radius=14,
                bgcolor=ft.Colors.WHITE,
                border=_border_all(1, ft.Colors.BLUE_GREY_100),
                content=ft.Column(
                    controls=[
                        ft.Text("Detalle integral de venta", size=20, weight=ft.FontWeight.W_700),
                        ft.Text(
                            "Ficha operativa read-only cargada automáticamente.",
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                        ft.Text(
                            f"Referencia interna: venta {venta.get('id_venta') or '-'} · plan {plan.get('id_plan_pago_venta') or '-'}",
                            size=11,
                            color=ft.Colors.BLUE_GREY_500,
                        ),
                        self._build_executive_summary_card(sale_summary_items, plan_summary_items),
                        ft.Row(
                            controls=[
                                ft.Container(expand=True, content=self._build_detail_objects_table(objetos, moneda)),
                                ft.Container(expand=True, content=self._build_detail_buyers_table(compradores)),
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        *(
                            [
                                self._build_financial_summary_table(precio_venta, anticipo_importe, saldo_financiado, interes_total, total_obligaciones, resumen_plan, plan, moneda),
                                self._build_advance_table(anticipo_obligacion, moneda),
                                self._build_financed_plan_section(cuotas_obligaciones, bloques, saldo_financiado, interes_total, total_cuotas_obligaciones, moneda, plan),
                            ]
                            if confirmed_payment_method == "FINANCIADO"
                            else []
                        ),
                        self._build_detail_asset_impact_table(impacto),
                        ft.Row(
                            controls=[
                                ft.Container(expand=True),
                                ft.Button("Finalizar / Nueva venta", icon=ft.Icons.ADD_HOME_OUTLINED, on_click=self._restart_wizard),
                                *(
                                    [ft.OutlinedButton("Cerrar", icon=ft.Icons.CLOSE, on_click=lambda _: self.on_close())]
                                    if self.on_close is not None
                                    else []
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=14,
                ),
            )
        ]

    def _build_executive_summary_card(self, sale_items: list[tuple[str, Any]], plan_items: list[tuple[str, Any]]) -> ft.Control:
        summary_controls: list[ft.Control] = [self._summary_fields_row(sale_items)]
        if plan_items:
            summary_controls.extend([
                ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                self._summary_fields_row(plan_items),
            ])
        return self._compact_section(
            "Resumen de venta",
            ft.Column(controls=summary_controls, spacing=10),
        )

    def _summary_fields_row(self, items: list[tuple[str, Any]]) -> ft.Control:
        return ft.ResponsiveRow(
            columns=12,
            controls=[self._summary_field(label, value) for label, value in items],
            spacing=16,
            run_spacing=10,
        )

    def _summary_field(self, label: str, value: Any) -> ft.Control:
        value_control = value if isinstance(value, ft.Control) else ft.Text(
            str(value if value not in (None, "") else "-"),
            weight=ft.FontWeight.W_700,
            color=ft.Colors.BLUE_GREY_900,
            no_wrap=True,
        )
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4, "lg": 2},
            content=ft.Column(
                controls=[
                    ft.Text(label, size=11, color=ft.Colors.BLUE_GREY_600, no_wrap=True),
                    value_control,
                ],
                spacing=3,
            ),
        )

    def _compact_section(self, title: str, content: ft.Control) -> ft.Control:
        return ft.Container(
            padding=12,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=[ft.Text(title, size=16, weight=ft.FontWeight.W_700), content], spacing=8),
        )

    def _build_detail_objects_table(self, objetos: list[Any], moneda_default: Any) -> ft.Control:
        rows: list[list[Any]] = []
        for idx, raw in enumerate(objetos, start=1):
            obj = raw if isinstance(raw, dict) else {}
            rows.append([
                self._object_identifier(obj),
                obj.get("tipo_objeto"),
                self._detail_money(obj.get("precio_asignado"), obj.get("moneda") or moneda_default),
            ])
        return self._compact_section(
            "Objetos vendidos",
            self._compact_table(["Objeto", "Tipo", "Precio"], rows, empty_text="Sin objetos informados en el payload."),
        )

    def _build_detail_buyers_table(self, compradores: list[Any]) -> ft.Control:
        rows: list[list[Any]] = []
        for idx, raw in enumerate(compradores, start=1):
            comprador = raw if isinstance(raw, dict) else {}
            persona = comprador.get("persona") if isinstance(comprador.get("persona"), dict) else {}
            rol = comprador.get("rol_participacion") if isinstance(comprador.get("rol_participacion"), dict) else {}
            rows.append([
                self._confirmed_buyer_name(comprador) or "Comprador",
                self._first_present(comprador.get("codigo_rol"), rol.get("codigo_rol"), comprador.get("rol")),
                comprador.get("porcentaje_responsabilidad"),
            ])
        return self._compact_section(
            "Compradores",
            self._compact_table(["Comprador", "Rol", "Participación"], rows, empty_text="Sin compradores informados en el payload."),
        )

    def _confirmed_payment_method_label(self, venta: dict[str, Any], plan: dict[str, Any], detalle: dict[str, Any], cuotas: list[dict[str, Any]]) -> str:
        if self.state.pantalla_actual == "VENTA_CONFIRMADA" and self.state.forma_pago in {"CONTADO", "FINANCIADO"}:
            return self.state.forma_pago
        return self._sale_payment_form_label(venta, plan, detalle, cuotas)

    def _sale_payment_form_label(self, venta: dict[str, Any], plan: dict[str, Any], detalle: dict[str, Any], cuotas: list[dict[str, Any]]) -> str:
        candidates = [
            venta.get("forma_pago"),
            venta.get("metodo_pago"),
            detalle.get("forma_pago"),
            plan.get("metodo_plan_pago"),
            plan.get("tipo_plan"),
            plan.get("forma_pago"),
        ]
        normalized_values = [str(value or "").upper() for value in candidates if value not in (None, "")]
        if any(value in {"CONTADO", "PAGO_CONTADO"} or "CONTADO" in value for value in normalized_values):
            return "CONTADO"
        if cuotas or any(value in {"PLAN_POR_BLOQUES", "FINANCIADO", "FINANCIADA"} or "CUOTA" in value or "FINANC" in value for value in normalized_values):
            return "FINANCIADO"
        return "-"

    def _build_financial_summary_table(
        self,
        precio_venta: Any,
        anticipo: Any,
        saldo_financiado: Any,
        interes_total: Any,
        total_obligaciones: Any,
        resumen: dict[str, Any],
        plan: dict[str, Any],
        moneda: Any,
    ) -> ft.Control:
        headers = [
            "Precio de venta",
            "Anticipo",
            "Saldo financiado",
            "Interés total",
            "Total a cobrar",
            "Saldo pendiente",
            "Importe cancelado",
        ]
        rows = [[
            self._detail_money(precio_venta, moneda),
            self._detail_money(anticipo, moneda),
            self._detail_money(saldo_financiado, moneda),
            self._detail_money(interes_total, moneda),
            self._detail_money(total_obligaciones, moneda),
            self._detail_money(self._first_present(resumen.get("saldo_pendiente"), plan.get("saldo_pendiente")), moneda),
            self._detail_money(self._first_present(resumen.get("importe_cancelado"), plan.get("importe_cancelado")), moneda),
        ]]
        return self._compact_section(
            "Resumen financiero",
            self._compact_table(headers, rows, empty_text="Sin resumen financiero informado en el payload."),
        )

    def _build_advance_table(self, anticipo: dict[str, Any] | None, moneda_default: Any) -> ft.Control:
        rows: list[list[Any]] = []
        if anticipo is not None:
            rows.append([
                self._obligation_concept(anticipo, 1, default="Anticipo"),
                self._obligation_due_date(anticipo),
                self._detail_money(self._obligation_amount(anticipo), anticipo.get("moneda") or moneda_default),
                self._obligation_status(anticipo),
            ])
        return self._compact_section(
            "Anticipo",
            self._compact_table(["Concepto", "Vencimiento", "Importe", "Estado"], rows, empty_text="Sin anticipo informado en el payload."),
        )

    def _build_financed_plan_section(
        self,
        cuotas: list[dict[str, Any]],
        bloques: list[Any],
        capital_financiado: Any,
        interes_total: Any,
        total_financiado: Any,
        moneda: Any,
        plan: dict[str, Any],
    ) -> ft.Control:
        page_size = max(1, self.state.detalle_cuotas_page_size)
        total_cuotas = len(cuotas)
        total_pages = max(1, (total_cuotas + page_size - 1) // page_size)
        page = min(max(1, self.state.detalle_cuotas_page), total_pages)
        start_index = (page - 1) * page_size
        end_index = min(start_index + page_size, total_cuotas)
        cuotas_visibles = cuotas[start_index:end_index]
        cuotas_rows = [
            [
                f"Cuota {start_index + idx}",
                self._obligation_due_date(cuota),
                self._detail_money(self._obligation_amount(cuota), cuota.get("moneda") or moneda),
                self._obligation_status(cuota),
            ]
            for idx, cuota in enumerate(cuotas_visibles, start=1)
        ]

        controls: list[ft.Control] = []
        if total_cuotas > page_size:
            controls.append(ft.Text(f"Cuotas {start_index + 1} a {end_index} de {total_cuotas}", size=12, color=ft.Colors.BLUE_GREY_700))
        controls.append(
            self._compact_table(
                ["Cuota", "Vencimiento", "Importe", "Estado"],
                cuotas_rows,
                empty_text="Sin cuotas financiadas informadas en el payload.",
            )
        )
        if total_pages > 1:
            controls.append(
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Anterior", disabled=page <= 1, on_click=self._previous_detail_installments_page),
                        ft.Text(f"Página {page} de {total_pages}", color=ft.Colors.BLUE_GREY_700),
                        ft.OutlinedButton("Siguiente", disabled=page >= total_pages, on_click=self._next_detail_installments_page),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        return self._compact_section(
            "Plan financiado",
            ft.Column(controls=controls, spacing=8),
        )

    def _previous_detail_installments_page(self, _: Any = None) -> None:
        self.state.detalle_cuotas_page = max(1, self.state.detalle_cuotas_page - 1)
        self._render()

    def _next_detail_installments_page(self, _: Any = None) -> None:
        self.state.detalle_cuotas_page += 1
        self._render()

    def _split_advance_and_installment_obligations(self, obligaciones: list[Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        normalized = [ob for ob in obligaciones if isinstance(ob, dict)]
        advance_index: int | None = None
        for idx, ob in enumerate(normalized):
            if self._is_advance_obligation(ob):
                advance_index = idx
                break
        if advance_index is None and normalized and (self.state.tiene_anticipo or self.state.importe_anticipo):
            advance_index = 0
        if advance_index is None and len(normalized) > 1:
            first_amount = _parse_money_display_decimal(self._obligation_amount(normalized[0]))
            other_amounts = [_parse_money_display_decimal(self._obligation_amount(ob)) for ob in normalized[1:]]
            comparable_amounts = [amount for amount in other_amounts if amount is not None]
            if first_amount is not None and comparable_amounts and first_amount > max(comparable_amounts):
                advance_index = 0
        if advance_index is None:
            return None, normalized
        advance = normalized[advance_index]
        installments = [ob for idx, ob in enumerate(normalized) if idx != advance_index]
        return advance, installments

    def _is_advance_obligation(self, ob: dict[str, Any]) -> bool:
        candidates = [ob.get("tipo_obligacion"), ob.get("concepto"), ob.get("tipo_item_cronograma")]
        return any("ANTICIPO" in str(value or "").upper() for value in candidates)

    def _obligation_concept(self, ob: dict[str, Any], index: int, *, default: str) -> str:
        return str(self._first_present(ob.get("tipo_obligacion"), ob.get("tipo_item_cronograma"), ob.get("concepto"), ob.get("descripcion"), default))

    def _obligation_amount(self, ob: dict[str, Any] | None) -> Any:
        if ob is None:
            return None
        return self._first_present(ob.get("importe"), ob.get("importe_total"), ob.get("saldo_total"))

    def _obligation_due_date(self, ob: dict[str, Any]) -> Any:
        value = self._first_present(ob.get("fecha_vencimiento"), ob.get("vencimiento"))
        return _format_date_ar(value) or value

    def _obligation_status(self, ob: dict[str, Any]) -> Any:
        return self._first_present(ob.get("estado"), ob.get("estado_obligacion"))

    def _sum_obligations_amount(self, obligaciones: list[Any]) -> Decimal | None:
        total = Decimal("0")
        found = False
        for raw in obligaciones:
            ob = raw if isinstance(raw, dict) else {}
            amount = _parse_money_display_decimal(self._obligation_amount(ob))
            if amount is not None:
                total += amount
                found = True
        return total if found else None

    def _subtract_money_values(self, left: Any, right: Any) -> Decimal | None:
        left_value = _parse_money_display_decimal(left)
        right_value = _parse_money_display_decimal(right)
        if left_value is None or right_value is None:
            return None
        return left_value - right_value

    def _build_detail_asset_impact_table(self, impacto: Any) -> ft.Control:
        items = self._normalize_asset_impact_items(impacto)
        include_state_columns = any(
            self._first_present(item.get("estado_anterior"), item.get("estado_activo_anterior"), item.get("estado_nuevo"), item.get("estado_activo_nuevo"))
            not in (None, "", "-")
            for item in items
        )
        headers = ["Objeto", "Disponibilidad informada", "Ocupación informada", "Observaciones"]
        if include_state_columns:
            headers = ["Objeto", "Estado anterior", "Estado nuevo", "Disponibilidad informada", "Ocupación informada", "Observaciones"]

        rows: list[list[Any]] = []
        for item in items:
            base_row = [
                self._impact_object_label(item),
                item.get("disponibilidad_actual"),
                item.get("ocupacion_actual") or "Sin ocupación",
                item.get("observaciones"),
            ]
            row = base_row
            if include_state_columns:
                row = [
                    self._impact_object_label(item),
                    self._first_present(item.get("estado_anterior"), item.get("estado_activo_anterior")),
                    self._first_present(item.get("estado_nuevo"), item.get("estado_activo_nuevo")),
                    item.get("disponibilidad_actual"),
                    item.get("ocupacion_actual") or "Sin ocupación",
                    item.get("observaciones"),
                ]
            if any(value not in (None, "", "-") for value in row):
                rows.append(row)
        return self._compact_section(
            "Impacto del activo",
            self._compact_table(headers, rows, empty_text="Sin impacto informado en el payload."),
        )

    def _compact_table(self, headers: list[str], rows: list[list[Any]], *, empty_text: str) -> ft.Control:
        if not rows:
            return ft.Text(empty_text, color=ft.Colors.BLUE_GREY_700)
        header = ft.Row(
            controls=[self._table_cell(text, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_GREY_700) for text in headers],
            spacing=0,
        )
        body_rows = [
            ft.Row(
                controls=[self._table_cell(value) for value in row],
                spacing=0,
            )
            for row in rows
        ]
        return ft.Column(
            controls=[header, ft.Divider(height=1), *body_rows],
            spacing=4,
        )

    def _table_cell(self, value: Any, *, weight: ft.FontWeight | None = None, color: ft.ColorValue | None = None) -> ft.Control:
        if isinstance(value, ft.Control):
            content = value
        else:
            content = ft.Text(str(value if value not in (None, "") else "-"), size=12, color=color or ft.Colors.BLUE_GREY_900)
        return ft.Container(
            expand=True,
            padding=ft.Padding(left=6, top=4, right=6, bottom=4),
            content=content if isinstance(value, ft.Control) else ft.Text(str(value if value not in (None, "") else "-"), size=12, color=color or ft.Colors.BLUE_GREY_900, weight=weight),
        )

    def _object_identifier(self, obj: dict[str, Any]) -> str:
        visual = self._first_present(obj.get("descripcion"), obj.get("codigo"), obj.get("texto_visual"))
        if visual:
            return str(visual)
        if obj.get("id_inmueble") not in (None, ""):
            return f"Inmueble {obj.get('id_inmueble')}"
        if obj.get("id_unidad_funcional") not in (None, ""):
            return f"Unidad funcional {obj.get('id_unidad_funcional')}"
        return "-"

    def _impact_object_label(self, item: dict[str, Any]) -> Any:
        return self._first_present(item.get("codigo"), item.get("descripcion"), item.get("id_inmueble"), item.get("id_unidad_funcional"))

    def _normalize_asset_impact_items(self, impacto: Any) -> list[dict[str, Any]]:
        if isinstance(impacto, dict):
            objetos = impacto.get("objetos")
            if isinstance(objetos, list):
                return [item for item in objetos if isinstance(item, dict) and self._has_useful_asset_impact_data(item)]
            return [impacto] if self._has_useful_asset_impact_data(impacto) else []
        if isinstance(impacto, list):
            return [item for item in impacto if isinstance(item, dict) and self._has_useful_asset_impact_data(item)]
        return []

    def _has_useful_asset_impact_data(self, item: dict[str, Any]) -> bool:
        values = [
            self._impact_object_label(item),
            self._first_present(item.get("estado_anterior"), item.get("estado_activo_anterior")),
            self._first_present(item.get("estado_nuevo"), item.get("estado_activo_nuevo")),
            item.get("disponibilidad_actual"),
            item.get("ocupacion_actual"),
            item.get("observaciones"),
        ]
        return any(value not in (None, "", "-") for value in values)

    def _status_badge(self, status: str) -> ft.Control:
        normalized = str(status or "-").upper()
        if normalized == "CONFIRMADA":
            return _badge(normalized, ft.Colors.GREEN_50, ft.Colors.GREEN_200)
        if normalized in {"GENERADO", "PROYECTADA"}:
            return _badge(normalized, ft.Colors.BLUE_50, ft.Colors.BLUE_200)
        return _badge(normalized, ft.Colors.BLUE_GREY_50, ft.Colors.BLUE_GREY_200)

    def _as_list(self, value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    def _detail_money(self, value: Any, moneda: Any = None) -> str:
        if value in (None, ""):
            return "-"
        amount = _format_money(value)
        return f"{amount} {moneda}" if moneda not in (None, "") and amount != "-" else amount

    def _first_present(self, *values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None

    def _confirmed_buyer_name(self, comprador: dict[str, Any]) -> str:
        persona = comprador.get("persona") if isinstance(comprador.get("persona"), dict) else {}
        return persona.get("razon_social") or " ".join(part for part in [persona.get("nombre"), persona.get("apellido")] if part) or comprador.get("nombre") or ""

    def _confirmed_buyer_label(self, comprador: dict[str, Any]) -> str:
        persona = comprador.get("persona") if isinstance(comprador.get("persona"), dict) else {}
        rol = comprador.get("rol_participacion") if isinstance(comprador.get("rol_participacion"), dict) else {}
        nombre = self._confirmed_buyer_name(comprador)
        return f"{nombre or persona.get('id_persona') or comprador.get('id_persona') or '-'} / {rol.get('codigo_rol') or comprador.get('codigo_rol') or '-'} / {comprador.get('porcentaje_responsabilidad') or '-'}%"

    def _confirm_error_message(self, result: ApiResult) -> str:
        if self._is_reservation_already_converted_error(result):
            friendly = "La reserva seleccionada ya fue convertida en venta."
            if self.state.mostrar_datos_tecnicos:
                technical = {
                    "status_code": result.status_code,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                    "error_details": result.error_details,
                }
                return f"{friendly} Detalle técnico: {json.dumps(technical, ensure_ascii=False, default=str)}"
            return friendly
        if result.status_code == 400:
            prefix = "El sistema rechazó la confirmación por validación."
        elif result.status_code == 409:
            prefix = "El sistema informó un conflicto de concurrencia o estado."
        elif result.status_code == 500:
            prefix = "El sistema devolvió un error interno al confirmar."
        elif result.status_code is None:
            prefix = "No se pudo conectar con el sistema para confirmar la venta."
        else:
            prefix = "No se pudo confirmar la venta."
        parts = [prefix]
        if result.status_code is not None:
            parts.append(f"HTTP {result.status_code}.")
        if result.error_code:
            parts.append(f"{result.error_code}.")
        if result.error_message:
            parts.append(result.error_message)
        return " ".join(parts)

    @staticmethod
    def _is_reservation_already_converted_error(result: ApiResult) -> bool:
        haystack = " ".join(
            str(value or "")
            for value in (result.error_code, result.error_message, result.error_details)
        ).upper()
        converted_markers = (
            "YA FUE CONVERTIDA",
            "YA CONVERTIDA",
            "RESERVA_CONVERTIDA",
            "RESERVA_ALREADY_CONVERTED",
            "RESERVA_YA_CONVERTIDA",
            "CONFIRMADA_VENTA",
            "VENTA_CONFIRMADA",
            "YA TIENE VENTA",
        )
        return any(marker in haystack for marker in converted_markers)

    def _reset_confirm_attempt(self, *, clear_error: bool = True) -> None:
        self.state.confirm_op_id = None
        self.state.confirm_payload_signature = None
        self.state.confirm_data = None
        self.state.confirm_status_code = None
        self.state.confirm_payload = None
        self.state.confirm_endpoint = None
        self.state.confirm_error_details = None
        if clear_error:
            self.state.confirm_error = None

    def _mark_plan_preview_stale(self, clear_error: bool = True) -> None:
        self.state.preview_stale = True
        self.state.preview_obligaciones_page = 1
        self._reset_confirm_attempt(clear_error=clear_error)
        if clear_error:
            self.state.preview_error = None

    def _build_review_validation_panel(self, errors: list[str]) -> ft.Control:
        valid = not errors
        if valid:
            controls: list[ft.Control] = [
                ft.Text("6. Validación general", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_900),
                ft.Text("La venta directa está lista para confirmar.", weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_900),
            ]
            bgcolor = ft.Colors.GREEN_50
            border_color = ft.Colors.GREEN_300
        else:
            controls = [
                ft.Text("6. Validación general", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.RED_900),
                ft.Text("Faltan datos o hay pendientes antes de confirmar.", weight=ft.FontWeight.W_700, color=ft.Colors.RED_900),
                ft.Column(controls=[ft.Text(f"• {error}", color=ft.Colors.RED_800) for error in errors], spacing=4),
            ]
            bgcolor = ft.Colors.RED_50
            border_color = ft.Colors.RED_300
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=bgcolor,
            border=_border_all(1, border_color),
            content=ft.Column(controls=controls, spacing=8),
        )

    def _build_confirm_status_panel(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("7. Confirmación real", size=18, weight=ft.FontWeight.W_700),
            ft.Text(
                "Al confirmar, se registrará la venta y se generarán el plan y las obligaciones correspondientes.",
                color=ft.Colors.BLUE_GREY_800,
            ),
            *self._technical_controls([
                ft.Text(
                    f"Confirmar venta es COMMAND_WRITE_NEGOCIO: usa {'POST /api/v1/reservas-venta/' + str(self.state.id_reserva_venta) + '/confirmar-venta-completa' if self.state.origen == 'RESERVA' else 'POST /api/v1/ventas/directa/confirmar-venta-completa'} y genera venta, plan y obligaciones en la misma operación.",
                    size=12,
                    color=ft.Colors.BLUE_GREY_700,
                ),
                ft.Text(
                    "Headers CORE-EF de prototipo: ApiClient envía X-Op-Id autogenerado y placeholders visibles X-Usuario-Id=1, X-Sucursal-Id=1, X-Instalacion-Id=1 hasta integrar contexto real de sesión/sucursal/instalación.",
                    size=12,
                    color=ft.Colors.BLUE_GREY_700,
                ),
            ]),
        ]
        if self.state.confirm_loading:
            controls.append(
                ft.Row(
                    controls=[ft.ProgressRing(width=18, height=18), ft.Text("Generando venta desde reserva..." if self.state.origen == "RESERVA" else "Confirmando venta directa...")],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        persisted_errors = self._non_persisted_confirmation_errors()
        if persisted_errors:
            controls.append(
                self._build_help_card(
                    "La confirmación requiere objetos y compradores válidos. Activá datos técnicos para ver el detalle de persistencia.",
                    ft.Colors.AMBER_50,
                    ft.Colors.AMBER_200,
                )
            )
            controls.append(ft.Column(controls=[ft.Text(f"• {error}", color=ft.Colors.AMBER_900) for error in persisted_errors], spacing=4))
        if self.state.confirm_error is not None:
            controls.append(self._build_help_card(self.state.confirm_error, ft.Colors.RED_50, ft.Colors.RED_200))
        elif self._can_confirm_sale():
            controls.append(self._build_help_card("Preview vigente y revisión completa. Podés presionar Confirmar venta.", ft.Colors.GREEN_50, ft.Colors.GREEN_200))
        else:
            controls.append(self._build_help_card("No se habilita la confirmación hasta resolver validaciones reales y tener la vista previa vigente.", ft.Colors.AMBER_50, ft.Colors.AMBER_200))
        return self._build_review_section_container(controls)

    def _build_review_section_container(self, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=8),
        )

    def _non_persisted_confirmation_errors(self) -> list[str]:
        errors: list[str] = []
        if self.state.origen != "DIRECTA":
            return errors
        non_persisted_objects = [objeto.texto_visual for objeto in self.state.objetos if not objeto.persisted]
        if non_persisted_objects:
            errors.append("Objetos no persistidos: " + ", ".join(non_persisted_objects))
        non_persisted_buyers = [comprador.texto_visual for comprador in self.state.compradores if not comprador.persisted]
        if non_persisted_buyers:
            errors.append("Compradores no persistidos: " + ", ".join(non_persisted_buyers))
        return errors

    def _has_only_persisted_confirmation_records(self) -> bool:
        return not self._non_persisted_confirmation_errors()

    @staticmethod
    def _record_source_label(source: str, persisted: bool) -> str:
        if persisted:
            return f"dato confirmado ({source or 'backend'})"
        return f"dato pendiente ({source or 'manual'})"

    def _general_review_errors(self) -> list[str]:
        errors: list[str] = []
        if self.state.origen not in {"DIRECTA", "RESERVA"}:
            errors.append("Seleccioná un origen válido.")
        if self.state.origen == "RESERVA" and self.state.id_reserva_venta is None:
            errors.append("No hay una reserva real seleccionada desde el sistema.")
        if not self._has_valid_currency():
            errors.append("Seleccioná una moneda válida.")
        if not self.state.fecha_venta_iso or self.fecha_venta_error is not None:
            errors.append("Cargá una fecha_venta válida.")
        if not self.state.codigo_venta.strip():
            errors.append("Cargá el código de venta: es requerido para confirmar la venta.")
        if not self.state.objetos:
            errors.append("Cargá al menos un objeto de venta.")
        invalid_objects = [objeto for objeto in self.state.objetos if _parse_money_decimal(objeto.precio_asignado) is None]
        if invalid_objects:
            errors.append("Todos los objetos deben tener precio_asignado válido.")
        if self._objects_total() <= Decimal("0"):
            errors.append("El total derivado de objetos debe ser mayor que 0.")
        if self.state.origen == "DIRECTA":
            buyer_error = self._buyers_validation_error()
            if buyer_error is not None:
                errors.append(buyer_error)
            errors.extend(self._non_persisted_confirmation_errors())
        if self.state.origen == "RESERVA":
            if self.state.version_registro is None:
                errors.append("La reserva seleccionada no informa version_registro para confirmar con control de versión.")
            if not self.state.objetos:
                errors.append("La reserva seleccionada no tiene objetos heredados para generar la venta.")
            if not self.state.compradores:
                errors.append("La reserva seleccionada no tiene compradores heredados para generar la venta.")
        if self.state.forma_pago not in {"CONTADO", "FINANCIADO"}:
            errors.append("Elegí una forma de pago.")
        if self.state.forma_pago == "CONTADO" and (not self.state.fecha_pago_contado_iso or self.state.fecha_pago_contado_error is not None):
            errors.append("Cargá una fecha de pago contado válida.")
        if self.state.forma_pago == "FINANCIADO" and self._financed_plan_difference() != Decimal("0"):
            errors.append("El plan financiado debe estar completo con diferencia 0.")
        if self.state.preview_data is None:
            errors.append("Calculá la vista previa del plan de pago antes de confirmar.")
        if self.state.preview_stale:
            errors.append("El preview está desactualizado; recalculalo antes de confirmar.")
        return errors

    def _general_review_is_valid(self) -> bool:
        return not self._general_review_errors()

    def _can_confirm_sale(self) -> bool:
        return (
            self.state.pantalla_actual == "REVISION_GENERAL"
            and not self.state.confirm_loading
            and self._general_review_is_valid()
            and self.state.preview_data is not None
            and not self.state.preview_stale
            and self.state.origen in {"DIRECTA", "RESERVA"}
            and self._has_only_persisted_confirmation_records()
        )

    def _build_confirmed_sale_step(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Venta confirmada", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_900),
            self._build_help_card(
                "La venta se confirmó correctamente. Esta operación ya no se edita desde el wizard; usá Nueva venta para iniciar otro flujo limpio.",
                ft.Colors.GREEN_50,
                ft.Colors.GREEN_200,
            ),
            *self._technical_controls(self._build_confirmed_sale_technical_controls()),
            *self._build_confirmed_sale_detail_controls(),
            ft.Row(
                controls=[
                    ft.Container(expand=True),
                    ft.FilledButton("Nueva venta", icon=ft.Icons.ADD_HOME_OUTLINED, on_click=self._restart_wizard),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]
        return ft.Container(
            padding=ft.Padding(left=24, top=24, right=24, bottom=40),
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(controls=controls, spacing=14),
        )


    def _build_confirmed_sale_technical_controls(self) -> list[ft.Control]:
        response = self.state.confirm_data if self.state.confirm_data is not None else {
            "error": self.state.confirm_error,
            "details": self.state.confirm_error_details,
        }
        payload = self.state.confirm_payload or {}
        rows = [
            _info_row("Endpoint", self.state.confirm_endpoint or "-"),
            _info_row("id_venta", self._confirmed_sale_id() or "-"),
            _info_row("id_reserva_venta", self.state.id_reserva_venta if self.state.origen == "RESERVA" else "NO APLICA"),
            _info_row("op_id", self.state.confirm_op_id or "-"),
        ]
        return [
            self._build_review_section_container(
                [
                    ft.Text("Datos técnicos de confirmación", size=16, weight=ft.FontWeight.W_700),
                    *rows,
                    ft.Text("Payload de confirmación", size=12, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_GREY_700),
                    ft.Text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), selectable=True, size=11),
                    ft.Text("Response backend", size=12, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_GREY_700),
                    ft.Text(json.dumps(response, ensure_ascii=False, indent=2, default=str), selectable=True, size=11),
                ]
            )
        ]

    def _build_flow_state_panel(self) -> ft.Control:
        controls: list[ft.Control] = [ft.Text("Estado del flujo", size=20, weight=ft.FontWeight.W_700)]
        controls.extend(self._build_flow_state_sections())
        controls.extend([ft.Divider(height=10), self._build_technical_mode_switch()])

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

    def _build_flow_state_sections(self) -> list[ft.Control]:
        if self.state.pantalla_actual == "VENTA_CONFIRMADA":
            return [
                self._build_flow_state_section(
                    "Operación",
                    [
                        _flow_info_row("Origen", self._origin_label()),
                        _flow_info_row("Reserva", self.state.id_reserva_venta if self.state.origen == "RESERVA" else "NO APLICA"),
                        _flow_info_row("Venta", self._confirmed_sale_id() or "-"),
                        _flow_info_row("Forma de pago", self._payment_method_status()),
                    ],
                ),
                self._build_flow_state_section(
                    "Participantes",
                    [
                        _flow_info_row("Objetos", len(self.state.objetos)),
                        _flow_info_row("Compradores", self._buyers_flow_status()),
                    ],
                ),
                self._build_flow_state_section(
                    "Importes / Plan",
                    [
                        _flow_info_row("Total venta", self._format_money_with_currency(self._objects_total())),
                    ],
                ),
                self._build_flow_state_section(
                    "Revisión / Estado",
                    [_flow_info_row("Estado", self._flow_status_badge("venta confirmada"))],
                ),
                self._build_next_step_card("Finalizar / Nueva venta"),
            ]

        sections: list[ft.Control] = []
        operation_rows: list[ft.Control] = [_flow_info_row("Origen", self._origin_label())]
        if self.state.origen == "RESERVA" or self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            operation_rows.append(_flow_info_row("Reserva", self._reservation_status()))
            operation_rows.append(_flow_info_row("Estado", self._flow_status_badge("reserva seleccionada" if self.state.id_reserva_venta is not None else "pendiente")))
            operation_rows.append(_flow_info_row("Moneda heredada", "sí" if self._reservation_has_allowed_currency() else "no"))
        operation_rows.extend(
            [
                _flow_info_row("Moneda", self._currency_label()),
                _flow_info_row("Forma de pago", self._flow_status_badge(self._payment_method_status())),
            ]
        )
        sections.append(self._build_flow_state_section("Operación", operation_rows))
        sections.append(
            self._build_flow_state_section(
                "Participantes",
                [
                    _flow_info_row("Objetos", self._object_count_status()),
                    _flow_info_row("Compradores", self._flow_status_badge(self._buyers_flow_status())),
                ],
            )
        )

        financial_rows = self._financial_flow_rows()
        if financial_rows:
            sections.append(self._build_flow_state_section("Importes / Plan", financial_rows))
        sections.append(
            self._build_flow_state_section(
                "Revisión / Estado",
                [_flow_info_row("Estado", self._flow_status_badge(self._review_flow_status()), value_no_wrap=False)],
            )
        )
        sections.append(self._build_next_step_card(self._next_step_label()))
        return sections

    def _build_flow_state_section(self, title: str, rows: list[ft.Control]) -> ft.Control:
        return ft.Container(
            padding=ft.Padding(left=10, top=8, right=10, bottom=8),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                controls=[
                    ft.Text(title, size=12, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_GREY_700),
                    *rows,
                ],
                spacing=6,
            ),
        )

    def _build_next_step_card(self, label: str) -> ft.Control:
        return ft.Container(
            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
            border_radius=12,
            bgcolor=ft.Colors.BLUE_50,
            border=_border_all(1, ft.Colors.BLUE_200),
            content=ft.Column(
                controls=[
                    ft.Text("Próximo paso", size=11, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_GREY_700),
                    ft.Text(label, size=14, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_900, no_wrap=False),
                ],
                spacing=4,
            ),
        )

    def _financial_flow_rows(self) -> list[ft.Control]:
        if self.state.forma_pago not in {"CONTADO", "FINANCIADO"}:
            return []
        rows: list[ft.Control] = [_flow_info_row("Total venta", self._format_money_with_currency(self._objects_total()))]
        if self.state.forma_pago == "FINANCIADO":
            rows.extend(
                [
                    _flow_info_row("Anticipo", self._advance_status()),
                    _flow_info_row("Tramos", self._installments_status()),
                    _flow_info_row("Total asignado", self._format_money_with_currency(self._financed_plan_total_assigned())),
                    _flow_info_row("Diferencia", self._format_money_with_currency(self._financed_plan_difference())),
                ]
            )
        return rows

    def _object_count_status(self) -> ft.Control:
        if self.state.objetos:
            suffix = " heredados de reserva" if self.state.origen == "RESERVA" and any(obj.heredado_reserva for obj in self.state.objetos) else " listo"
            return self._flow_status_badge(f"{len(self.state.objetos)}{suffix}")
        if self.state.origen == "RESERVA" and self.state.id_reserva_venta is not None:
            return self._flow_status_badge("0 heredados de reserva")
        return self._flow_status_badge("0")

    def _installments_status(self) -> ft.Control:
        if self.state.tramos_cuotas:
            return self._flow_status_badge(f"{len(self.state.tramos_cuotas)} listo")
        return self._flow_status_badge("pendiente")

    def _flow_status_badge(self, value: Any) -> ft.Control:
        label = str(value if value not in (None, "") else "sin datos")
        normalized = label.lower()
        if "venta confirmada" in normalized or "lista para confirmar" in normalized or "listo" in normalized:
            bgcolor, border_color, text_color = ft.Colors.GREEN_50, ft.Colors.GREEN_200, ft.Colors.GREEN_900
        elif "preview calculado" in normalized or "en progreso" in normalized:
            bgcolor, border_color, text_color = ft.Colors.BLUE_50, ft.Colors.BLUE_200, ft.Colors.BLUE_900
        elif "pendiente" in normalized or "incompleto" in normalized or "desactualizado" in normalized:
            bgcolor, border_color, text_color = ft.Colors.AMBER_50, ft.Colors.AMBER_200, ft.Colors.AMBER_900
        else:
            bgcolor, border_color, text_color = ft.Colors.BLUE_GREY_50, ft.Colors.BLUE_GREY_100, ft.Colors.BLUE_GREY_800
        return ft.Container(
            padding=ft.Padding(left=8, top=3, right=8, bottom=3),
            border_radius=999,
            bgcolor=bgcolor,
            border=_border_all(1, border_color),
            content=ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=text_color, no_wrap=True),
        )

    def _build_technical_mode_switch(self) -> ft.Control:
        return ft.Switch(
            label="Mostrar datos técnicos",
            value=self.state.mostrar_datos_tecnicos,
            on_change=self._on_toggle_technical_data,
        )

    def _build_navigation(self) -> ft.Control:
        if self.state.pantalla_actual == "REVISION_GENERAL":
            self.next_button = ft.Button(
                "Confirmar venta",
                icon=ft.Icons.CHECK_CIRCLE,
                disabled=self.state.confirm_loading or self.state.preview_loading or not self._can_confirm_sale(),
                on_click=self._confirm_sale,
            )
        else:
            self.next_button = ft.Button(
                "Siguiente",
                icon=ft.Icons.ARROW_FORWARD,
                disabled=self.state.confirm_loading or self.state.preview_loading or not self._can_advance(),
                on_click=self._next_step,
            )
        return ft.Row(
            controls=[
                ft.OutlinedButton(
                    "Anterior",
                    icon=ft.Icons.ARROW_BACK,
                    disabled=self.state.pantalla_actual in {"ORIGEN", "VENTA_CONFIRMADA"} or self.state.confirm_loading,
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
            self.state.reserva_visible_data = {}
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
                    controls=[self._build_currency_card(moneda, currency_locked) for moneda in MONEDAS_PERMITIDAS],
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
        if selected_currency not in MONEDAS_PERMITIDAS or self._currency_locked_by_objects():
            self._render()
            return
        self.state.moneda = selected_currency
        self.precio_objeto_field.label = f"Valor asignado al objeto ({self._currency_label()})"
        self._mark_plan_preview_stale()
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
        self._mark_plan_preview_stale()
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
            self._mark_plan_preview_stale()
            self._sync_fecha_venta_feedback()
            self._refresh_navigation_controls()
            self.page.update()

    def _on_codigo_venta_change(self, event: ft.ControlEvent) -> None:
        self.state.codigo_venta = str(event.control.value or "")
        self._reset_confirm_attempt()

    def _on_observaciones_change(self, event: ft.ControlEvent) -> None:
        self.state.observaciones_comerciales = str(event.control.value or "")
        self._mark_plan_preview_stale()


    def _preload_reservation_context(self, selected: dict[str, Any]) -> None:
        self.state.objetos = self._reservation_object_drafts(selected)
        self.state.compradores = self._reservation_buyer_drafts(selected)
        moneda = self._display_or_none(self._reservation_first_present(selected, ("moneda", "codigo_moneda")))
        if moneda and moneda.strip().upper() in MONEDAS_PERMITIDAS:
            self.state.moneda = moneda.strip().upper()
        self._mark_plan_preview_stale()

    def _reservation_payloads(self, selected: dict[str, Any]) -> list[dict[str, Any]]:
        raw = selected.get("raw") if isinstance(selected.get("raw"), dict) else {}
        payloads = [selected]
        if isinstance(raw, dict):
            for key in ("detalle", "listado"):
                nested = raw.get(key)
                if isinstance(nested, dict):
                    payloads.append(nested)
            payloads.append(raw)
        return [payload for payload in payloads if isinstance(payload, dict)]

    @staticmethod
    def _reservation_detail_payload(data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {}
        current = data
        for key in ("data", "item", "reserva"):
            nested = current.get(key)
            if isinstance(nested, dict):
                current = nested
        return current if isinstance(current, dict) else {}

    @staticmethod
    def _reservation_detail_list_count(detail: dict[str, Any], keys: tuple[str, ...]) -> int:
        for key in keys:
            value = detail.get(key)
            if isinstance(value, list):
                return len([item for item in value if isinstance(item, dict)])
            if isinstance(value, dict):
                return 1
        return 0

    def _reset_reservation_detail_diagnostics(self) -> None:
        self.state.reserva_detalle_error = None
        self.state.reserva_detalle_loaded = False
        self.state.reserva_detalle_source = "listado_parcial"
        self.state.reserva_detalle_participaciones_count = 0
        self.state.reserva_detalle_objetos_count = 0
        self.state.reserva_detalle_conversion_warning = None

    def _enriched_reservation_payload(self, selected: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        self._reset_reservation_detail_diagnostics()
        id_reserva = _safe_int(selected.get("id_reserva_venta"))
        if id_reserva is None:
            return dict(selected), None
        result = self.api.get_reserva_venta(id_reserva)
        if not result.success:
            warning = "No se pudo cargar el detalle de la reserva; se usará la información parcial del listado."
            self.state.reserva_detalle_error = warning
            return {**selected, "raw": {"listado": selected.get("raw") if isinstance(selected.get("raw"), dict) else selected}, "precarga_source": "listado_parcial"}, warning
        detail = self._reservation_detail_payload(result.data)
        self.state.reserva_detalle_loaded = True
        self.state.reserva_detalle_source = "detalle"
        self.state.reserva_detalle_participaciones_count = self._reservation_detail_list_count(detail, ("participaciones",))
        self.state.reserva_detalle_objetos_count = self._reservation_detail_list_count(detail, ("objetos", "objeto", "inmuebles", "unidades_funcionales"))
        enriched = dict(selected)
        enriched.update({key: value for key, value in detail.items() if value not in (None, "", [])})
        for key in ("objetos", "objeto", "inmuebles", "unidades_funcionales", "participaciones"):
            if key in detail:
                enriched[key] = detail[key]
        enriched["raw"] = {
            "listado": selected.get("raw") if isinstance(selected.get("raw"), dict) else selected,
            "detalle": detail,
        }
        enriched["precarga_source"] = "detalle"
        return enriched, None

    def _reservation_first_present(self, selected: dict[str, Any], keys: tuple[str, ...]) -> Any:
        for payload in self._reservation_payloads(selected):
            value = self._first_present_field(payload, keys)
            if value not in (None, "", []):
                return value
        return None

    def _reservation_collection(self, selected: dict[str, Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen: set[tuple[Any, Any, str]] = set()
        for payload in self._reservation_payloads(selected):
            for key in keys:
                value = payload.get(key)
                candidates = value if isinstance(value, list) else [value] if isinstance(value, dict) else []
                for item in candidates:
                    if not isinstance(item, dict):
                        continue
                    persona = item.get("persona") if isinstance(item.get("persona"), dict) else {}
                    primary_id = item.get("id_inmueble") or item.get("id_persona") or persona.get("id_persona")
                    secondary_id = item.get("id_unidad_funcional")
                    marker = (
                        primary_id,
                        secondary_id,
                        "" if primary_id is not None or secondary_id is not None else self._visible_join(item),
                    )
                    if marker in seen:
                        continue
                    seen.add(marker)
                    items.append(item)
        return items

    def _reservation_object_drafts(self, selected: dict[str, Any]) -> list[ObjetoVentaWizardDraft]:
        object_items = self._reservation_collection(selected, ("objetos", "objeto", "inmuebles", "unidades_funcionales"))
        total_amount = self._reservation_money_value(selected, None)
        drafts: list[ObjetoVentaWizardDraft] = []
        for item in object_items:
            id_unidad = _safe_int(self._first_present_field(item, ("id_unidad_funcional", "id_unidad", "unidad_funcional_id")))
            id_inmueble = _safe_int(self._first_present_field(item, ("id_inmueble", "inmueble_id")))
            tipo = "UNIDAD_FUNCIONAL" if id_unidad is not None or "unidad" in str(item.get("tipo_objeto") or "").lower() else "INMUEBLE"
            amount = self._reservation_item_money_value(item)
            if amount is None and len(object_items) == 1:
                amount = total_amount
            drafts.append(
                ObjetoVentaWizardDraft(
                    tipo_objeto=tipo,
                    id_inmueble=id_inmueble if tipo == "INMUEBLE" else None,
                    id_unidad_funcional=id_unidad if tipo == "UNIDAD_FUNCIONAL" else None,
                    texto_visual=self._reservation_visible_text(item, fallback="Objeto heredado de reserva"),
                    precio_asignado=_format_decimal(amount) if amount is not None else "",
                    source="reserva",
                    persisted=(id_unidad is not None if tipo == "UNIDAD_FUNCIONAL" else id_inmueble is not None),
                    heredado_reserva=True,
                )
            )
        return drafts

    def _reservation_buyer_drafts(self, selected: dict[str, Any]) -> list[CompradorWizardDraft]:
        buyer_items = self._reservation_collection(selected, ("participaciones", "compradores", "comprador", "reservantes", "reservante", "cliente"))
        if any(self._first_present_field(item, ("id_rol_participacion", "rol_participacion_id")) in (None, "") for item in buyer_items):
            self._load_rol_comprador_if_needed()
        role_id = self._rol_comprador_id_resuelto() or ""
        drafts: list[CompradorWizardDraft] = []
        for item in buyer_items:
            persona = item.get("persona") if isinstance(item.get("persona"), dict) else {}
            id_persona = _safe_int(
                self._first_present_field(item, ("id_persona", "persona_id", "id_cliente", "id_reservante"))
                or persona.get("id_persona")
            )
            if id_persona is None:
                continue
            porcentaje_text = ""
            raw_percentage = self._first_present_field(item, ("porcentaje_responsabilidad", "porcentaje", "responsabilidad"))
            parsed_percentage = _parse_percentage(str(raw_percentage)) if raw_percentage not in (None, "") else None
            if parsed_percentage is not None:
                porcentaje_text = _format_decimal(parsed_percentage)
            item_role_id = _safe_int(self._first_present_field(item, ("id_rol_participacion", "rol_participacion_id")))
            drafts.append(
                CompradorWizardDraft(
                    id_persona=id_persona,
                    texto_visual=self._reservation_participant_visible_text(item),
                    porcentaje_responsabilidad=porcentaje_text,
                    id_rol_participacion=str(item_role_id) if item_role_id is not None else role_id,
                    source="reserva",
                    persisted=True,
                    heredado_reserva=True,
                )
            )
        if len(drafts) == 1 and not drafts[0].porcentaje_responsabilidad.strip():
            drafts[0].porcentaje_responsabilidad = "100.00"
        return drafts

    def _reservation_item_money_value(self, item: dict[str, Any]) -> Decimal | None:
        raw = self._first_present_field(item, ("precio_asignado", "precio_reservado", "importe", "precio_total", "monto"))
        return _parse_money_decimal(str(raw)) if raw not in (None, "") else None

    def _reservation_money_value(self, selected: dict[str, Any], item: dict[str, Any] | None) -> Decimal | None:
        if item is not None:
            parsed_item = self._reservation_item_money_value(item)
            if parsed_item is not None:
                return parsed_item
        keys = ("precio_reservado", "importe_reserva", "precio_total", "importe", "monto")
        for source in self._reservation_payloads(selected):
            raw = self._first_present_field(source, keys)
            parsed = _parse_money_decimal(str(raw)) if raw not in (None, "") else None
            if parsed is not None:
                return parsed
        return None

    def _reservation_visible_text(self, value: Any, *, fallback: str) -> str:
        text = self._visible_join(value)
        return text if text else fallback

    def _reservation_participant_visible_text(self, item: dict[str, Any]) -> str:
        persona = item.get("persona") if isinstance(item.get("persona"), dict) else item
        for key in ("texto_visual", "display_name", "nombre_completo", "razon_social"):
            text = self._visible_join(persona.get(key))
            if text:
                return text
        apellido_nombre = " ".join(
            part for part in [self._visible_join(persona.get("apellido")), self._visible_join(persona.get("nombre"))] if part
        )
        if apellido_nombre:
            return apellido_nombre
        nombre_apellido = " ".join(
            part for part in [self._visible_join(persona.get("nombre")), self._visible_join(persona.get("apellido"))] if part
        )
        if nombre_apellido:
            return nombre_apellido
        documento = self._visible_join(
            persona.get("documento") or persona.get("documento_principal") or persona.get("cuit_cuil")
        )
        return documento or "Comprador heredado de reserva"

    def _reservation_has_allowed_currency(self) -> bool:
        moneda = self.state.reserva_visible_data.get("moneda")
        return str(moneda or "").strip().upper() in MONEDAS_PERMITIDAS

    def _reservation_buyers_preload_warning(self) -> str | None:
        if self.state.compradores:
            return None
        if self.state.reserva_detalle_error:
            return self.state.reserva_detalle_error
        if self.state.reserva_detalle_loaded and self.state.reserva_detalle_participaciones_count == 0:
            return "El detalle de la reserva no informa participaciones."
        if self.state.reserva_detalle_loaded and self.state.reserva_detalle_participaciones_count > 0:
            self.state.reserva_detalle_conversion_warning = "El detalle informa participaciones, pero no se pudieron convertir a compradores válidos."
            return self.state.reserva_detalle_conversion_warning
        return "La reserva seleccionada no informa compradores/reservantes luego de consultar el detalle."

    def _reservation_buyers_missing_message(self) -> str:
        return self.state.reserva_visible_data.get("compradores_warning") or self._reservation_buyers_preload_warning() or "La reserva seleccionada no informa compradores/reservantes luego de consultar el detalle."

    def _request_reserva_selected(self, selected: dict[str, Any] | None) -> None:
        self._request_selector_selection(
            selected,
            self._on_reserva_selected,
            "reserva_select_loading",
            "reserva_select_error",
            "No se pudo aplicar la selección de reserva.",
        )

    def _request_objeto_selected(self, selected: dict[str, Any] | None) -> None:
        self._request_selector_selection(
            selected,
            self._on_objeto_selected,
            "object_select_loading",
            "object_select_error",
            "No se pudo aplicar la selección de objeto.",
        )

    def _request_comprador_selected(self, selected: dict[str, Any] | None) -> None:
        self._request_selector_selection(
            selected,
            self._on_comprador_selected,
            "buyer_select_loading",
            "buyer_select_error",
            "No se pudo aplicar la selección de comprador.",
        )

    def _request_selector_selection(
        self,
        selected: dict[str, Any] | None,
        handler: Callable[[dict[str, Any] | None], None],
        loading_attr: str,
        error_attr: str,
        fallback_error: str,
    ) -> None:
        if getattr(self, loading_attr, False):
            return
        setattr(self, loading_attr, True)
        setattr(self, error_attr, None)
        self._render()
        self.page.run_thread(
            lambda: self._run_selector_selection(
                selected, handler, loading_attr, error_attr, fallback_error
            )
        )

    def _run_selector_selection(
        self,
        selected: dict[str, Any] | None,
        handler: Callable[[dict[str, Any] | None], None],
        loading_attr: str,
        error_attr: str,
        fallback_error: str,
    ) -> None:
        try:
            handler(selected)
        except Exception as exc:
            setattr(self, error_attr, str(exc) or fallback_error)
        finally:
            setattr(self, loading_attr, False)
            self._render()

    def _on_reserva_selected(self, selected: dict[str, Any] | None) -> None:
        self.state.id_reserva_venta = None
        self.state.version_registro = None
        self.state.texto_visual_reserva = None
        self.state.reserva_visible_data = {}
        self._reset_reservation_detail_diagnostics()
        self.reserva_select_error = None
        if selected is not None:
            self.state.origen = "RESERVA"
            self.state.id_reserva_venta = _safe_int(selected.get("id_reserva_venta"))
            self.state.version_registro = _safe_int(selected.get("version_registro"))
            codigo = self._display_or_none(selected.get("codigo_reserva"))
            estado = self._display_or_none(selected.get("estado")) or self._display_or_none(selected.get("estado_reserva"))
            objetos = self._display_or_none(selected.get("objeto")) or self._display_or_none(selected.get("objetos"))
            compradores = self._display_or_none(selected.get("comprador")) or self._display_or_none(selected.get("compradores"))
            self.state.texto_visual_reserva = selected.get("texto_visual") or " — ".join(part for part in [codigo, estado, objetos, compradores] if part) or "Reserva seleccionada"
            enriched_selected, detail_warning = self._enriched_reservation_payload(selected)
            self.state.version_registro = _safe_int(enriched_selected.get("version_registro")) or self.state.version_registro
            objetos = self._display_or_none(enriched_selected.get("objeto")) or self._display_or_none(enriched_selected.get("objetos")) or objetos
            compradores = (
                self._display_or_none(enriched_selected.get("comprador"))
                or self._display_or_none(enriched_selected.get("compradores"))
                or self._display_or_none(enriched_selected.get("participaciones"))
                or compradores
            )
            self._preload_reservation_context(enriched_selected)
            compradores_warning = self._reservation_buyers_preload_warning()
            self.state.reserva_visible_data = {
                "codigo": codigo or self._display_or_none(enriched_selected.get("codigo_reserva")),
                "estado": estado or self._display_or_none(enriched_selected.get("estado")) or self._display_or_none(enriched_selected.get("estado_reserva")),
                "fecha": self._display_or_none(enriched_selected.get("fecha")) or self._display_or_none(enriched_selected.get("fecha_reserva")),
                "vencimiento": self._display_or_none(enriched_selected.get("vencimiento")) or self._display_or_none(enriched_selected.get("fecha_vencimiento")),
                "objetos": objetos,
                "compradores": compradores,
                "moneda": self._display_or_none(self._reservation_first_present(enriched_selected, ("moneda", "codigo_moneda"))),
                "importe": self._display_or_none(self._reservation_first_present(enriched_selected, ("importe", "precio_reservado", "importe_reserva", "precio_total", "monto"))),
                "detalle_warning": detail_warning,
                "compradores_warning": compradores_warning,
                "precarga_source": enriched_selected.get("precarga_source") or "listado_parcial",
            }
            self.state.reserva_visible_data["compradores_warning"] = self._reservation_buyers_preload_warning()
        else:
            self.state.objetos.clear()
            self.state.compradores.clear()
            self._reset_reservation_detail_diagnostics()
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
                self._request_plan_payment_preview_before_next("PREVIEW_PLAN_PAGO")
                return
        elif self.state.pantalla_actual == "PLAN_ANTICIPO":
            self.state.pantalla_actual = "PLAN_TRAMOS"
        elif self.state.pantalla_actual == "PLAN_TRAMOS":
            self.state.pantalla_actual = "PLAN_RESUMEN"
        elif self.state.pantalla_actual == "PLAN_RESUMEN":
            self._request_plan_payment_preview_before_next("PREVIEW_PLAN_PAGO")
            return
        elif self.state.pantalla_actual == "PREVIEW_PLAN_PAGO":
            if self.state.preview_stale:
                self.state.preview_error = "El preview está desactualizado. Volvé a la edición del plan y avanzá con Siguiente para recalcularlo."
                self._render()
                return
            self.state.pantalla_actual = "REVISION_GENERAL"
        self._render()

    def _previous_step(self, _: ft.ControlEvent | None = None) -> None:
        if self.state.pantalla_actual == "ORIGEN":
            return
        if self.state.pantalla_actual == "SELECCIONAR_RESERVA":
            self.state.pantalla_actual = "ORIGEN"
        elif self.state.pantalla_actual == "PLAN_TRAMO_FORM":
            self._clear_installment_form_state()
            self.state.pantalla_actual = "PLAN_TRAMOS"
        elif self.state.pantalla_actual == "PLAN_TRAMOS":
            self.state.pantalla_actual = "PLAN_ANTICIPO"
        elif self.state.pantalla_actual == "PLAN_RESUMEN":
            self.state.pantalla_actual = "PLAN_TRAMOS"
        elif self.state.pantalla_actual == "PREVIEW_PLAN_PAGO" and self.state.forma_pago == "FINANCIADO":
            self.state.pantalla_actual = "PLAN_RESUMEN"
        elif self.state.pantalla_actual == "PREVIEW_PLAN_PAGO":
            self.state.pantalla_actual = "FORMA_PAGO"
        elif self.state.pantalla_actual == "VENTA_CONFIRMADA":
            return
        elif self.state.pantalla_actual == "REVISION_GENERAL":
            self.state.pantalla_actual = "PREVIEW_PLAN_PAGO"
        elif self.state.pantalla_actual == "PLAN_ANTICIPO":
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
            return self.state.id_reserva_venta is not None and not self._reservation_state_blocks_next()
        if self.state.pantalla_actual == "DATOS_INICIALES":
            return self._has_valid_currency() and self.fecha_venta_error is None
        if self.state.pantalla_actual == "OBJETOS":
            if not self._has_valid_currency():
                return False
            return bool(self.state.objetos) and all(
                _parse_money_decimal(objeto.precio_asignado) is not None for objeto in self.state.objetos
            )
        if self.state.pantalla_actual == "COMPRADORES":
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
            return self._installments_can_advance()
        if self.state.pantalla_actual == "PLAN_RESUMEN":
            return self._financed_plan_difference() == Decimal("0")
        if self.state.pantalla_actual == "PREVIEW_PLAN_PAGO":
            return self.state.preview_data is not None and not self.state.preview_stale
        if self.state.pantalla_actual == "REVISION_GENERAL":
            return self._general_review_is_valid()
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
            if self.state.pantalla_actual == "REVISION_GENERAL":
                self.next_button.disabled = self.state.confirm_loading or self.state.preview_loading or not self._can_confirm_sale()
            else:
                self.next_button.disabled = self.state.confirm_loading or self.state.preview_loading or not self._can_advance()

    def _select_payment_method(self, payment_method: FormaPagoWizard) -> None:
        if payment_method not in {"CONTADO", "FINANCIADO"}:
            return
        self.state.forma_pago = payment_method
        self._mark_plan_preview_stale()
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
        self._mark_plan_preview_stale()
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
            self._mark_plan_preview_stale()
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
        self._mark_plan_preview_stale()
        if not has_advance:
            self.state.importe_anticipo_error = None
            self.state.fecha_anticipo_error = None
        else:
            self._validate_advance_state()
        self._render()

    def _on_importe_anticipo_change(self, event: ft.ControlEvent) -> None:
        self.state.importe_anticipo = str(event.control.value or "")
        self._mark_plan_preview_stale()
        self._validate_advance_amount()
        self._sync_importe_anticipo_feedback()
        self._sync_advance_visual_amounts()
        self._refresh_navigation_controls()
        self.page.update()

    def _on_importe_anticipo_commit(self, event: ft.ControlEvent) -> None:
        self.state.importe_anticipo = str(event.control.value or self.state.importe_anticipo or "")
        parsed = self._validate_advance_amount()
        if parsed is not None:
            self.state.importe_anticipo = _format_money(parsed)
            event.control.value = self.state.importe_anticipo
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
        self._mark_plan_preview_stale()
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
            self._mark_plan_preview_stale()
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
        validation_error = _money_amount_validation_error(
            raw_value,
            empty_message="El importe anticipo es requerido.",
            invalid_message="El importe debe ser un número finito mayor que 0.",
        )
        if validation_error is not None:
            self.state.importe_anticipo_error = validation_error
            return None
        parsed = _parse_money_decimal(raw_value)
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
        parsed = _parse_money_decimal(self.state.importe_anticipo)
        if parsed is None or parsed > self._objects_total():
            return Decimal("0")
        return parsed

    def _capital_pending_after_advance(self) -> Decimal:
        return self._objects_total() - self._valid_advance_amount_or_zero()

    def _advance_status(self) -> str:
        if not self.state.tiene_anticipo:
            return "No"
        parsed = _parse_money_decimal(self.state.importe_anticipo)
        if parsed is None:
            return "importe pendiente"
        return self._format_money_with_currency(parsed)

    def _sync_importe_anticipo_feedback(self) -> None:
        if self.state.importe_anticipo_error is not None:
            self.importe_anticipo_feedback.value = self.state.importe_anticipo_error
            self.importe_anticipo_feedback.color = ft.Colors.RED_700
            return
        self.importe_anticipo_feedback.value = "Ingresá un importe mayor que 0, con máximo 2 decimales, y menor o igual al total derivado."
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
        self.tramo_tasa_interes_field.value = self.state.tramo_tasa_interes_value
        self.tramo_codigo_indice_visual_field.value = self.state.tramo_codigo_indice_visual_value
        self.tramo_id_indice_financiero_field.value = self.state.tramo_id_indice_financiero_value
        self.tramo_fecha_base_indice_field.value = self._installment_index_base_date_display_value()
        self.tramo_valor_base_indice_field.value = self.state.tramo_valor_base_indice_value
        self.refuerzo_cantidad_field.value = self.state.refuerzo_cantidad_value
        self._sync_tramo_capital_feedback()
        self._sync_tramo_cantidad_feedback()
        self._sync_tramo_fecha_feedback()
        self._sync_tramo_tasa_interes_feedback()
        self._sync_tramo_id_indice_financiero_feedback()
        self._sync_tramo_fecha_base_indice_feedback()
        self._sync_tramo_valor_base_indice_feedback()
        self._sync_refuerzo_cantidad_feedback()
        self._sync_refuerzo_numero_feedback()
        self._sync_installment_estimate_feedback()

    def _on_tramo_capital_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_capital_value = str(event.control.value or "")
        self.state.tramo_capital_error = None
        self._sync_installment_estimate_feedback()
        self.page.update()

    def _on_tramo_capital_commit(self, event: ft.ControlEvent) -> None:
        self.state.tramo_capital_value = str(event.control.value or self.state.tramo_capital_value or "")
        parsed = _parse_money_decimal(self.state.tramo_capital_value)
        if parsed is not None:
            self.state.tramo_capital_value = _format_money(parsed)
            event.control.value = self.state.tramo_capital_value
        self._sync_installment_estimate_feedback()
        self.page.update()

    def _on_tramo_cantidad_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_cantidad_cuotas_value = str(event.control.value or "")
        self.state.tramo_cantidad_error = None
        self.state.refuerzo_cantidad_error = None
        self.state.refuerzo_numero_error = None
        self._discard_reinforcement_locations_outside_effective_duration()
        self._sync_installment_estimate_feedback()
        self.page.update()

    def _on_tramo_fecha_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_fecha_display = str(event.control.value or "")
        self.state.tramo_fecha_iso = ""
        self.state.tramo_fecha_error = None

    def _select_installment_liquidation_method(self, method: MetodoLiquidacionTramoWizard) -> None:
        previous_method = self.state.tramo_metodo_liquidacion
        if previous_method == method:
            return
        self.state.tramo_metodo_liquidacion = method
        if previous_method == "INTERES_DIRECTO" or method != "INTERES_DIRECTO":
            self._clear_installment_interest_fields()
        if previous_method == "INDEXACION" or method != "INDEXACION":
            self._clear_installment_index_fields()
        if method == "INTERES_DIRECTO":
            self._clear_installment_reinforcements()
        self._render()

    def _on_tramo_tasa_interes_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_tasa_interes_value = str(event.control.value or "")
        self.state.tramo_tasa_interes_error = None
        self._sync_installment_estimate_feedback()
        self.page.update()

    def _on_tramo_codigo_indice_visual_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_codigo_indice_visual_value = str(event.control.value or "")

    def _on_tramo_id_indice_financiero_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_id_indice_financiero_value = str(event.control.value or "")
        self.state.tramo_id_indice_financiero_error = None

    def _on_tramo_fecha_base_indice_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_fecha_base_indice_display = str(event.control.value or "")
        self.state.tramo_fecha_base_indice_iso = ""
        self.state.tramo_fecha_base_indice_error = None

    def _on_tramo_valor_base_indice_change(self, event: ft.ControlEvent) -> None:
        self.state.tramo_valor_base_indice_value = str(event.control.value or "")
        self.state.tramo_valor_base_indice_error = None

    def _on_refuerzo_cantidad_change(self, event: ft.ControlEvent) -> None:
        new_value = str(event.control.value or "")
        if new_value != self.state.refuerzo_cantidad_value:
            self.state.refuerzo_cantidad_value = new_value
            self.state.refuerzo_cantidad_error = None
            self._clear_installment_reinforcement_locations()

    def _on_refuerzo_cantidad_commit(self, _: ft.ControlEvent) -> None:
        self._validate_reinforcement_count()
        self._discard_reinforcement_locations_outside_effective_duration()
        self._render()

    def _select_installment_reinforcements_usage(self, value: bool) -> None:
        if not self._installment_method_allows_reinforcements():
            self._clear_installment_reinforcements()
            self._render()
            return
        self.state.tramo_usa_refuerzos = value
        if not value:
            self._clear_installment_reinforcements()
        self._render()

    def _toggle_installment_reinforcement_position(self, number: int) -> None:
        reinforcement_count = self._validate_reinforcement_count()
        if reinforcement_count is None:
            self._render()
            return
        effective_duration = self._effective_duration_for_reinforcements(reinforcement_count)
        if number < 1 or number > effective_duration:
            self.state.refuerzo_numero_error = "La cuota seleccionada está fuera de las posiciones válidas."
            self._sync_refuerzo_numero_feedback()
            self.page.update()
            return
        existing_index = next(
            (
                index
                for index, reinforcement in enumerate(self.state.tramo_cuotas_refuerzo_draft)
                if reinforcement.numero_cuota == number
            ),
            None,
        )
        if existing_index is not None:
            self.state.tramo_cuotas_refuerzo_draft.pop(existing_index)
            self.state.refuerzo_numero_error = None
            self._render()
            return
        if len(self.state.tramo_cuotas_refuerzo_draft) >= reinforcement_count:
            self.state.refuerzo_numero_error = "Ya seleccionaste la cantidad de cuotas refuerzo definida."
            self._sync_refuerzo_numero_feedback()
            self.page.update()
            return
        self.state.tramo_cuotas_refuerzo_draft.append(
            CuotaRefuerzoWizardDraft(
                numero_cuota=number,
                etiqueta=f"Refuerzo cuota {number}",
                unidades_refuerzo="1.00",
            )
        )
        self.state.tramo_cuotas_refuerzo_draft.sort(key=lambda item: item.numero_cuota)
        self.state.refuerzo_numero_error = None
        self._render()

    def _remove_installment_reinforcement(self, index: int) -> None:
        if 0 <= index < len(self.state.tramo_cuotas_refuerzo_draft):
            self.state.tramo_cuotas_refuerzo_draft.pop(index)
            self.state.refuerzo_numero_error = None
            self._render()

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


    def _open_tramo_fecha_base_indice_picker(self, _: ft.ControlEvent | None = None) -> None:
        if not hasattr(ft, "DatePicker"):
            if self.state.tramo_fecha_base_indice_error is None:
                self.tramo_fecha_base_indice_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.tramo_fecha_base_indice_feedback.color = ft.Colors.AMBER_800
            self.page.update()
            return
        selected_date = _date_from_iso(self.state.tramo_fecha_base_indice_iso) or date.today()
        try:
            picker = ft.DatePicker(
                value=selected_date,
                first_date=date(1900, 1, 1),
                last_date=date(2100, 12, 31),
            )
            picker.on_change = self._on_tramo_fecha_base_indice_picker_change
            self.page.overlay.append(picker)
            picker.open = True
            self.page.update()
        except Exception:
            if self.state.tramo_fecha_base_indice_error is None:
                self.tramo_fecha_base_indice_feedback.value = "Selector calendario no disponible; ingresá la fecha manualmente en formato DD/MM/AAAA."
                self.tramo_fecha_base_indice_feedback.color = ft.Colors.AMBER_800
            self.page.update()

    def _on_tramo_fecha_base_indice_picker_change(self, event: ft.ControlEvent) -> None:
        selected_date = getattr(event.control, "value", None)
        if selected_date is None:
            return
        if isinstance(selected_date, datetime):
            selected_date = selected_date.date()
        if isinstance(selected_date, date):
            self.state.tramo_fecha_base_indice_iso = selected_date.isoformat()
            self.state.tramo_fecha_base_indice_display = _format_date_ar(self.state.tramo_fecha_base_indice_iso)
            self.tramo_fecha_base_indice_field.value = self.state.tramo_fecha_base_indice_display
            self.state.tramo_fecha_base_indice_error = None
            self._sync_tramo_fecha_base_indice_feedback()
            self.page.update()


    def _open_installment_form_step(self, _: ft.ControlEvent | None = None) -> None:
        self._clear_installment_form_state()
        self.state.pantalla_actual = "PLAN_TRAMO_FORM"
        self._render()

    def _cancel_installment_form_step(self, _: ft.ControlEvent | None = None) -> None:
        self._clear_installment_form_state()
        self.state.pantalla_actual = "PLAN_TRAMOS"
        self._render()

    def _add_installment_block(self, _: ft.ControlEvent | None = None) -> None:
        capital = self._validate_installment_capital()
        quantity = self._validate_installment_quantity()
        due_date_iso = self._validate_installment_date()
        liquidation_data = self._validate_installment_liquidation_method(quantity)
        reinforcement_data = self._validate_installment_reinforcements_for_save(quantity)
        if (
            capital is None
            or quantity is None
            or due_date_iso is None
            or liquidation_data is None
            or reinforcement_data is None
        ):
            self._render()
            return
        self._mark_plan_preview_stale()
        self.state.tramos_cuotas.append(
            TramoCuotasWizardDraft(
                importe_total_bloque=_format_decimal(capital),
                cantidad_cuotas=quantity,
                fecha_primer_vencimiento_iso=due_date_iso,
                fecha_primer_vencimiento_display=_format_date_ar(due_date_iso),
                metodo_liquidacion=self.state.tramo_metodo_liquidacion,
                cuotas_refuerzo=reinforcement_data,
                **liquidation_data,
            )
        )
        self._clear_installment_form_state()
        self.state.pantalla_actual = "PLAN_TRAMOS"
        self._render()

    def _remove_installment_block(self, index: int) -> None:
        if 0 <= index < len(self.state.tramos_cuotas):
            self.state.tramos_cuotas.pop(index)
            self._mark_plan_preview_stale()
            self._clear_installment_errors()
            self._render()

    def _validate_installment_capital(self) -> Decimal | None:
        raw_value = self.state.tramo_capital_value.strip()
        if not raw_value:
            self.state.tramo_capital_error = "El capital del tramo es requerido."
            return None
        validation_error = _money_amount_validation_error(
            raw_value,
            empty_message="El capital del tramo es requerido.",
            invalid_message="El capital del tramo debe ser un número finito mayor que 0.",
        )
        if validation_error is not None:
            self.state.tramo_capital_error = validation_error
            return None
        parsed = _parse_money_decimal(raw_value)
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

    def _validate_installment_liquidation_method(self, quantity: int | None) -> dict[str, str | None] | None:
        if self.state.tramo_metodo_liquidacion == "INTERES_DIRECTO":
            return self._validate_installment_direct_interest_fields(quantity)
        if self.state.tramo_metodo_liquidacion == "INDEXACION":
            return self._validate_installment_index_fields()
        self._clear_installment_interest_errors()
        self._clear_installment_index_errors()
        return {}

    def _validate_installment_direct_interest_fields(self, quantity: int | None) -> dict[str, str | None] | None:
        raw_rate = self.state.tramo_tasa_interes_value.strip()
        rate = _parse_decimal(raw_rate) if raw_rate else None

        if not raw_rate:
            self.state.tramo_tasa_interes_error = "La tasa periódica (%) es requerida."
        elif rate is None:
            self.state.tramo_tasa_interes_error = "La tasa periódica (%) debe ser un porcentaje mayor que 0."
        else:
            self.state.tramo_tasa_interes_error = None

        if self.state.tramo_tasa_interes_error is not None or quantity is None or rate is None:
            return None
        tasa_decimal = rate / Decimal("100")
        self._clear_installment_index_errors()
        return {
            "tasa_interes_directo_periodica": _format_rate_decimal_for_backend(
                tasa_decimal
            ),
            "cantidad_periodos": str(quantity),
        }

    def _validate_installment_index_fields(self) -> dict[str, str | None] | None:
        raw_index_id = self.state.tramo_id_indice_financiero_value.strip()
        raw_date = self.state.tramo_fecha_base_indice_display.strip()
        raw_base_value = self.state.tramo_valor_base_indice_value.strip()
        index_id = self._parse_positive_integer(raw_index_id) if raw_index_id else None
        parsed_date = _parse_date_ar_strict(raw_date) if raw_date else None
        base_value = _parse_decimal(raw_base_value) if raw_base_value else None

        if not raw_index_id:
            self.state.tramo_id_indice_financiero_error = "El ID índice financiero backend es requerido."
        elif index_id is None:
            self.state.tramo_id_indice_financiero_error = "El ID índice financiero backend debe ser un entero mayor que 0."
        else:
            self.state.tramo_id_indice_financiero_error = None

        if not raw_date:
            self.state.tramo_fecha_base_indice_error = "La fecha base índice es requerida."
        elif parsed_date is None:
            self.state.tramo_fecha_base_indice_error = "Fecha inválida. Usá formato DD/MM/AAAA."
            self.state.tramo_fecha_base_indice_iso = ""
        else:
            self.state.tramo_fecha_base_indice_error = None
            self.state.tramo_fecha_base_indice_iso = parsed_date
            self.state.tramo_fecha_base_indice_display = _format_date_ar(parsed_date)

        if not raw_base_value:
            self.state.tramo_valor_base_indice_error = "El valor base índice es requerido."
        elif base_value is None:
            self.state.tramo_valor_base_indice_error = "El valor base índice debe ser un número finito mayor que 0."
        else:
            self.state.tramo_valor_base_indice_error = None

        if (
            self.state.tramo_id_indice_financiero_error is not None
            or self.state.tramo_fecha_base_indice_error is not None
            or self.state.tramo_valor_base_indice_error is not None
        ):
            return None
        self._clear_installment_interest_errors()
        return {
            "id_indice_financiero": raw_index_id,
            "codigo_indice_visual": self.state.tramo_codigo_indice_visual_value.strip() or None,
            "fecha_base_indice_iso": self.state.tramo_fecha_base_indice_iso,
            "fecha_base_indice_display": self.state.tramo_fecha_base_indice_display,
            "valor_base_indice": raw_base_value,
        }

    def _validate_reinforcement_count(self, quantity: int | None = None) -> int | None:
        total_quantity = quantity if quantity is not None else self._current_installment_quantity_or_zero()
        raw_count = self.state.refuerzo_cantidad_value.strip()
        parsed_count = self._parse_positive_integer(raw_count) if raw_count else None
        if not raw_count:
            self.state.refuerzo_cantidad_error = "La cantidad de cuotas refuerzo es requerida."
            return None
        if parsed_count is None:
            self.state.refuerzo_cantidad_error = "La cantidad de cuotas refuerzo debe ser un entero mayor que 0."
            return None
        if total_quantity <= 0:
            self.state.refuerzo_cantidad_error = "Ingresá primero una cantidad total de cuotas válida para el tramo."
            return None
        if parsed_count >= total_quantity:
            self.state.refuerzo_cantidad_error = "La cantidad de refuerzos debe ser menor que la cantidad total de cuotas."
            return None
        self.state.refuerzo_cantidad_error = None
        return parsed_count

    def _current_reinforcement_count_or_none(self) -> int | None:
        total_quantity = self._current_installment_quantity_or_zero()
        raw_count = self.state.refuerzo_cantidad_value.strip()
        parsed_count = self._parse_positive_integer(raw_count) if raw_count else None
        if parsed_count is None or total_quantity <= 0 or parsed_count >= total_quantity:
            return None
        return parsed_count

    def _effective_duration_for_reinforcements(self, reinforcement_count: int, quantity: int | None = None) -> int:
        total_quantity = quantity if quantity is not None else self._current_installment_quantity_or_zero()
        return max(total_quantity - reinforcement_count, 0)

    def _validate_installment_reinforcements_for_save(
        self,
        quantity: int | None,
    ) -> list[CuotaRefuerzoWizardDraft] | None:
        if self.state.tramo_metodo_liquidacion == "INTERES_DIRECTO":
            if self.state.tramo_cuotas_refuerzo_draft or self.state.refuerzo_cantidad_value.strip():
                self.state.refuerzo_numero_error = "Interés directo no permite cuotas refuerzo en esta versión."
                return None
            self._clear_installment_reinforcements()
            return []
        if not self.state.tramo_usa_refuerzos:
            self._clear_installment_reinforcements()
            return []
        reinforcement_count = self._validate_reinforcement_count(quantity)
        if reinforcement_count is None:
            return None
        effective_duration = self._effective_duration_for_reinforcements(reinforcement_count, quantity)
        numbers = [item.numero_cuota for item in self.state.tramo_cuotas_refuerzo_draft]
        if len(numbers) != reinforcement_count:
            self.state.refuerzo_numero_error = "La cantidad de ubicaciones asignadas debe coincidir con la cantidad de refuerzos."
            return None
        if len(numbers) != len(set(numbers)):
            self.state.refuerzo_numero_error = "No puede haber cuotas refuerzo duplicadas."
            return None
        if any(number < 1 or number > effective_duration for number in numbers):
            self.state.refuerzo_numero_error = "Hay cuotas refuerzo fuera de la duración efectiva del tramo."
            return None
        self.state.refuerzo_numero_error = None
        return [
            CuotaRefuerzoWizardDraft(
                numero_cuota=item.numero_cuota,
                etiqueta=item.etiqueta.strip(),
                unidades_refuerzo="1.00",
            )
            for item in self.state.tramo_cuotas_refuerzo_draft
        ]

    def _sync_refuerzo_cantidad_feedback(self) -> None:
        if self.state.refuerzo_cantidad_error is not None:
            self.refuerzo_cantidad_feedback.value = self.state.refuerzo_cantidad_error
            self.refuerzo_cantidad_feedback.color = ft.Colors.RED_700
            return
        self.refuerzo_cantidad_feedback.value = "Debe ser un entero mayor que 0 y menor que la cantidad total de cuotas."
        self.refuerzo_cantidad_feedback.color = ft.Colors.BLUE_GREY_600

    def _sync_refuerzo_numero_feedback(self) -> None:
        if self.state.refuerzo_numero_error is not None:
            self.refuerzo_numero_feedback.value = self.state.refuerzo_numero_error
            self.refuerzo_numero_feedback.color = ft.Colors.RED_700
            return
        reinforcement_count = self._current_reinforcement_count_or_none()
        if reinforcement_count is None:
            self.refuerzo_numero_feedback.value = "Definí primero una cantidad válida de refuerzos."
        else:
            effective_duration = self._effective_duration_for_reinforcements(reinforcement_count)
            self.refuerzo_numero_feedback.value = f"Marcá hasta {reinforcement_count} cuotas entre 1 y {effective_duration}."
        self.refuerzo_numero_feedback.color = ft.Colors.BLUE_GREY_600

    def _selected_reinforcement_numbers_text(self) -> str:
        if not self.state.tramo_cuotas_refuerzo_draft:
            return "ninguna"
        ordered_numbers = sorted(item.numero_cuota for item in self.state.tramo_cuotas_refuerzo_draft)
        return ", ".join(f"cuota {number}" for number in ordered_numbers)

    def _clear_installment_reinforcement_locations(self) -> None:
        self.state.refuerzo_numero_cuota_value = ""
        self.state.refuerzo_etiqueta_value = ""
        self.state.refuerzo_numero_error = None
        self.state.tramo_cuotas_refuerzo_draft.clear()

    def _clear_installment_reinforcements(self) -> None:
        self.state.tramo_usa_refuerzos = False
        self.state.refuerzo_cantidad_value = ""
        self.state.refuerzo_cantidad_error = None
        self._clear_installment_reinforcement_locations()
        self.refuerzo_cantidad_field.value = ""

    def _discard_reinforcement_locations_outside_effective_duration(self) -> None:
        reinforcement_count = self._current_reinforcement_count_or_none()
        if reinforcement_count is None:
            self._clear_installment_reinforcement_locations()
            return
        effective_duration = self._effective_duration_for_reinforcements(reinforcement_count)
        self.state.tramo_cuotas_refuerzo_draft = [
            item
            for item in self.state.tramo_cuotas_refuerzo_draft[:reinforcement_count]
            if 1 <= item.numero_cuota <= effective_duration
        ]

    def _current_installment_quantity_or_zero(self) -> int:
        parsed = self._parse_positive_integer(self.state.tramo_cantidad_cuotas_value.strip())
        return parsed or 0

    def _installment_method_allows_reinforcements(self) -> bool:
        return self.state.tramo_metodo_liquidacion in {"SIN_INTERES", "INDEXACION"}

    @staticmethod
    def _parse_positive_integer(raw_value: str) -> int | None:
        try:
            parsed = int(raw_value)
        except ValueError:
            return None
        if str(parsed) != raw_value or parsed <= 0:
            return None
        return parsed

    def _clear_installment_form_state(self) -> None:
        self.state.tramo_capital_value = ""
        self.state.tramo_cantidad_cuotas_value = ""
        self.state.tramo_fecha_display = ""
        self.state.tramo_fecha_iso = ""
        self.state.tramo_metodo_liquidacion = "SIN_INTERES"
        self._clear_installment_reinforcements()
        self._clear_installment_interest_fields()
        self._clear_installment_index_fields()
        self._clear_installment_errors()
        self.tramo_capital_field.value = ""
        self.tramo_cantidad_field.value = ""
        self.tramo_fecha_field.value = ""

    def _clear_installment_errors(self) -> None:
        self.state.tramo_capital_error = None
        self.state.tramo_cantidad_error = None
        self.state.tramo_fecha_error = None
        self._clear_installment_interest_errors()
        self._clear_installment_index_errors()
        self.state.refuerzo_cantidad_error = None
        self.state.refuerzo_numero_error = None

    def _clear_installment_interest_fields(self) -> None:
        self.state.tramo_tasa_interes_value = ""
        self._clear_installment_interest_errors()
        self.tramo_tasa_interes_field.value = ""

    def _clear_installment_interest_errors(self) -> None:
        self.state.tramo_tasa_interes_error = None

    def _clear_installment_index_fields(self) -> None:
        self.state.tramo_id_indice_financiero_value = ""
        self.state.tramo_codigo_indice_visual_value = ""
        self.state.tramo_fecha_base_indice_display = ""
        self.state.tramo_fecha_base_indice_iso = ""
        self.state.tramo_valor_base_indice_value = ""
        self._clear_installment_index_errors()
        self.tramo_id_indice_financiero_field.value = ""
        self.tramo_codigo_indice_visual_field.value = ""
        self.tramo_fecha_base_indice_field.value = ""
        self.tramo_valor_base_indice_field.value = ""

    def _clear_installment_index_errors(self) -> None:
        self.state.tramo_id_indice_financiero_error = None
        self.state.tramo_fecha_base_indice_error = None
        self.state.tramo_valor_base_indice_error = None

    def _installment_date_display_value(self) -> str:
        if self.state.tramo_fecha_error is not None:
            return self.state.tramo_fecha_display
        return self.state.tramo_fecha_display or _format_date_ar(self.state.tramo_fecha_iso)

    def _installment_index_base_date_display_value(self) -> str:
        if self.state.tramo_fecha_base_indice_error is not None:
            return self.state.tramo_fecha_base_indice_display
        return self.state.tramo_fecha_base_indice_display or _format_date_ar(self.state.tramo_fecha_base_indice_iso)


    def _sync_installment_estimate_feedback(self) -> None:
        lines = self._installment_estimate_lines()
        if lines:
            self.tramo_cuota_estimada_feedback.value = "\n".join(lines)
            self.tramo_cuota_estimada_feedback.color = ft.Colors.BLUE_GREY_900
            return
        self.tramo_cuota_estimada_feedback.value = "Ingresá capital del tramo y cantidad de cuotas para ver una estimación simple."
        self.tramo_cuota_estimada_feedback.color = ft.Colors.BLUE_GREY_600

    def _installment_estimate_lines(self) -> list[str]:
        capital = _parse_money_decimal(self.state.tramo_capital_value)
        quantity = self._parse_positive_integer(self.state.tramo_cantidad_cuotas_value.strip())
        if capital is None or quantity is None or quantity <= 0:
            return []
        cuota_base = (capital / Decimal(quantity)).quantize(MONEY_DECIMAL_QUANTUM)
        if self.state.tramo_metodo_liquidacion == "INDEXACION":
            return [
                f"Cuota base estimada antes de actualización: {self._format_money_with_currency(cuota_base)}",
                "Estimación visual. El cálculo definitivo se validará al confirmar la venta.",
            ]
        if self.state.tramo_metodo_liquidacion == "INTERES_DIRECTO":
            return [
                f"Cuota base sin interés: {self._format_money_with_currency(cuota_base)}",
                "Estimación visual. El cálculo definitivo se validará al confirmar la venta.",
            ]
        return [f"Cuota base estimada: {self._format_money_with_currency(cuota_base)}"]

    def _sync_tramo_capital_feedback(self) -> None:
        if self.state.tramo_capital_error is not None:
            self.tramo_capital_feedback.value = self.state.tramo_capital_error
            self.tramo_capital_feedback.color = ft.Colors.RED_700
            return
        self.tramo_capital_feedback.value = "Podés asignar todo el capital restante o un valor menor, con máximo 2 decimales."
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

    def _sync_tramo_tasa_interes_feedback(self) -> None:
        if self.state.tramo_tasa_interes_error is not None:
            self.tramo_tasa_interes_feedback.value = self.state.tramo_tasa_interes_error
            self.tramo_tasa_interes_feedback.color = ft.Colors.RED_700
            return
        self.tramo_tasa_interes_feedback.value = "Ingresá un porcentaje mayor que 0. Ej: 6 para 6%."
        self.tramo_tasa_interes_feedback.color = ft.Colors.BLUE_GREY_600

    def _sync_tramo_id_indice_financiero_feedback(self) -> None:
        if self.state.tramo_id_indice_financiero_error is not None:
            self.tramo_id_indice_financiero_feedback.value = self.state.tramo_id_indice_financiero_error
            self.tramo_id_indice_financiero_feedback.color = ft.Colors.RED_700
            return
        self.tramo_id_indice_financiero_feedback.value = "Ingresá el identificador numérico del índice financiero."
        self.tramo_id_indice_financiero_feedback.color = ft.Colors.BLUE_GREY_600

    def _sync_tramo_fecha_base_indice_feedback(self) -> None:
        if self.state.tramo_fecha_base_indice_error is not None:
            self.tramo_fecha_base_indice_feedback.value = self.state.tramo_fecha_base_indice_error
            self.tramo_fecha_base_indice_feedback.color = ft.Colors.RED_700
            return
        self.tramo_fecha_base_indice_feedback.value = "Formato: DD/MM/AAAA"
        self.tramo_fecha_base_indice_feedback.color = ft.Colors.BLUE_GREY_600

    def _sync_tramo_valor_base_indice_feedback(self) -> None:
        if self.state.tramo_valor_base_indice_error is not None:
            self.tramo_valor_base_indice_feedback.value = self.state.tramo_valor_base_indice_error
            self.tramo_valor_base_indice_feedback.color = ft.Colors.RED_700
            return
        self.tramo_valor_base_indice_feedback.value = "Ingresá un valor numérico mayor que 0."
        self.tramo_valor_base_indice_feedback.color = ft.Colors.BLUE_GREY_600

    @staticmethod
    def _installment_liquidation_label(method: MetodoLiquidacionTramoWizard) -> str:
        labels = {
            "SIN_INTERES": "Cuotas fijas / sin interés",
            "INTERES_DIRECTO": "Interés directo",
            "INDEXACION": "Indexado por índice",
        }
        return labels[method]


    @staticmethod
    def _format_rate_decimal_as_percentage(value: str | None) -> str:
        parsed = _parse_decimal(value) if value else None
        if parsed is None:
            return "-"
        return f"{_format_decimal(parsed * Decimal('100'))}%"

    @staticmethod
    def _installment_liquidation_secondary_text(tramo: TramoCuotasWizardDraft) -> str:
        if tramo.metodo_liquidacion == "INTERES_DIRECTO":
            tasa = VentaCompletaWizardV3Prototype._format_rate_decimal_as_percentage(
                tramo.tasa_interes_directo_periodica
            )
            return f"Tasa: {tasa} — Períodos: {tramo.cantidad_periodos or tramo.cantidad_cuotas}"
        if tramo.metodo_liquidacion == "INDEXACION":
            index_label = tramo.codigo_indice_visual or f"ID {tramo.id_indice_financiero or '-'}"
            return f"Índice: {index_label} · fecha base: {tramo.fecha_base_indice_display or '-'}"
        return ""

    @staticmethod
    def _installment_reinforcements_list_text(tramo: TramoCuotasWizardDraft) -> str:
        if not tramo.cuotas_refuerzo:
            return ""
        ordered_numbers = sorted(item.numero_cuota for item in tramo.cuotas_refuerzo)
        if len(ordered_numbers) <= 3:
            numbers_text = ", ".join(f"cuota {number}" for number in ordered_numbers)
            return f"Refuerzos: {numbers_text}"
        return f"Refuerzos internos: {len(ordered_numbers)}"

    @staticmethod
    def _installment_reinforcements_duration_value(tramo: TramoCuotasWizardDraft) -> str:
        effective_duration = max(tramo.cantidad_cuotas - len(tramo.cuotas_refuerzo), 0)
        return f"{effective_duration} vencimientos"

    @staticmethod
    def _installment_reinforcements_duration_text(tramo: TramoCuotasWizardDraft) -> str:
        if not tramo.cuotas_refuerzo:
            return ""
        return f"Duración efectiva: {VentaCompletaWizardV3Prototype._installment_reinforcements_duration_value(tramo)}"

    def _capital_assigned_to_installments(self) -> Decimal:
        total = Decimal("0")
        for tramo in self.state.tramos_cuotas:
            parsed = _parse_money_decimal(tramo.importe_total_bloque)
            if parsed is not None:
                total += parsed
        return total

    def _capital_remaining_for_installments(self) -> Decimal:
        return self._capital_pending_after_advance() - self._capital_assigned_to_installments()

    def _financed_plan_total_assigned(self) -> Decimal:
        return self._valid_advance_amount_or_zero() + self._capital_assigned_to_installments()

    def _financed_plan_difference(self) -> Decimal:
        return self._objects_total() - self._financed_plan_total_assigned()

    def _installments_obligations_count(self) -> int:
        return sum(tramo.cantidad_cuotas for tramo in self.state.tramos_cuotas)

    def _installments_can_advance(self) -> bool:
        return bool(self.state.tramos_cuotas)

    def _currency_locked_by_objects(self) -> bool:
        return bool(self.state.objetos)

    def _has_valid_currency(self) -> bool:
        return self.state.moneda.strip().upper() in MONEDAS_PERMITIDAS

    def _currency_label(self) -> str:
        return self.state.moneda.strip().upper() or "sin moneda"

    def _format_money_with_currency(self, value: Decimal) -> str:
        return f"{self._currency_label()} {_format_money(value)}"

    def _on_objeto_selected(self, selected: dict[str, Any] | None) -> None:
        if selected is not None and not is_object_selectable(
            selected.get("estado"),
            selected.get("ocupacion_actual"),
            selected.get("venta_vigente") or selected.get("venta_conflictiva") or selected.get("venta_conflictiva_jerarquica"),
            selected.get("motivo_bloqueo"),
        ):
            self.objeto_seleccionado = None
            if self.objeto_selector is not None:
                self.objeto_selector.selected_panel.visible = False
            self._render()
            return
        self.object_select_error = None
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

    def _on_precio_objeto_commit(self, event: ft.ControlEvent) -> None:
        self.precio_objeto_value = str(event.control.value or self.precio_objeto_value or "")
        parsed = _parse_money_decimal(self.precio_objeto_value)
        if parsed is not None:
            self.precio_objeto_value = _format_money(parsed)
            event.control.value = self.precio_objeto_value
        self.precio_objeto_error = self._selected_price_validation_message(show_required=False)
        self.page.update()

    def _selected_price_validation_message(self, *, show_required: bool) -> str | None:
        raw_value = self.precio_objeto_value.strip()
        if not raw_value:
            return "precio_asignado es obligatorio." if show_required else None
        validation_error = _money_amount_validation_error(
            raw_value,
            empty_message="precio_asignado es obligatorio.",
            invalid_message="precio_asignado debe ser un decimal finito mayor que cero.",
        )
        if validation_error is not None:
            return validation_error
        if self.objeto_seleccionado is not None:
            if not is_object_selectable(
                self.objeto_seleccionado.get("estado"),
                self.objeto_seleccionado.get("ocupacion_actual"),
                self.objeto_seleccionado.get("venta_vigente") or self.objeto_seleccionado.get("venta_conflictiva") or self.objeto_seleccionado.get("venta_conflictiva_jerarquica"),
                self.objeto_seleccionado.get("motivo_bloqueo"),
            ):
                return object_selection_warning(
                    self.objeto_seleccionado.get("estado"),
                    self.objeto_seleccionado.get("ocupacion_actual"),
                    self.objeto_seleccionado.get("venta_vigente") or self.objeto_seleccionado.get("venta_conflictiva") or self.objeto_seleccionado.get("venta_conflictiva_jerarquica"),
                    self.objeto_seleccionado.get("motivo_bloqueo"),
                ) or "El objeto no está disponible para esta venta."
            if self.objeto_seleccionado.get("source") != "backend" or not self.objeto_seleccionado.get("persisted", False):
                return "El objeto debe estar disponible y confirmado en el sistema."
        return None

    def _parse_selected_price(self) -> Decimal | None:
        return _parse_money_decimal(self.precio_objeto_value)

    def _is_duplicate_selected_object(self) -> bool:
        if self.objeto_seleccionado is None:
            return False
        return any(_same_object_payload(objeto, self.objeto_seleccionado) for objeto in self.state.objetos)

    def _add_selected_object(self, _: ft.ControlEvent | None = None) -> None:
        if self.objeto_seleccionado is None:
            return
        if not is_object_selectable(
            self.objeto_seleccionado.get("estado"),
            self.objeto_seleccionado.get("ocupacion_actual"),
            self.objeto_seleccionado.get("venta_vigente") or self.objeto_seleccionado.get("venta_conflictiva") or self.objeto_seleccionado.get("venta_conflictiva_jerarquica"),
            self.objeto_seleccionado.get("motivo_bloqueo"),
        ):
            self.precio_objeto_error = object_selection_warning(
                self.objeto_seleccionado.get("estado"),
                self.objeto_seleccionado.get("ocupacion_actual"),
                self.objeto_seleccionado.get("venta_vigente") or self.objeto_seleccionado.get("venta_conflictiva") or self.objeto_seleccionado.get("venta_conflictiva_jerarquica"),
                self.objeto_seleccionado.get("motivo_bloqueo"),
            ) or "El objeto no está disponible para esta venta."
            self._render()
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
        self._mark_plan_preview_stale()
        self.state.objetos.append(
            ObjetoVentaWizardDraft(
                tipo_objeto=tipo_objeto,
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                texto_visual=str(self.objeto_seleccionado.get("texto_visual") or "-"),
                precio_asignado=_format_decimal(precio),
                source=str(self.objeto_seleccionado.get("source") or "backend"),
                persisted=bool(self.objeto_seleccionado.get("persisted", False)),
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
            self._mark_plan_preview_stale()
        self._render()

    def _on_reservation_object_price_change(self, index: int, event: ft.ControlEvent) -> None:
        if 0 <= index < len(self.state.objetos):
            self.state.objetos[index].precio_asignado = str(event.control.value or "")
            self._mark_plan_preview_stale()
            self._refresh_navigation_controls()

    def _on_reservation_object_price_blur(self, index: int, event: ft.ControlEvent) -> None:
        if 0 <= index < len(self.state.objetos):
            raw_value = str(event.control.value or self.state.objetos[index].precio_asignado or "")
            parsed = _parse_money_decimal(raw_value)
            formatted_value = _format_decimal(parsed) if parsed is not None else raw_value
            self.state.objetos[index].precio_asignado = formatted_value
            event.control.value = formatted_value
            self._mark_plan_preview_stale()
        self._refresh_navigation_controls()
        self.page.update()

    def _on_manual_buyer_id_change(self, event: ft.ControlEvent) -> None:
        self.manual_buyer_id_value = str(event.control.value or "")

    def _on_manual_buyer_text_change(self, event: ft.ControlEvent) -> None:
        self.manual_buyer_text_value = str(event.control.value or "")

    def _on_manual_buyer_role_change(self, event: ft.ControlEvent) -> None:
        self.manual_buyer_role_value = str(event.control.value or "")

    def _on_manual_buyer_percentage_change(self, event: ft.ControlEvent) -> None:
        self.manual_buyer_percentage_value = str(event.control.value or "")

    def _manual_buyer_validation_message(self) -> str | None:
        person_id = self.manual_buyer_id_value.strip()
        if not person_id.isdigit() or int(person_id) <= 0:
            return "Ingresá un id_persona persistido mayor que 0."
        if any(comprador.id_persona == int(person_id) for comprador in self.state.compradores):
            return "Ese id_persona ya fue agregado como comprador."
        if not self.manual_buyer_text_value.strip():
            return "Ingresá un texto visual para reconocer el comprador persistido."
        role_id = self.manual_buyer_role_value.strip()
        if not role_id.isdigit() or int(role_id) <= 0:
            return "Ingresá un id_rol_participacion persistido mayor que 0."
        percentage = self.manual_buyer_percentage_value.strip()
        if percentage and _parse_percentage(percentage) is None:
            return "porcentaje_responsabilidad debe ser mayor que 0 y menor o igual que 100."
        return None

    def _add_manual_persisted_buyer(self, _: ft.ControlEvent | None = None) -> None:
        self.manual_buyer_id_value = str(self.manual_buyer_id_field.value or self.manual_buyer_id_value or "")
        self.manual_buyer_text_value = str(self.manual_buyer_text_field.value or self.manual_buyer_text_value or "")
        self.manual_buyer_role_value = str(self.manual_buyer_role_field.value or self.manual_buyer_role_value or "")
        self.manual_buyer_percentage_value = str(self.manual_buyer_percentage_field.value or self.manual_buyer_percentage_value or "")
        self.manual_buyer_error = self._manual_buyer_validation_message()
        if self.manual_buyer_error is not None:
            self._render()
            return
        percentage = self.manual_buyer_percentage_value.strip()
        parsed_percentage = _parse_percentage(percentage) if percentage else None
        self.state.compradores.append(
            CompradorWizardDraft(
                id_persona=int(self.manual_buyer_id_value.strip()),
                texto_visual=self.manual_buyer_text_value.strip(),
                porcentaje_responsabilidad=_format_decimal(parsed_percentage) if parsed_percentage is not None else "",
                id_rol_participacion=self.manual_buyer_role_value.strip(),
                source="manual",
                persisted=True,
            )
        )
        self._mark_plan_preview_stale()
        self.manual_buyer_id_value = ""
        self.manual_buyer_text_value = ""
        self.manual_buyer_role_value = ""
        self.manual_buyer_percentage_value = ""
        self.manual_buyer_id_field.value = ""
        self.manual_buyer_text_field.value = ""
        self.manual_buyer_role_field.value = ""
        self.manual_buyer_percentage_field.value = ""
        self.manual_buyer_error = None
        self._render()

    def _on_comprador_selected(self, selected: dict[str, Any] | None) -> None:
        self.buyer_select_error = None
        self.comprador_seleccionado = selected
        self.porcentaje_comprador_value = ""
        self.porcentaje_comprador_field.value = ""
        if self.rol_comprador_data is None:
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
        if self.rol_comprador_data is None:
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
        role_id = self._rol_comprador_id_resuelto()
        if not role_id:
            return self.rol_comprador_catalog_error or "No se encontró el rol comprador en el sistema."
        if not role_id.isdigit():
            return "El rol comprador debe estar resuelto con un ID técnico válido."
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
                id_rol_participacion=self._rol_comprador_id_resuelto(),
                source=str(self.comprador_seleccionado.get("source") or "backend"),
                persisted=bool(self.comprador_seleccionado.get("persisted", False)),
            )
        )
        self._mark_plan_preview_stale()
        self.comprador_seleccionado = None
        self.comprador_selector = None
        self.porcentaje_comprador_value = ""
        self.porcentaje_comprador_field.value = ""
        if self.rol_comprador_data is None:
            self.rol_comprador_value = ""
            self.rol_comprador_field.value = ""
        self.comprador_error = None
        self._render()

    def _remove_buyer(self, index: int) -> None:
        if 0 <= index < len(self.state.compradores):
            self.state.compradores.pop(index)
            self._mark_plan_preview_stale()
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
        self._mark_plan_preview_stale()
        self._render()

    def _objects_total(self) -> Decimal:
        total = Decimal("0")
        for objeto in self.state.objetos:
            parsed = _parse_money_decimal(objeto.precio_asignado)
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
        if self.state.origen == "RESERVA" and not self.state.compradores:
            return "La reserva seleccionada no aporta compradores/reservantes; no se inventan datos."
        if self.state.origen != "DIRECTA" and self.state.origen != "RESERVA":
            return "Agregá al menos un comprador para continuar."
        if not self.state.compradores:
            return "Agregá al menos un comprador para continuar."

        seen_ids: set[int] = set()
        for comprador in self.state.compradores:
            if comprador.id_persona in seen_ids:
                return "No se puede duplicar id_persona entre compradores."
            seen_ids.add(comprador.id_persona)
            if self.state.origen in {"DIRECTA", "RESERVA"} and not comprador.id_rol_participacion.strip():
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
            return "La responsabilidad total debe sumar 100%."
        if _format_decimal(total) != "100.00":
            return "La responsabilidad total debe sumar 100%."
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
        return self.state.texto_visual_reserva or "pendiente"

    @staticmethod
    def _display_or_none(value: Any) -> str | None:
        text = VentaCompletaWizardV3Prototype._visible_join(value)
        return text or None

    def _reservation_state_blocks_next(self) -> bool:
        estado = str(self.state.reserva_visible_data.get("estado") or "").strip().upper()
        if not estado:
            return False
        valid_states = {"VIGENTE", "ACTIVA", "CONFIRMADA", "RESERVADA"}
        invalid_markers = {"FINALIZADA", "CANCELADA", "ANULADA", "VENCIDA", "RECHAZADA", "CONFIRMADA_VENTA", "VENTA_CONFIRMADA"}
        return estado in invalid_markers and estado not in valid_states

    def _reservation_state_warning(self) -> str | None:
        if self.state.id_reserva_venta is None:
            return None
        estado = str(self.state.reserva_visible_data.get("estado") or "").strip().upper()
        if not estado:
            return "La reserva no informa estado; se permite continuar y el backend validará en una confirmación futura."
        if self._reservation_state_blocks_next():
            return f"La reserva tiene estado {estado}; no se puede avanzar desde este estado."
        valid_states = {"VIGENTE", "ACTIVA", "CONFIRMADA", "RESERVADA"}
        if estado not in valid_states:
            return f"Estado {estado} no reconocido como válido por la UI; se permite continuar y el backend validará en una confirmación futura."
        return None

    def _buyers_flow_status(self) -> str:
        if self.state.origen == "RESERVA":
            if self.state.compradores:
                return f"{len(self.state.compradores)} heredados de reserva"
            return "pendiente" if self.state.id_reserva_venta is None else "sin compradores heredados"
        return str(len(self.state.compradores))

    def _payment_method_status(self) -> str:
        if self.state.forma_pago == "CONTADO":
            return "CONTADO"
        if self.state.forma_pago == "FINANCIADO":
            return "FINANCIADO"
        return "pendiente"

    def _review_flow_status(self) -> str:
        if self.state.pantalla_actual == "VENTA_CONFIRMADA":
            return "venta confirmada"
        if self.state.pantalla_actual == "REVISION_GENERAL" and self._general_review_is_valid():
            return "lista para confirmar"
        if self.state.pantalla_actual == "PREVIEW_PLAN_PAGO" and self.state.preview_data is not None and not self.state.preview_stale:
            return "preview calculado"
        if self.state.preview_stale and self.state.preview_data is not None:
            return "preview desactualizado"
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
                return "calcular preview del plan" if self._can_advance() else "cargar fecha de pago contado"
            if self.state.forma_pago == "FINANCIADO":
                return "cargar anticipo"
            return "elegir forma de pago"
        if self.state.pantalla_actual == "PLAN_ANTICIPO":
            return "cargar tramos de cuotas" if self._can_advance() else "completar anticipo"
        if self.state.pantalla_actual == "PLAN_TRAMOS":
            return "revisar plan financiado" if self._can_advance() else "cargar tramos de cuotas"
        if self.state.pantalla_actual == "PLAN_TRAMO_FORM":
            return "guardar tramo o cancelar"
        if self.state.pantalla_actual == "PLAN_RESUMEN":
            return "calcular preview del plan" if self._can_advance() else "ajustar diferencia del plan"
        if self.state.pantalla_actual == "PREVIEW_PLAN_PAGO":
            return "revisión general de venta" if self._can_advance() else "recalcular preview del plan"
        if self.state.pantalla_actual == "REVISION_GENERAL":
            return "confirmar venta" if self._can_confirm_sale() else "resolver pendientes de revisión"
        if self.state.pantalla_actual == "VENTA_CONFIRMADA":
            return "venta persistida con detalle integral read-only"
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


def _format_date_ar(iso_date: Any) -> str:
    if isinstance(iso_date, datetime):
        return iso_date.strftime("%d/%m/%Y")
    if isinstance(iso_date, date):
        return iso_date.strftime("%d/%m/%Y")
    text = str(iso_date or "").strip()
    if not text:
        return ""
    normalized = text.split("T", 1)[0]
    try:
        return datetime.strptime(normalized, "%Y-%m-%d").strftime("%d/%m/%Y")
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


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    days_by_month = [31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(value.day, days_by_month[month - 1])
    return date(year, month, day)


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _parse_decimal(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value or "").strip())
        if not parsed.is_finite() or parsed <= 0:
            return None
    except (InvalidOperation, ValueError):
        return None
    return parsed


def _has_max_two_decimal_places(value: Decimal) -> bool:
    return value.as_tuple().exponent >= -2


def _normalize_money_text(value: Any) -> str | None:
    text = str(value or "").strip().replace(" ", "")
    if not text:
        return ""
    if text[0] in "+-":
        return None
    if any(character not in "0123456789.," for character in text):
        return None

    has_comma = "," in text
    has_dot = "." in text
    if has_comma:
        if text.count(",") > 1:
            return None
        integer_part, decimal_part = text.split(",", 1)
        if decimal_part and not decimal_part.isdigit():
            return None
        integer_digits = integer_part.replace(".", "")
        if not integer_digits.isdigit():
            return None
        return f"{integer_digits}.{decimal_part}" if decimal_part else integer_digits

    if has_dot:
        parts = text.split(".")
        if any(not part.isdigit() for part in parts):
            return None
        if len(parts) > 2:
            if any(len(part) != 3 for part in parts[1:]):
                return None
            return "".join(parts)
        integer_part, suffix = parts
        if len(suffix) == 3 and len(integer_part) <= 3:
            return integer_part + suffix
        return text

    if not text.isdigit():
        return None
    return text


def _parse_money_decimal(value: Any) -> Decimal | None:
    normalized = _normalize_money_text(value)
    if not normalized:
        return None
    try:
        parsed = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite() or parsed <= 0 or not _has_max_two_decimal_places(parsed):
        return None
    return parsed.quantize(MONEY_DECIMAL_QUANTUM)


def _money_amount_validation_error(raw_value: str, *, empty_message: str, invalid_message: str) -> str | None:
    if not raw_value:
        return empty_message
    normalized = _normalize_money_text(raw_value)
    if not normalized:
        return invalid_message
    try:
        parsed = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return invalid_message
    if not parsed.is_finite() or parsed <= 0:
        return invalid_message
    if not _has_max_two_decimal_places(parsed):
        return MONEY_PRECISION_ERROR
    return None


def _parse_percentage(value: Any) -> Decimal | None:
    parsed = _parse_decimal(value)
    if parsed is None or parsed > Decimal("100"):
        return None
    return parsed


def _format_decimal(value: Decimal) -> str:
    return format(value.quantize(MONEY_DECIMAL_QUANTUM), "f")


def _format_rate_decimal_for_backend(value: Decimal) -> str:
    two_decimal_value = value.quantize(Decimal("0.01"))
    if value == two_decimal_value:
        return format(two_decimal_value, "f")
    return format(value.normalize(), "f")


def _parse_money_display_decimal(value: Any) -> Decimal | None:
    if isinstance(value, Decimal):
        parsed = value
    else:
        raw_text = str(value or "").strip()
        if not raw_text:
            return None
        sign = ""
        if raw_text[0] == "-":
            sign = "-"
            raw_text = raw_text[1:]
        normalized = _normalize_money_text(raw_text)
        if not normalized:
            return None
        try:
            parsed = Decimal(f"{sign}{normalized}")
        except (InvalidOperation, ValueError):
            return None
    if not parsed.is_finite():
        return None
    return parsed.quantize(MONEY_DECIMAL_QUANTUM)


def _format_money(value: Any) -> str:
    parsed = _parse_money_display_decimal(value)
    if parsed is None:
        return str(value or "-")
    sign = "-" if parsed < Decimal("0") else ""
    integer_part, decimal_part = _format_decimal(abs(parsed)).split(".")
    groups: list[str] = []
    while integer_part:
        groups.append(integer_part[-3:])
        integer_part = integer_part[:-3]
    return f"{sign}{'.'.join(reversed(groups))},{decimal_part}"


def _object_id_label_value(payload: dict[str, Any]) -> tuple[str, Any]:
    if payload.get("tipo_objeto") == "UNIDAD_FUNCIONAL":
        return "id_unidad_funcional", payload.get("id_unidad_funcional")
    return "id_inmueble", payload.get("id_inmueble")


def _safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _flow_info_row(label: str, value: Any, *, value_no_wrap: bool = True) -> ft.Control:
    value_control: ft.Control
    if isinstance(value, ft.Control):
        value_control = value
    else:
        display_value = str(value if value not in (None, "") else "-")
        value_control = ft.Text(
            display_value,
            color=ft.Colors.BLUE_GREY_900,
            expand=True,
            no_wrap=value_no_wrap,
        )
    return ft.Row(
        controls=[
            ft.Container(
                width=104,
                content=ft.Text(
                    f"{label}:",
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.BLUE_GREY_700,
                    no_wrap=True,
                ),
            ),
            value_control,
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.START,
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


def _control_texts(control: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(control, list):
        for child in control:
            texts.extend(_control_texts(child))
        return texts
    for attr in ("value", "text"):
        value = getattr(control, attr, None)
        if isinstance(value, str):
            texts.append(value)
    content = getattr(control, "content", None)
    if content is not None:
        texts.extend(_control_texts(content))
    controls = getattr(control, "controls", None)
    if isinstance(controls, list):
        for child in controls:
            texts.extend(_control_texts(child))
    rows = getattr(control, "rows", None)
    if isinstance(rows, list):
        for row in rows:
            texts.extend(_control_texts(row))
    cells = getattr(control, "cells", None)
    if isinstance(cells, list):
        for cell in cells:
            texts.extend(_control_texts(cell))
    return texts


def _run_self_test() -> None:
    class TestWizard(VentaCompletaWizardV3Prototype):
        def _render(self) -> None:  # type: ignore[override]
            return None

    wizard = TestWizard(page=None)  # type: ignore[arg-type]
    wizard.state.origen = "RESERVA"
    wizard.state.pantalla_actual = "VENTA_CONFIRMADA"
    wizard.state.id_reserva_venta = 77
    wizard.state.version_registro = 3
    wizard.state.texto_visual_reserva = "Reserva R-77"
    wizard.state.reserva_visible_data = {"codigo": "R-77", "estado": "VIGENTE"}
    wizard.state.objetos.append(
        ObjetoVentaWizardDraft(
            tipo_objeto="INMUEBLE",
            id_inmueble=10,
            id_unidad_funcional=None,
            texto_visual="Inmueble 10",
            precio_asignado="1000.00",
            persisted=True,
            heredado_reserva=True,
        )
    )
    wizard.state.compradores.append(
        CompradorWizardDraft(
            id_persona=20,
            texto_visual="Comprador 20",
            porcentaje_responsabilidad="100.00",
            id_rol_participacion="1",
            persisted=True,
            heredado_reserva=True,
        )
    )
    wizard.state.preview_data = {"preview": True}
    wizard.state.preview_stale = False
    wizard.state.confirm_data = {"venta": {"id_venta": 555}}
    wizard.state.confirm_error = "error anterior"
    wizard.state.confirm_status_code = 201
    wizard.state.confirm_op_id = "11111111-1111-1111-1111-111111111111"
    wizard.state.confirm_payload_signature = "signature"
    wizard.state.confirm_payload = {"payload": True}
    wizard.state.confirm_endpoint = "POST /api/v1/reservas-venta/77/confirmar-venta-completa"
    wizard.state.confirm_error_details = {"detail": "technical"}
    wizard.state.detalle_venta_data = {"venta": {"id_venta": 555}}
    wizard.state.detalle_venta_error = "detalle anterior"
    wizard.state.detalle_venta_status_code = 200
    wizard.state.detalle_venta_requested_id = 555
    wizard.state.mostrar_datos_tecnicos = True
    wizard.objeto_seleccionado = {"tipo_objeto": "INMUEBLE", "id_inmueble": 10, "texto_visual": "Inmueble seleccionado"}
    wizard.precio_objeto_value = "1000.00"
    wizard.precio_objeto_field.value = "1000.00"
    wizard.precio_objeto_error = "error anterior"
    wizard.backend_object_records = [{"tipo_objeto": "INMUEBLE", "id_inmueble": 10}]
    wizard.backend_objects_loaded = True

    wizard._restart_wizard()

    assert wizard.state.pantalla_actual == "ORIGEN"
    assert wizard.state.origen is None
    assert wizard.state.id_reserva_venta is None
    assert wizard.state.version_registro is None
    assert wizard.state.reserva_visible_data == {}
    assert wizard.state.objetos == []
    assert wizard.state.compradores == []
    assert wizard.state.preview_data is None
    assert wizard.state.confirm_data is None
    assert wizard.state.confirm_error is None
    assert wizard.state.confirm_op_id is None
    assert wizard.state.confirm_payload_signature is None
    assert wizard.state.confirm_payload is None
    assert wizard.state.confirm_endpoint is None
    assert wizard.state.detalle_venta_data is None
    assert wizard.state.detalle_venta_requested_id is None
    assert wizard.state.mostrar_datos_tecnicos is False
    assert wizard.objeto_seleccionado is None
    assert wizard.precio_objeto_value == ""
    assert wizard.precio_objeto_field.value == ""
    assert wizard.precio_objeto_error is None
    assert wizard.backend_object_records == []
    assert wizard.backend_objects_loaded is False
    assert wizard._currency_locked_by_objects() is False
    assert "0" in _control_texts(wizard._object_count_status())

    direct_payload = {"codigo_venta": "VD-1", "objetos": [], "compradores": []}
    wizard.state.origen = "DIRECTA"
    assert wizard._ensure_confirm_op_id_for_payload(direct_payload) == wizard.state.confirm_op_id
    assert wizard.state.confirm_payload_signature == wizard._confirm_payload_signature(direct_payload)

    wizard.state.pantalla_actual = "VENTA_CONFIRMADA"
    wizard.state.forma_pago = "CONTADO"
    detalle_contado = {
        "venta": {"id_venta": 1, "codigo_venta": "VC-1", "estado_venta": "CONFIRMADA", "precio_total": "1000.00", "moneda": "ARS"},
        "compradores": [],
        "objetos": [],
        "plan_pago_v2": {"metodo_plan_pago": "PLAN_POR_BLOQUES", "tipo_plan": "FINANCIADO"},
        "obligaciones_financieras": [{"importe_total": "1000.00", "tipo_item_cronograma": "CUOTA"}],
    }
    assert wizard._confirmed_payment_method_label(
        detalle_contado["venta"],
        detalle_contado["plan_pago_v2"],
        detalle_contado,
        detalle_contado["obligaciones_financieras"],
    ) == "CONTADO"
    wizard.state.detalle_venta_data = detalle_contado
    confirmed_text = " ".join(_control_texts(wizard._build_confirmed_sale_detail_controls())).upper()
    panel_text = " ".join(text for section in wizard._build_flow_state_sections() for text in _control_texts(section)).upper()
    assert "CONTADO" in confirmed_text
    assert "FINANCIADO" not in confirmed_text
    assert "CONTADO" in panel_text
    assert "FINANCIADO" not in panel_text



    selectable_object = {
        "tipo_objeto": "INMUEBLE",
        "id_inmueble": 11,
        "estado": "DISPONIBLE",
        "ocupacion_actual": None,
        "texto_visual": "Inmueble libre",
        "source": "backend",
        "persisted": True,
    }
    blocked_object = {
        "tipo_objeto": "UNIDAD_FUNCIONAL",
        "id_unidad_funcional": 12,
        "estado": "DISPONIBLE",
        "ocupacion_actual": None,
        "venta_vigente": True,
        "motivo_bloqueo": VENTA_SELECTOR_BLOCK_REASON,
        "texto_visual": "UF vendida",
        "source": "backend",
        "persisted": True,
    }
    assert is_object_selectable(
        selectable_object["estado"],
        selectable_object["ocupacion_actual"],
        selectable_object.get("venta_vigente"),
        selectable_object.get("motivo_bloqueo"),
    ) is True
    assert is_object_selectable(
        blocked_object["estado"],
        blocked_object["ocupacion_actual"],
        blocked_object.get("venta_vigente"),
        blocked_object.get("motivo_bloqueo"),
    ) is False
    assert object_selection_warning(
        blocked_object["estado"],
        blocked_object["ocupacion_actual"],
        blocked_object.get("venta_vigente"),
        blocked_object.get("motivo_bloqueo"),
    ) == VENTA_SELECTOR_BLOCK_REASON



    class BatchWizard(TestWizard):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.batch_fetch_count = 0

        def _fetch_selector_active_ventas(self) -> list[dict[str, Any]]:  # type: ignore[override]
            self.batch_fetch_count += 1
            return [
                {
                    "id_venta": 900,
                    "codigo_venta": "V-INM-900",
                    "estado_venta": "confirmada",
                    "objetos_resumen": [{"id_inmueble": 20, "id_unidad_funcional": None}],
                },
                {
                    "id_venta": 901,
                    "codigo_venta": "V-UF-901",
                    "estado_venta": "activa",
                    "objetos_resumen": [{"id_inmueble": None, "id_unidad_funcional": 31}],
                },
            ]

    batch_wizard = BatchWizard(page=None)  # type: ignore[arg-type]
    hierarchy_records = batch_wizard._enrich_object_records_with_venta_conflicts([
        {"tipo_objeto": "INMUEBLE", "id_inmueble": 20, "estado": "DISPONIBLE"},
        {"tipo_objeto": "UNIDAD_FUNCIONAL", "id_unidad_funcional": 21, "id_inmueble": 20, "estado": "DISPONIBLE"},
        {"tipo_objeto": "INMUEBLE", "id_inmueble": 30, "estado": "DISPONIBLE"},
        {"tipo_objeto": "UNIDAD_FUNCIONAL", "id_unidad_funcional": 31, "id_inmueble": 30, "estado": "DISPONIBLE"},
        {"tipo_objeto": "INMUEBLE", "id_inmueble": 40, "estado": "DISPONIBLE"},
    ])
    direct_inmueble = hierarchy_records[0]
    unit_blocked_by_parent = hierarchy_records[1]
    inmueble_blocked_by_child = hierarchy_records[2]
    direct_unit = hierarchy_records[3]
    free_inmueble = hierarchy_records[4]
    assert batch_wizard.batch_fetch_count == 1
    assert direct_inmueble["motivo_bloqueo"] == VENTA_SELECTOR_BLOCK_REASON
    assert direct_unit["motivo_bloqueo"] == VENTA_SELECTOR_BLOCK_REASON
    assert unit_blocked_by_parent["motivo_bloqueo"] == VENTA_SELECTOR_RELATED_BLOCK_REASON
    assert unit_blocked_by_parent.get("venta_conflictiva_jerarquica") is not None
    assert object_selection_warning(
        unit_blocked_by_parent["estado"],
        unit_blocked_by_parent.get("ocupacion_actual"),
        unit_blocked_by_parent.get("venta_conflictiva_jerarquica"),
        unit_blocked_by_parent.get("motivo_bloqueo"),
    ) == VENTA_SELECTOR_RELATED_BLOCK_REASON
    assert inmueble_blocked_by_child["motivo_bloqueo"] == VENTA_SELECTOR_RELATED_BLOCK_REASON
    assert inmueble_blocked_by_child.get("venta_conflictiva_jerarquica") is not None
    assert is_object_selectable(
        inmueble_blocked_by_child["estado"],
        inmueble_blocked_by_child.get("ocupacion_actual"),
        inmueble_blocked_by_child.get("venta_conflictiva_jerarquica"),
        inmueble_blocked_by_child.get("motivo_bloqueo"),
    ) is False
    assert free_inmueble.get("motivo_bloqueo") in (None, "")
    assert is_object_selectable(
        free_inmueble["estado"],
        free_inmueble.get("ocupacion_actual"),
        free_inmueble.get("venta_vigente"),
        free_inmueble.get("motivo_bloqueo"),
    ) is True

    wizard.state.objetos = [
        ObjetoVentaWizardDraft(
            tipo_objeto="INMUEBLE",
            id_inmueble=11,
            id_unidad_funcional=None,
            texto_visual="Inmueble libre",
            precio_asignado="1000.00",
            persisted=True,
        ),
        ObjetoVentaWizardDraft(
            tipo_objeto="UNIDAD_FUNCIONAL",
            id_inmueble=None,
            id_unidad_funcional=13,
            texto_visual="UF agregada",
            precio_asignado="500.00",
            persisted=True,
        ),
    ]
    marked = wizard._mark_current_sale_objects_in_selector_records([
        selectable_object,
        {
            "tipo_objeto": "UNIDAD_FUNCIONAL",
            "id_unidad_funcional": 13,
            "estado": "DISPONIBLE",
            "ocupacion_actual": None,
            "texto_visual": "UF agregada",
        },
        blocked_object,
    ])
    added_inmueble = marked[0]
    added_unidad = marked[1]
    still_sale_blocked = marked[2]
    assert added_inmueble["agregado_en_venta_actual"] is True
    assert added_inmueble["motivo_bloqueo"] == VENTA_SELECTOR_ALREADY_ADDED_REASON
    assert is_object_selectable(
        added_inmueble["estado"],
        added_inmueble["ocupacion_actual"],
        added_inmueble.get("venta_vigente"),
        added_inmueble.get("motivo_bloqueo"),
    ) is False
    assert object_selection_warning(
        added_inmueble["estado"],
        added_inmueble["ocupacion_actual"],
        added_inmueble.get("venta_vigente"),
        added_inmueble.get("motivo_bloqueo"),
    ) == VENTA_SELECTOR_ALREADY_ADDED_REASON
    assert added_unidad["agregado_en_venta_actual"] is True
    assert added_unidad["motivo_bloqueo"] == VENTA_SELECTOR_ALREADY_ADDED_REASON
    assert is_object_selectable(
        added_unidad["estado"],
        added_unidad["ocupacion_actual"],
        added_unidad.get("venta_vigente"),
        added_unidad.get("motivo_bloqueo"),
    ) is False
    assert still_sale_blocked["motivo_bloqueo"] == VENTA_SELECTOR_BLOCK_REASON

    friendly = wizard._confirm_error_message(
        ApiResult(
            success=False,
            status_code=409,
            error_code="RESERVA_YA_CONVERTIDA",
            error_message="La reserva ya fue convertida",
        )
    )
    assert friendly == "La reserva seleccionada ya fue convertida en venta."

    friendly_from_details = wizard._confirm_error_message(
        ApiResult(
            success=False,
            status_code=409,
            error_code="APPLICATION_ERROR",
            error_details={"errors": ["RESERVA_ALREADY_CONVERTED"]},
        )
    )
    assert friendly_from_details == "La reserva seleccionada ya fue convertida en venta."
    print("self-test ok")


def main(page: ft.Page) -> None:
    VentaCompletaWizardV3Prototype(page).run()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _run_self_test()
    elif hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
