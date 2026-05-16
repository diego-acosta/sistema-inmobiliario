"""Prototipo Flet no productivo para plan de pago V2 por bloques.

Uso:
  cd frontend/flet_app
  python prototypes/plan_pago_v2_bloques_prototype.py

Requisitos:
  - Backend levantado, por defecto en http://127.0.0.1:8000.
  - Dependencias del prototipo instaladas desde frontend/flet_app/requirements.txt.

Alcance:
  - Pantalla aislada para validar UX de carga y visualizacion.
  - No integra el flujo productivo de la app.
  - No modifica backend, SQL, pagos, caja ni recibos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from typing import Any, Callable
from uuid import uuid4

import flet as ft
import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_MONEDA = "ARS"
UNIQUE_BLOCKS = ("CONTADO", "ANTICIPO", "REFUERZO", "SALDO")


def _border_all(width: int | float, color: ft.ColorValue) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


@dataclass
class BloqueDraft:
    uid: str
    tipo_bloque: str
    etiqueta_bloque: str = ""
    importe_total_bloque: str = ""
    fecha_vencimiento: str = ""
    capital_tramo: str = ""
    cantidad_cuotas: str = ""
    fecha_primer_vencimiento: str = ""
    periodicidad: str = "MENSUAL"


@dataclass
class CronogramaRow:
    numero: int
    bloque: str
    tipo_obligacion: str
    etiqueta: str
    vencimiento: str
    importe: Decimal
    concepto: str


@dataclass
class PrototypeState:
    bloques: list[BloqueDraft] = field(default_factory=list)
    current_step: int = 1
    loading: bool = False
    validation_requested: bool = False
    response_json_visible: bool = False
    detail_json_visible: bool = False
    backend_preview_json_visible: bool = False
    last_response: dict[str, Any] | None = None
    backend_preview_response: dict[str, Any] | None = None
    detail_response: dict[str, Any] | None = None
    backend_preview_status_code: int | None = None
    backend_preview_stale: bool = True
    error_message: str | None = None
    status_code: int | None = None


class PlanPagoV2BloquesPrototype:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = PrototypeState()

        self.base_url = ft.TextField(
            label="Base URL",
            value=DEFAULT_BASE_URL,
            width=280,
            on_change=self._on_input_change,
        )
        self.id_venta = ft.TextField(
            label="ID venta", width=120, on_change=self._on_input_change
        )
        self.tipo_pago = ft.SegmentedButton(
            selected=["CONTADO"],
            allow_empty_selection=False,
            allow_multiple_selection=False,
            segments=[
                ft.Segment(value="CONTADO", label=ft.Text("CONTADO")),
                ft.Segment(value="FINANCIADO", label=ft.Text("FINANCIADO")),
            ],
            on_change=self._on_tipo_pago_change,
        )
        self.moneda = ft.TextField(
            label="Moneda",
            value=DEFAULT_MONEDA,
            width=110,
            on_change=self._on_input_change,
        )
        self.monto_total_plan = ft.TextField(
            label="Monto total del plan",
            value="12000000.00",
            width=180,
            on_change=self._on_input_change,
        )

        self.summary = ft.Column(spacing=4)
        self.main_column = ft.Column(expand=True)
        self.validation_banner = ft.Container(visible=False)
        self.blocks_column = ft.ListView(spacing=10, expand=True)
        self.preview_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        self.response_column = ft.Column(spacing=10)
        self.detail_column = ft.Column(spacing=10)
        self.tramo_cuota_texts: dict[str, ft.Text] = {}
        self.tramo_rounding_texts: dict[str, ft.Text] = {}
        self.tramo_due_fields: dict[str, ft.TextField] = {}

        self.generate_button = ft.Button(
            "Generar plan definitivo",
            icon=ft.Icons.SEND,
            on_click=self._generate_plan,
        )
        self.backend_preview_button = ft.OutlinedButton(
            "Vista previa del plan",
            icon=ft.Icons.CLOUD_SYNC,
            on_click=self._load_backend_preview,
        )
        self.back_button = ft.OutlinedButton(
            "Volver y modificar",
            icon=ft.Icons.ARROW_BACK,
            on_click=self._back_to_edit,
        )
        self.validate_button = ft.OutlinedButton(
            "Validar",
            icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
            on_click=self._validate_current,
        )
        self.detail_button = ft.OutlinedButton(
            "Cargar detalle integral",
            icon=ft.Icons.REFRESH,
            on_click=self._load_detail,
        )

    def run(self) -> None:
        self.page.title = "Prototipo Plan Pago V2 por Bloques"
        self.page.padding = 20
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self._reset_blocks_for_tipo("CONTADO")
        self.page.add(self._build_layout())
        self._refresh()

    def _build_layout(self) -> ft.Control:
        return ft.Column(
            controls=[
                self._build_header(),
                self.main_column,
            ],
            spacing=14,
            expand=True,
        )

    def _build_header(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text(
                    "Plan de pago V2 por bloques",
                    size=26,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    "Prototipo aislado para carga y visualizacion. No forma parte del flujo productivo.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
            ],
            spacing=4,
        )

    def _build_editor_panel(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Datos y bloques", size=18, weight=ft.FontWeight.W_700),
                    self._build_general_inputs(),
                    self.validation_banner,
                    ft.Row(
                        controls=self._add_block_buttons(),
                        wrap=True,
                        spacing=8,
                    ),
                    ft.Text("Bloques", weight=ft.FontWeight.W_700),
                    self.blocks_column,
                ],
                spacing=12,
                expand=True,
            ),
            padding=14,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
            expand=3,
            height=720,
        )

    def _build_general_inputs(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        self.base_url,
                        self.id_venta,
                        self.moneda,
                        self.monto_total_plan,
                    ],
                    wrap=True,
                    spacing=10,
                ),
                ft.Row(
                    controls=[
                        ft.Text("Tipo de pago", weight=ft.FontWeight.W_600),
                        self.tipo_pago,
                    ],
                    wrap=True,
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
        )

    def _build_step1_view(self) -> ft.Control:
        return ft.Row(
            controls=[
                self._build_editor_panel(),
                self._build_step1_side_panel(),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
            expand=True,
        )

    def _build_step1_side_panel(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Paso 1", size=18, weight=ft.FontWeight.W_700),
                    ft.Container(
                        content=self.summary,
                        padding=12,
                        border=_border_all(1, ft.Colors.BLUE_GREY_100),
                        border_radius=6,
                    ),
                    ft.Row(
                        controls=[
                            self.backend_preview_button,
                            self.validate_button,
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                ],
                spacing=12,
                expand=True,
            ),
            padding=14,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
            expand=2,
            height=720,
        )

    def _build_step2_view(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Paso 2", size=18, weight=ft.FontWeight.W_700),
                    ft.Text("Vista previa del plan", size=22, weight=ft.FontWeight.W_700),
                    self.preview_column,
                    ft.Row(
                        controls=[
                            self.back_button,
                            self.generate_button,
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Text("Resultado de generacion", weight=ft.FontWeight.W_700),
                    self.response_column,
                ],
                spacing=12,
                expand=True,
            ),
            padding=14,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
            height=720,
        )

    def _add_block_buttons(self) -> list[ft.Control]:
        return [
            ft.OutlinedButton(
                "Agregar anticipo",
                icon=ft.Icons.ADD,
                on_click=lambda _: self._add_block("ANTICIPO"),
            ),
            ft.OutlinedButton(
                "Agregar tramo cuotas",
                icon=ft.Icons.ADD,
                on_click=lambda _: self._add_block("TRAMO_CUOTAS"),
            ),
            ft.OutlinedButton(
                "Agregar refuerzo",
                icon=ft.Icons.ADD,
                on_click=lambda _: self._add_block("REFUERZO"),
            ),
            ft.OutlinedButton(
                "Agregar saldo",
                icon=ft.Icons.ADD,
                on_click=lambda _: self._add_block("SALDO"),
            ),
        ]

    def _selected_tipo_pago(self) -> str:
        selected = self.tipo_pago.selected or ["CONTADO"]
        if isinstance(selected, str):
            value = selected
        else:
            values = list(selected)
            value = str(values[0]) if values else "CONTADO"
        return value if value in ("CONTADO", "FINANCIADO") else "CONTADO"

    def _on_tipo_pago_change(self, _: ft.ControlEvent) -> None:
        tipo_pago = self._selected_tipo_pago()
        self.tipo_pago.selected = [tipo_pago]
        self.state.current_step = 1
        self.state.error_message = None
        self.state.validation_requested = False
        self.state.response_json_visible = False
        self.state.detail_json_visible = False
        self.state.backend_preview_json_visible = False
        self.state.last_response = None
        self.state.backend_preview_response = None
        self.state.detail_response = None
        self.state.status_code = None
        self.state.backend_preview_status_code = None
        self.state.backend_preview_stale = True
        self.response_column.controls = []
        self.detail_column.controls = []
        self._reset_blocks_for_tipo(tipo_pago)
        self._refresh()

    def _reset_blocks_for_tipo(self, tipo_pago: str) -> None:
        monto_total = _decimal_or_zero(self.monto_total_plan.value)
        if tipo_pago == "CONTADO":
            self.state.bloques = [
                BloqueDraft(
                    uid=str(uuid4()),
                    tipo_bloque="CONTADO",
                    etiqueta_bloque="Pago contado",
                    importe_total_bloque=_money(monto_total),
                    fecha_vencimiento=_format_ar_date(date.today()),
                )
            ]
            return
        anticipo = min(Decimal("2000000.00"), monto_total)
        cuotas = 6
        total_cuotas = max(monto_total - anticipo, Decimal("0"))
        saldo = monto_total - anticipo - total_cuotas
        bloques = [
            BloqueDraft(
                uid=str(uuid4()),
                tipo_bloque="ANTICIPO",
                etiqueta_bloque="Anticipo",
                importe_total_bloque=_money(anticipo),
                fecha_vencimiento=_format_ar_date(date.today()),
            ),
            BloqueDraft(
                uid=str(uuid4()),
                tipo_bloque="TRAMO_CUOTAS",
                etiqueta_bloque="Primer tramo",
                capital_tramo=_money(total_cuotas),
                cantidad_cuotas="6",
                fecha_primer_vencimiento=_format_ar_date(date.today()),
                periodicidad="MENSUAL",
            ),
        ]
        if saldo > 0:
            bloques.append(
                BloqueDraft(
                    uid=str(uuid4()),
                    tipo_bloque="SALDO",
                    etiqueta_bloque="Ajuste saldo",
                    importe_total_bloque=_money(saldo),
                    fecha_vencimiento=_format_ar_date(date.today()),
                )
            )
        self.state.bloques = bloques

    def _add_block(self, tipo_bloque: str) -> None:
        if self._selected_tipo_pago() == "CONTADO":
            self._set_error("CONTADO solo admite un bloque CONTADO.")
            return
        labels = {
            "ANTICIPO": "Anticipo",
            "TRAMO_CUOTAS": "Tramo de cuotas",
            "REFUERZO": "Refuerzo",
            "SALDO": "Saldo final",
        }
        self.state.bloques.append(
            self._new_block(
                tipo_bloque,
                labels.get(tipo_bloque, tipo_bloque),
            )
        )
        self._recalculate_tramo_dates()
        self.state.validation_requested = False
        self.state.current_step = 1
        self.state.error_message = None
        self._mark_backend_preview_stale()
        self._refresh()

    def _remove_block(self, uid: str) -> None:
        self.state.bloques = [b for b in self.state.bloques if b.uid != uid]
        self._recalculate_tramo_dates()
        self.state.validation_requested = False
        self.state.current_step = 1
        self.state.error_message = None
        self._mark_backend_preview_stale()
        self._refresh()

    def _new_block(self, tipo_bloque: str, label: str) -> BloqueDraft:
        bloque = BloqueDraft(
            uid=str(uuid4()),
            tipo_bloque=tipo_bloque,
            etiqueta_bloque=label,
            periodicidad="MENSUAL",
        )
        if tipo_bloque == "TRAMO_CUOTAS":
            bloque.fecha_primer_vencimiento = self._next_tramo_first_due() or _format_ar_date(
                date.today()
            )
        elif tipo_bloque in UNIQUE_BLOCKS:
            bloque.fecha_vencimiento = _format_ar_date(date.today())
        return bloque

    def _on_input_change(self, _: ft.ControlEvent) -> None:
        self.state.validation_requested = False
        self.state.current_step = 1
        self.state.error_message = None
        self._mark_backend_preview_stale()
        self._refresh_summary_and_preview(rebuild_step=False)

    def _refresh(self, _: ft.ControlEvent | None = None) -> None:
        self._render_blocks()
        self._refresh_summary_and_preview(update_page=False)
        self._render_current_step()
        self.page.update()

    def _refresh_summary_and_preview(
        self,
        update_page: bool = True,
        rebuild_step: bool = True,
    ) -> None:
        errors = self._validate()
        preview = self._build_preview()
        self._refresh_tramo_calculated_labels()
        self._render_summary(preview, errors)
        self._render_validation(errors)
        self._render_preview()
        self.validate_button.disabled = self.state.loading
        self.backend_preview_button.disabled = self.state.loading
        self.generate_button.disabled = (
            self.state.loading
            or bool(errors)
            or self.state.current_step != 2
            or not self._backend_preview_ready()
            or self.state.backend_preview_stale
        )
        self.detail_button.disabled = self.state.loading
        self.back_button.disabled = self.state.loading
        if rebuild_step:
            self._render_current_step()
        if update_page:
            self.page.update()

    def _render_current_step(self) -> None:
        if self.state.current_step == 2:
            self.main_column.controls = [self._build_step2_view()]
        else:
            self.main_column.controls = [self._build_step1_view()]

    def _render_summary(
        self, preview: list[CronogramaRow], errors: list[str]
    ) -> None:
        monto_total = _decimal_or_zero(self.monto_total_plan.value)
        suma_ux = self._blocks_total()
        suma_backend = self._backend_payload_total()
        diff_ux = monto_total - suma_ux
        diff_backend = monto_total - suma_backend
        has_errors = bool(errors) and self.state.validation_requested
        diff_ux_color = (
            ft.Colors.GREEN_700 if diff_ux == Decimal("0") else ft.Colors.AMBER_800
        )
        diff_backend_color = (
            ft.Colors.GREEN_700 if diff_backend == Decimal("0") else ft.Colors.RED_700
        )
        if has_errors:
            status_text = "Revisar validaciones."
            status_color = ft.Colors.RED_700
        elif diff_backend != Decimal("0"):
            status_text = "La suma enviada al backend no cierra."
            status_color = ft.Colors.RED_700
        elif diff_ux != Decimal("0"):
            status_text = "Diferencia UX pendiente de ajustar."
            status_color = ft.Colors.AMBER_800
        else:
            status_text = "Listo para generar."
            status_color = ft.Colors.GREEN_700
        if not self._backend_preview_ready():
            status_text = "Genera la vista previa para habilitar la generacion."
            status_color = ft.Colors.BLUE_GREY_700
        elif self.state.backend_preview_stale:
            status_text = "Vista previa desactualizada."
            status_color = ft.Colors.AMBER_800
        self.summary.controls = [
            ft.Text("Resumen", weight=ft.FontWeight.W_700),
            ft.Row(
                controls=[
                    _kv("Monto total", _money(monto_total)),
                    _kv("Suma bloques UX", _money(suma_ux)),
                    _kv("Suma enviada backend", _money(suma_backend)),
                    _kv("Diferencia UX", _money(diff_ux), color=diff_ux_color),
                    _kv(
                        "Diferencia backend",
                        _money(diff_backend),
                        color=diff_backend_color,
                    ),
                    _kv("Obligaciones estimadas", str(len(preview))),
                ],
                wrap=True,
                spacing=18,
            ),
            ft.Text(
                status_text,
                color=status_color,
            ),
        ]
        if diff_backend != Decimal("0"):
            self.summary.controls.append(
                ft.Text(
                    "La vista previa oficial ajusta la ultima cuota cuando el "
                    "tramo se envia por capital total.",
                    size=12,
                    color=ft.Colors.AMBER_800,
                )
            )

    def _render_validation(self, errors: list[str]) -> None:
        show_errors = self.state.validation_requested and bool(errors)
        self.validation_banner.visible = show_errors or bool(self.state.error_message)
        messages = list(errors) if show_errors else []
        if self.state.error_message:
            messages.append(self.state.error_message)
        self.validation_banner.content = ft.Column(
            controls=[ft.Text(message, color=ft.Colors.RED_700) for message in messages],
            spacing=4,
        )
        self.validation_banner.padding = 12
        self.validation_banner.border = _border_all(1, ft.Colors.RED_200)
        self.validation_banner.border_radius = 6

    def _render_blocks(self) -> None:
        self.tramo_cuota_texts = {}
        self.tramo_rounding_texts = {}
        self.tramo_due_fields = {}
        self.blocks_column.controls = [
            self._block_card(index, bloque)
            for index, bloque in enumerate(self.state.bloques, start=1)
        ] or [ft.Text("Sin bloques cargados.")]

    def _block_card(self, index: int, bloque: BloqueDraft) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Text(
                        f"{index}. {bloque.tipo_bloque}",
                        weight=ft.FontWeight.W_700,
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        tooltip="Eliminar bloque",
                        disabled=self._selected_tipo_pago() == "CONTADO",
                        on_click=lambda _, uid=bloque.uid: self._remove_block(uid),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.TextField(
                label="Etiqueta",
                value=bloque.etiqueta_bloque,
                on_change=lambda e, b=bloque: self._update_block(
                    b, "etiqueta_bloque", e.control.value
                ),
            ),
        ]
        if bloque.tipo_bloque == "TRAMO_CUOTAS":
            first_tramo = self._is_first_tramo(bloque)
            calculated_text = ft.Text(
                self._calculated_cuota_label(bloque),
                weight=ft.FontWeight.W_600,
            )
            rounding_text = ft.Text(
                self._tramo_rounding_warning(bloque) or "",
                size=12,
                color=ft.Colors.AMBER_800,
                visible=bool(self._tramo_rounding_warning(bloque)),
            )
            due_field = ft.TextField(
                label="Primer vencimiento",
                value=bloque.fecha_primer_vencimiento,
                width=170,
                read_only=not first_tramo,
                on_change=lambda e, b=bloque: self._update_block(
                    b, "fecha_primer_vencimiento", e.control.value
                ),
            )
            self.tramo_cuota_texts[bloque.uid] = calculated_text
            self.tramo_rounding_texts[bloque.uid] = rounding_text
            self.tramo_due_fields[bloque.uid] = due_field
            controls.extend(
                [
                    ft.Row(
                        controls=[
                            ft.TextField(
                                label="Capital del tramo",
                                value=bloque.capital_tramo,
                                width=170,
                                on_change=lambda e, b=bloque: self._update_block(
                                    b, "capital_tramo", e.control.value
                                ),
                            ),
                            ft.TextField(
                                label="Cantidad cuotas",
                                value=bloque.cantidad_cuotas,
                                width=150,
                                on_change=lambda e, b=bloque: self._update_block(
                                    b, "cantidad_cuotas", e.control.value
                                ),
                            ),
                            ft.Row(
                                controls=[
                                    due_field,
                                    ft.IconButton(
                                        icon=ft.Icons.CALENDAR_MONTH,
                                        tooltip="Seleccionar fecha",
                                        disabled=not first_tramo,
                                        on_click=lambda _, b=bloque: self._open_date_picker(
                                            b, "fecha_primer_vencimiento"
                                        ),
                                    ),
                                ],
                                spacing=2,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        "Importe de cuota calculado",
                                        size=12,
                                        color=ft.Colors.BLUE_GREY_700,
                                    ),
                                    calculated_text,
                                    rounding_text,
                                ],
                                spacing=2,
                                tight=True,
                            ),
                            ft.Dropdown(
                                label="Periodicidad",
                                value=bloque.periodicidad,
                                width=150,
                                options=[ft.dropdown.Option("MENSUAL")],
                                on_select=lambda e, b=bloque: self._update_block(
                                    b, "periodicidad", e.control.value
                                ),
                            ),
                        ],
                        wrap=True,
                        spacing=10,
                    )
                ]
            )
        else:
            controls.extend(
                [
                    ft.Row(
                        controls=[
                            ft.TextField(
                                label="Importe total",
                                value=bloque.importe_total_bloque,
                                width=170,
                                on_change=lambda e, b=bloque: self._update_block(
                                    b, "importe_total_bloque", e.control.value
                                ),
                            ),
                            ft.TextField(
                                label="Vencimiento",
                                value=bloque.fecha_vencimiento,
                                width=170,
                                on_change=lambda e, b=bloque: self._update_block(
                                    b, "fecha_vencimiento", e.control.value
                                ),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CALENDAR_MONTH,
                                tooltip="Seleccionar fecha",
                                on_click=lambda _, b=bloque: self._open_date_picker(
                                    b, "fecha_vencimiento"
                                ),
                            ),
                        ],
                        wrap=True,
                        spacing=10,
                    )
                ]
            )
        return ft.Container(
            content=ft.Column(controls=controls, spacing=10),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
        )

    def _update_block(
        self, bloque: BloqueDraft, field_name: str, value: str | None
    ) -> None:
        setattr(bloque, field_name, value or "")
        if bloque.tipo_bloque == "TRAMO_CUOTAS" and field_name in (
            "capital_tramo",
            "cantidad_cuotas",
            "fecha_primer_vencimiento",
            "periodicidad",
        ):
            self._recalculate_tramo_dates()
        self.state.error_message = None
        self.state.validation_requested = False
        self.state.current_step = 1
        self._mark_backend_preview_stale()
        self._refresh_summary_and_preview(rebuild_step=False)

    def _is_first_tramo(self, bloque: BloqueDraft) -> bool:
        for item in self.state.bloques:
            if item.tipo_bloque == "TRAMO_CUOTAS":
                return item.uid == bloque.uid
        return False

    def _next_tramo_first_due(self) -> str | None:
        previous_due: date | None = None
        for bloque in self.state.bloques:
            if bloque.tipo_bloque != "TRAMO_CUOTAS":
                continue
            previous_due = self._last_due_for_tramo(bloque)
        if previous_due is None:
            return None
        return _format_ar_date(_add_months(previous_due, 1))

    def _recalculate_tramo_dates(self) -> None:
        previous_due: date | None = None
        first_tramo_seen = False
        for bloque in self.state.bloques:
            if bloque.tipo_bloque != "TRAMO_CUOTAS":
                continue
            if not first_tramo_seen:
                first_tramo_seen = True
                previous_due = self._last_due_for_tramo(bloque)
                continue
            if previous_due is None:
                continue
            bloque.fecha_primer_vencimiento = _format_ar_date(
                _add_months(previous_due, 1)
            )
            field = self.tramo_due_fields.get(bloque.uid)
            if field is not None:
                field.value = bloque.fecha_primer_vencimiento
            previous_due = self._last_due_for_tramo(bloque)

    def _last_due_for_tramo(self, bloque: BloqueDraft) -> date | None:
        first_due = _date_or_none(bloque.fecha_primer_vencimiento)
        qty = _int_or_none(bloque.cantidad_cuotas)
        if first_due is None or qty is None:
            return None
        return _add_months(first_due, qty - 1)

    def _open_date_picker(self, bloque: BloqueDraft, field_name: str) -> None:
        current = _date_or_none(getattr(bloque, field_name, ""))

        def on_change(event: ft.ControlEvent) -> None:
            selected = event.control.value
            if isinstance(selected, date):
                setattr(bloque, field_name, _format_ar_date(selected))
                if bloque.tipo_bloque == "TRAMO_CUOTAS":
                    self._recalculate_tramo_dates()
                self.state.error_message = None
                self.state.validation_requested = False
                self.state.current_step = 1
                self._mark_backend_preview_stale()
                self._refresh()

        picker = ft.DatePicker(
            value=current,
            modal=True,
            locale=ft.Locale("es", "AR"),
            help_text="Seleccionar fecha",
            cancel_text="Cancelar",
            confirm_text="Aceptar",
            field_label_text="Fecha",
            field_hint_text="dd/mm/aaaa",
            on_change=on_change,
        )
        self.page.show_dialog(picker)

    def _render_preview(self) -> None:
        self.preview_column.controls = []
        if self.state.backend_preview_response is None:
            self.preview_column.controls = [
                ft.Container(
                    content=ft.Text(
                        "Actualiza el preview para ver el cronograma oficial.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    padding=10,
                    border=_border_all(1, ft.Colors.BLUE_GREY_100),
                    border_radius=6,
                )
            ]
            return

        if self.state.backend_preview_status_code is not None:
            self.preview_column.controls.append(
                ft.Text(f"Status HTTP: {self.state.backend_preview_status_code}")
            )
        if self.state.backend_preview_stale:
            self.preview_column.controls.append(
                ft.Text(
                    "Preview desactualizado por cambios locales. Actualizalo de nuevo.",
                    color=ft.Colors.AMBER_800,
                    weight=ft.FontWeight.W_600,
                )
            )

        data = _data_envelope(self.state.backend_preview_response)
        if (
            self.state.backend_preview_status_code is not None
            and self.state.backend_preview_status_code >= 400
        ):
            self.preview_column.controls.append(
                _backend_error_panel(
                    status_code=self.state.backend_preview_status_code,
                    payload=self.state.backend_preview_response,
                )
            )
        elif isinstance(data, dict):
            self.preview_column.controls.append(_backend_preview_panel(data))

        self.preview_column.controls.append(
            self._technical_json_toggle(
                value=self.state.backend_preview_response,
                visible=self.state.backend_preview_json_visible,
                on_click=self._toggle_backend_preview_json,
            )
        )

    def _preview_row(self, row: CronogramaRow) -> ft.Control:
        secondary = f"{row.tipo_obligacion} · {row.concepto}"
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                ft.Text(
                                    str(row.numero),
                                    size=12,
                                    weight=ft.FontWeight.W_600,
                                ),
                                width=34,
                            ),
                            ft.Container(
                                ft.Text(row.bloque, size=12),
                                expand=2,
                            ),
                            ft.Container(
                                ft.Text(row.etiqueta, size=12),
                                expand=2,
                            ),
                            ft.Container(ft.Text(row.vencimiento, size=12), width=92),
                            ft.Container(
                                ft.Text(
                                    _money(row.importe),
                                    size=12,
                                    weight=ft.FontWeight.W_600,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                                width=96,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Text(
                        secondary,
                        size=11,
                        color=ft.Colors.BLUE_GREY_600,
                    ),
                ],
                spacing=2,
            ),
            padding=ft.Padding.symmetric(horizontal=4, vertical=6),
            border=ft.Border.only(
                bottom=ft.BorderSide(1, ft.Colors.BLUE_GREY_50),
            ),
        )

    def _validate(self) -> list[str]:
        errors: list[str] = []
        tipo_pago = self._selected_tipo_pago()
        monto_total = _decimal_or_none(self.monto_total_plan.value)
        if monto_total is None or monto_total <= 0:
            errors.append("El monto total del plan debe ser mayor a cero.")
        if not (self.moneda.value or "").strip():
            errors.append("La moneda es requerida.")
        if not self.state.bloques:
            errors.append("Debe cargar al menos un bloque.")
        if tipo_pago == "CONTADO":
            if len(self.state.bloques) != 1 or self.state.bloques[0].tipo_bloque != "CONTADO":
                errors.append("CONTADO solo admite un bloque CONTADO.")
        if tipo_pago == "FINANCIADO":
            if any(b.tipo_bloque == "CONTADO" for b in self.state.bloques):
                errors.append("FINANCIADO no admite bloque CONTADO.")
        for bloque in self.state.bloques:
            if bloque.tipo_bloque in UNIQUE_BLOCKS:
                if _decimal_or_none(bloque.importe_total_bloque) is None:
                    errors.append(f"{bloque.tipo_bloque}: importe total requerido.")
                if not _valid_date(bloque.fecha_vencimiento):
                    errors.append(f"{bloque.tipo_bloque}: vencimiento requerido.")
            if bloque.tipo_bloque == "TRAMO_CUOTAS":
                if _int_or_none(bloque.cantidad_cuotas) is None:
                    errors.append("TRAMO_CUOTAS: cantidad de cuotas requerida.")
                capital = _decimal_or_none(bloque.capital_tramo)
                if capital is None or capital <= 0:
                    errors.append("TRAMO_CUOTAS: capital del tramo requerido.")
                if not _valid_date(bloque.fecha_primer_vencimiento):
                    errors.append("TRAMO_CUOTAS: primer vencimiento requerido.")
                if bloque.periodicidad != "MENSUAL":
                    errors.append("TRAMO_CUOTAS: periodicidad debe ser MENSUAL.")
        if monto_total is not None and self._blocks_total() != monto_total:
            errors.append("La suma UX de bloques no coincide con el monto total del plan.")
        if monto_total is not None and self._backend_payload_total() != monto_total:
            errors.append(
                "La suma enviada al backend no coincide con el monto total del plan."
            )
        return _dedupe(errors)

    def _validate_current(self, _: ft.ControlEvent) -> None:
        self.state.validation_requested = True
        self.state.error_message = None
        self._refresh_summary_and_preview()

    def _refresh_tramo_calculated_labels(self) -> None:
        for bloque in self.state.bloques:
            if bloque.tipo_bloque != "TRAMO_CUOTAS":
                continue
            cuota_text = self.tramo_cuota_texts.get(bloque.uid)
            if cuota_text is not None:
                cuota_text.value = self._calculated_cuota_label(bloque)
            rounding_text = self.tramo_rounding_texts.get(bloque.uid)
            if rounding_text is not None:
                warning = self._tramo_rounding_warning(bloque)
                rounding_text.value = warning or ""
                rounding_text.visible = bool(warning)
            due_field = self.tramo_due_fields.get(bloque.uid)
            if due_field is not None and not self._is_first_tramo(bloque):
                due_field.value = bloque.fecha_primer_vencimiento

    def _calculated_cuota_label(self, bloque: BloqueDraft) -> str:
        cuota = self._calculated_importe_cuota(bloque)
        return _money(cuota) if cuota is not None else "-"

    def _calculated_importe_cuota(self, bloque: BloqueDraft) -> Decimal | None:
        capital = _decimal_or_none(bloque.capital_tramo)
        qty = _int_or_none(bloque.cantidad_cuotas)
        if capital is None or capital <= 0 or qty is None:
            return None
        return (capital / Decimal(qty)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def _tramo_rounding_warning(self, bloque: BloqueDraft) -> str | None:
        capital = _decimal_or_none(bloque.capital_tramo)
        qty = _int_or_none(bloque.cantidad_cuotas)
        cuota = self._calculated_importe_cuota(bloque)
        if capital is None or qty is None or cuota is None:
            return None
        total_calculado = (cuota * Decimal(qty)).quantize(Decimal("0.01"))
        diferencia = (capital - total_calculado).quantize(Decimal("0.01"))
        if diferencia == Decimal("0.00"):
            return None
        return f"Redondeo: total cuotas difiere {_money(diferencia)} del capital."

    def _blocks_total(self) -> Decimal:
        total = Decimal("0")
        for bloque in self.state.bloques:
            if bloque.tipo_bloque == "TRAMO_CUOTAS":
                total += _decimal_or_zero(bloque.capital_tramo)
            else:
                total += _decimal_or_zero(bloque.importe_total_bloque)
        return total.quantize(Decimal("0.01"))

    def _backend_payload_total(self) -> Decimal:
        total = Decimal("0")
        for bloque in self.state.bloques:
            if bloque.tipo_bloque == "TRAMO_CUOTAS":
                total += _decimal_or_zero(bloque.capital_tramo)
            else:
                total += _decimal_or_zero(bloque.importe_total_bloque)
        return total.quantize(Decimal("0.01"))

    def _build_preview(self) -> list[CronogramaRow]:
        rows: list[CronogramaRow] = []
        for bloque in self.state.bloques:
            label = bloque.etiqueta_bloque or bloque.tipo_bloque
            if bloque.tipo_bloque == "CONTADO":
                rows.append(
                    CronogramaRow(
                        numero=len(rows) + 1,
                        bloque=label,
                        tipo_obligacion="SALDO",
                        etiqueta=label,
                        vencimiento=_format_display_date(bloque.fecha_vencimiento),
                        importe=_decimal_or_zero(bloque.importe_total_bloque),
                        concepto="CAPITAL_VENTA",
                    )
                )
            elif bloque.tipo_bloque == "ANTICIPO":
                rows.append(
                    CronogramaRow(
                        numero=len(rows) + 1,
                        bloque=label,
                        tipo_obligacion="ANTICIPO",
                        etiqueta=label,
                        vencimiento=_format_display_date(bloque.fecha_vencimiento),
                        importe=_decimal_or_zero(bloque.importe_total_bloque),
                        concepto="ANTICIPO_VENTA",
                    )
                )
            elif bloque.tipo_bloque == "TRAMO_CUOTAS":
                qty = _int_or_none(bloque.cantidad_cuotas) or 0
                first_due = _date_or_none(bloque.fecha_primer_vencimiento)
                importe_cuota = self._calculated_importe_cuota(bloque) or Decimal("0.00")
                for index in range(qty):
                    due = _format_ar_date(_add_months(first_due, index)) if first_due else ""
                    rows.append(
                        CronogramaRow(
                            numero=len(rows) + 1,
                            bloque=label,
                            tipo_obligacion="CUOTA",
                            etiqueta=f"{label} {index + 1}",
                            vencimiento=due,
                            importe=importe_cuota,
                            concepto="CAPITAL_VENTA",
                        )
                    )
            elif bloque.tipo_bloque in ("REFUERZO", "SALDO"):
                rows.append(
                    CronogramaRow(
                        numero=len(rows) + 1,
                        bloque=label,
                        tipo_obligacion=bloque.tipo_bloque,
                        etiqueta=label,
                        vencimiento=_format_display_date(bloque.fecha_vencimiento),
                        importe=_decimal_or_zero(bloque.importe_total_bloque),
                        concepto="CAPITAL_VENTA",
                    )
                )
        return rows

    def _payload(self) -> dict[str, Any]:
        return {
            "tipo_pago": self._selected_tipo_pago(),
            "monto_total_plan": float(_decimal_or_zero(self.monto_total_plan.value)),
            "moneda": (self.moneda.value or DEFAULT_MONEDA).strip(),
            "bloques": [self._block_payload(bloque) for bloque in self.state.bloques],
        }

    def _block_payload(self, bloque: BloqueDraft) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tipo_bloque": bloque.tipo_bloque,
            "etiqueta_bloque": bloque.etiqueta_bloque or bloque.tipo_bloque,
        }
        if bloque.tipo_bloque == "TRAMO_CUOTAS":
            payload.update(
                {
                    "cantidad_cuotas": _int_or_none(bloque.cantidad_cuotas),
                    "importe_total_bloque": float(
                        _decimal_or_zero(bloque.capital_tramo)
                    ),
                    "fecha_primer_vencimiento": _iso_date_or_empty(
                        bloque.fecha_primer_vencimiento
                    ),
                    "periodicidad": bloque.periodicidad,
                }
            )
        else:
            payload.update(
                {
                    "importe_total_bloque": float(
                        _decimal_or_zero(bloque.importe_total_bloque)
                    ),
                    "fecha_vencimiento": _iso_date_or_empty(bloque.fecha_vencimiento),
                }
            )
        return payload

    def _mark_backend_preview_stale(self) -> None:
        if self.state.backend_preview_response is not None:
            self.state.backend_preview_stale = True

    def _backend_preview_ready(self) -> bool:
        data = _data_envelope(self.state.backend_preview_response)
        return (
            self.state.backend_preview_response is not None
            and self.state.backend_preview_status_code is not None
            and self.state.backend_preview_status_code < 400
            and isinstance(data, dict)
        )

    def _load_backend_preview(self, _: ft.ControlEvent) -> None:
        self.state.validation_requested = True
        self.state.error_message = None
        errors = self._validate()
        if errors:
            self._refresh_summary_and_preview()
            return
        id_venta = _int_or_none(self.id_venta.value)
        if id_venta is None:
            self._set_error("ID venta requerido.")
            return

        self.state.loading = True
        self._refresh_summary_and_preview()
        path = f"/api/v1/ventas/{id_venta}/plan-pago-v2/preview"
        response = self._post(path, self._payload())
        self.state.loading = False
        self.state.backend_preview_status_code = response.get("status_code")
        self.state.backend_preview_response = response.get("json")
        self.state.backend_preview_json_visible = False
        self.state.backend_preview_stale = not response.get("ok")
        if response.get("ok"):
            self.state.error_message = None
            self.state.current_step = 2
        else:
            self.state.current_step = 1
            self.state.error_message = response.get("error") or "Error en vista previa."
        self._refresh_summary_and_preview()

    def _back_to_edit(self, _: ft.ControlEvent) -> None:
        self.state.current_step = 1
        self.state.error_message = None
        self._refresh()

    def _generate_plan(self, _: ft.ControlEvent) -> None:
        self.state.validation_requested = True
        self.state.error_message = None
        errors = self._validate()
        if errors:
            self._refresh_summary_and_preview()
            return
        if not self._backend_preview_ready() or self.state.backend_preview_stale:
            self._set_error("Genera la vista previa antes de generar el plan definitivo.")
            return
        id_venta = _int_or_none(self.id_venta.value)
        if id_venta is None:
            self._set_error("ID venta requerido.")
            return

        self.state.loading = True
        self.state.error_message = None
        self._refresh_summary_and_preview()
        path = f"/api/v1/ventas/{id_venta}/plan-pago-v2/generar"
        response = self._post(path, self._payload())
        self.state.loading = False
        self.state.status_code = response.get("status_code")
        if response.get("ok"):
            self.state.last_response = response.get("json")
            self.state.error_message = None
            self.state.response_json_visible = False
        else:
            self.state.last_response = response.get("json")
            self.state.response_json_visible = False
            self.state.error_message = response.get("error") or "Error al generar plan."
        self._render_response()
        self._refresh_summary_and_preview()

    def _load_detail(self, _: ft.ControlEvent) -> None:
        id_venta = _int_or_none(self.id_venta.value)
        if id_venta is None:
            self._set_error("ID venta requerido.")
            return
        self.state.loading = True
        self.state.error_message = None
        self._refresh_summary_and_preview()
        path = f"/api/v1/ventas/{id_venta}/detalle-integral"
        response = self._get(path)
        self.state.loading = False
        self.state.status_code = response.get("status_code")
        if response.get("ok"):
            self.state.detail_response = response.get("json")
            self.state.error_message = None
            self.state.detail_json_visible = False
        else:
            self.state.detail_response = response.get("json")
            self.state.detail_json_visible = False
            self.state.error_message = response.get("error") or "Error al cargar detalle."
        self._render_detail()
        self._refresh_summary_and_preview()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url()}{path}"
        headers = self._headers()
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}
        return _response_payload(response)

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self._base_url()}{path}"
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}
        return _response_payload(response)

    def _headers(self) -> dict[str, str]:
        return {
            "X-Op-Id": str(uuid4()),
            "X-Usuario-Id": "1",
            "X-Sucursal-Id": "1",
            "X-Instalacion-Id": "1",
        }

    def _base_url(self) -> str:
        return (self.base_url.value or DEFAULT_BASE_URL).rstrip("/")

    def _set_error(self, message: str) -> None:
        self.state.error_message = message
        self.state.validation_requested = True
        self._refresh_summary_and_preview()

    def _render_response(self) -> None:
        self.response_column.controls = []
        if self.state.status_code is not None:
            self.response_column.controls.append(
                ft.Text(f"Status HTTP: {self.state.status_code}")
            )
        data = _data_envelope(self.state.last_response)
        if self.state.status_code is not None and self.state.status_code >= 400:
            self.response_column.controls.append(
                _backend_error_panel(
                    status_code=self.state.status_code,
                    payload=self.state.last_response,
                )
            )
        elif isinstance(data, dict):
            self.response_column.controls.append(_plan_summary(data))
        if self.state.last_response is not None:
            self.response_column.controls.append(
                self._technical_json_toggle(
                    value=self.state.last_response,
                    visible=self.state.response_json_visible,
                    on_click=self._toggle_response_json,
                )
            )

    def _render_detail(self) -> None:
        self.detail_column.controls = []
        if self.state.status_code is not None:
            self.detail_column.controls.append(ft.Text(f"Status HTTP: {self.state.status_code}"))
        data = _data_envelope(self.state.detail_response)
        plan = data.get("plan_pago_v2") if isinstance(data, dict) else None
        if self.state.status_code is not None and self.state.status_code >= 400:
            self.detail_column.controls.append(
                _backend_error_panel(
                    status_code=self.state.status_code,
                    payload=self.state.detail_response,
                )
            )
        elif isinstance(plan, dict):
            self.detail_column.controls.append(_plan_readonly(plan))
        elif self.state.detail_response is not None:
            self.detail_column.controls.append(
                ft.Text("El detalle integral no devolvio plan_pago_v2.")
            )
        if self.state.detail_response is not None:
            self.detail_column.controls.append(
                self._technical_json_toggle(
                    value=self.state.detail_response,
                    visible=self.state.detail_json_visible,
                    on_click=self._toggle_detail_json,
                )
            )

    def _toggle_response_json(self, _: ft.ControlEvent) -> None:
        self.state.response_json_visible = not self.state.response_json_visible
        self._render_response()
        self.page.update()

    def _toggle_backend_preview_json(self, _: ft.ControlEvent) -> None:
        self.state.backend_preview_json_visible = (
            not self.state.backend_preview_json_visible
        )
        self._render_preview()
        self.page.update()

    def _toggle_detail_json(self, _: ft.ControlEvent) -> None:
        self.state.detail_json_visible = not self.state.detail_json_visible
        self._render_detail()
        self.page.update()

    def _technical_json_toggle(
        self,
        *,
        value: Any,
        visible: bool,
        on_click: Callable[[ft.ControlEvent], None],
    ) -> ft.Control:
        controls: list[ft.Control] = [
            ft.OutlinedButton(
                "Ocultar JSON tecnico" if visible else "Ver JSON tecnico",
                icon=ft.Icons.CODE,
                on_click=on_click,
            )
        ]
        if visible:
            controls.extend(
                [
                    ft.Text(
                        "Solo para depuracion",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    _json_view(value),
                ]
            )
        return ft.Column(controls=controls, spacing=6)


def _backend_preview_panel(data: dict[str, Any]) -> ft.Control:
    bloques = _list_or_empty(data.get("bloques"))
    obligaciones = _list_or_empty(data.get("obligaciones"))
    redondeos = _list_or_empty(data.get("redondeos"))
    diff = _decimal_or_zero(str(data.get("diferencia") or "0"))
    diff_color = ft.Colors.GREEN_700 if diff == Decimal("0") else ft.Colors.RED_700
    controls: list[ft.Control] = [
        ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Calculo oficial backend", weight=ft.FontWeight.W_700),
                    ft.Row(
                        controls=[
                            _kv(
                                "Total calculado",
                                str(data.get("total_calculado") or "-"),
                            ),
                            _kv(
                                "Diferencia",
                                str(data.get("diferencia") or "-"),
                                color=diff_color,
                            ),
                            _kv("Bloques", str(len(bloques))),
                            _kv("Obligaciones", str(len(obligaciones))),
                        ],
                        wrap=True,
                        spacing=16,
                    ),
                ],
                spacing=8,
            ),
            padding=10,
            border=_border_all(1, ft.Colors.GREEN_200),
            border_radius=6,
        )
    ]
    if redondeos:
        controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Redondeos", weight=ft.FontWeight.W_700),
                        *[
                            ft.Text(
                                f"Bloque {item.get('numero_bloque')} "
                                f"{item.get('tipo_bloque')}: "
                                f"ajuste ultima cuota "
                                f"{item.get('ajuste_ultima_cuota')}",
                                size=12,
                            )
                            for item in redondeos
                        ],
                    ],
                    spacing=4,
                ),
                padding=10,
                border=_border_all(1, ft.Colors.AMBER_200),
                border_radius=6,
            )
        )
    controls.append(_backend_blocks_preview(bloques))
    controls.append(_backend_obligaciones_preview(obligaciones))
    return ft.Column(controls=controls, spacing=8)


def _backend_blocks_preview(bloques: list[dict[str, Any]]) -> ft.Control:
    rows: list[ft.Control] = [
        ft.Text("Bloques normalizados", weight=ft.FontWeight.W_700)
    ]
    if not bloques:
        rows.append(ft.Text("Sin bloques."))
    for bloque in bloques:
        importe = bloque.get("importe_total_bloque") or bloque.get("importe_cuota") or "-"
        detalle = (
            f"{bloque.get('tipo_bloque', '-')} | "
            f"{bloque.get('etiqueta_bloque', '-')} | "
            f"importe {importe}"
        )
        if bloque.get("cantidad_cuotas"):
            detalle += f" | cuotas {bloque.get('cantidad_cuotas')}"
        rows.append(ft.Text(detalle, size=12))
    return ft.Container(
        content=ft.Column(controls=rows, spacing=4),
        padding=10,
        border=_border_all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _backend_obligaciones_preview(obligaciones: list[dict[str, Any]]) -> ft.Control:
    header_style = {
        "size": 11,
        "weight": ft.FontWeight.W_700,
        "color": ft.Colors.BLUE_GREY_700,
    }
    rows: list[ft.Control] = [
        ft.Text("Obligaciones preview", weight=ft.FontWeight.W_700)
    ]
    if not obligaciones:
        rows.append(ft.Text("Sin obligaciones."))
    else:
        rows.append(
            ft.Row(
                controls=[
                    ft.Container(ft.Text("N", **header_style), width=34),
                    ft.Container(ft.Text("Bloque", **header_style), width=70),
                    ft.Container(ft.Text("Tipo", **header_style), width=76),
                    ft.Container(ft.Text("Vencimiento", **header_style), width=92),
                    ft.Container(ft.Text("Importe", **header_style), width=96),
                ],
                spacing=8,
            )
        )
    for obligacion in obligaciones:
        rows.append(
            ft.Row(
                controls=[
                    ft.Container(
                        ft.Text(str(obligacion.get("numero_obligacion") or "-"), size=12),
                        width=34,
                    ),
                    ft.Container(
                        ft.Text(str(obligacion.get("numero_bloque") or "-"), size=12),
                        width=70,
                    ),
                    ft.Container(
                        ft.Text(str(obligacion.get("tipo_item_cronograma") or "-"), size=12),
                        width=76,
                    ),
                    ft.Container(
                        ft.Text(
                            _format_display_date(
                                str(obligacion.get("fecha_vencimiento") or "")
                            ),
                            size=12,
                        ),
                        width=92,
                    ),
                    ft.Container(
                        ft.Text(
                            str(obligacion.get("importe_total") or "-"),
                            size=12,
                            weight=ft.FontWeight.W_600,
                            text_align=ft.TextAlign.RIGHT,
                        ),
                        width=96,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )
    return ft.Container(
        content=ft.Column(controls=rows, spacing=5),
        padding=10,
        border=_border_all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _plan_summary(data: dict[str, Any]) -> ft.Control:
    plan = data.get("plan") if isinstance(data.get("plan"), dict) else data
    bloques = _list_or_empty(data.get("bloques") or plan.get("bloques"))
    obligaciones = _list_or_empty(data.get("obligaciones") or plan.get("obligaciones"))
    for bloque in bloques:
        obligaciones.extend(_list_or_empty(bloque.get("obligaciones")))
    tipos_bloque = ", ".join(
        sorted(
            dict.fromkeys(
                str(b.get("tipo_bloque")) for b in bloques if b.get("tipo_bloque")
            )
        )
    )
    tipos_obligacion = ", ".join(
        sorted(
            dict.fromkeys(
                str(o.get("tipo_item_cronograma") or o.get("tipo_obligacion"))
                for o in obligaciones
                if o.get("tipo_item_cronograma") or o.get("tipo_obligacion")
            )
        )
    )
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Resumen generado", weight=ft.FontWeight.W_700),
                ft.Row(
                    controls=[
                        _kv("Metodo", str(plan.get("metodo_plan_pago") or "-")),
                        _kv("Bloques", str(len(bloques))),
                        _kv("Obligaciones", str(len(obligaciones))),
                    ],
                    wrap=True,
                    spacing=18,
                ),
                _kv("Tipos de bloque", tipos_bloque or "-"),
                _kv("Tipos de obligacion", tipos_obligacion or "-"),
            ],
            spacing=8,
        ),
        padding=12,
        border=_border_all(1, ft.Colors.GREEN_200),
        border_radius=6,
    )


def _plan_readonly(plan: dict[str, Any]) -> ft.Control:
    bloques = _list_or_empty(plan.get("bloques"))
    controls: list[ft.Control] = [
        ft.Text("Plan generado", weight=ft.FontWeight.W_700),
        ft.Row(
            controls=[
                _kv("Metodo", str(plan.get("metodo_plan_pago") or "-")),
                _kv("Estado", str(plan.get("estado_plan_pago") or "-")),
                _kv("Monto", str(plan.get("monto_total_plan") or "-")),
                _kv("Moneda", str(plan.get("moneda") or "-")),
            ],
            wrap=True,
            spacing=18,
        ),
    ]
    for bloque in bloques:
        obligaciones = _list_or_empty(bloque.get("obligaciones"))
        controls.append(
            ft.ExpansionTile(
                title=ft.Text(
                    f"{bloque.get('numero_bloque', '-')}. "
                    f"{bloque.get('tipo_bloque', '-')} - "
                    f"{bloque.get('etiqueta_bloque', '-')}"
                ),
                subtitle=ft.Text(
                    f"Obligaciones: {len(obligaciones)} | "
                    f"Importe: {bloque.get('importe_total_bloque') or bloque.get('importe_cuota') or '-'}"
                ),
                controls=[
                    _obligaciones_table(obligaciones),
                    _json_view(
                        {
                            key: value
                            for key, value in bloque.items()
                            if key not in ("obligaciones", "clave_bloque")
                        }
                    ),
                ],
            )
        )
    return ft.Container(
        content=ft.Column(controls=controls, spacing=8),
        padding=12,
        border=_border_all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _obligaciones_table(obligaciones: list[dict[str, Any]]) -> ft.Control:
    if not obligaciones:
        return ft.Text("Sin obligaciones en este bloque.")
    return ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("N")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Etiqueta")),
            ft.DataColumn(ft.Text("Vencimiento")),
            ft.DataColumn(ft.Text("Importe")),
            ft.DataColumn(ft.Text("Saldo")),
            ft.DataColumn(ft.Text("Estado")),
            ft.DataColumn(ft.Text("Composiciones")),
        ],
        rows=[
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(item.get("numero_obligacion") or "-"))),
                    ft.DataCell(ft.Text(str(item.get("tipo_item_cronograma") or "-"))),
                    ft.DataCell(ft.Text(str(item.get("etiqueta_obligacion") or "-"))),
                    ft.DataCell(ft.Text(str(item.get("fecha_vencimiento") or "-"))),
                    ft.DataCell(ft.Text(str(item.get("importe_total") or "-"))),
                    ft.DataCell(ft.Text(str(item.get("saldo_pendiente") or "-"))),
                    ft.DataCell(ft.Text(str(item.get("estado_obligacion") or "-"))),
                    ft.DataCell(
                        ft.Text(str(len(_list_or_empty(item.get("composiciones")))))
                    ),
                ]
            )
            for item in obligaciones
        ],
    )


def _backend_error_panel(status_code: int, payload: Any) -> ft.Control:
    error = payload if isinstance(payload, dict) else {}
    details = error.get("details") if isinstance(error.get("details"), dict) else {}
    errors = details.get("errors") if isinstance(details, dict) else None
    controls: list[ft.Control] = [
        ft.Text("Error backend", weight=ft.FontWeight.W_700, color=ft.Colors.RED_700),
        _kv("Status HTTP", str(status_code), color=ft.Colors.RED_700),
        _kv("error_code", str(error.get("error_code") or "-")),
        _kv(
            "error_message",
            str(error.get("error_message") or error.get("detail") or "-"),
        ),
    ]
    error_lines = _backend_error_lines(errors)
    if error_lines:
        controls.append(ft.Text("details.errors", weight=ft.FontWeight.W_600))
        controls.extend(
            ft.Text(f"- {line}", color=ft.Colors.RED_700) for line in error_lines
        )
    return ft.Container(
        content=ft.Column(controls=controls, spacing=6),
        padding=12,
        border=_border_all(1, ft.Colors.RED_200),
        border_radius=6,
    )


def _backend_error_lines(errors: Any) -> list[str]:
    if isinstance(errors, list):
        return [_format_backend_error_item(error) for error in errors]
    if errors:
        return [_format_backend_error_item(errors)]
    return []


def _format_backend_error_item(error: Any) -> str:
    if isinstance(error, dict):
        for key in ("code", "error_code", "message", "error_message", "detail"):
            value = error.get(key)
            if value:
                return str(value)
        return json.dumps(error, ensure_ascii=True, default=str)
    return str(error)


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


def _data_envelope(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data")
    return payload


def _json_view(value: Any) -> ft.Control:
    return ft.TextField(
        value=json.dumps(value, ensure_ascii=True, indent=2, default=str),
        multiline=True,
        read_only=True,
        min_lines=8,
        max_lines=22,
    )


def _kv(label: str, value: str, color: str | None = None) -> ft.Control:
    return ft.Column(
        controls=[
            ft.Text(label, size=12, color=ft.Colors.BLUE_GREY_700),
            ft.Text(value, weight=ft.FontWeight.W_600, color=color),
        ],
        spacing=2,
        tight=True,
    )


def _decimal_or_none(value: str | None) -> Decimal | None:
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


def _decimal_or_zero(value: str | None) -> Decimal:
    return _decimal_or_none(value) or Decimal("0.00")


def _int_or_none(value: str | None) -> int | None:
    try:
        number = int(str(value or "").strip())
    except ValueError:
        return None
    return number if number > 0 else None


def _valid_date(value: str | None) -> bool:
    return _date_or_none(value) is not None


def _date_or_none(value: str | None) -> date | None:
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


def _format_ar_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _format_display_date(value: str | None) -> str:
    parsed = _date_or_none(value)
    return _format_ar_date(parsed) if parsed else str(value or "")


def _iso_date_or_empty(value: str | None) -> str:
    parsed = _date_or_none(value)
    return parsed.isoformat() if parsed else ""


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _list_or_empty(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def main(page: ft.Page) -> None:
    PlanPagoV2BloquesPrototype(page).run()


if __name__ == "__main__":
    ft.run(main)
