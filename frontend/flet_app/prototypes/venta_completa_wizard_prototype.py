from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from typing import Any
from uuid import uuid4

import flet as ft
import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
LIQUIDATION_METHODS = ("SIN_INTERES", "INTERES_DIRECTO", "INDEXACION")
DEMO_INDICES = (
    ("1", "CAC_DEMO", "CAC demo"),
    ("2", "IPC_DEMO", "IPC demo"),
    ("3", "UVA_DEMO", "UVA demo"),
    ("4", "RIPTE_DEMO", "RIPTE demo"),
)
UNIQUE_BLOCKS = {"CONTADO", "ANTICIPO", "REFUERZO", "SALDO"}


@dataclass
class ObjetoVentaDraft:
    tipo_objeto: str = "TERRENO"
    id_objeto: str = ""
    descripcion: str = ""
    precio_asignado: str = ""


@dataclass
class CompradorDraft:
    id_persona: str = ""
    nombre: str = ""
    rol: str = "COMPRADOR"


@dataclass
class BloquePlanDraft:
    tipo_bloque: str = "ANTICIPO"
    etiqueta: str = ""
    importe: str = ""
    vencimiento: str = ""
    cantidad_cuotas: str = ""
    primer_vencimiento: str = ""
    periodicidad: str = "MENSUAL"
    metodo_liquidacion: str = "SIN_INTERES"
    tasa_interes_directo_periodica: str = ""
    cantidad_periodos: str = ""
    id_indice_financiero: str = ""
    codigo_indice_financiero: str = ""
    fecha_base_indice: str = ""
    valor_base_indice: str = ""


@dataclass
class WizardState:
    current_step: int = 0
    codigo_venta: str = ""
    fecha_venta: str = field(default_factory=lambda: _format_ar_date(date.today()))
    estado_venta: str = "BORRADOR"
    moneda: str = "ARS"
    observaciones: str = ""
    objetos: list[ObjetoVentaDraft] = field(default_factory=list)
    compradores: list[CompradorDraft] = field(default_factory=list)
    monto_total: str = ""
    condiciones_generales: str = ""
    tipo_pago: str = "FINANCIADO"
    bloques: list[BloquePlanDraft] = field(default_factory=list)
    preview_generado: bool = False
    confirmacion_simulada: bool = False
    base_url: str = DEFAULT_BASE_URL
    id_venta_backend: str = ""
    loading_backend: bool = False
    backend_error: str | None = None
    preview_response: dict[str, Any] | None = None
    preview_status_code: int | None = None
    preview_stale: bool = True
    generate_response: dict[str, Any] | None = None
    generate_status_code: int | None = None
    detalle_response: dict[str, Any] | None = None
    detalle_status_code: int | None = None


STEPS = [
    "Datos base",
    "Objetos",
    "Compradores",
    "Condiciones",
    "Plan Pago V2",
    "Revisión final",
]


