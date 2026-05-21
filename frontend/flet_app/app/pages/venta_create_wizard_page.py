from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import flet as ft


ORIGEN_DIRECTA = "VENTA_DIRECTA"
ORIGEN_RESERVA = "DESDE_RESERVA"


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


@dataclass
class WizardState:
    current_step: int = 0
    origen_venta: str = ORIGEN_DIRECTA
    id_reserva_venta: str = ""
    codigo_venta: str = "VTA-BORRADOR-001"
    fecha_venta: str = field(default_factory=lambda: _format_ar_date(date.today()))
    estado_venta: str = "BORRADOR"
    moneda: str = "ARS"
    observaciones: str = ""
    objetos: list[ObjetoVentaDraft] = field(default_factory=lambda: [
        ObjetoVentaDraft(
            tipo_objeto="TERRENO",
            id_objeto="1",
            descripcion="Lote demo Manzana A - Parcela 12",
            precio_asignado="12000000.00",
        )
    ])
    compradores: list[CompradorDraft] = field(default_factory=lambda: [
        CompradorDraft(id_persona="1", nombre="Comprador demo")
    ])
    monto_total: str = "12000000.00"
    condiciones_generales: str = ""
    tipo_pago: str = "FINANCIADO"
    bloques: list[BloquePlanDraft] = field(default_factory=lambda: [
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
        ),
    ])
    preview_generado: bool = False
    confirmacion_simulada: bool = False


STEPS = [
    "Origen",
    "Datos base / Reserva",
    "Objetos",
    "Compradores",
    "Condiciones",
    "Plan Pago V2",
    "Revisión final",
]


