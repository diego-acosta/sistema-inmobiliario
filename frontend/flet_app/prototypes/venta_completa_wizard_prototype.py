from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import flet as ft


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
            compradores=[
                CompradorDraft(id_persona="1", nombre="Comprador demo")
            ],
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
                ),
            ],
        )
        self.root = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=14)

    def build(self) -> ft.Control:
        self._render()
        return self.root

    def _render(self) -> None:
        self.root.controls = [
            ft.Text("Prototipo — Alta guiada de venta completa", size=28, weight=ft.FontWeight.W_700),
            ft.Text(
                "Flujo incremental con venta en BORRADOR. Este prototipo no persiste datos ni modifica backend.",
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
            icon = ft.Icons.CHECK_CIRCLE if complete else ft.Icons.ERROR_OUTLINE if errors else ft.Icons.RADIO_BUTTON_UNCHECKED
            color = ft.Colors.GREEN_700 if complete else ft.Colors.RED_700 if errors else ft.Colors.BLUE_GREY_500
            controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon, size=18, color=color),
                            ft.Text(label, weight=ft.FontWeight.W_700 if is_current else ft.FontWeight.W_400),
                        ],
                        spacing=6,
                    ),
                    padding=8,
                    border=_border_all(2 if is_current else 1, ft.Colors.BLUE_300 if is_current else ft.Colors.BLUE_GREY_100),
                    border_radius=20,
                )
            )
        return ft.Row(controls=controls, wrap=True, spacing=8)

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
                        ft.TextField(label="Código / referencia", value=self.state.codigo_venta, width=220, on_change=lambda e: self._set("codigo_venta", e.control.value)),
                        ft.TextField(label="Fecha venta", value=self.state.fecha_venta, width=160, on_change=lambda e: self._set("fecha_venta", e.control.value)),
                        ft.TextField(label="Estado", value=self.state.estado_venta, width=140, read_only=True),
                        ft.TextField(label="Moneda", value=self.state.moneda, width=110, on_change=lambda e: self._set("moneda", e.control.value.upper())),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                ft.TextField(label="Observaciones", value=self.state.observaciones, multiline=True, min_lines=3, on_change=lambda e: self._set("observaciones", e.control.value)),
            ],
        )

    def _step_objetos(self) -> ft.Control:
        rows = [_objeto_row(obj) for obj in self.state.objetos]
        return self._card(
            "Paso 2 — Objetos inmobiliarios",
            [
                ft.Text("En productivo este paso debería validar disponibilidad, modalidad de comercialización y coherencia multiobjeto."),
                _simple_table(
                    ["Tipo", "ID", "Descripción", "Precio"],
                    rows,
                ),
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Agregar objeto demo", icon=ft.Icons.ADD, on_click=self._add_objeto_demo),
                        ft.OutlinedButton("Quitar último", icon=ft.Icons.DELETE_OUTLINE, on_click=self._remove_objeto),
                    ],
                    spacing=10,
                ),
                self._validation_box(1),
            ],
        )

    def _step_compradores(self) -> ft.Control:
        return self._card(
            "Paso 3 — Compradores / partes",
            [
                ft.Text("Regla inicial: exactamente un comprador financiero resoluble para generar Plan Pago V2."),
                _simple_table(
                    ["ID persona", "Nombre", "Rol"],
                    [[c.id_persona, c.nombre, c.rol] for c in self.state.compradores],
                ),
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Agregar comprador demo", icon=ft.Icons.ADD, on_click=self._add_comprador_demo),
                        ft.OutlinedButton("Quitar último", icon=ft.Icons.DELETE_OUTLINE, on_click=self._remove_comprador),
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
                self._validation_box(3),
            ],
        )

    def _step_plan_pago(self) -> ft.Control:
        total_bloques = self._suma_bloques()
        monto_total = _decimal_or_zero(self.state.monto_total)
        preview = self._preview_cronograma_local()
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
                    "Prototipo visual. En productivo este paso debe consumir preview backend oficial y reutilizar PlanPagoV2BloquesPanel.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
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
                        ft.OutlinedButton("Quitar último", icon=ft.Icons.DELETE_OUTLINE, on_click=self._remove_bloque),
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
                        ft.Button("Generar preview simulado", icon=ft.Icons.PREVIEW, on_click=self._generate_preview),
                        ft.Text("Preview generado" if self.state.preview_generado else "Preview pendiente", color=ft.Colors.GREEN_700 if self.state.preview_generado else ft.Colors.AMBER_800),
                    ],
                    spacing=10,
                ),
                ft.Text("Cronograma preview", weight=ft.FontWeight.W_700),
                _simple_table(["Bloque", "Etiqueta", "Vencimiento", "Importe"], preview),
                self._validation_box(4),
            ],
        )

    def _step_revision(self) -> ft.Control:
        errors = self._all_errors()
        return self._card(
            "Paso 6 — Revisión y confirmación final",
            [
                ft.Text("La confirmación está simulada en este prototipo. La implementación productiva debe orquestar servicios reales."),
                _kv_grid([
                    ("Código", self.state.codigo_venta or "-"),
                    ("Estado", self.state.estado_venta),
                    ("Fecha", self.state.fecha_venta or "-"),
                    ("Moneda", self.state.moneda or "-"),
                    ("Objetos", str(len(self.state.objetos))),
                    ("Compradores", str(len(self.state.compradores))),
                    ("Monto total", self.state.monto_total or "-"),
                    ("Tipo pago", self.state.tipo_pago),
                    ("Bloques", str(len(self.state.bloques))),
                ]),
                ft.Text("Alertas", weight=ft.FontWeight.W_700),
                ft.Column([ft.Text(error, color=ft.Colors.RED_700) for error in errors] or [ft.Text("Sin alertas bloqueantes.", color=ft.Colors.GREEN_700)]),
                ft.Button("Confirmar venta completa (simulado)", icon=ft.Icons.CHECK_CIRCLE, disabled=bool(errors), on_click=self._confirm_simulated),
                ft.Text("Venta completa confirmada en modo prototipo." if self.state.confirmacion_simulada else ""),
            ],
        )

    def _summary_panel(self) -> ft.Control:
        return self._card(
            "Resumen",
            [
                _kv_grid([
                    ("Estado", self.state.estado_venta),
                    ("Paso", f"{self.state.current_step + 1}/{len(STEPS)}"),
                    ("Objetos", str(len(self.state.objetos))),
                    ("Compradores", str(len(self.state.compradores))),
                    ("Suma objetos", _money(self._suma_objetos())),
                    ("Monto total", self.state.monto_total or "-"),
                    ("Suma bloques", _money(self._suma_bloques())),
                    ("Preview", "Sí" if self.state.preview_generado else "No"),
                ]),
                ft.Divider(),
                ft.Text("Brechas esperadas a validar", weight=ft.FontWeight.W_700),
                ft.Text("• crear/retomar venta BORRADOR"),
                ft.Text("• asociar objetos en borrador"),
                ft.Text("• asociar comprador financiero"),
                ft.Text("• modo preview-only para Plan Pago V2"),
                ft.Text("• confirmar venta completa"),
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
        return ft.Container(
            content=ft.Column([ft.Text(title, size=20, weight=ft.FontWeight.W_700), *controls], spacing=12),
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
            if not self.state.bloques:
                errors.append("Debe existir al menos un bloque de plan de pago.")
            if self._suma_bloques() != _decimal_or_zero(self.state.monto_total):
                errors.append("La suma de bloques debe coincidir con el monto total.")
            if not self.state.preview_generado:
                errors.append("Debe generarse preview antes de confirmar.")
        return (not errors, errors)

    def _all_errors(self) -> list[str]:
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
        self.state.compradores.append(CompradorDraft(id_persona=str(next_id), nombre=f"Comprador demo {next_id}"))
        self._render()

    def _remove_comprador(self, _: Any) -> None:
        if self.state.compradores:
            self.state.compradores.pop()
        self._render()

    def _add_bloque(self, tipo: str) -> None:
        label = {"ANTICIPO": "Anticipo", "TRAMO_CUOTAS": "Tramo", "REFUERZO": "Refuerzo"}.get(tipo, tipo)
        self.state.bloques.append(
            BloquePlanDraft(
                tipo_bloque=tipo,
                etiqueta=label,
                importe="1000000.00",
                vencimiento=_format_ar_date(date.today()),
                cantidad_cuotas="6" if tipo == "TRAMO_CUOTAS" else "",
                primer_vencimiento=_format_ar_date(date.today()) if tipo == "TRAMO_CUOTAS" else "",
            )
        )
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


def main(page: ft.Page) -> None:
    page.title = "Prototipo venta completa"
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.add(VentaCompletaWizardPrototype(page).build())


if __name__ == "__main__":
    ft.run(target=main)