class VentaCompletaWizardPrototype:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = WizardState(
            codigo_venta="VTA-BORRADOR-001",
            objetos=[
                ObjetoVentaDraft(
                    tipo_objeto="TERRENO",
                    id_objeto="1",
                    descripcion="Lote demo Manzana A - Parcela 12",
                    precio_asignado="12000000.00",
                )
            ],
            compradores=[CompradorDraft(id_persona="1", nombre="Comprador demo")],
            monto_total="12000000.00",
            bloques=[
                BloquePlanDraft(
                    tipo_bloque="ANTICIPO",
                    etiqueta="Anticipo",
                    importe="2000000.00",
                    vencimiento=_format_ar_date(date.today()),
                ),
                BloquePlanDraft(
                    tipo_bloque="TRAMO_CUOTAS",
                    etiqueta="Saldo financiado",
                    importe="10000000.00",
                    cantidad_cuotas="6",
                    primer_vencimiento=_format_ar_date(date.today()),
                    periodicidad="MENSUAL",
                ),
            ],
        )
        self.root = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)

    def build(self) -> ft.Control:
        self._render()
        return self.root

    def _render(self) -> None:
        self.root.controls = [
            ft.Text(
                "Prototipo — Alta guiada de venta completa",
                size=28,
                weight=ft.FontWeight.W_700,
            ),
            ft.Text(
                "Prototipo principal para probar el flujo completo de venta y Plan Pago V2 por bloques.",
                color=ft.Colors.BLUE_GREY_700,
            ),
            self._progress_header(),
            ft.Row(
                controls=[
                    ft.Container(content=self._step_content(), expand=3),
                    ft.Container(content=self._summary_panel(), expand=1),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=18,
            ),
            self._nav_buttons(),
        ]
        self.page.update()

    def _progress_header(self) -> ft.Control:
        controls: list[ft.Control] = []
        for index, label in enumerate(STEPS):
            complete, errors = self._step_status(index)
            is_current = index == self.state.current_step
            icon = (
                ft.Icons.CHECK_CIRCLE
                if complete
                else ft.Icons.ERROR_OUTLINE
                if errors
                else ft.Icons.RADIO_BUTTON_UNCHECKED
            )
            color = (
                ft.Colors.GREEN_700
                if complete
                else ft.Colors.RED_700
                if errors
                else ft.Colors.BLUE_GREY_500
            )
            controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon, size=14, color=color),
                            ft.Text(
                                label,
                                size=12,
                                weight=ft.FontWeight.W_700
                                if is_current
                                else ft.FontWeight.W_400,
                            ),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                    padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                    border=_border_all(
                        1.5 if is_current else 1,
                        ft.Colors.BLUE_300 if is_current else ft.Colors.BLUE_GREY_100,
                    ),
                    border_radius=14,
                )
            )
        return ft.Container(
            content=ft.Row(controls=controls, wrap=True, spacing=6, run_spacing=4),
            padding=ft.Padding(left=0, top=0, right=0, bottom=4),
        )

    def _step_content(self) -> ft.Control:
        step = self.state.current_step
        if step == 0:
            return self._step_datos_base()
        if step == 1:
            return self._step_objetos()
        if step == 2:
            return self._step_compradores()
        if step == 3:
            return self._step_condiciones()
        if step == 4:
            return self._step_plan_pago()
        return self._step_revision()

    def _step_datos_base(self) -> ft.Control:
        return self._card(
            "Paso 1 — Datos base",
            [
                ft.Row(
                    controls=[
                        ft.TextField(
                            label="Código/referencia",
                            value=self.state.codigo_venta,
                            width=220,
                            on_change=lambda e: self._set("codigo_venta", e.control.value),
                        ),
                        ft.TextField(
                            label="Fecha venta",
                            value=self.state.fecha_venta,
                            width=150,
                            on_change=lambda e: self._set("fecha_venta", e.control.value),
                        ),
                        ft.TextField(
                            label="Estado",
                            value=self.state.estado_venta,
                            width=160,
                            read_only=True,
                        ),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                ft.TextField(
                    label="Observaciones",
                    value=self.state.observaciones,
                    multiline=True,
                    min_lines=2,
                    on_change=lambda e: self._set("observaciones", e.control.value),
                ),
                self._validation_box(0),
            ],
        )

    def _step_objetos(self) -> ft.Control:
        return self._card(
            "Paso 2 — Objetos de venta",
            [
                ft.Text(
                    "Objetos inmobiliarios incluidos en la venta. Mock local del prototipo.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                _simple_table(
                    ["Tipo", "ID", "Descripción", "Precio"],
                    [_objeto_row(obj) for obj in self.state.objetos],
                ),
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            "Agregar objeto demo",
                            icon=ft.Icons.ADD,
                            on_click=self._add_objeto_demo,
                        ),
                        ft.OutlinedButton(
                            "Quitar último",
                            icon=ft.Icons.DELETE_OUTLINE,
                            on_click=self._remove_objeto,
                        ),
                    ],
                    spacing=10,
                ),
                self._validation_box(1),
            ],
        )

    def _step_compradores(self) -> ft.Control:
        return self._card(
            "Paso 3 — Compradores",
            [
                ft.Text(
                    "Regla inicial: exactamente un comprador financiero resoluble para generar Plan Pago V2.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                _simple_table(
                    ["ID persona", "Nombre", "Rol"],
                    [[c.id_persona, c.nombre, c.rol] for c in self.state.compradores],
                ),
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            "Agregar comprador demo",
                            icon=ft.Icons.ADD,
                            on_click=self._add_comprador_demo,
                        ),
                        ft.OutlinedButton(
                            "Quitar último",
                            icon=ft.Icons.DELETE_OUTLINE,
                            on_click=self._remove_comprador,
                        ),
                    ],
                    spacing=10,
                ),
                self._validation_box(2),
            ],
        )

    def _step_condiciones(self) -> ft.Control:
        suma_objetos = self._suma_objetos()
        monto_total = _decimal_or_zero(self.state.monto_total)
        diff = (monto_total - suma_objetos).quantize(Decimal("0.01"))
        return self._card(
            "Paso 4 — Condiciones comerciales",
            [
                ft.Text(
                    "Define el acuerdo comercial base. El modo de pago se carga en el paso siguiente.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                ft.Row(
                    controls=[
                        ft.TextField(
                            label="Monto total",
                            value=self.state.monto_total,
                            width=180,
                            on_change=lambda e: self._set("monto_total", e.control.value),
                        ),
                        ft.TextField(
                            label="Moneda",
                            value=self.state.moneda,
                            width=110,
                            on_change=lambda e: self._set("moneda", e.control.value.upper()),
                        ),
                    ],
                    spacing=10,
                ),
                ft.TextField(
                    label="Condiciones generales",
                    value=self.state.condiciones_generales,
                    multiline=True,
                    min_lines=3,
                    on_change=lambda e: self._set("condiciones_generales", e.control.value),
                ),
                _kv_grid(
                    [
                        ("Suma objetos", _money(suma_objetos)),
                        ("Monto total", _money(monto_total)),
                        ("Diferencia", _money(diff)),
                    ]
                ),
                self._validation_box(3),
            ],
        )

    def _step_plan_pago(self) -> ft.Control:
        total_bloques = self._suma_bloques()
        monto_total = _decimal_or_zero(self.state.monto_total)
        tipo_pago_dropdown = ft.Dropdown(
            label="Tipo de pago",
            value=self.state.tipo_pago,
            width=180,
            options=[ft.dropdown.Option("CONTADO"), ft.dropdown.Option("FINANCIADO")],
        )
        tipo_pago_dropdown.on_change = lambda e: self._set_tipo_pago(e.control.value)
        return self._card(
            "Paso 5 — Plan Pago V2 por bloques",
            [
                ft.Text(
                    "Carga la estructura del plan dentro del prototipo principal de venta completa. No implementa pagos, caja ni recibos.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                ft.Row(
                    controls=[
                        ft.TextField(
                            label="Base URL backend",
                            value=self.state.base_url,
                            width=260,
                            on_change=lambda e: self._set_backend_field("base_url", e.control.value),
                        ),
                        ft.TextField(
                            label="ID venta backend",
                            value=self.state.id_venta_backend,
                            width=150,
                            on_change=lambda e: self._set_backend_field("id_venta_backend", e.control.value),
                        ),
                        tipo_pago_dropdown,
                    ],
                    wrap=True,
                    spacing=10,
                ),
                self._bloques_editor(),
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            "Agregar anticipo",
                            icon=ft.Icons.ADD,
                            disabled=self.state.tipo_pago == "CONTADO",
                            on_click=lambda _: self._add_bloque("ANTICIPO"),
                        ),
                        ft.OutlinedButton(
                            "Agregar tramo",
                            icon=ft.Icons.ADD,
                            disabled=self.state.tipo_pago == "CONTADO",
                            on_click=lambda _: self._add_bloque("TRAMO_CUOTAS"),
                        ),
                        ft.OutlinedButton(
                            "Agregar refuerzo",
                            icon=ft.Icons.ADD,
                            disabled=self.state.tipo_pago == "CONTADO",
                            on_click=lambda _: self._add_bloque("REFUERZO"),
                        ),
                        ft.OutlinedButton(
                            "Agregar saldo",
                            icon=ft.Icons.ADD,
                            disabled=self.state.tipo_pago == "CONTADO",
                            on_click=lambda _: self._add_bloque("SALDO"),
                        ),
                        ft.OutlinedButton(
                            "Quitar último",
                            icon=ft.Icons.DELETE_OUTLINE,
                            disabled=self.state.tipo_pago == "CONTADO",
                            on_click=self._remove_bloque,
                        ),
                    ],
                    wrap=True,
                    spacing=8,
                ),
                _kv_grid(
                    [
                        ("Monto total", _money(monto_total)),
                        ("Suma bloques", _money(total_bloques)),
                        (
                            "Diferencia",
                            _money((monto_total - total_bloques).quantize(Decimal("0.01"))),
                        ),
                    ]
                ),
                ft.Row(
                    controls=[
                        ft.Button(
                            "Previsualizar plan",
                            icon=ft.Icons.PREVIEW,
                            disabled=self.state.loading_backend,
                            on_click=self._generate_preview,
                        ),
                        ft.Button(
                            "Generar plan de pago",
                            icon=ft.Icons.SEND,
                            disabled=(
                                self.state.loading_backend
                                or not self.state.preview_generado
                                or self.state.preview_stale
                            ),
                            on_click=self._generate_plan_backend,
                        ),
                        ft.OutlinedButton(
                            "Cargar consulta integral",
                            icon=ft.Icons.REFRESH,
                            disabled=self.state.loading_backend,
                            on_click=self._load_plan_integral,
                        ),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                self._backend_status_panel(),
                self._validation_box(4),
                self._backend_preview_panel(),
                self._plan_integral_panel(),
            ],
        )

    def _step_revision(self) -> ft.Control:
        errors = self._flow_errors_before_review()
        return self._card(
            "Paso 6 — Revisión y confirmación final",
            [
                ft.Text(
                    "Revisá toda la venta y el cronograma antes de confirmar. La confirmación está simulada en este prototipo."
                ),
                _kv_grid(
                    [
                        ("Código", self.state.codigo_venta or "-"),
                        ("Estado", self.state.estado_venta),
                        ("Fecha", self.state.fecha_venta or "-"),
                        ("Moneda", self.state.moneda or "-"),
                        ("Objetos", str(len(self.state.objetos))),
                        ("Compradores", str(len(self.state.compradores))),
                        ("Monto total", self.state.monto_total or "-"),
                        ("Tipo pago", self.state.tipo_pago),
                        ("Bloques", str(len(self.state.bloques))),
                    ]
                ),
                ft.Text("Estructura del plan", weight=ft.FontWeight.W_700),
                _simple_table(
                    ["Tipo", "Etiqueta", "Importe/capital", "Cuotas", "Método"],
                    [
                        [
                            b.tipo_bloque,
                            b.etiqueta,
                            b.importe,
                            b.cantidad_cuotas or "-",
                            b.metodo_liquidacion if b.tipo_bloque == "TRAMO_CUOTAS" else "-",
                        ]
                        for b in self.state.bloques
                    ],
                ),
                ft.Text(
                    "El cronograma visible se toma exclusivamente del Preview oficial backend.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                self._backend_preview_panel(),
                ft.Text("Alertas", weight=ft.FontWeight.W_700),
                ft.Column(
                    [ft.Text(error, color=ft.Colors.RED_700) for error in errors]
                    or [ft.Text("Sin alertas bloqueantes.", color=ft.Colors.GREEN_700)]
                ),
                ft.Button(
                    "Confirmar venta completa (simulado)",
                    icon=ft.Icons.CHECK_CIRCLE,
                    disabled=bool(errors),
                    on_click=self._confirm_simulated,
                ),
                ft.Text(
                    "Venta completa confirmada en modo prototipo."
                    if self.state.confirmacion_simulada
                    else ""
                ),
            ],
        )

    def _summary_panel(self) -> ft.Control:
        return self._card(
            "Resumen",
            [
                _kv_grid(
                    [
                        ("Prototipo principal", "venta_completa_wizard_prototype.py"),
                        ("Entrada futura", "Ventas → Nueva venta"),
                        ("Estado", self.state.estado_venta),
                        ("Paso", f"{self.state.current_step + 1}/{len(STEPS)}"),
                        ("Objetos", str(len(self.state.objetos))),
                        ("Compradores", str(len(self.state.compradores))),
                        ("Suma objetos", _money(self._suma_objetos())),
                        ("Monto total", self.state.monto_total or "-"),
                        ("Suma bloques", _money(self._suma_bloques())),
                        ("Preview backend", "Sí" if self.state.preview_generado else "No"),
                    ]
                ),
                ft.Divider(),
                ft.Text("Alcance", weight=ft.FontWeight.W_700),
                ft.Text("• Plan Pago V2 por bloques en dominio comercial"),
                ft.Text("• preview/generate/consulta integral backend existentes"),
                ft.Text("• sin pagos, caja, recibos, SQL ni backend"),
            ],
        )

    def _bloques_editor(self) -> ft.Control:
        if not self.state.bloques:
            return ft.Text("Sin bloques cargados.")
        return ft.Column(
            controls=[self._bloque_card(index, bloque) for index, bloque in enumerate(self.state.bloques, 1)],
            spacing=10,
        )

    def _bloque_card(self, index: int, bloque: BloquePlanDraft) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text(f"{index}. {bloque.tipo_bloque}", weight=ft.FontWeight.W_700),
            ft.TextField(
                label="Etiqueta",
                value=bloque.etiqueta,
                on_change=lambda e, b=bloque: self._update_bloque(b, "etiqueta", e.control.value),
            ),
        ]
        if bloque.tipo_bloque == "TRAMO_CUOTAS":
            controls.extend(
                [
                    ft.Row(
                        controls=[
                            ft.TextField(
                                label="Importe total bloque / capital",
                                value=bloque.importe,
                                width=210,
                                on_change=lambda e, b=bloque: self._update_bloque(b, "importe", e.control.value),
                            ),
                            ft.TextField(
                                label="Cantidad cuotas",
                                value=bloque.cantidad_cuotas,
                                width=150,
                                on_change=lambda e, b=bloque: self._update_bloque(b, "cantidad_cuotas", e.control.value),
                            ),
                            ft.TextField(
                                label="Primer vencimiento",
                                value=bloque.primer_vencimiento,
                                width=170,
                                on_change=lambda e, b=bloque: self._update_bloque(b, "primer_vencimiento", e.control.value),
                            ),
                            self._dropdown(
                                label="Periodicidad",
                                value=bloque.periodicidad,
                                width=150,
                                options=[ft.dropdown.Option("MENSUAL")],
                                on_change=lambda e, b=bloque: self._update_bloque(b, "periodicidad", e.control.value),
                            ),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    self._liquidation_editor(bloque),
                ]
            )
        else:
            controls.append(
                ft.Row(
                    controls=[
                        ft.TextField(
                            label="Importe total",
                            value=bloque.importe,
                            width=180,
                            on_change=lambda e, b=bloque: self._update_bloque(b, "importe", e.control.value),
                        ),
                        ft.TextField(
                            label="Vencimiento",
                            value=bloque.vencimiento,
                            width=170,
                            on_change=lambda e, b=bloque: self._update_bloque(b, "vencimiento", e.control.value),
                        ),
                    ],
                    wrap=True,
                    spacing=10,
                )
            )
        return ft.Container(
            content=ft.Column(controls=controls, spacing=8),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
        )


    @staticmethod
    def _dropdown(
        *,
        label: str,
        value: str | None,
        width: int,
        options: list[ft.dropdown.Option],
        on_change: Any,
    ) -> ft.Dropdown:
        """Build a Dropdown using event assignment for local Flet compatibility."""
        dropdown = ft.Dropdown(
            label=label,
            value=value,
            width=width,
            options=options,
        )
        dropdown.on_change = on_change
        return dropdown

    def _liquidation_editor(self, bloque: BloquePlanDraft) -> ft.Control:
        controls: list[ft.Control] = [
            self._dropdown(
                label="Metodo de liquidacion",
                value=bloque.metodo_liquidacion,
                width=230,
                options=[ft.dropdown.Option(method) for method in LIQUIDATION_METHODS],
                on_change=lambda e, b=bloque: self._set_liquidation_method(b, e.control.value),
            )
        ]
        if bloque.metodo_liquidacion == "INTERES_DIRECTO":
            controls.extend(
                [
                    ft.Text(
                        "Interes directo: interes simple sobre capital inicial del bloque.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Row(
                        controls=[
                            ft.TextField(
                                label="tasa_interes_directo_periodica",
                                value=bloque.tasa_interes_directo_periodica,
                                width=230,
                                on_change=lambda e, b=bloque: self._update_bloque(
                                    b, "tasa_interes_directo_periodica", e.control.value
                                ),
                            ),
                            ft.TextField(
                                label="cantidad_periodos",
                                value=bloque.cantidad_periodos,
                                width=180,
                                on_change=lambda e, b=bloque: self._update_bloque(
                                    b, "cantidad_periodos", e.control.value
                                ),
                            ),
                            _kv_inline("base_calculo_interes", "CAPITAL_INICIAL_BLOQUE"),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                ]
            )
        elif bloque.metodo_liquidacion == "INDEXACION":
            controls.extend(
                [
                    ft.Text(
                        "Indices DEV/demo: valores demo/no oficiales. Ajustar ID si la base local asigno otro identificador.",
                        size=12,
                        color=ft.Colors.AMBER_800,
                    ),
                    ft.Row(
                        controls=[
                            self._dropdown(
                                label="Indice demo",
                                value=bloque.codigo_indice_financiero or None,
                                width=180,
                                options=[ft.dropdown.Option(code) for _, code, _ in DEMO_INDICES],
                                on_change=lambda e, b=bloque: self._select_demo_index(b, e.control.value),
                            ),
                            ft.TextField(
                                label="id_indice_financiero",
                                value=bloque.id_indice_financiero,
                                width=170,
                                on_change=lambda e, b=bloque: self._update_bloque(b, "id_indice_financiero", e.control.value),
                            ),
                            ft.TextField(
                                label="fecha_base_indice",
                                value=bloque.fecha_base_indice,
                                width=170,
                                on_change=lambda e, b=bloque: self._update_bloque(b, "fecha_base_indice", e.control.value),
                            ),
                            ft.TextField(
                                label="valor_base_indice",
                                value=bloque.valor_base_indice,
                                width=170,
                                on_change=lambda e, b=bloque: self._update_bloque(b, "valor_base_indice", e.control.value),
                            ),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Row(
                        controls=[
                            _kv_inline("modo_indexacion", "POR_COEFICIENTE"),
                            _kv_inline("base_calculo_indexacion", "CAPITAL_INICIAL_BLOQUE"),
                            _kv_inline("tipo_generacion_indexada", "DEFINITIVA"),
                            _kv_inline("politica_valor_no_disponible", "ERROR_SI_NO_EXISTE"),
                            _kv_inline("conserva_capital_original", "true"),
                            _kv_inline("genera_ajuste_por_diferencia", "true"),
                        ],
                        wrap=True,
                        spacing=18,
                    ),
                ]
            )
        return ft.Container(
            content=ft.Column(controls=controls, spacing=8),
            padding=10,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
        )

    def _backend_status_panel(self) -> ft.Control:
        messages: list[ft.Control] = []
        if self.state.loading_backend:
            messages.append(ft.Text("Procesando backend...", color=ft.Colors.BLUE_700))
        if self.state.backend_error:
            messages.append(ft.Text(self.state.backend_error, color=ft.Colors.RED_700))
        if self.state.preview_generado and not self.state.preview_stale:
            messages.append(ft.Text("Preview backend vigente.", color=ft.Colors.GREEN_700))
        if self.state.generate_status_code is not None and self.state.generate_status_code < 400:
            messages.append(
                ft.Text(
                    "Plan de pago generado correctamente. Consulta integral refrescada.",
                    color=ft.Colors.GREEN_700,
                )
            )
        return ft.Column(controls=messages, spacing=4) if messages else ft.Text("")

    def _backend_preview_panel(self) -> ft.Control:
        if self.state.preview_response is None:
            return _official_preview_empty_panel(
                "No hay preview oficial. Presioná Previsualizar plan."
            )
        if self.state.preview_status_code and self.state.preview_status_code >= 400:
            return _backend_error_panel(self.state.preview_status_code, self.state.preview_response)
        if self.state.preview_stale:
            return _official_preview_empty_panel(
                "El preview oficial está desactualizado. Presioná Previsualizar plan."
            )
        data = _data_envelope(self.state.preview_response)
        if not isinstance(data, dict):
            return _json_expansion("Preview oficial backend", self.state.preview_response)
        bloques = _list_or_empty(data.get("bloques"))
        obligaciones = _list_or_empty(data.get("obligaciones"))
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Preview oficial backend", weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Cronograma renderizado exclusivamente desde POST /api/v1/ventas/{id_venta}/plan-pago-v2/preview.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Row(
                        controls=[
                            _kv_inline("total_calculado", _display_value(data.get("total_calculado"))),
                            _kv_inline("total_con_interes", _display_value(data.get("total_con_interes"))),
                            _kv_inline("total_con_indexacion", _display_value(data.get("total_con_indexacion"))),
                            _kv_inline("total_ajuste_indexacion", _display_value(data.get("total_ajuste_indexacion"))),
                            _kv_inline("bloques", str(len(bloques))),
                            _kv_inline("obligaciones", str(len(obligaciones))),
                        ],
                        wrap=True,
                        spacing=18,
                    ),
                    _preview_blocks_view(bloques),
                    _preview_obligaciones_view(obligaciones),
                    _json_expansion("JSON preview tecnico", self.state.preview_response),
                ],
                spacing=8,
            ),
            padding=12,
            border=_border_all(1, ft.Colors.GREEN_200),
            border_radius=8,
        )

    def _plan_integral_panel(self) -> ft.Control:
        if self.state.detalle_response is None:
            return ft.Text("Consulta integral pendiente.", color=ft.Colors.BLUE_GREY_700)
        data = _data_envelope(self.state.detalle_response)
        if self.state.detalle_status_code and self.state.detalle_status_code >= 400:
            return _backend_error_panel(self.state.detalle_status_code, self.state.detalle_response)
        if not isinstance(data, dict):
            return _json_expansion("Consulta integral", self.state.detalle_response)
        return _plan_integral_view(data)

    def _nav_buttons(self) -> ft.Control:
        return ft.Row(
            controls=[
                ft.OutlinedButton(
                    "Anterior",
                    icon=ft.Icons.ARROW_BACK,
                    disabled=self.state.current_step == 0,
                    on_click=lambda _: self._go(-1),
                ),
                ft.Button(
                    "Siguiente",
                    icon=ft.Icons.ARROW_FORWARD,
                    disabled=self.state.current_step >= len(STEPS) - 1,
                    on_click=lambda _: self._go(1),
                ),
            ],
            spacing=10,
        )

    def _card(self, title: str, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [ft.Text(title, size=20, weight=ft.FontWeight.W_700), *controls],
                spacing=12,
            ),
            padding=16,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _validation_box(self, step: int) -> ft.Control:
        _, errors = self._step_status(step)
        if not errors:
            return ft.Text("Paso completo o sin errores bloqueantes.", color=ft.Colors.GREEN_700)
        return ft.Column([ft.Text(error, color=ft.Colors.RED_700) for error in errors], spacing=4)

    def _step_status(self, step: int) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if step == 0:
            if not self.state.codigo_venta.strip():
                errors.append("El código/referencia es requerido.")
            if _date_or_none(self.state.fecha_venta) is None:
                errors.append("La fecha debe tener formato dd/mm/aaaa o ISO.")
            if not self.state.moneda.strip():
                errors.append("La moneda es requerida.")
        elif step == 1:
            if not self.state.objetos:
                errors.append("Debe existir al menos un objeto inmobiliario.")
            if self._suma_objetos() <= 0:
                errors.append("La suma de precios de objetos debe ser mayor a cero.")
        elif step == 2:
            if len(self.state.compradores) != 1:
                errors.append("Plan Pago V2 inicial requiere exactamente un comprador financiero.")
        elif step == 3:
            monto = _decimal_or_zero(self.state.monto_total)
            if monto <= 0:
                errors.append("El monto total debe ser mayor a cero.")
            if monto != self._suma_objetos():
                errors.append("El monto total debe coincidir con la suma de objetos.")
        elif step == 4:
            errors.extend(self._plan_pago_errors(require_preview=True))
        elif step == 5:
            errors.extend(self._flow_errors_before_review())
        return (not errors, errors)

    def _plan_pago_errors(self, *, require_preview: bool) -> list[str]:
        errors: list[str] = []
        if not self.state.bloques:
            errors.append("Debe existir al menos un bloque de plan de pago.")
        if self._suma_bloques() != _decimal_or_zero(self.state.monto_total):
            errors.append("La suma de bloques debe coincidir con el monto total.")
        if self.state.tipo_pago == "CONTADO":
            if len(self.state.bloques) != 1 or self.state.bloques[0].tipo_bloque != "CONTADO":
                errors.append("CONTADO solo admite un bloque CONTADO.")
        if self.state.tipo_pago == "FINANCIADO":
            if any(b.tipo_bloque == "CONTADO" for b in self.state.bloques):
                errors.append("FINANCIADO no admite bloque CONTADO.")
        if _int_or_zero(self.state.id_venta_backend) <= 0:
            errors.append("ID venta backend requerido para preview/generate/consulta integral.")
        for bloque in self.state.bloques:
            importe = _decimal_or_zero(bloque.importe)
            if importe <= 0:
                errors.append(f"{bloque.tipo_bloque}: importe/capital requerido.")
            if bloque.tipo_bloque in UNIQUE_BLOCKS and _date_or_none(bloque.vencimiento) is None:
                errors.append(f"{bloque.tipo_bloque}: vencimiento requerido.")
            if bloque.tipo_bloque == "TRAMO_CUOTAS":
                if _int_or_zero(bloque.cantidad_cuotas) <= 0:
                    errors.append("TRAMO_CUOTAS: cantidad de cuotas requerida.")
                if _date_or_none(bloque.primer_vencimiento) is None:
                    errors.append("TRAMO_CUOTAS: primer vencimiento requerido.")
                if bloque.periodicidad != "MENSUAL":
                    errors.append("TRAMO_CUOTAS: periodicidad debe ser MENSUAL.")
                if bloque.metodo_liquidacion not in LIQUIDATION_METHODS:
                    errors.append("TRAMO_CUOTAS: metodo de liquidacion invalido.")
                if bloque.metodo_liquidacion == "INTERES_DIRECTO":
                    if _decimal_or_none(bloque.tasa_interes_directo_periodica) is None:
                        errors.append("INTERES_DIRECTO: tasa_interes_directo_periodica requerida.")
                    if _int_or_zero(bloque.cantidad_periodos) <= 0:
                        errors.append("INTERES_DIRECTO: cantidad_periodos requerida.")
                    if bloque.id_indice_financiero or bloque.fecha_base_indice or bloque.valor_base_indice:
                        errors.append("INTERES_DIRECTO: no puede combinar campos de INDEXACION.")
                elif bloque.metodo_liquidacion == "INDEXACION":
                    if _int_or_zero(bloque.id_indice_financiero) <= 0:
                        errors.append("INDEXACION: id_indice_financiero requerido.")
                    if _date_or_none(bloque.fecha_base_indice) is None:
                        errors.append("INDEXACION: fecha_base_indice requerida.")
                    valor_base = _decimal_or_none(bloque.valor_base_indice)
                    if valor_base is None or valor_base <= 0:
                        errors.append("INDEXACION: valor_base_indice debe ser mayor a cero.")
                    if bloque.tasa_interes_directo_periodica or bloque.cantidad_periodos:
                        errors.append("INDEXACION: no puede combinar campos de INTERES_DIRECTO.")
                elif (
                    bloque.tasa_interes_directo_periodica
                    or bloque.cantidad_periodos
                    or bloque.id_indice_financiero
                    or bloque.fecha_base_indice
                    or bloque.valor_base_indice
                ):
                    errors.append("SIN_INTERES: no debe contener campos de interes ni indexacion.")
        if require_preview and not self.state.preview_generado:
            errors.append("Debe generarse preview backend antes de confirmar.")
        if require_preview and self.state.preview_stale:
            errors.append("El preview backend esta desactualizado.")
        return _dedupe(errors)

    def _flow_errors_before_review(self) -> list[str]:
        errors: list[str] = []
        for step in range(len(STEPS) - 1):
            errors.extend(self._step_status(step)[1])
        return _dedupe(errors)

    def _set(self, field_name: str, value: str) -> None:
        setattr(self.state, field_name, value or "")
        if field_name in {"monto_total", "moneda"}:
            self._mark_preview_stale()
        self._render()

    def _set_backend_field(self, field_name: str, value: str) -> None:
        setattr(self.state, field_name, value or "")
        self.state.backend_error = None
        self._mark_preview_stale()
        self._render()

    def _set_tipo_pago(self, value: str | None) -> None:
        self.state.tipo_pago = value or "FINANCIADO"
        if self.state.tipo_pago == "CONTADO":
            self.state.bloques = [
                BloquePlanDraft(
                    tipo_bloque="CONTADO",
                    etiqueta="Pago contado",
                    importe=self.state.monto_total,
                    vencimiento=_format_ar_date(date.today()),
                )
            ]
        elif not self.state.bloques or self.state.bloques[0].tipo_bloque == "CONTADO":
            self.state.bloques = [
                BloquePlanDraft(
                    tipo_bloque="ANTICIPO",
                    etiqueta="Anticipo",
                    importe="2000000.00",
                    vencimiento=_format_ar_date(date.today()),
                ),
                BloquePlanDraft(
                    tipo_bloque="TRAMO_CUOTAS",
                    etiqueta="Saldo financiado",
                    importe=_money(max(_decimal_or_zero(self.state.monto_total) - Decimal("2000000.00"), Decimal("0.00"))),
                    cantidad_cuotas="6",
                    primer_vencimiento=_format_ar_date(date.today()),
                ),
            ]
        self._mark_preview_stale()
        self._render()

    def _go(self, delta: int) -> None:
        self.state.current_step = max(0, min(len(STEPS) - 1, self.state.current_step + delta))
        self._render()

    def _add_objeto_demo(self, _: Any) -> None:
        next_id = len(self.state.objetos) + 1
        self.state.objetos.append(
            ObjetoVentaDraft(
                tipo_objeto="UNIDAD_FUNCIONAL" if next_id % 2 == 0 else "TERRENO",
                id_objeto=str(next_id),
                descripcion=f"Objeto demo {next_id}",
                precio_asignado="1000000.00",
            )
        )
        self._render()

    def _remove_objeto(self, _: Any) -> None:
        if self.state.objetos:
            self.state.objetos.pop()
        self._render()

    def _add_comprador_demo(self, _: Any) -> None:
        next_id = len(self.state.compradores) + 1
        self.state.compradores.append(
            CompradorDraft(id_persona=str(next_id), nombre=f"Comprador demo {next_id}")
        )
        self._render()

    def _remove_comprador(self, _: Any) -> None:
        if self.state.compradores:
            self.state.compradores.pop()
        self._render()

    def _add_bloque(self, tipo: str) -> None:
        label = {
            "ANTICIPO": "Anticipo",
            "TRAMO_CUOTAS": "Tramo",
            "REFUERZO": "Refuerzo",
            "SALDO": "Saldo",
        }.get(tipo, tipo)
        self.state.bloques.append(
            BloquePlanDraft(
                tipo_bloque=tipo,
                etiqueta=label,
                importe="1000000.00",
                vencimiento=_format_ar_date(date.today()) if tipo != "TRAMO_CUOTAS" else "",
                cantidad_cuotas="6" if tipo == "TRAMO_CUOTAS" else "",
                primer_vencimiento=_format_ar_date(date.today()) if tipo == "TRAMO_CUOTAS" else "",
                periodicidad="MENSUAL",
            )
        )
        self._mark_preview_stale()
        self._render()

    def _remove_bloque(self, _: Any) -> None:
        if self.state.bloques:
            self.state.bloques.pop()
        self._mark_preview_stale()
        self._render()

    def _update_bloque(self, bloque: BloquePlanDraft, field_name: str, value: str | None) -> None:
        setattr(bloque, field_name, value or "")
        self._mark_preview_stale()
        self._render()

    def _set_liquidation_method(self, bloque: BloquePlanDraft, value: str | None) -> None:
        method = value if value in LIQUIDATION_METHODS else "SIN_INTERES"
        bloque.metodo_liquidacion = method
        if method != "INTERES_DIRECTO":
            bloque.tasa_interes_directo_periodica = ""
            bloque.cantidad_periodos = ""
        if method != "INDEXACION":
            bloque.id_indice_financiero = ""
            bloque.codigo_indice_financiero = ""
            bloque.fecha_base_indice = ""
            bloque.valor_base_indice = ""
        elif not bloque.fecha_base_indice:
            bloque.fecha_base_indice = _format_ar_date(date.today().replace(day=1))
        self._mark_preview_stale()
        self._render()

    def _select_demo_index(self, bloque: BloquePlanDraft, code: str | None) -> None:
        for demo_id, demo_code, _ in DEMO_INDICES:
            if demo_code == code:
                bloque.codigo_indice_financiero = demo_code
                bloque.id_indice_financiero = demo_id
                break
        else:
            bloque.codigo_indice_financiero = ""
        self._mark_preview_stale()
        self._render()

    def _generate_preview(self, _: Any) -> None:
        self.state.backend_error = None
        errors = self._plan_pago_errors(require_preview=False)
        if errors:
            self.state.backend_error = "No se puede previsualizar: " + " | ".join(errors)
            self._render()
            return
        id_venta = _int_or_zero(self.state.id_venta_backend)
        self.state.loading_backend = True
        self._render()
        response = self._post(
            f"/api/v1/ventas/{id_venta}/plan-pago-v2/preview",
            self._payload(),
            include_core_headers=False,
        )
        self.state.loading_backend = False
        self.state.preview_status_code = response.get("status_code")
        self.state.preview_response = response.get("json")
        self.state.preview_generado = bool(response.get("ok"))
        self.state.preview_stale = not bool(response.get("ok"))
        self.state.backend_error = None if response.get("ok") else response.get("error")
        self._render()

    def _generate_plan_backend(self, _: Any) -> None:
        self.state.backend_error = None
        errors = self._plan_pago_errors(require_preview=True)
        if errors:
            self.state.backend_error = "No se puede generar: " + " | ".join(errors)
            self._render()
            return
        id_venta = _int_or_zero(self.state.id_venta_backend)
        self.state.loading_backend = True
        self._render()
        response = self._post(
            f"/api/v1/ventas/{id_venta}/plan-pago-v2/generar",
            self._payload(),
            include_core_headers=True,
        )
        self.state.loading_backend = False
        self.state.generate_status_code = response.get("status_code")
        self.state.generate_response = response.get("json")
        if response.get("ok"):
            self.state.backend_error = None
            self._load_plan_integral(None, render=False)
        else:
            self.state.backend_error = response.get("error")
        self._render()

    def _load_plan_integral(self, _: Any, *, render: bool = True) -> None:
        id_venta = _int_or_zero(self.state.id_venta_backend)
        if id_venta <= 0:
            self.state.backend_error = "ID venta backend requerido para consulta integral."
            self._render()
            return
        self.state.loading_backend = True
        if render:
            self._render()
        response = self._get(f"/api/v1/ventas/{id_venta}/plan-pago-v2")
        self.state.loading_backend = False
        self.state.detalle_status_code = response.get("status_code")
        self.state.detalle_response = response.get("json")
        self.state.backend_error = None if response.get("ok") else response.get("error")
        if render:
            self._render()

    def _confirm_simulated(self, _: Any) -> None:
        self.state.confirmacion_simulada = True
        self._render()

    def _mark_preview_stale(self) -> None:
        if self.state.preview_response is not None:
            self.state.preview_stale = True
        self.state.preview_generado = False
        self.state.generate_status_code = None
        self.state.backend_error = None

    def _payload(self) -> dict[str, Any]:
        return {
            "tipo_pago": self.state.tipo_pago,
            "monto_total_plan": float(_decimal_or_zero(self.state.monto_total)),
            "moneda": self.state.moneda or "ARS",
            "bloques": [self._block_payload(bloque) for bloque in self.state.bloques],
        }

    def _block_payload(self, bloque: BloquePlanDraft) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tipo_bloque": bloque.tipo_bloque,
            "etiqueta_bloque": bloque.etiqueta or bloque.tipo_bloque,
        }
        if bloque.tipo_bloque == "TRAMO_CUOTAS":
            payload.update(
                {
                    "importe_total_bloque": float(_decimal_or_zero(bloque.importe)),
                    "cantidad_cuotas": _int_or_zero(bloque.cantidad_cuotas),
                    "fecha_primer_vencimiento": _iso_date_or_empty(bloque.primer_vencimiento),
                    "periodicidad": bloque.periodicidad,
                    "metodo_liquidacion": bloque.metodo_liquidacion,
                }
            )
            if bloque.metodo_liquidacion == "INTERES_DIRECTO":
                payload.update(
                    {
                        "tasa_interes_directo_periodica": float(
                            _decimal_or_zero(bloque.tasa_interes_directo_periodica)
                        ),
                        "cantidad_periodos": _int_or_zero(bloque.cantidad_periodos),
                        "base_calculo_interes": "CAPITAL_INICIAL_BLOQUE",
                    }
                )
            elif bloque.metodo_liquidacion == "INDEXACION":
                payload.update(
                    {
                        "id_indice_financiero": _int_or_zero(bloque.id_indice_financiero),
                        "fecha_base_indice": _iso_date_or_empty(bloque.fecha_base_indice),
                        "valor_base_indice": float(_decimal_or_zero(bloque.valor_base_indice)),
                        "modo_indexacion": "POR_COEFICIENTE",
                        "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
                        "tipo_generacion_indexada": "DEFINITIVA",
                        "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
                        "conserva_capital_original": True,
                        "genera_ajuste_por_diferencia": True,
                    }
                )
        else:
            payload.update(
                {
                    "importe_total_bloque": float(_decimal_or_zero(bloque.importe)),
                    "fecha_vencimiento": _iso_date_or_empty(bloque.vencimiento),
                }
            )
        return payload

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        include_core_headers: bool,
    ) -> dict[str, Any]:
        url = f"{self.state.base_url.rstrip('/')}{path}"
        headers = self._core_ef_headers() if include_core_headers else {}
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}
        return _response_payload(response)

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self.state.base_url.rstrip('/')}{path}"
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(url)
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}
        return _response_payload(response)

    def _core_ef_headers(self) -> dict[str, str]:
        return {
            "X-Op-Id": str(uuid4()),
            "X-Usuario-Id": "1",
            "X-Sucursal-Id": "1",
            "X-Instalacion-Id": "1",
        }

    def _suma_objetos(self) -> Decimal:
        return sum(
            (_decimal_or_zero(obj.precio_asignado) for obj in self.state.objetos),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

    def _suma_bloques(self) -> Decimal:
        return sum(
            (_decimal_or_zero(bloque.importe) for bloque in self.state.bloques),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

def _official_preview_empty_panel(message: str) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Preview oficial backend", weight=ft.FontWeight.W_700),
                ft.Text(message, color=ft.Colors.BLUE_GREY_700),
            ],
            spacing=6,
        ),
        padding=12,
        border=_border_all(1, ft.Colors.BLUE_GREY_100),
        border_radius=8,
    )