class VentaCreateWizardPage:
    def __init__(self, on_navigate: Callable[..., None]) -> None:
        self.on_navigate = on_navigate
        self.state = WizardState()
        self.root = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)

    def build(self) -> ft.Control:
        self._render(update=False)
        return self.root

    def _render(self, *, update: bool = True) -> None:
        self.root.controls = [
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("Nueva venta", size=28, weight=ft.FontWeight.W_700),
                            ft.Text(
                                "Alta guiada inicial. La persistencia completa queda pendiente de endpoints productivos.",
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.OutlinedButton(
                        "Volver a ventas",
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda _: self.on_navigate("ventas"),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
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
        if update and self.root.page is not None:
            self.root.update()

    def _progress_header(self) -> ft.Control:
        controls: list[ft.Control] = []
        for index, label in enumerate(STEPS):
            complete, errors = self._step_status(index)
            is_current = index == self.state.current_step
            icon = ft.Icons.CHECK_CIRCLE if complete else ft.Icons.ERROR_OUTLINE if errors else ft.Icons.RADIO_BUTTON_UNCHECKED
            color = ft.Colors.GREEN_700 if complete else ft.Colors.RED_700 if errors else ft.Colors.BLUE_GREY_500
            controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon, size=14, color=color),
                            ft.Text(
                                label,
                                size=12,
                                weight=ft.FontWeight.W_700 if is_current else ft.FontWeight.W_400,
                            ),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                    padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                    border=_border_all(1.5 if is_current else 1, ft.Colors.BLUE_300 if is_current else ft.Colors.BLUE_GREY_100),
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
            return self._step_origen()
        if step == 1:
            if self.state.origen_venta == ORIGEN_RESERVA:
                return self._step_reserva_existente()
            return self._step_datos_base()
        if step == 2:
            return self._step_objetos()
        if step == 3:
            return self._step_compradores()
        if step == 4:
            return self._step_condiciones()
        if step == 5:
            return self._step_plan_pago()
        return self._step_revision()

    def _step_origen(self) -> ft.Control:
        origen_group = ft.RadioGroup(
            value=self.state.origen_venta,
            content=ft.Column(
                controls=[
                    ft.Radio(value=ORIGEN_DIRECTA, label="Venta directa sin reserva"),
                    ft.Text(
                        "“Venta directa sin reserva” carga objetos y comprador manualmente.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Radio(value=ORIGEN_RESERVA, label="Desde reserva existente"),
                    ft.Text(
                        "“Desde reserva existente” usa una reserva ya cargada/confirmada.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                ],
                spacing=6,
            ),
            on_change=lambda e: self._set_origen(e.control.value),
        )
        return self._card(
            "Paso 1 - Origen de la venta",
            [
                ft.Text("Defini si la venta nace desde una reserva comercial o si se carga como venta directa."),
                origen_group,
                self._validation_box(0),
            ],
        )

    def _nav_buttons(self) -> ft.Control:
        return ft.Row(
            controls=[
                ft.OutlinedButton("Anterior", icon=ft.Icons.ARROW_BACK, disabled=self.state.current_step == 0, on_click=lambda _: self._go(-1)),
                ft.Button("Siguiente", icon=ft.Icons.ARROW_FORWARD, disabled=self.state.current_step >= len(STEPS) - 1, on_click=lambda _: self._go(1)),
            ],
            spacing=10,
        )

    def _card(self, title: str, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(content=ft.Column([ft.Text(title, size=20, weight=ft.FontWeight.W_700), *controls], spacing=12), padding=16, border=_border_all(1, ft.Colors.BLUE_GREY_100), border_radius=10)

    def _validation_box(self, step: int) -> ft.Control:
        _, errors = self._step_status(step)
        if not errors:
            return ft.Text("Paso completo o sin errores bloqueantes.", color=ft.Colors.GREEN_700)
        return ft.Column([ft.Text(error, color=ft.Colors.RED_700) for error in errors], spacing=4)

    def _flow_errors_before_review(self) -> list[str]:
        errors: list[str] = []
        for step in range(len(STEPS) - 1):
            errors.extend(self._step_status(step)[1])
        return errors

    def _set(self, field_name: str, value: str) -> None:
        setattr(self.state, field_name, value or "")
        if field_name in {"monto_total", "moneda"}:
            self.state.preview_generado = False
        self._render()

    def _set_tipo_pago(self, value: str | None) -> None:
        self.state.tipo_pago = value or "FINANCIADO"
        self.state.preview_generado = False
        self._render()

    def _go(self, delta: int) -> None:
        self.state.current_step = max(0, min(len(STEPS) - 1, self.state.current_step + delta))
        self._render()

    def _add_objeto_demo(self, _: Any) -> None:
        next_id = len(self.state.objetos) + 1
        self.state.objetos.append(ObjetoVentaDraft(tipo_objeto="UNIDAD_FUNCIONAL" if next_id % 2 == 0 else "TERRENO", id_objeto=str(next_id), descripcion=f"Objeto demo {next_id}", precio_asignado="1000000.00"))
        self._render()

    def _remove_objeto(self, _: Any) -> None:
        if self.state.objetos:
            self.state.objetos.pop()
        self._render()

    def _add_comprador_demo(self, _: Any) -> None:
        next_id = len(self.state.compradores) + 1
        self.state.compradores.append(CompradorDraft(id_persona=str(next_id), nombre=f"Comprador demo {next_id}"))
        self._render()

    def _remove_comprador(self, _: Any) -> None:
        if self.state.compradores:
            self.state.compradores.pop()
        self._render()

    def _add_bloque(self, tipo: str) -> None:
        label = {"ANTICIPO": "Anticipo", "TRAMO_CUOTAS": "Tramo", "REFUERZO": "Refuerzo"}.get(tipo, tipo)
        self.state.bloques.append(BloquePlanDraft(tipo_bloque=tipo, etiqueta=label, importe="1000000.00", vencimiento=_format_ar_date(date.today()), cantidad_cuotas="6" if tipo == "TRAMO_CUOTAS" else "", primer_vencimiento=_format_ar_date(date.today()) if tipo == "TRAMO_CUOTAS" else ""))
        self.state.preview_generado = False
        self._render()

    def _remove_bloque(self, _: Any) -> None:
        if self.state.bloques:
            self.state.bloques.pop()
        self.state.preview_generado = False
        self._render()

    def _generate_preview(self, _: Any) -> None:
        self.state.preview_generado = True
        self._render()

    def _confirm_simulated(self, _: Any) -> None:
        self.state.confirmacion_simulada = True
        self._render()

    def _suma_objetos(self) -> Decimal:
        return sum((_decimal_or_zero(obj.precio_asignado) for obj in self.state.objetos), Decimal("0.00")).quantize(Decimal("0.01"))

    def _suma_bloques(self) -> Decimal:
        return sum((_decimal_or_zero(bloque.importe) for bloque in self.state.bloques), Decimal("0.00")).quantize(Decimal("0.01"))

    def _preview_cronograma_local(self) -> list[list[str]]:
        rows: list[list[str]] = []
        for bloque in self.state.bloques:
            total = _decimal_or_zero(bloque.importe)
            if bloque.tipo_bloque == "TRAMO_CUOTAS":
                cantidad = _int_or_zero(bloque.cantidad_cuotas)
                cuota = (total / Decimal(cantidad or 1)).quantize(Decimal("0.01"))
                for index in range(1, cantidad + 1):
                    rows.append([bloque.tipo_bloque, f"Cuota {index}", bloque.primer_vencimiento or "-", _money(cuota)])
            else:
                rows.append([bloque.tipo_bloque, bloque.etiqueta or bloque.tipo_bloque, bloque.vencimiento or "-", _money(total)])
        return rows

    def _set_origen(self, value: str | None) -> None:
        self.state.origen_venta = value if value in {ORIGEN_DIRECTA, ORIGEN_RESERVA} else ORIGEN_DIRECTA
        self.state.confirmacion_simulada = False
        self._render()

    def _origen_label(self) -> str:
        if self.state.origen_venta == ORIGEN_RESERVA:
            return "Desde reserva existente"
        return "Venta directa sin reserva"

    def _step_datos_base(self) -> ft.Control:
        return self._card(
            "Paso 2 - Datos base",
            [
                ft.Row(
                    controls=[
                        ft.TextField(label="Codigo / referencia", value=self.state.codigo_venta, width=220, on_change=lambda e: self._set("codigo_venta", e.control.value)),
                        ft.TextField(label="Fecha venta", value=self.state.fecha_venta, width=160, on_change=lambda e: self._set("fecha_venta", e.control.value)),
                        ft.TextField(label="Estado", value=self.state.estado_venta, width=140, read_only=True),
                        ft.TextField(label="Moneda", value=self.state.moneda, width=110, on_change=lambda e: self._set("moneda", e.control.value.upper())),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                ft.TextField(label="Observaciones", value=self.state.observaciones, multiline=True, min_lines=3, on_change=lambda e: self._set("observaciones", e.control.value)),
                self._validation_box(1),
            ],
        )

    def _step_reserva_existente(self) -> ft.Control:
        return self._card(
            "Paso 2 - Reserva existente",
            [
                ft.Text(
                    "Selecciona la reserva de venta origen. Por ahora el control queda visual, sin conexion backend.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                ft.Row(
                    controls=[
                        ft.TextField(
                            label="ID reserva de venta",
                            value=self.state.id_reserva_venta,
                            width=220,
                            on_change=lambda e: self._set("id_reserva_venta", e.control.value),
                        ),
                        ft.OutlinedButton("Buscar reserva (pendiente)", icon=ft.Icons.SEARCH, disabled=True),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                ft.Text("Los objetos y compradores se tomaran de la reserva seleccionada cuando exista integracion backend."),
                self._validation_box(1),
            ],
        )

    def _step_objetos(self) -> ft.Control:
        desde_reserva = self.state.origen_venta == ORIGEN_RESERVA
        return self._card(
            "Paso 3 - Objetos inmobiliarios",
            [
                ft.Text(
                    "Objetos provenientes de la reserva seleccionada. Edicion manual deshabilitada en este origen."
                    if desde_reserva
                    else "Version inicial: selector demo. En productivo debe validar disponibilidad, modalidad y coherencia multiobjeto.",
                    color=ft.Colors.BLUE_GREY_700 if desde_reserva else None,
                ),
                _simple_table(["Tipo", "ID", "Descripcion", "Precio"], [_objeto_row(obj) for obj in self.state.objetos]),
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Agregar objeto demo", icon=ft.Icons.ADD, disabled=desde_reserva, on_click=self._add_objeto_demo),
                        ft.OutlinedButton("Quitar ultimo", icon=ft.Icons.DELETE_OUTLINE, disabled=desde_reserva, on_click=self._remove_objeto),
                    ],
                    spacing=10,
                ),
                self._validation_box(2),
            ],
        )

    def _step_compradores(self) -> ft.Control:
        desde_reserva = self.state.origen_venta == ORIGEN_RESERVA
        return self._card(
            "Paso 4 - Compradores / partes",
            [
                ft.Text(
                    "Compradores provenientes de la reserva seleccionada. Edicion manual deshabilitada en este origen."
                    if desde_reserva
                    else "Regla inicial: exactamente un comprador financiero resoluble para Plan Pago V2.",
                    color=ft.Colors.BLUE_GREY_700 if desde_reserva else None,
                ),
                _simple_table(["ID persona", "Nombre", "Rol"], [[c.id_persona, c.nombre, c.rol] for c in self.state.compradores]),
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Agregar comprador demo", icon=ft.Icons.ADD, disabled=desde_reserva, on_click=self._add_comprador_demo),
                        ft.OutlinedButton("Quitar ultimo", icon=ft.Icons.DELETE_OUTLINE, disabled=desde_reserva, on_click=self._remove_comprador),
                    ],
                    spacing=10,
                ),
                self._validation_box(3),
            ],
        )

    def _step_condiciones(self) -> ft.Control:
        suma_objetos = self._suma_objetos()
        monto_total = _decimal_or_zero(self.state.monto_total)
        diff = (monto_total - suma_objetos).quantize(Decimal("0.01"))
        return self._card(
            "Paso 5 - Condiciones comerciales",
            [
                ft.Text("Define el acuerdo comercial base. El modo de pago se carga en el paso siguiente.", color=ft.Colors.BLUE_GREY_700),
                ft.Row(
                    controls=[
                        ft.TextField(label="Monto total", value=self.state.monto_total, width=180, on_change=lambda e: self._set("monto_total", e.control.value)),
                        ft.TextField(label="Moneda", value=self.state.moneda, width=110, on_change=lambda e: self._set("moneda", e.control.value.upper())),
                    ],
                    spacing=10,
                ),
                ft.TextField(label="Condiciones generales", value=self.state.condiciones_generales, multiline=True, min_lines=3, on_change=lambda e: self._set("condiciones_generales", e.control.value)),
                _kv_grid([
                    ("Suma objetos", _money(suma_objetos)),
                    ("Monto total", _money(monto_total)),
                    ("Diferencia", _money(diff)),
                ]),
                self._validation_box(4),
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
            "Paso 6 - Plan Pago V2 por bloques",
            [
                ft.Text("Carga la estructura del plan. El cronograma se revisa en la pestana siguiente antes de confirmar.", color=ft.Colors.BLUE_GREY_700),
                tipo_pago_dropdown,
                _simple_table(
                    ["Tipo", "Etiqueta", "Importe/capital", "Cuotas", "Vencimiento"],
                    [[b.tipo_bloque, b.etiqueta, b.importe, b.cantidad_cuotas or "-", b.primer_vencimiento or b.vencimiento] for b in self.state.bloques],
                ),
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Agregar anticipo", icon=ft.Icons.ADD, on_click=lambda _: self._add_bloque("ANTICIPO")),
                        ft.OutlinedButton("Agregar tramo", icon=ft.Icons.ADD, on_click=lambda _: self._add_bloque("TRAMO_CUOTAS")),
                        ft.OutlinedButton("Agregar refuerzo", icon=ft.Icons.ADD, on_click=lambda _: self._add_bloque("REFUERZO")),
                        ft.OutlinedButton("Quitar ultimo", icon=ft.Icons.DELETE_OUTLINE, on_click=self._remove_bloque),
                    ],
                    wrap=True,
                    spacing=8,
                ),
                _kv_grid([
                    ("Monto total", _money(monto_total)),
                    ("Suma bloques", _money(total_bloques)),
                    ("Diferencia", _money((monto_total - total_bloques).quantize(Decimal("0.01")))),
                ]),
                ft.Row(
                    controls=[
                        ft.Button("Generar preview para revision", icon=ft.Icons.PREVIEW, on_click=self._generate_preview),
                        ft.Text("Preview listo para revision" if self.state.preview_generado else "Preview pendiente", color=ft.Colors.GREEN_700 if self.state.preview_generado else ft.Colors.AMBER_800),
                    ],
                    spacing=10,
                ),
                self._validation_box(5),
            ],
        )

    def _step_revision(self) -> ft.Control:
        errors = self._flow_errors_before_review()
        preview = self._preview_cronograma_local()
        reserva_value = self.state.id_reserva_venta or "-" if self.state.origen_venta == ORIGEN_RESERVA else "-"
        return self._card(
            "Paso 7 - Revision y confirmacion final",
            [
                ft.Text("Revisa toda la venta y el cronograma antes de confirmar. La confirmacion esta simulada hasta tener orquestacion backend."),
                _kv_grid([
                    ("Origen", self._origen_label()),
                    ("ID reserva", reserva_value),
                    ("Codigo", self.state.codigo_venta or "-"),
                    ("Estado", self.state.estado_venta),
                    ("Fecha", self.state.fecha_venta or "-"),
                    ("Moneda", self.state.moneda or "-"),
                    ("Objetos", str(len(self.state.objetos))),
                    ("Compradores", str(len(self.state.compradores))),
                    ("Monto total", self.state.monto_total or "-"),
                    ("Tipo pago", self.state.tipo_pago),
                    ("Bloques", str(len(self.state.bloques))),
                ]),
                ft.Text("Estructura del plan", weight=ft.FontWeight.W_700),
                _simple_table(["Tipo", "Etiqueta", "Importe/capital", "Cuotas", "Vencimiento"], [[b.tipo_bloque, b.etiqueta, b.importe, b.cantidad_cuotas or "-", b.primer_vencimiento or b.vencimiento] for b in self.state.bloques]),
                ft.Text("Cronograma preview", weight=ft.FontWeight.W_700),
                _simple_table(["Bloque", "Etiqueta", "Vencimiento", "Importe"], preview),
                ft.Text("Alertas", weight=ft.FontWeight.W_700),
                ft.Column([ft.Text(error, color=ft.Colors.RED_700) for error in errors] or [ft.Text("Sin alertas bloqueantes.", color=ft.Colors.GREEN_700)]),
                ft.Button("Confirmar venta completa (simulado)", icon=ft.Icons.CHECK_CIRCLE, disabled=bool(errors), on_click=self._confirm_simulated),
                ft.Text("Venta completa confirmada en modo simulado." if self.state.confirmacion_simulada else ""),
            ],
        )

    def _summary_panel(self) -> ft.Control:
        reserva_value = self.state.id_reserva_venta or "-" if self.state.origen_venta == ORIGEN_RESERVA else "-"
        return self._card(
            "Resumen",
            [
                _kv_grid([
                    ("Entrada", "Ventas -> Nueva venta"),
                    ("Origen", self._origen_label()),
                    ("ID reserva", reserva_value),
                    ("Estado", self.state.estado_venta),
                    ("Paso", f"{self.state.current_step + 1}/{len(STEPS)}"),
                    ("Objetos", str(len(self.state.objetos))),
                    ("Compradores", str(len(self.state.compradores))),
                    ("Suma objetos", _money(self._suma_objetos())),
                    ("Monto total", self.state.monto_total or "-"),
                    ("Suma bloques", _money(self._suma_bloques())),
                    ("Preview", "Si" if self.state.preview_generado else "No"),
                ]),
                ft.Divider(),
                ft.Text("Brechas detectadas", weight=ft.FontWeight.W_700),
                ft.Text("- crear venta BORRADOR real"),
                ft.Text("- asociar objetos en borrador"),
                ft.Text("- asociar comprador financiero"),
                ft.Text("- modo preview-only backend"),
                ft.Text("- confirmar venta completa"),
                ft.Text("- integrar origen desde reserva"),
            ],
        )

    def _step_status(self, step: int) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if step == 0:
            if self.state.origen_venta not in {ORIGEN_DIRECTA, ORIGEN_RESERVA}:
                errors.append("Debe seleccionarse un origen de venta.")
        elif step == 1 and self.state.origen_venta == ORIGEN_RESERVA:
            if not self.state.id_reserva_venta.strip():
                errors.append("Debe indicarse el ID de reserva de venta.")
        elif step == 1:
            if not self.state.codigo_venta.strip():
                errors.append("El codigo/referencia es requerido.")
            if _date_or_none(self.state.fecha_venta) is None:
                errors.append("La fecha debe tener formato dd/mm/aaaa o ISO.")
            if not self.state.moneda.strip():
                errors.append("La moneda es requerida.")
        elif step == 2:
            if not self.state.objetos:
                errors.append("Debe existir al menos un objeto inmobiliario.")
            if self._suma_objetos() <= 0:
                errors.append("La suma de precios de objetos debe ser mayor a cero.")
        elif step == 3:
            if len(self.state.compradores) != 1:
                errors.append("Plan Pago V2 inicial requiere exactamente un comprador financiero.")
        elif step == 4:
            monto = _decimal_or_zero(self.state.monto_total)
            if monto <= 0:
                errors.append("El monto total debe ser mayor a cero.")
            if monto != self._suma_objetos():
                errors.append("El monto total debe coincidir con la suma de objetos.")
        elif step == 5:
            if not self.state.bloques:
                errors.append("Debe existir al menos un bloque de plan de pago.")
            if self._suma_bloques() != _decimal_or_zero(self.state.monto_total):
                errors.append("La suma de bloques debe coincidir con el monto total.")
            if not self.state.preview_generado:
                errors.append("Debe generarse preview antes de confirmar.")
        elif step == 6:
            errors.extend(self._flow_errors_before_review())
        return (not errors, errors)


def _simple_table(headers: list[str], rows: list[list[str]]) -> ft.Control:
    return ft.DataTable(columns=[ft.DataColumn(ft.Text(header)) for header in headers], rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(str(cell))) for cell in row]) for row in rows])


def _kv_grid(items: list[tuple[str, str]]) -> ft.Control:
    return ft.Column(controls=[ft.Row(controls=[ft.Text(label, width=150, color=ft.Colors.BLUE_GREY_700), ft.Text(value, selectable=True)], vertical_alignment=ft.CrossAxisAlignment.START) for label, value in items], spacing=6)


def _objeto_row(obj: ObjetoVentaDraft) -> list[str]:
    return [obj.tipo_objeto, obj.id_objeto, obj.descripcion, obj.precio_asignado]


def _border_all(width: int | float, color: ft.ColorValue) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


def _decimal_or_zero(value: object) -> Decimal:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return Decimal("0.00")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


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


def _format_ar_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _money(value: Decimal) -> str:
    return f"{value:.2f}"
