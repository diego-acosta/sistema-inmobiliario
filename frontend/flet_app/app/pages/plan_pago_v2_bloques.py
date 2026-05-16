from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

import flet as ft

from app.api_client import ApiClient
from app.components.entity_table import entity_table


UNIQUE_BLOCKS = ("CONTADO", "ANTICIPO", "REFUERZO", "SALDO")


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
class PanelState:
    bloques: list[BloqueDraft] = field(default_factory=list)
    current_step: int = 1
    loading: bool = False
    preview_data: dict[str, Any] | None = None
    preview_stale: bool = True
    validation_requested: bool = False
    error_message: str | None = None
    generated_message: str | None = None
    generated_data: dict[str, Any] | None = None


class PlanPagoV2BloquesPanel:
    def __init__(
        self,
        *,
        api: ApiClient,
        id_venta: int,
        monto_total: Any = None,
        moneda: str | None = None,
        existing_plan: dict[str, Any] | None = None,
        on_generated=None,
    ) -> None:
        self.api = api
        self.id_venta = id_venta
        self.existing_plan = existing_plan if isinstance(existing_plan, dict) else None
        self.on_generated = on_generated
        self.state = PanelState()

        self.monto_total_plan = ft.TextField(
            label="Monto total",
            value=_money(_decimal_or_zero(str(monto_total or "0"))),
            width=170,
            on_change=self._on_input_change,
        )
        self.moneda = ft.TextField(
            label="Moneda",
            value=str(moneda or "ARS"),
            width=110,
            on_change=self._on_input_change,
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

        self.validation_banner = ft.Container(visible=False)
        self.existing_plan_column = ft.Column(spacing=10)
        self.summary = ft.Column(spacing=4)
        self.blocks_column = ft.ListView(spacing=10, height=360)
        self.preview_column = ft.Column(spacing=8)
        self.generated_column = ft.Column(spacing=8)
        self.tramo_cuota_texts: dict[str, ft.Text] = {}

        self.preview_button = ft.Button(
            "Vista previa del plan",
            icon=ft.Icons.PREVIEW,
            on_click=self._load_preview,
        )
        self.back_button = ft.OutlinedButton(
            "Volver y modificar",
            icon=ft.Icons.ARROW_BACK,
            on_click=self._back_to_edit,
        )
        self.generate_button = ft.Button(
            "Generar plan definitivo",
            icon=ft.Icons.SEND,
            on_click=self._generate,
        )

        self._reset_blocks_for_tipo("CONTADO")

    def build(self) -> ft.Control:
        self._render_existing_plan()
        controls: list[ft.Control] = [self.existing_plan_column]
        controls.append(self._build_wizard_container())
        self._render_blocks()
        self._refresh_light(update_page=False, rebuild_step=True)
        return ft.Column(controls=controls, spacing=14)

    def _render_existing_plan(self) -> None:
        if self.existing_plan is not None:
            self.existing_plan_column.controls = [_existing_plan_view(self.existing_plan)]
            return
        self.existing_plan_column.controls = [
            ft.Container(
                content=ft.Text("La venta no tiene plan de pago V2 generado."),
                padding=12,
                border=_border_all(1, ft.Colors.BLUE_GREY_100),
                border_radius=6,
            )
        ]

    def _build_wizard_container(self) -> ft.Control:
        self.wizard_content = ft.Column(spacing=12)
        return ft.Container(
            content=self.wizard_content,
            padding=14,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
        )

    def _build_step1(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Armar plan", size=18, weight=ft.FontWeight.W_700),
                ft.Row(
                    controls=[
                        ft.Text(f"Venta {self.id_venta}", weight=ft.FontWeight.W_600),
                        self.moneda,
                        self.monto_total_plan,
                        self.tipo_pago,
                    ],
                    wrap=True,
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.validation_banner,
                ft.Row(
                    controls=self._add_block_buttons(),
                    wrap=True,
                    spacing=8,
                ),
                self.blocks_column,
                self.summary,
                ft.Row(
                    controls=[self.preview_button],
                    wrap=True,
                    spacing=10,
                ),
            ],
            spacing=12,
        )

    def _build_step2(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Vista previa del plan", size=18, weight=ft.FontWeight.W_700),
                self.preview_column,
                ft.Row(
                    controls=[self.back_button, self.generate_button],
                    wrap=True,
                    spacing=10,
                ),
                self.generated_column,
            ],
            spacing=12,
        )

    def _render_current_step(self) -> None:
        self.wizard_content.controls = [
            self._build_step2() if self.state.current_step == 2 else self._build_step1()
        ]

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
        values = [selected] if isinstance(selected, str) else list(selected)
        value = str(values[0]) if values else "CONTADO"
        return value if value in ("CONTADO", "FINANCIADO") else "CONTADO"

    def _on_tipo_pago_change(self, _: ft.ControlEvent) -> None:
        tipo_pago = self._selected_tipo_pago()
        self.tipo_pago.selected = [tipo_pago]
        self._clear_preview()
        self.state.current_step = 1
        self._reset_blocks_for_tipo(tipo_pago)
        self._render_blocks()
        self._refresh_light()

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
        total_cuotas = max(monto_total - anticipo, Decimal("0"))
        self.state.bloques = [
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

    def _add_block(self, tipo_bloque: str) -> None:
        if self._selected_tipo_pago() == "CONTADO":
            self.state.error_message = "CONTADO solo admite un bloque CONTADO."
            self.state.validation_requested = True
            self._refresh_light()
            return
        labels = {
            "ANTICIPO": "Anticipo",
            "TRAMO_CUOTAS": "Tramo de cuotas",
            "REFUERZO": "Refuerzo",
            "SALDO": "Saldo final",
        }
        self.state.bloques.append(self._new_block(tipo_bloque, labels[tipo_bloque]))
        self._clear_preview()
        self._recalculate_tramo_dates()
        self._render_blocks()
        self._refresh_light()

    def _remove_block(self, uid: str) -> None:
        self.state.bloques = [bloque for bloque in self.state.bloques if bloque.uid != uid]
        self._clear_preview()
        self._recalculate_tramo_dates()
        self._render_blocks()
        self._refresh_light()

    def _new_block(self, tipo_bloque: str, label: str) -> BloqueDraft:
        bloque = BloqueDraft(uid=str(uuid4()), tipo_bloque=tipo_bloque, etiqueta_bloque=label)
        if tipo_bloque == "TRAMO_CUOTAS":
            bloque.fecha_primer_vencimiento = self._next_tramo_first_due() or _format_ar_date(date.today())
            bloque.periodicidad = "MENSUAL"
        else:
            bloque.fecha_vencimiento = _format_ar_date(date.today())
        return bloque

    def _render_blocks(self) -> None:
        self.tramo_cuota_texts = {}
        self.blocks_column.controls = [
            self._block_card(index, bloque)
            for index, bloque in enumerate(self.state.bloques, start=1)
        ] or [ft.Text("Sin bloques cargados.")]

    def _block_card(self, index: int, bloque: BloqueDraft) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Text(f"{index}. {bloque.tipo_bloque}", weight=ft.FontWeight.W_700),
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
            cuota_text = ft.Text(self._cuota_label(bloque), weight=ft.FontWeight.W_600)
            self.tramo_cuota_texts[bloque.uid] = cuota_text
            controls.append(
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
                        ft.TextField(
                            label="Primer vencimiento",
                            value=bloque.fecha_primer_vencimiento,
                            width=170,
                            on_change=lambda e, b=bloque: self._update_block(
                                b, "fecha_primer_vencimiento", e.control.value
                            ),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text("Cuota base", size=12, color=ft.Colors.BLUE_GREY_700),
                                cuota_text,
                            ],
                            spacing=2,
                            tight=True,
                        ),
                    ],
                    wrap=True,
                    spacing=10,
                )
            )
        else:
            controls.append(
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
                    ],
                    wrap=True,
                    spacing=10,
                )
            )
        return ft.Container(
            content=ft.Column(controls=controls, spacing=10),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
        )

    def _update_block(self, bloque: BloqueDraft, field_name: str, value: str | None) -> None:
        setattr(bloque, field_name, value or "")
        if bloque.tipo_bloque == "TRAMO_CUOTAS" and field_name in {
            "cantidad_cuotas",
            "fecha_primer_vencimiento",
        }:
            self._recalculate_tramo_dates()
        self._clear_preview()
        self.state.current_step = 1
        self.state.validation_requested = False
        self.state.error_message = None
        self._refresh_light(rebuild_step=False)

    def _on_input_change(self, _: ft.ControlEvent) -> None:
        self._clear_preview()
        self.state.current_step = 1
        self.state.validation_requested = False
        self.state.error_message = None
        self._refresh_light(rebuild_step=False)

    def _refresh_light(self, *, update_page: bool = True, rebuild_step: bool = True) -> None:
        errors = self._validate()
        self._refresh_tramo_labels()
        self._render_summary(errors)
        self._render_validation(errors)
        self._render_preview()
        self.preview_button.disabled = self.state.loading
        self.generate_button.disabled = (
            self.state.loading
            or self.state.current_step != 2
            or bool(errors)
            or self.state.preview_data is None
            or self.state.preview_stale
        )
        self.back_button.disabled = self.state.loading
        if rebuild_step:
            self._render_current_step()
        if update_page:
            self.wizard_content.update()

    def _render_summary(self, errors: list[str]) -> None:
        monto = _decimal_or_zero(self.monto_total_plan.value)
        total = self._blocks_total()
        diff = monto - total
        color = ft.Colors.GREEN_700 if diff == Decimal("0.00") else ft.Colors.RED_700
        status = "Listo para vista previa."
        status_color = ft.Colors.GREEN_700
        if errors and self.state.validation_requested:
            status = "Revisar validaciones."
            status_color = ft.Colors.RED_700
        elif self.state.preview_stale and self.state.preview_data is not None:
            status = "Vista previa desactualizada."
            status_color = ft.Colors.AMBER_800
        self.summary.controls = [
            ft.Text("Resumen", weight=ft.FontWeight.W_700),
            ft.Row(
                controls=[
                    _kv("Monto total", _money(monto)),
                    _kv("Suma bloques", _money(total)),
                    _kv("Diferencia", _money(diff), color=color),
                ],
                wrap=True,
                spacing=16,
            ),
            ft.Text(status, color=status_color),
        ]

    def _render_validation(self, errors: list[str]) -> None:
        self.validation_banner.visible = bool(self.state.error_message) or (
            self.state.validation_requested and bool(errors)
        )
        messages = list(errors) if self.state.validation_requested else []
        if self.state.error_message:
            messages.append(self.state.error_message)
        self.validation_banner.content = ft.Column(
            controls=[ft.Text(message, color=ft.Colors.RED_700) for message in messages],
            spacing=4,
        )
        self.validation_banner.padding = 10
        self.validation_banner.border = _border_all(1, ft.Colors.RED_200)
        self.validation_banner.border_radius = 6

    def _render_preview(self) -> None:
        if self.state.preview_data is None:
            self.preview_column.controls = [
                ft.Text("Solicita la vista previa para revisar el cronograma oficial.")
            ]
            return
        controls: list[ft.Control] = []
        if self.state.preview_stale:
            controls.append(
                ft.Text(
                    "Vista previa desactualizada. Volve y actualizala antes de generar.",
                    color=ft.Colors.AMBER_800,
                    weight=ft.FontWeight.W_600,
                )
            )
        controls.append(_preview_data_view(self.state.preview_data))
        self.preview_column.controls = controls

    def _load_preview(self, _: ft.ControlEvent) -> None:
        self.state.validation_requested = True
        self.state.error_message = None
        errors = self._validate()
        if errors:
            self._refresh_light()
            return
        self.state.loading = True
        self._refresh_light()
        result = self.api.preview_plan_pago_venta_v2_por_bloques(
            self.id_venta, self._payload()
        )
        self.state.loading = False
        if result.success and isinstance(result.data, dict):
            self.state.preview_data = result.data
            self.state.preview_stale = False
            self.state.current_step = 2
        else:
            self.state.current_step = 1
            self.state.error_message = result.error_message or "No se pudo obtener la vista previa."
        self._refresh_light()

    def _back_to_edit(self, _: ft.ControlEvent) -> None:
        self.state.current_step = 1
        self.state.error_message = None
        self._render_blocks()
        self._refresh_light()

    def _generate(self, _: ft.ControlEvent) -> None:
        if self.state.preview_data is None or self.state.preview_stale:
            self.state.error_message = "Actualiza la vista previa antes de generar."
            self._refresh_light()
            return
        self.state.loading = True
        self.generated_column.controls = []
        self._refresh_light()
        result = self.api.generar_plan_pago_venta_v2_por_bloques(
            self.id_venta, self._payload()
        )
        self.state.loading = False
        if result.success and isinstance(result.data, dict):
            self.state.generated_data = result.data
            self.existing_plan = _plan_from_generate_response(result.data)
            self._render_existing_plan()
            self.generated_column.controls = [_generated_summary(result.data)]
            if self.on_generated is not None:
                self.on_generated()
        else:
            self.generated_column.controls = [
                ft.Text(result.error_message or "No se pudo generar el plan.", color=ft.Colors.RED_700)
            ]
        self._refresh_light()

    def _validate(self) -> list[str]:
        errors: list[str] = []
        monto = _decimal_or_none(self.monto_total_plan.value)
        if monto is None or monto <= 0:
            errors.append("El monto total debe ser mayor a cero.")
        if not (self.moneda.value or "").strip():
            errors.append("La moneda es requerida.")
        tipo_pago = self._selected_tipo_pago()
        if tipo_pago == "CONTADO" and (
            len(self.state.bloques) != 1
            or self.state.bloques[0].tipo_bloque != "CONTADO"
        ):
            errors.append("CONTADO solo admite un bloque CONTADO.")
        if tipo_pago == "FINANCIADO" and any(
            bloque.tipo_bloque == "CONTADO" for bloque in self.state.bloques
        ):
            errors.append("FINANCIADO no admite bloque CONTADO.")
        for bloque in self.state.bloques:
            if bloque.tipo_bloque == "TRAMO_CUOTAS":
                if _decimal_or_none(bloque.capital_tramo) is None:
                    errors.append("TRAMO_CUOTAS: capital requerido.")
                if _int_or_none(bloque.cantidad_cuotas) is None:
                    errors.append("TRAMO_CUOTAS: cantidad de cuotas requerida.")
                if _date_or_none(bloque.fecha_primer_vencimiento) is None:
                    errors.append("TRAMO_CUOTAS: primer vencimiento requerido.")
            else:
                if _decimal_or_none(bloque.importe_total_bloque) is None:
                    errors.append(f"{bloque.tipo_bloque}: importe requerido.")
                if _date_or_none(bloque.fecha_vencimiento) is None:
                    errors.append(f"{bloque.tipo_bloque}: vencimiento requerido.")
        if monto is not None and self._blocks_total() != monto:
            errors.append("La suma de bloques debe coincidir con el monto total.")
        return _dedupe(errors)

    def _payload(self) -> dict[str, Any]:
        return {
            "tipo_pago": self._selected_tipo_pago(),
            "monto_total_plan": float(_decimal_or_zero(self.monto_total_plan.value)),
            "moneda": (self.moneda.value or "ARS").strip().upper(),
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
                    "importe_total_bloque": float(_decimal_or_zero(bloque.capital_tramo)),
                    "cantidad_cuotas": _int_or_none(bloque.cantidad_cuotas),
                    "fecha_primer_vencimiento": _iso_date_or_empty(
                        bloque.fecha_primer_vencimiento
                    ),
                    "periodicidad": "MENSUAL",
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

    def _blocks_total(self) -> Decimal:
        total = Decimal("0.00")
        for bloque in self.state.bloques:
            total += _decimal_or_zero(
                bloque.capital_tramo
                if bloque.tipo_bloque == "TRAMO_CUOTAS"
                else bloque.importe_total_bloque
            )
        return total.quantize(Decimal("0.01"))

    def _clear_preview(self) -> None:
        if self.state.preview_data is not None:
            self.state.preview_stale = True
        self.state.generated_message = None

    def _refresh_tramo_labels(self) -> None:
        for bloque in self.state.bloques:
            text = self.tramo_cuota_texts.get(bloque.uid)
            if text is not None:
                text.value = self._cuota_label(bloque)

    def _cuota_label(self, bloque: BloqueDraft) -> str:
        capital = _decimal_or_none(bloque.capital_tramo)
        cantidad = _int_or_none(bloque.cantidad_cuotas)
        if capital is None or cantidad is None:
            return "-"
        return _money((capital / Decimal(cantidad)).quantize(Decimal("0.01")))

    def _next_tramo_first_due(self) -> str | None:
        previous_due: date | None = None
        for bloque in self.state.bloques:
            if bloque.tipo_bloque == "TRAMO_CUOTAS":
                previous_due = self._last_due_for_tramo(bloque)
        return _format_ar_date(_add_months(previous_due, 1)) if previous_due else None

    def _recalculate_tramo_dates(self) -> None:
        previous_due: date | None = None
        first_seen = False
        for bloque in self.state.bloques:
            if bloque.tipo_bloque != "TRAMO_CUOTAS":
                continue
            if not first_seen:
                first_seen = True
                previous_due = self._last_due_for_tramo(bloque)
                continue
            if previous_due is not None:
                bloque.fecha_primer_vencimiento = _format_ar_date(
                    _add_months(previous_due, 1)
                )
                previous_due = self._last_due_for_tramo(bloque)

    def _last_due_for_tramo(self, bloque: BloqueDraft) -> date | None:
        first_due = _date_or_none(bloque.fecha_primer_vencimiento)
        cantidad = _int_or_none(bloque.cantidad_cuotas)
        if first_due is None or cantidad is None:
            return None
        return _add_months(first_due, cantidad - 1)


def _existing_plan_view(plan: dict[str, Any]) -> ft.Control:
    bloques = _safe_list(plan.get("bloques"))
    return ft.Column(
        controls=[
            ft.Text("Plan Pago V2 por bloques generado", size=18, weight=ft.FontWeight.W_700),
            key_value_grid_local(
                [
                    ("Metodo", plan.get("metodo_plan_pago")),
                    ("Estado", plan.get("estado_plan_pago")),
                    ("Monto", plan.get("monto_total_plan")),
                    ("Moneda", plan.get("moneda")),
                    ("Bloques", len(bloques)),
                ]
            ),
            _existing_blocks_view(bloques),
        ],
        spacing=10,
    )


def _existing_blocks_view(bloques: list[dict[str, Any]]) -> ft.Control:
    controls: list[ft.Control] = []
    for bloque in bloques:
        obligaciones = _safe_list(bloque.get("obligaciones"))
        controls.append(
            ft.ExpansionTile(
                title=ft.Text(
                    f"{bloque.get('tipo_bloque', '-')} - {bloque.get('etiqueta_bloque', '-')}"
                ),
                subtitle=ft.Text(
                    f"Obligaciones: {len(obligaciones)} | "
                    f"Importe: {bloque.get('importe_total_bloque') or bloque.get('importe_cuota') or '-'}"
                ),
                controls=[_obligaciones_table(obligaciones)],
            )
        )
    return ft.Column(controls=controls or [ft.Text("Sin bloques.")], spacing=8)


def _preview_data_view(data: dict[str, Any]) -> ft.Control:
    bloques = _safe_list(data.get("bloques"))
    obligaciones = _safe_list(data.get("obligaciones"))
    redondeos = _safe_list(data.get("redondeos"))
    controls: list[ft.Control] = [
        key_value_grid_local(
            [
                ("Monto total", data.get("monto_total_plan")),
                ("Total calculado", data.get("total_calculado")),
                ("Diferencia", data.get("diferencia")),
                ("Bloques", len(bloques)),
                ("Obligaciones", len(obligaciones)),
            ]
        ),
        ft.Text("Bloques", weight=ft.FontWeight.W_700),
        _preview_blocks_table(bloques),
        ft.Text("Cronograma", weight=ft.FontWeight.W_700),
        _preview_obligaciones_table(obligaciones),
    ]
    if redondeos:
        controls.extend([ft.Text("Redondeos", weight=ft.FontWeight.W_700), _redondeos_table(redondeos)])
    return ft.Column(controls=controls, spacing=10)


def _preview_blocks_table(rows: list[dict[str, Any]]) -> ft.Control:
    return entity_table(
        columns=[
            ("Tipo", "tipo_bloque"),
            ("Etiqueta", "etiqueta_bloque"),
            ("Importe", "importe"),
            ("Cuotas", "cantidad_cuotas"),
            ("Primer vencimiento", "fecha_primer_vencimiento"),
        ],
        rows=[
            {
                "tipo_bloque": row.get("tipo_bloque"),
                "etiqueta_bloque": row.get("etiqueta_bloque"),
                "importe": row.get("importe_total_bloque") or row.get("importe_cuota"),
                "cantidad_cuotas": row.get("cantidad_cuotas"),
                "fecha_primer_vencimiento": _format_display_date(row.get("fecha_primer_vencimiento")),
            }
            for row in rows
        ],
    )


def _preview_obligaciones_table(rows: list[dict[str, Any]]) -> ft.Control:
    return entity_table(
        columns=[
            ("Bloque", "bloque"),
            ("Tipo", "tipo"),
            ("Etiqueta", "etiqueta"),
            ("Vencimiento", "vencimiento"),
            ("Importe", "importe"),
            ("Moneda", "moneda"),
        ],
        rows=[
            {
                "bloque": row.get("tipo_bloque"),
                "tipo": row.get("tipo_item_cronograma"),
                "etiqueta": row.get("etiqueta_obligacion"),
                "vencimiento": _format_display_date(row.get("fecha_vencimiento")),
                "importe": row.get("importe_total"),
                "moneda": row.get("moneda"),
            }
            for row in rows
        ],
    )


def _obligaciones_table(rows: list[dict[str, Any]]) -> ft.Control:
    return entity_table(
        columns=[
            ("Tipo", "tipo"),
            ("Etiqueta", "etiqueta"),
            ("Vencimiento", "vencimiento"),
            ("Importe", "importe"),
            ("Saldo", "saldo"),
            ("Estado", "estado"),
        ],
        rows=[
            {
                "tipo": row.get("tipo_item_cronograma"),
                "etiqueta": row.get("etiqueta_obligacion"),
                "vencimiento": _format_display_date(row.get("fecha_vencimiento")),
                "importe": row.get("importe_total"),
                "saldo": row.get("saldo_pendiente"),
                "estado": row.get("estado_obligacion"),
            }
            for row in rows
        ],
    )


def _redondeos_table(rows: list[dict[str, Any]]) -> ft.Control:
    return entity_table(
        columns=[
            ("Bloque", "tipo_bloque"),
            ("Ajuste ultima cuota", "ajuste_ultima_cuota"),
        ],
        rows=rows,
    )


def _generated_summary(data: dict[str, Any]) -> ft.Control:
    bloques = _safe_list(data.get("bloques"))
    obligaciones = _safe_list(data.get("obligaciones"))
    plan = data.get("plan_pago_venta") if isinstance(data.get("plan_pago_venta"), dict) else {}
    return ft.Container(
        content=key_value_grid_local(
            [
                ("Plan generado", plan.get("metodo_plan_pago") or "PLAN_POR_BLOQUES"),
                ("Estado", plan.get("estado_plan_pago")),
                ("Bloques", len(bloques)),
                ("Obligaciones", len(obligaciones)),
                ("Total", plan.get("monto_total_plan")),
            ]
        ),
        padding=12,
        border=_border_all(1, ft.Colors.GREEN_200),
        border_radius=6,
    )


def _plan_from_generate_response(data: dict[str, Any]) -> dict[str, Any] | None:
    plan = data.get("plan_pago_venta")
    if not isinstance(plan, dict):
        return None
    bloques = _safe_list(data.get("bloques"))
    obligaciones = _safe_list(data.get("obligaciones"))
    by_block: dict[Any, list[dict[str, Any]]] = {}
    for obligacion in obligaciones:
        key = obligacion.get("id_plan_pago_venta_bloque")
        by_block.setdefault(key, []).append(obligacion)
    visible_bloques: list[dict[str, Any]] = []
    for bloque in bloques:
        copy = dict(bloque)
        copy["obligaciones"] = by_block.get(bloque.get("id_plan_pago_venta_bloque"), [])
        visible_bloques.append(copy)
    return {**plan, "bloques": visible_bloques}


def key_value_grid_local(items: list[tuple[str, object]]) -> ft.Control:
    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text(label, width=170, color=ft.Colors.BLUE_GREY_700),
                    ft.Text(_format_value(value), selectable=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            for label, value in items
        ],
        spacing=6,
    )


def _border_all(width: int | float, color: ft.ColorValue) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


def _safe_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


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


def _int_or_none(value: object) -> int | None:
    try:
        number = int(str(value or "").strip())
    except ValueError:
        return None
    return number if number > 0 else None


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


def _format_ar_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _format_display_date(value: object) -> str:
    parsed = _date_or_none(value)
    return _format_ar_date(parsed) if parsed else str(value or "")


def _iso_date_or_empty(value: object) -> str:
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


def _format_value(value: object) -> str:
    return "-" if value is None else str(value)


def _kv(label: str, value: str, color: str | None = None) -> ft.Control:
    return ft.Column(
        controls=[
            ft.Text(label, size=12, color=ft.Colors.BLUE_GREY_700),
            ft.Text(value, weight=ft.FontWeight.W_600, color=color),
        ],
        spacing=2,
        tight=True,
    )


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