def _preview_blocks_view(bloques: list[dict[str, Any]]) -> ft.Control:
    controls: list[ft.Control] = [ft.Text("Bloques devueltos por backend", weight=ft.FontWeight.W_700)]
    if not bloques:
        controls.append(ft.Text("Sin bloques."))
    for bloque in bloques:
        metodo = bloque.get("metodo_liquidacion") or "SIN_INTERES"
        controls.append(
            ft.Text(
                f"{bloque.get('numero_bloque', '-')} | {bloque.get('tipo_bloque', '-')} | "
                f"{bloque.get('etiqueta_bloque', '-')} | metodo {metodo} | "
                f"importe {bloque.get('importe_total_bloque') or bloque.get('importe_cuota') or '-'}",
                size=12,
            )
        )
        if metodo == "INDEXACION":
            controls.append(
                ft.Text(
                    f"  INDEXACION: con indice {bloque.get('cantidad_cuotas_con_indice', 0)} | "
                    f"cuotas proyectadas sin indice {bloque.get('cantidad_cuotas_proyectadas_sin_indice', 0)} | "
                    f"ajuste {bloque.get('total_ajuste_indexacion') or '-'}",
                    size=11,
                    color=ft.Colors.BLUE_GREY_700,
                )
            )
    return ft.Container(
        content=ft.Column(controls=controls, spacing=4),
        padding=10,
        border=_border_all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _preview_obligaciones_view(obligaciones: list[dict[str, Any]]) -> ft.Control:
    rows = [
        [
            _display_value(obligacion.get("numero_obligacion") or ordinal),
            _display_value(obligacion.get("numero_bloque")),
            _display_value(obligacion.get("tipo_bloque")),
            _display_value(obligacion.get("etiqueta_obligacion")),
            _display_value(obligacion.get("fecha_vencimiento")),
            _display_value(obligacion.get("capital_cuota")),
            _display_value(obligacion.get("ajuste_indexacion_cuota")),
            _display_value(obligacion.get("importe_total")),
            _display_value(obligacion.get("estado_preview_indexacion")),
            _display_value(obligacion.get("concepto_financiero_codigo")),
        ]
        for ordinal, obligacion in enumerate(obligaciones, 1)
    ]
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Obligaciones devueltas por backend", weight=ft.FontWeight.W_700),
                _simple_table(
                    [
                        "N°",
                        "Bloque",
                        "Tipo bloque",
                        "Etiqueta",
                        "Vencimiento",
                        "Capital cuota",
                        "Ajuste indexación",
                        "Importe total",
                        "Estado indexación",
                        "Concepto",
                    ],
                    rows,
                ),
            ],
            spacing=6,
        ),
        padding=10,
        border=_border_all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _plan_integral_view(data: dict[str, Any]) -> ft.Control:
    plan = data.get("plan_pago_venta") if isinstance(data.get("plan_pago_venta"), dict) else data
    bloques = _list_or_empty(data.get("bloques") or plan.get("bloques"))
    resumen = data.get("resumen") if isinstance(data.get("resumen"), dict) else {}
    controls: list[ft.Control] = [
        ft.Text("Consulta integral Plan Pago V2", weight=ft.FontWeight.W_700),
        ft.Row(
            controls=[
                _kv_inline("Metodo", str(plan.get("metodo_plan_pago") or "-")),
                _kv_inline("Estado", str(plan.get("estado_plan_pago") or "-")),
                _kv_inline("Monto", str(plan.get("monto_total_plan") or "-")),
                _kv_inline("Moneda", str(plan.get("moneda") or "-")),
            ],
            wrap=True,
            spacing=18,
        ),
    ]
    if resumen:
        controls.append(
            ft.Row(
                controls=[
                    _kv_inline("total_capital", str(resumen.get("total_capital") or "-")),
                    _kv_inline("total_interes", str(resumen.get("total_interes") or "-")),
                    _kv_inline("total_ajuste_indexacion", str(resumen.get("total_ajuste_indexacion") or "-")),
                    _kv_inline("total_obligaciones", str(resumen.get("total_obligaciones") or "-")),
                    _kv_inline("con indexacion", str(resumen.get("cantidad_obligaciones_con_indexacion") or 0)),
                    _kv_inline("proyectadas", str(resumen.get("cantidad_obligaciones_proyectadas_sin_indexacion") or 0)),
                ],
                wrap=True,
                spacing=18,
            )
        )
    for bloque in bloques:
        obligaciones = _list_or_empty(bloque.get("obligaciones"))
        indexacion = bloque.get("indexacion") if isinstance(bloque.get("indexacion"), dict) else None
        block_controls: list[ft.Control] = [
            ft.Row(
                controls=[
                    _kv_inline("Metodo liquidacion", str(bloque.get("metodo_liquidacion") or "SIN_INTERES")),
                    _kv_inline("Interes", str(bloque.get("tasa_interes_directo_periodica") or "NO APLICA")),
                    _kv_inline("Base interes", str(bloque.get("base_calculo_interes") or "NO APLICA")),
                ],
                wrap=True,
                spacing=18,
            )
        ]
        if indexacion:
            block_controls.append(
                ft.Row(
                    controls=[
                        _kv_inline("Indice", str(indexacion.get("codigo_indice_financiero") or indexacion.get("id_indice_financiero") or "-")),
                        _kv_inline("Fecha base", str(indexacion.get("fecha_base_indice") or "-")),
                        _kv_inline("Valor base", str(indexacion.get("valor_base_indice") or "-")),
                        _kv_inline("Modo", str(indexacion.get("modo_indexacion") or "-")),
                    ],
                    wrap=True,
                    spacing=18,
                )
            )
        block_controls.append(_obligaciones_integrales_view(obligaciones, bloque.get("metodo_liquidacion")))
        controls.append(
            ft.ExpansionTile(
                title=ft.Text(
                    f"{bloque.get('numero_bloque', '-')} | {bloque.get('tipo_bloque', '-')} | {bloque.get('etiqueta_bloque', '-')}"
                ),
                subtitle=ft.Text(f"Obligaciones: {len(obligaciones)}"),
                controls=block_controls,
            )
        )
    controls.append(_json_expansion("JSON consulta integral tecnico", data))
    return ft.Container(
        content=ft.Column(controls=controls, spacing=8),
        padding=12,
        border=_border_all(1, ft.Colors.BLUE_GREY_100),
        border_radius=8,
    )


def _obligaciones_integrales_view(obligaciones: list[dict[str, Any]], metodo_bloque: Any) -> ft.Control:
    if not obligaciones:
        return ft.Text("Sin obligaciones en este bloque.")
    rows: list[ft.Control] = []
    for obligacion in obligaciones:
        composiciones = _list_or_empty(obligacion.get("composiciones"))
        indexacion = obligacion.get("indexacion") if isinstance(obligacion.get("indexacion"), dict) else None
        composiciones_text = ", ".join(
            f"{comp.get('codigo_concepto_financiero')}: {comp.get('importe_componente')}"
            for comp in composiciones
        ) or "Sin composiciones"
        if indexacion:
            indexacion_text = (
                "Indexacion aplicada: "
                f"valor {indexacion.get('valor_aplicado_indice')} | "
                f"coeficiente {indexacion.get('coeficiente_indexacion')} | "
                f"fecha {indexacion.get('fecha_aplicacion_indice')}"
            )
        elif metodo_bloque == "INDEXACION":
            indexacion_text = "Proyectada sin índice aplicado"
        else:
            indexacion_text = "Sin indexacion"
        rows.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                _kv_inline("N", str(obligacion.get("numero_obligacion") or "-")),
                                _kv_inline("Tipo", str(obligacion.get("tipo_item_cronograma") or "-")),
                                _kv_inline("Vencimiento", str(obligacion.get("fecha_vencimiento") or "-")),
                                _kv_inline("Importe", str(obligacion.get("importe_total") or "-")),
                                _kv_inline("Saldo", str(obligacion.get("saldo_pendiente") or "-")),
                                _kv_inline("Estado", str(obligacion.get("estado_obligacion") or "-")),
                            ],
                            wrap=True,
                            spacing=14,
                        ),
                        ft.Text(
                            f"Composiciones: {composiciones_text}",
                            size=11,
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                        ft.Text(indexacion_text, size=11, color=ft.Colors.BLUE_GREY_700),
                    ],
                    spacing=4,
                ),
                padding=8,
                border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.BLUE_GREY_50)),
            )
        )
    return ft.Column(controls=rows, spacing=4)


def _display_value(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def _simple_table(headers: list[str], rows: list[list[str]]) -> ft.Control:
    return ft.DataTable(
        columns=[ft.DataColumn(ft.Text(header)) for header in headers],
        rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(str(cell))) for cell in row]) for row in rows],
    )


def _kv_grid(items: list[tuple[str, str]]) -> ft.Control:
    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text(label, width=150, color=ft.Colors.BLUE_GREY_700),
                    ft.Text(value, selectable=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            for label, value in items
        ],
        spacing=6,
    )


def _kv_inline(label: str, value: str) -> ft.Control:
    return ft.Column(
        controls=[
            ft.Text(label, size=11, color=ft.Colors.BLUE_GREY_700),
            ft.Text(value, size=12, weight=ft.FontWeight.W_600, selectable=True),
        ],
        spacing=2,
        tight=True,
    )


def _json_expansion(title: str, value: Any) -> ft.Control:
    return ft.ExpansionTile(
        title=ft.Text(title),
        controls=[
            ft.TextField(
                value=json.dumps(value, ensure_ascii=True, indent=2, default=str),
                multiline=True,
                read_only=True,
                min_lines=6,
                max_lines=18,
            )
        ],
    )


def _objeto_row(obj: ObjetoVentaDraft) -> list[str]:
    return [obj.tipo_objeto, obj.id_objeto, obj.descripcion, obj.precio_asignado]


def _border_all(width: int | float, color: ft.ColorValue) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


def _decimal_or_none(value: object) -> Decimal | None:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if number.as_tuple().exponent < -2:
        return None
    return number.quantize(Decimal("0.01"))


def _decimal_or_zero(value: object) -> Decimal:
    return _decimal_or_none(value) or Decimal("0.00")


def _int_or_zero(value: object) -> int:
    try:
        parsed = int(str(value or "").strip())
    except ValueError:
        return 0
    return max(parsed, 0)


def _date_or_none(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    try:
        day, month, year = text.split("/")
        return date(int(year), int(month), int(day))
    except (TypeError, ValueError):
        return None


def _iso_date_or_empty(value: object) -> str:
    parsed = _date_or_none(value)
    return parsed.isoformat() if parsed else ""


def _format_ar_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    if response.status_code >= 400:
        return {
            "ok": False,
            "status_code": response.status_code,
            "json": payload,
            "error": _format_backend_error(response.status_code, payload),
        }
    return {"ok": True, "status_code": response.status_code, "json": payload}


def _format_backend_error(status_code: int, payload: Any) -> str:
    if isinstance(payload, dict):
        code = payload.get("error_code")
        message = payload.get("error_message") or payload.get("detail")
        if code and message:
            return f"{status_code} {code}: {message}"
        if message:
            return f"{status_code}: {message}"
    return f"Error HTTP {status_code}."


def _backend_error_panel(status_code: int, payload: Any) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Error backend", weight=ft.FontWeight.W_700, color=ft.Colors.RED_700),
                _kv_inline("Status HTTP", str(status_code)),
                _json_expansion("JSON error", payload),
            ],
            spacing=6,
        ),
        padding=12,
        border=_border_all(1, ft.Colors.RED_200),
        border_radius=6,
    )


def _data_envelope(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data")
    return payload


def _list_or_empty(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def main(page: ft.Page) -> None:
    page.title = "Prototipo venta completa"
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.add(VentaCompletaWizardPrototype(page).build())


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
