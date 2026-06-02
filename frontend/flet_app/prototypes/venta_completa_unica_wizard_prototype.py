"""Prototipo Flet limpio para el wizard unico de venta completa.

Uso:
  cd frontend/flet_app
  python prototypes/venta_completa_unica_wizard_prototype.py

Alcance:
  - Prototipo UX/tecnico no productivo del dominio comercial.
  - No modifica backend, SQL, pagos, caja, recibos ni el wizard viejo.
  - No pide id_venta manual: la venta nace solamente al confirmar.
  - No calcula cronograma, interes ni indexacion localmente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
import importlib
import importlib.util
import json
from typing import Any, Callable
from urllib import error as urllib_error
from urllib import request as urllib_request
from uuid import uuid4

import flet as ft


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_MONEDA = "ARS"
DEFAULT_ID_ROL_PARTICIPACION_COMPRADOR = "1"
STEPS = [
    "Origen",
    "Datos de venta",
    "Compradores",
    "Objetos",
    "Plan Pago V2",
    "Revision",
    "Confirmar",
    "Resultado",
]
ORIGENES = ("RESERVA", "DIRECTA")
TIPOS_OBJETO = ("INMUEBLE", "UNIDAD_FUNCIONAL")
METODOS_TRAMO = {
    "Cuotas fijas / sin interes": "SIN_INTERES",
    "Interes directo": "INTERES_DIRECTO",
    "Indexado por indice": "INDEXACION",
}


def _requests_module() -> Any | None:
    if importlib.util.find_spec("requests") is None:
        return None
    return importlib.import_module("requests")


def _border_all(width: int | float, color: ft.ColorValue) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


def _today() -> str:
    return date.today().isoformat()


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _decimal_or_none(value: str | None) -> Decimal | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _int_or_none(value: str | None) -> int | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _money(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{value.quantize(Decimal('0.01'))}"


def _drop(label: str, options: list[str], value: str | None = None, width: int = 240) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        width=width,
        options=[ft.dropdown.Option(item) for item in options],
    )


def _text_json(data: Any) -> ft.Control:
    return ft.Text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        selectable=True,
        font_family="monospace",
        size=12,
    )


@dataclass
class CompradorDraft:
    id_persona: str = ""
    nombre_visual: str = ""
    porcentaje_responsabilidad: str = ""
    id_rol_participacion: str = DEFAULT_ID_ROL_PARTICIPACION_COMPRADOR


@dataclass
class ObjetoDraft:
    tipo: str = "INMUEBLE"
    id_inmueble: str = ""
    id_unidad_funcional: str = ""
    id_inmueble_contenedor: str = ""
    precio_asignado: str = ""
    descripcion: str = ""


@dataclass
class TramoCuotasDraft:
    capital_tramo: str = ""
    cantidad_cuotas: str = ""
    primer_vencimiento: str = field(default_factory=_today)
    metodo_label: str = "Cuotas fijas / sin interes"
    tasa_periodica: str = ""
    cantidad_periodos: str = ""
    indice: str = ""
    id_indice_financiero: str = ""
    fecha_base_indice: str = field(default_factory=_today)
    valor_base_indice: str = ""


@dataclass
class RefuerzoDraft:
    importe: str = ""
    vencimiento: str = field(default_factory=_today)
    etiqueta: str = "Refuerzo"


@dataclass
class WizardState:
    current_step: int = 0
    base_url: str = DEFAULT_BASE_URL
    origen: str = "RESERVA"
    id_reserva_venta: str = ""
    if_match_version: str = ""
    reserva_descripcion: str = ""
    codigo_venta: str = "VTA-DEMO-001"
    fecha_venta: str = field(default_factory=_today)
    moneda: str = DEFAULT_MONEDA
    monto_total: str = "12000000.00"
    observaciones: str = ""
    compradores: list[CompradorDraft] = field(default_factory=lambda: [CompradorDraft()])
    objetos: list[ObjetoDraft] = field(default_factory=lambda: [ObjetoDraft(precio_asignado="12000000.00")])
    tipo_pago_ui: str = "Contado"
    contado_importe: str = "12000000.00"
    contado_vencimiento: str = field(default_factory=_today)
    contado_observaciones: str = ""
    tiene_anticipo: bool = False
    anticipo_importe: str = ""
    anticipo_vencimiento: str = field(default_factory=_today)
    tramos: list[TramoCuotasDraft] = field(default_factory=list)
    refuerzos: list[RefuerzoDraft] = field(default_factory=list)
    tiene_saldo_final: bool = False
    saldo_importe: str = ""
    saldo_vencimiento: str = field(default_factory=_today)
    confirm_observaciones: str = ""
    x_op_id: str = field(default_factory=lambda: str(uuid4()))
    x_usuario_id: str = "1"
    x_sucursal_id: str = "1"
    x_instalacion_id: str = "1"
    loading: bool = False
    last_status: int | None = None
    last_response: Any | None = None
    last_error: str | None = None
    plan_status: int | None = None
    plan_response: Any | None = None
    plan_error: str | None = None


@dataclass
class HttpResult:
    status_code: int | None
    data: Any | None
    error: str | None = None


class VentaCompletaUnicaWizardPrototype:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = WizardState()
        self.root = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)

    def build(self) -> ft.Control:
        self._render()
        return self.root

    def _render(self) -> None:
        self.root.controls = [
            ft.Text(
                "Prototipo — Wizard unico de venta completa",
                size=28,
                weight=ft.FontWeight.W_700,
            ),
            ft.Text(
                "Un solo flujo comercial: RESERVA o DIRECTA solo cambia el adapter final. "
                "La venta no existe hasta confirmar; no se pide id_venta manual.",
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
            errors = self._step_errors(index)
            complete = not errors
            is_current = index == self.state.current_step
            icon = ft.Icons.CHECK_CIRCLE if complete else ft.Icons.ERROR_OUTLINE
            color = ft.Colors.GREEN_700 if complete else ft.Colors.RED_700
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
            return self._step_origen()
        if step == 1:
            return self._step_datos_venta()
        if step == 2:
            return self._step_compradores()
        if step == 3:
            return self._step_objetos()
        if step == 4:
            return self._step_plan_pago()
        if step == 5:
            return self._step_revision()
        if step == 6:
            return self._step_confirmar()
        return self._step_resultado()

    def _card(self, title: str, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=[ft.Text(title, size=20, weight=ft.FontWeight.W_700), *controls],
                spacing=10,
            ),
            padding=16,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=12,
        )

    def _field(self, label: str, value: str, on_change: Callable[[str], None], width: int = 220) -> ft.TextField:
        return ft.TextField(
            label=label,
            value=value,
            width=width,
            on_change=lambda event: self._set_and_render(on_change, event.control.value),
        )

    def _set_and_render(self, setter: Callable[[str], None], value: str) -> None:
        setter(value)
        self._render()

    def _set_bool_and_render(self, setter: Callable[[bool], None], value: bool) -> None:
        setter(value)
        self._render()

    def _step_origen(self) -> ft.Control:
        origen = _drop("Origen", list(ORIGENES), self.state.origen, width=180)
        origen.on_change = lambda event: self._set_and_render(self._set_origen, event.control.value)
        reserva_controls: list[ft.Control] = []
        if self.state.origen == "RESERVA":
            reserva_controls = [
                ft.Row(
                    controls=[
                        self._field("id_reserva_venta", self.state.id_reserva_venta, lambda v: setattr(self.state, "id_reserva_venta", v), 180),
                        self._field("If-Match-Version de la reserva", self.state.if_match_version, lambda v: setattr(self.state, "if_match_version", v), 240),
                    ],
                    wrap=True,
                ),
                self._field("Codigo/descripcion opcional", self.state.reserva_descripcion, lambda v: setattr(self.state, "reserva_descripcion", v), 420),
            ]
        return self._card(
            "Paso 1 — Origen",
            [
                origen,
                ft.Text("RESERVA: cuando la operacion nace de una reserva vigente."),
                ft.Text("DIRECTA: cuando la venta no nace de una reserva."),
                ft.Text("No se pide id_venta porque la venta se crea al confirmar.", weight=ft.FontWeight.W_700),
                *reserva_controls,
            ],
        )

    def _set_origen(self, value: str) -> None:
        self.state.origen = value
        if value == "DIRECTA":
            self.state.if_match_version = ""

    def _step_datos_venta(self) -> ft.Control:
        return self._card(
            "Paso 2 — Datos de venta",
            [
                ft.Text("Campos adaptados a generar_venta y condiciones_comerciales de los contratos reales."),
                ft.Row(
                    controls=[
                        self._field("codigo_venta", self.state.codigo_venta, lambda v: setattr(self.state, "codigo_venta", v)),
                        self._field("fecha_venta (ISO)", self.state.fecha_venta, lambda v: setattr(self.state, "fecha_venta", v)),
                        self._field("moneda", self.state.moneda, lambda v: setattr(self.state, "moneda", v), 120),
                        self._field("monto_total", self.state.monto_total, lambda v: setattr(self.state, "monto_total", v)),
                    ],
                    wrap=True,
                ),
                self._field("observaciones", self.state.observaciones, lambda v: setattr(self.state, "observaciones", v), 520),
            ],
        )

    def _step_compradores(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Cargar uno o varios compradores. Se registra responsabilidad pactada; la participacion es informativa."),
            ft.Text("No se interpreta como deuda individual."),
        ]
        for index, comprador in enumerate(self.state.compradores):
            controls.append(self._comprador_card(index, comprador))
        controls.append(
            ft.Row(
                controls=[
                    ft.Button("Agregar comprador", icon=ft.Icons.ADD, on_click=lambda _: self._add_comprador()),
                    ft.OutlinedButton("Quitar ultimo", icon=ft.Icons.REMOVE, on_click=lambda _: self._remove_last(self.state.compradores)),
                ],
                wrap=True,
            )
        )
        return self._card("Paso 3 — Compradores", controls)

    def _comprador_card(self, index: int, comprador: CompradorDraft) -> ft.Control:
        controls = [
            self._field("id_persona", comprador.id_persona, lambda v, c=comprador: setattr(c, "id_persona", v), 140),
            self._field("nombre visual opcional", comprador.nombre_visual, lambda v, c=comprador: setattr(c, "nombre_visual", v), 220),
            self._field("porcentaje de responsabilidad", comprador.porcentaje_responsabilidad, lambda v, c=comprador: setattr(c, "porcentaje_responsabilidad", v), 230),
        ]
        if self.state.origen == "DIRECTA":
            controls.append(
                self._field(
                    "id_rol_participacion (soporte contrato DIRECTA)",
                    comprador.id_rol_participacion,
                    lambda v, c=comprador: setattr(c, "id_rol_participacion", v),
                    330,
                )
            )
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Comprador #{index + 1}", weight=ft.FontWeight.W_700),
                    ft.Row(controls=controls, wrap=True),
                ]
            ),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _step_objetos(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Cada objeto debe tener exactamente un id_inmueble o un id_unidad_funcional."),
            ft.Text("Si se carga id_inmueble_contenedor en una unidad funcional, el prototipo valida no mezclarlo con el inmueble completo."),
        ]
        for index, objeto in enumerate(self.state.objetos):
            controls.append(self._objeto_card(index, objeto))
        controls.append(
            ft.Row(
                controls=[
                    ft.Button("Agregar objeto", icon=ft.Icons.ADD, on_click=lambda _: self._add_objeto()),
                    ft.OutlinedButton("Quitar ultimo", icon=ft.Icons.REMOVE, on_click=lambda _: self._remove_last(self.state.objetos)),
                ],
                wrap=True,
            )
        )
        return self._card("Paso 4 — Objetos", controls)

    def _objeto_card(self, index: int, objeto: ObjetoDraft) -> ft.Control:
        tipo = _drop("tipo", list(TIPOS_OBJETO), objeto.tipo, width=210)
        tipo.on_change = lambda event, o=objeto: self._set_objeto_tipo(o, event.control.value)
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Objeto #{index + 1}", weight=ft.FontWeight.W_700),
                    ft.Row(
                        controls=[
                            tipo,
                            self._field("id_inmueble", objeto.id_inmueble, lambda v, o=objeto: setattr(o, "id_inmueble", v), 150),
                            self._field("id_unidad_funcional", objeto.id_unidad_funcional, lambda v, o=objeto: setattr(o, "id_unidad_funcional", v), 190),
                            self._field("id_inmueble_contenedor (validacion UX)", objeto.id_inmueble_contenedor, lambda v, o=objeto: setattr(o, "id_inmueble_contenedor", v), 270),
                            self._field("precio_asignado", objeto.precio_asignado, lambda v, o=objeto: setattr(o, "precio_asignado", v), 180),
                        ],
                        wrap=True,
                    ),
                    self._field("descripcion opcional", objeto.descripcion, lambda v, o=objeto: setattr(o, "descripcion", v), 520),
                ]
            ),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _set_objeto_tipo(self, objeto: ObjetoDraft, value: str) -> None:
        objeto.tipo = value
        if value == "INMUEBLE":
            objeto.id_unidad_funcional = ""
            objeto.id_inmueble_contenedor = ""
        else:
            objeto.id_inmueble = ""
        self._render()

    def _step_plan_pago(self) -> ft.Control:
        tipo_pago = _drop("Forma de pago comercial", ["Contado", "Financiado"], self.state.tipo_pago_ui, width=240)
        tipo_pago.on_change = lambda event: self._set_and_render(lambda v: setattr(self.state, "tipo_pago_ui", v), event.control.value)
        controls: list[ft.Control] = [
            tipo_pago,
            ft.Text("La UI carga una forma comercial y construye internamente plan_pago_v2.bloques."),
            ft.Text("No se calcula cronograma, interes ni indexacion localmente.", weight=ft.FontWeight.W_700),
        ]
        if self.state.tipo_pago_ui == "Contado":
            controls.extend(self._contado_controls())
        else:
            controls.extend(self._financiado_controls())
        controls.append(self._plan_summary_panel())
        return self._card("Paso 5 — Plan Pago V2", controls)

    def _contado_controls(self) -> list[ft.Control]:
        return [
            ft.Text("Contado: se genera un unico bloque CONTADO. No permite anticipo, cuotas, refuerzos ni saldo final."),
            ft.Row(
                controls=[
                    self._field("importe total", self.state.contado_importe, lambda v: setattr(self.state, "contado_importe", v), 180),
                    self._field("fecha de pago/vencimiento", self.state.contado_vencimiento, lambda v: setattr(self.state, "contado_vencimiento", v), 220),
                ],
                wrap=True,
            ),
            self._field("observaciones opcionales", self.state.contado_observaciones, lambda v: setattr(self.state, "contado_observaciones", v), 520),
        ]

    def _financiado_controls(self) -> list[ft.Control]:
        anticipo = ft.Switch(value=self.state.tiene_anticipo, text="Tiene anticipo")
        anticipo.on_change = lambda event: self._set_bool_and_render(lambda v: setattr(self.state, "tiene_anticipo", v), event.control.value)
        saldo = ft.Switch(value=self.state.tiene_saldo_final, text="Tiene saldo final")
        saldo.on_change = lambda event: self._set_bool_and_render(lambda v: setattr(self.state, "tiene_saldo_final", v), event.control.value)
        controls: list[ft.Control] = [
            ft.Text("A. Anticipo opcional", weight=ft.FontWeight.W_700),
            anticipo,
        ]
        if self.state.tiene_anticipo:
            controls.append(
                ft.Row(
                    controls=[
                        self._field("importe anticipo", self.state.anticipo_importe, lambda v: setattr(self.state, "anticipo_importe", v), 180),
                        self._field("vencimiento anticipo", self.state.anticipo_vencimiento, lambda v: setattr(self.state, "anticipo_vencimiento", v), 210),
                    ],
                    wrap=True,
                )
            )
        controls.extend([ft.Text("B. Cuotas principales / tramos", weight=ft.FontWeight.W_700)])
        for index, tramo in enumerate(self.state.tramos):
            controls.append(self._tramo_card(index, tramo))
        controls.append(ft.Button("Agregar tramo de cuotas", icon=ft.Icons.ADD, on_click=lambda _: self._add_tramo()))
        controls.extend([ft.Text("C. Refuerzos opcionales", weight=ft.FontWeight.W_700)])
        for index, refuerzo in enumerate(self.state.refuerzos):
            controls.append(self._refuerzo_card(index, refuerzo))
        controls.append(ft.Button("Agregar refuerzo", icon=ft.Icons.ADD, on_click=lambda _: self._add_refuerzo()))
        controls.extend([ft.Text("D. Saldo final opcional", weight=ft.FontWeight.W_700), saldo])
        if self.state.tiene_saldo_final:
            controls.append(
                ft.Row(
                    controls=[
                        self._field("importe saldo final", self.state.saldo_importe, lambda v: setattr(self.state, "saldo_importe", v), 190),
                        self._field("vencimiento saldo final", self.state.saldo_vencimiento, lambda v: setattr(self.state, "saldo_vencimiento", v), 220),
                    ],
                    wrap=True,
                )
            )
        controls.append(
            ft.Row(
                controls=[
                    ft.OutlinedButton("Quitar ultimo tramo", on_click=lambda _: self._remove_last(self.state.tramos)),
                    ft.OutlinedButton("Quitar ultimo refuerzo", on_click=lambda _: self._remove_last(self.state.refuerzos)),
                ],
                wrap=True,
            )
        )
        return controls

    def _tramo_card(self, index: int, tramo: TramoCuotasDraft) -> ft.Control:
        metodo = _drop("metodo de actualizacion", list(METODOS_TRAMO.keys()), tramo.metodo_label, width=260)
        metodo.on_change = lambda event, t=tramo: self._set_and_render(lambda v: setattr(t, "metodo_label", v), event.control.value)
        extra: list[ft.Control] = []
        if METODOS_TRAMO[tramo.metodo_label] == "INTERES_DIRECTO":
            extra = [
                ft.Row(
                    controls=[
                        self._field("tasa periodica", tramo.tasa_periodica, lambda v, t=tramo: setattr(t, "tasa_periodica", v), 180),
                        self._field("cantidad de periodos", tramo.cantidad_periodos, lambda v, t=tramo: setattr(t, "cantidad_periodos", v), 210),
                    ],
                    wrap=True,
                ),
                ft.Text("Interes simple sobre capital inicial del tramo."),
            ]
        if METODOS_TRAMO[tramo.metodo_label] == "INDEXACION":
            extra = [
                ft.Row(
                    controls=[
                        self._field("indice", tramo.indice, lambda v, t=tramo: setattr(t, "indice", v), 160),
                        self._field("id_indice_financiero", tramo.id_indice_financiero, lambda v, t=tramo: setattr(t, "id_indice_financiero", v), 210),
                        self._field("fecha_base_indice", tramo.fecha_base_indice, lambda v, t=tramo: setattr(t, "fecha_base_indice", v), 200),
                        self._field("valor_base_indice", tramo.valor_base_indice, lambda v, t=tramo: setattr(t, "valor_base_indice", v), 190),
                    ],
                    wrap=True,
                ),
                ft.Text("El ajuste se calcula contra el indice publicado aplicable. No se inventan valores futuros."),
            ]
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Tramo de cuotas #{index + 1}", weight=ft.FontWeight.W_700),
                    ft.Row(
                        controls=[
                            self._field("capital del tramo", tramo.capital_tramo, lambda v, t=tramo: setattr(t, "capital_tramo", v), 180),
                            self._field("cantidad de cuotas", tramo.cantidad_cuotas, lambda v, t=tramo: setattr(t, "cantidad_cuotas", v), 190),
                            self._field("primer vencimiento", tramo.primer_vencimiento, lambda v, t=tramo: setattr(t, "primer_vencimiento", v), 190),
                            ft.Text("periodicidad = MENSUAL", weight=ft.FontWeight.W_700),
                            metodo,
                        ],
                        wrap=True,
                    ),
                    *extra,
                ]
            ),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _refuerzo_card(self, index: int, refuerzo: RefuerzoDraft) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"Refuerzo #{index + 1}", weight=ft.FontWeight.W_700),
                    self._field("importe", refuerzo.importe, lambda v, r=refuerzo: setattr(r, "importe", v), 160),
                    self._field("vencimiento", refuerzo.vencimiento, lambda v, r=refuerzo: setattr(r, "vencimiento", v), 170),
                    self._field("etiqueta", refuerzo.etiqueta, lambda v, r=refuerzo: setattr(r, "etiqueta", v), 180),
                ],
                wrap=True,
            ),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _step_revision(self) -> ft.Control:
        payload = self._build_payload()
        return self._card(
            "Paso 6 — Revision",
            [
                ft.Text("Revision completa antes de confirmar. No se muestran cuotas calculadas ni cronograma local falso."),
                ft.Text(f"Origen: {self.state.origen}"),
                ft.Text(f"Reserva: {self.state.id_reserva_venta or 'NO APLICA'}"),
                self._plan_summary_panel(),
                ft.Text("Payload final que se enviara", weight=ft.FontWeight.W_700),
                _text_json(payload),
            ],
        )

    def _step_confirmar(self) -> ft.Control:
        endpoint = self._endpoint_path()
        header_rows = [
            self._field("X-Op-Id", self.state.x_op_id, lambda v: setattr(self.state, "x_op_id", v), 360),
            self._field("X-Usuario-Id", self.state.x_usuario_id, lambda v: setattr(self.state, "x_usuario_id", v), 180),
            self._field("X-Sucursal-Id", self.state.x_sucursal_id, lambda v: setattr(self.state, "x_sucursal_id", v), 180),
            self._field("X-Instalacion-Id", self.state.x_instalacion_id, lambda v: setattr(self.state, "x_instalacion_id", v), 200),
        ]
        if self.state.origen == "RESERVA":
            header_rows.append(ft.Text(f"If-Match-Version: {self.state.if_match_version}", weight=ft.FontWeight.W_700))
        return self._card(
            "Paso 7 — Confirmar",
            [
                self._field("Base URL", self.state.base_url, lambda v: setattr(self.state, "base_url", v), 360),
                ft.Text(f"POST {endpoint}", weight=ft.FontWeight.W_700),
                ft.Row(controls=header_rows, wrap=True),
                ft.Text("DIRECTA no envia If-Match-Version porque el contrato actual no lo exige." if self.state.origen == "DIRECTA" else "RESERVA envia If-Match-Version de la reserva."),
                self._field("observaciones de confirmacion", self.state.confirm_observaciones, lambda v: setattr(self.state, "confirm_observaciones", v), 520),
                ft.Button(
                    "Confirmar venta completa",
                    icon=ft.Icons.SEND,
                    disabled=self.state.loading,
                    on_click=lambda _: self._confirmar(),
                ),
                ft.Text("La accion llama al backend real y muestra errores JSON o excepciones de red legibles."),
            ],
        )

    def _step_resultado(self) -> ft.Control:
        id_venta = self._extract_id_venta(self.state.last_response)
        controls: list[ft.Control] = [
            ft.Text(f"Status HTTP: {self.state.last_status or '-'}"),
            ft.Text(f"id_venta resuelto: {id_venta or '-'}"),
            ft.Text(f"Estado de venta: {self._extract_estado_venta(self.state.last_response) or '-'}"),
            ft.Text(self._final_message(), weight=ft.FontWeight.W_700),
        ]
        if self.state.last_error:
            controls.append(ft.Text(self.state.last_error, color=ft.Colors.RED_700, selectable=True))
        if self.state.last_response is not None:
            controls.extend([ft.Text("Response JSON", weight=ft.FontWeight.W_700), _text_json(self.state.last_response)])
        if id_venta:
            controls.append(
                ft.Button(
                    "Consultar Plan Pago V2",
                    icon=ft.Icons.SEARCH,
                    on_click=lambda _, venta_id=id_venta: self._consultar_plan_pago(venta_id),
                )
            )
        if self.state.plan_error:
            controls.append(ft.Text(self.state.plan_error, color=ft.Colors.RED_700, selectable=True))
        if self.state.plan_response is not None:
            controls.extend(
                [
                    ft.Text(f"Status consulta Plan Pago V2: {self.state.plan_status or '-'}"),
                    ft.Text("Consulta integral: resumen, bloques, obligaciones, composiciones, obligados por obligacion e indexacion si existe."),
                    _text_json(self.state.plan_response),
                ]
            )
        return self._card("Paso 8 — Resultado", controls)

    def _summary_panel(self) -> ft.Control:
        errors = self._all_errors()
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Resumen local", size=18, weight=ft.FontWeight.W_700),
                    ft.Text(f"Origen: {self.state.origen}"),
                    ft.Text(f"Monto total venta: {_money(_decimal_or_none(self.state.monto_total))}"),
                    ft.Text(f"Monto total plan: {_money(self._plan_total())}"),
                    ft.Text(f"Diferencia: {_money(self._plan_difference())}"),
                    ft.Text(f"Obligaciones estimadas: {self._estimated_obligations()}"),
                    ft.Text("Alertas", weight=ft.FontWeight.W_700),
                    *(ft.Text(error, color=ft.Colors.RED_700, size=12) for error in errors[:12]),
                    ft.Text("Sin alertas criticas." if not errors else "", color=ft.Colors.GREEN_700),
                ],
                spacing=5,
            ),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=12,
        )

    def _plan_summary_panel(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Resumen local Plan Pago V2", weight=ft.FontWeight.W_700),
                    ft.Text(f"Monto total de venta: {_money(_decimal_or_none(self.state.monto_total))}"),
                    ft.Text(f"Monto total del plan: {_money(self._plan_total())}"),
                    ft.Text(f"Suma cargada: {_money(self._plan_total())}"),
                    ft.Text(f"Diferencia: {_money(self._plan_difference())}"),
                    ft.Text(f"Cantidad estimada de obligaciones: {self._estimated_obligations()}"),
                    ft.Text("Alertas: " + ("; ".join(self._step_errors(4)) or "sin alertas")),
                    ft.Text("No se genera cronograma local."),
                ]
            ),
            padding=10,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _nav_buttons(self) -> ft.Control:
        return ft.Row(
            controls=[
                ft.OutlinedButton("Anterior", disabled=self.state.current_step == 0, on_click=lambda _: self._go(-1)),
                ft.Button("Siguiente", disabled=self.state.current_step >= len(STEPS) - 1, on_click=lambda _: self._go(1)),
                ft.OutlinedButton("Ir a resultado", on_click=lambda _: self._set_step(7)),
            ],
            spacing=10,
        )

    def _go(self, delta: int) -> None:
        self.state.current_step = max(0, min(len(STEPS) - 1, self.state.current_step + delta))
        self._render()

    def _set_step(self, step: int) -> None:
        self.state.current_step = step
        self._render()

    def _add_comprador(self) -> None:
        self.state.compradores.append(CompradorDraft())
        self._render()

    def _add_objeto(self) -> None:
        self.state.objetos.append(ObjetoDraft())
        self._render()

    def _add_tramo(self) -> None:
        self.state.tramos.append(TramoCuotasDraft())
        self._render()

    def _add_refuerzo(self) -> None:
        self.state.refuerzos.append(RefuerzoDraft())
        self._render()

    def _remove_last(self, items: list[Any]) -> None:
        if items:
            items.pop()
        self._render()

    def _step_errors(self, step: int) -> list[str]:
        if step == 0:
            errors = []
            if self.state.origen not in ORIGENES:
                errors.append("Origen requerido.")
            if self.state.origen == "RESERVA":
                if _int_or_none(self.state.id_reserva_venta) is None:
                    errors.append("RESERVA requiere id_reserva_venta numerico.")
                if _int_or_none(self.state.if_match_version) is None:
                    errors.append("RESERVA requiere If-Match-Version numerico.")
            return errors
        if step == 1:
            errors = []
            if not _clean_text(self.state.codigo_venta):
                errors.append("codigo_venta requerido.")
            if not _clean_text(self.state.fecha_venta):
                errors.append("fecha_venta requerida.")
            if not _clean_text(self.state.moneda):
                errors.append("moneda requerida.")
            monto = _decimal_or_none(self.state.monto_total)
            if monto is None or monto <= 0:
                errors.append("monto_total requerido y mayor a 0.")
            return errors
        if step == 2:
            return self._compradores_errors()
        if step == 3:
            return self._objetos_errors()
        if step == 4:
            return self._plan_errors()
        if step in (5, 6):
            errors = self._all_errors()
            if step == 6:
                for label, value in (
                    ("X-Op-Id", self.state.x_op_id),
                    ("X-Usuario-Id", self.state.x_usuario_id),
                    ("X-Sucursal-Id", self.state.x_sucursal_id),
                    ("X-Instalacion-Id", self.state.x_instalacion_id),
                ):
                    if not _clean_text(value):
                        errors.append(f"Header {label} requerido.")
            return errors
        return []

    def _compradores_errors(self) -> list[str]:
        errors: list[str] = []
        compradores = self.state.compradores
        if not compradores:
            return ["Al menos un comprador requerido."]
        ids = [_clean_text(c.id_persona) for c in compradores]
        valid_ids = [item for item in ids if item]
        if len(valid_ids) != len(compradores):
            errors.append("Todos los compradores requieren id_persona.")
        if len(set(valid_ids)) != len(valid_ids):
            errors.append("No duplicar id_persona.")
        percentages: list[Decimal] = []
        if len(compradores) == 1 and not _clean_text(compradores[0].porcentaje_responsabilidad):
            percentages = [Decimal("100")]
        else:
            for comprador in compradores:
                pct = _decimal_or_none(comprador.porcentaje_responsabilidad)
                if pct is None:
                    errors.append("Si hay varios compradores, todos deben tener porcentaje de responsabilidad.")
                    continue
                percentages.append(pct)
        for pct in percentages:
            if pct <= 0 or pct > 100:
                errors.append("Cada porcentaje debe ser > 0 y <= 100.")
        if percentages and sum(percentages) != Decimal("100"):
            errors.append("La suma de porcentajes de responsabilidad debe ser 100.")
        if self.state.origen == "DIRECTA":
            for comprador in compradores:
                if _int_or_none(comprador.id_rol_participacion) is None:
                    errors.append("DIRECTA requiere id_rol_participacion segun contrato actual.")
                    break
        return errors

    def _objetos_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.state.objetos:
            return ["Al menos un objeto requerido."]
        inmuebles = set()
        contenedores_uf = set()
        for index, objeto in enumerate(self.state.objetos, start=1):
            has_inmueble = bool(_clean_text(objeto.id_inmueble))
            has_uf = bool(_clean_text(objeto.id_unidad_funcional))
            if has_inmueble == has_uf:
                errors.append(f"Objeto #{index}: cargar exactamente uno de id_inmueble o id_unidad_funcional.")
            if objeto.tipo == "INMUEBLE" and not has_inmueble:
                errors.append(f"Objeto #{index}: INMUEBLE requiere id_inmueble.")
            if objeto.tipo == "UNIDAD_FUNCIONAL" and not has_uf:
                errors.append(f"Objeto #{index}: UNIDAD_FUNCIONAL requiere id_unidad_funcional.")
            precio = _decimal_or_none(objeto.precio_asignado)
            if precio is None or precio <= 0:
                errors.append(f"Objeto #{index}: precio_asignado requerido y mayor a 0.")
            if has_inmueble:
                inmuebles.add(_clean_text(objeto.id_inmueble))
            if has_uf and _clean_text(objeto.id_inmueble_contenedor):
                contenedores_uf.add(_clean_text(objeto.id_inmueble_contenedor))
        mixed = sorted(inmuebles.intersection(contenedores_uf))
        if mixed:
            errors.append("No seleccionar inmueble completo junto con unidad funcional contenida: " + ", ".join(mixed))
        return errors

    def _plan_errors(self) -> list[str]:
        errors: list[str] = []
        total = _decimal_or_none(self.state.monto_total)
        if total is None:
            errors.append("monto_total de venta requerido para validar plan.")
            return errors
        plan_total = self._plan_total()
        if plan_total is None or plan_total <= 0:
            errors.append("La suma del plan debe ser mayor a 0.")
        elif plan_total != total:
            errors.append("La suma de plan debe coincidir con monto_total.")
        if self.state.tipo_pago_ui == "Contado":
            importe = _decimal_or_none(self.state.contado_importe)
            if importe is None or importe <= 0:
                errors.append("Contado requiere importe total mayor a 0.")
            if not _clean_text(self.state.contado_vencimiento):
                errors.append("Contado requiere fecha de pago/vencimiento.")
            return errors
        has_any = self.state.tiene_anticipo or self.state.tramos or self.state.refuerzos or self.state.tiene_saldo_final
        if not has_any:
            errors.append("Financiado requiere anticipo, tramos, refuerzos o saldo final.")
        if self.state.tiene_anticipo:
            if (_decimal_or_none(self.state.anticipo_importe) or Decimal("0")) <= 0:
                errors.append("Anticipo requiere importe mayor a 0.")
            if not _clean_text(self.state.anticipo_vencimiento):
                errors.append("Anticipo requiere vencimiento.")
        for index, tramo in enumerate(self.state.tramos, start=1):
            if (_decimal_or_none(tramo.capital_tramo) or Decimal("0")) <= 0:
                errors.append(f"Tramo #{index}: capital del tramo requerido y mayor a 0.")
            cuotas = _int_or_none(tramo.cantidad_cuotas)
            if cuotas is None or cuotas <= 0:
                errors.append(f"Tramo #{index}: cantidad de cuotas requerida y mayor a 0.")
            if not _clean_text(tramo.primer_vencimiento):
                errors.append(f"Tramo #{index}: primer vencimiento requerido.")
            metodo = METODOS_TRAMO[tramo.metodo_label]
            if metodo == "INTERES_DIRECTO":
                if (_decimal_or_none(tramo.tasa_periodica) or Decimal("0")) <= 0:
                    errors.append(f"Tramo #{index}: interes directo requiere tasa periodica mayor a 0.")
                periodos = _int_or_none(tramo.cantidad_periodos)
                if periodos is None or periodos <= 0:
                    errors.append(f"Tramo #{index}: interes directo requiere cantidad de periodos mayor a 0.")
            if metodo == "INDEXACION":
                if _int_or_none(tramo.id_indice_financiero) is None:
                    errors.append(f"Tramo #{index}: indexacion requiere id_indice_financiero numerico.")
                if not _clean_text(tramo.fecha_base_indice):
                    errors.append(f"Tramo #{index}: indexacion requiere fecha_base_indice.")
                if (_decimal_or_none(tramo.valor_base_indice) or Decimal("0")) <= 0:
                    errors.append(f"Tramo #{index}: indexacion requiere valor_base_indice mayor a 0.")
        for index, refuerzo in enumerate(self.state.refuerzos, start=1):
            if (_decimal_or_none(refuerzo.importe) or Decimal("0")) <= 0:
                errors.append(f"Refuerzo #{index}: importe requerido y mayor a 0.")
            if not _clean_text(refuerzo.vencimiento):
                errors.append(f"Refuerzo #{index}: vencimiento requerido.")
        if self.state.tiene_saldo_final:
            if (_decimal_or_none(self.state.saldo_importe) or Decimal("0")) <= 0:
                errors.append("Saldo final requiere importe mayor a 0.")
            if not _clean_text(self.state.saldo_vencimiento):
                errors.append("Saldo final requiere vencimiento.")
        return errors

    def _all_errors(self) -> list[str]:
        errors: list[str] = []
        for step in range(5):
            errors.extend(self._step_errors(step))
        return errors

    def _plan_total(self) -> Decimal | None:
        if self.state.tipo_pago_ui == "Contado":
            return _decimal_or_none(self.state.contado_importe)
        total = Decimal("0")
        if self.state.tiene_anticipo:
            total += _decimal_or_none(self.state.anticipo_importe) or Decimal("0")
        for tramo in self.state.tramos:
            total += _decimal_or_none(tramo.capital_tramo) or Decimal("0")
        for refuerzo in self.state.refuerzos:
            total += _decimal_or_none(refuerzo.importe) or Decimal("0")
        if self.state.tiene_saldo_final:
            total += _decimal_or_none(self.state.saldo_importe) or Decimal("0")
        return total

    def _plan_difference(self) -> Decimal | None:
        total = _decimal_or_none(self.state.monto_total)
        plan_total = self._plan_total()
        if total is None or plan_total is None:
            return None
        return plan_total - total

    def _estimated_obligations(self) -> int:
        if self.state.tipo_pago_ui == "Contado":
            return 1 if _decimal_or_none(self.state.contado_importe) else 0
        count = 0
        if self.state.tiene_anticipo:
            count += 1
        count += sum(max(_int_or_none(t.cantidad_cuotas) or 0, 0) for t in self.state.tramos)
        count += len(self.state.refuerzos)
        if self.state.tiene_saldo_final:
            count += 1
        return count

    def _build_payload(self) -> dict[str, Any]:
        generar_venta = {
            "codigo_venta": _clean_text(self.state.codigo_venta),
            "fecha_venta": _clean_text(self.state.fecha_venta),
            "monto_total": str(_decimal_or_none(self.state.monto_total) or ""),
            "observaciones": _clean_text(self.state.observaciones) or None,
        }
        condiciones = {
            "monto_total": str(_decimal_or_none(self.state.monto_total) or ""),
            "tipo_plan_financiero": "CONTADO" if self.state.tipo_pago_ui == "Contado" else "FINANCIADO",
            "moneda": _clean_text(self.state.moneda),
            "importe_anticipo": str(_decimal_or_none(self.state.anticipo_importe) or "") if self.state.tiene_anticipo else None,
            "fecha_vencimiento_anticipo": _clean_text(self.state.anticipo_vencimiento) if self.state.tiene_anticipo else None,
            "importe_saldo": str(_decimal_or_none(self.state.saldo_importe) or "") if self.state.tiene_saldo_final else None,
            "fecha_vencimiento_saldo": _clean_text(self.state.saldo_vencimiento) if self.state.tiene_saldo_final else None,
            "cuotas": [],
        }
        objetos = [self._objeto_payload(item) for item in self.state.objetos]
        plan_pago_v2 = {
            "tipo_pago": "CONTADO" if self.state.tipo_pago_ui == "Contado" else "FINANCIADO",
            "monto_total_plan": str(self._plan_total() or ""),
            "moneda": _clean_text(self.state.moneda),
            "bloques": self._bloques_payload(),
            "observaciones": _clean_text(self.state.contado_observaciones) if self.state.tipo_pago_ui == "Contado" else None,
        }
        payload: dict[str, Any] = {
            "generar_venta": generar_venta,
            "condiciones_comerciales": condiciones,
            "plan_pago_v2": plan_pago_v2,
            "confirmacion": {"observaciones": _clean_text(self.state.confirm_observaciones) or None},
        }
        if self.state.origen == "RESERVA":
            payload["condiciones_comerciales"]["objetos"] = objetos
        else:
            payload["objetos"] = objetos
            payload["compradores"] = [self._comprador_payload(item) for item in self.state.compradores]
        return self._strip_empty(payload)

    def _objeto_payload(self, objeto: ObjetoDraft) -> dict[str, Any]:
        return self._strip_empty(
            {
                "id_inmueble": _int_or_none(objeto.id_inmueble),
                "id_unidad_funcional": _int_or_none(objeto.id_unidad_funcional),
                "precio_asignado": str(_decimal_or_none(objeto.precio_asignado) or ""),
                "observaciones": _clean_text(objeto.descripcion) or None,
            }
        )

    def _comprador_payload(self, comprador: CompradorDraft) -> dict[str, Any]:
        pct = _decimal_or_none(comprador.porcentaje_responsabilidad)
        if pct is None and len(self.state.compradores) == 1:
            pct = Decimal("100")
        return self._strip_empty(
            {
                "id_persona": _int_or_none(comprador.id_persona),
                "id_rol_participacion": _int_or_none(comprador.id_rol_participacion),
                "porcentaje_responsabilidad": str(pct) if pct is not None else None,
                "observaciones": _clean_text(comprador.nombre_visual) or None,
            }
        )

    def _bloques_payload(self) -> list[dict[str, Any]]:
        if self.state.tipo_pago_ui == "Contado":
            return [
                self._strip_empty(
                    {
                        "tipo_bloque": "CONTADO",
                        "importe_total_bloque": str(_decimal_or_none(self.state.contado_importe) or ""),
                        "fecha_vencimiento": _clean_text(self.state.contado_vencimiento),
                        "observaciones": _clean_text(self.state.contado_observaciones) or None,
                    }
                )
            ]
        bloques: list[dict[str, Any]] = []
        if self.state.tiene_anticipo:
            bloques.append(
                self._strip_empty(
                    {
                        "tipo_bloque": "ANTICIPO",
                        "importe_total_bloque": str(_decimal_or_none(self.state.anticipo_importe) or ""),
                        "fecha_vencimiento": _clean_text(self.state.anticipo_vencimiento),
                    }
                )
            )
        for index, tramo in enumerate(self.state.tramos, start=1):
            metodo = METODOS_TRAMO[tramo.metodo_label]
            bloque: dict[str, Any] = {
                "tipo_bloque": "TRAMO_CUOTAS",
                "etiqueta_bloque": f"Tramo de cuotas {index}",
                "importe_total_bloque": str(_decimal_or_none(tramo.capital_tramo) or ""),
                "cantidad_cuotas": _int_or_none(tramo.cantidad_cuotas),
                "fecha_primer_vencimiento": _clean_text(tramo.primer_vencimiento),
                "periodicidad": "MENSUAL",
                "metodo_liquidacion": metodo,
            }
            if metodo == "INTERES_DIRECTO":
                bloque.update(
                    {
                        "tasa_interes_directo_periodica": str(_decimal_or_none(tramo.tasa_periodica) or ""),
                        "cantidad_periodos": _int_or_none(tramo.cantidad_periodos),
                        "base_calculo_interes": "CAPITAL_INICIAL_BLOQUE",
                    }
                )
            if metodo == "INDEXACION":
                bloque.update(
                    {
                        "id_indice_financiero": _int_or_none(tramo.id_indice_financiero),
                        "fecha_base_indice": _clean_text(tramo.fecha_base_indice),
                        "valor_base_indice": str(_decimal_or_none(tramo.valor_base_indice) or ""),
                        "modo_indexacion": "POR_COEFICIENTE",
                        "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
                        "tipo_generacion_indexada": "DEFINITIVA",
                        "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
                        "conserva_capital_original": True,
                        "genera_ajuste_por_diferencia": True,
                    }
                )
            bloques.append(self._strip_empty(bloque))
        for refuerzo in self.state.refuerzos:
            bloques.append(
                self._strip_empty(
                    {
                        "tipo_bloque": "REFUERZO",
                        "etiqueta_bloque": _clean_text(refuerzo.etiqueta) or "Refuerzo",
                        "importe_total_bloque": str(_decimal_or_none(refuerzo.importe) or ""),
                        "fecha_vencimiento": _clean_text(refuerzo.vencimiento),
                    }
                )
            )
        if self.state.tiene_saldo_final:
            bloques.append(
                self._strip_empty(
                    {
                        "tipo_bloque": "SALDO",
                        "importe_total_bloque": str(_decimal_or_none(self.state.saldo_importe) or ""),
                        "fecha_vencimiento": _clean_text(self.state.saldo_vencimiento),
                    }
                )
            )
        return bloques

    def _strip_empty(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._strip_empty(item) for key, item in value.items() if item not in (None, "")}
        if isinstance(value, list):
            return [self._strip_empty(item) for item in value]
        return value

    def _endpoint_path(self) -> str:
        if self.state.origen == "RESERVA":
            return f"/api/v1/reservas-venta/{_clean_text(self.state.id_reserva_venta)}/confirmar-venta-completa"
        return "/api/v1/ventas/directa/confirmar-venta-completa"

    def _headers(self) -> dict[str, str]:
        headers = {
            "X-Op-Id": _clean_text(self.state.x_op_id),
            "X-Usuario-Id": _clean_text(self.state.x_usuario_id),
            "X-Sucursal-Id": _clean_text(self.state.x_sucursal_id),
            "X-Instalacion-Id": _clean_text(self.state.x_instalacion_id),
        }
        if self.state.origen == "RESERVA":
            headers["If-Match-Version"] = _clean_text(self.state.if_match_version)
        return headers

    def _confirmar(self) -> None:
        errors = self._step_errors(6)
        if errors:
            self.state.last_status = None
            self.state.last_response = {"errores_validacion_ux": errors}
            self.state.last_error = "No se envia al backend porque hay errores UX."
            self.state.current_step = 7
            self._render()
            return
        self.state.loading = True
        self._render()
        result = self._http_json("POST", self._endpoint_path(), headers=self._headers(), payload=self._build_payload())
        self.state.loading = False
        self.state.last_status = result.status_code
        self.state.last_response = result.data
        self.state.last_error = result.error
        self.state.current_step = 7
        self._render()

    def _consultar_plan_pago(self, id_venta: int) -> None:
        self.state.loading = True
        self._render()
        result = self._http_json("GET", f"/api/v1/ventas/{id_venta}/plan-pago-v2", headers={}, payload=None)
        self.state.loading = False
        self.state.plan_status = result.status_code
        self.state.plan_response = result.data
        self.state.plan_error = result.error
        self._render()

    def _http_json(self, method: str, path: str, headers: dict[str, str], payload: dict[str, Any] | None) -> HttpResult:
        base_url = self.state.base_url.rstrip("/")
        url = f"{base_url}{path}"
        request_headers = {"Content-Type": "application/json", **headers}
        requests_module = _requests_module()
        if requests_module is not None:
            return self._http_with_requests(requests_module, method, url, request_headers, payload)
        return self._http_with_urllib(method, url, request_headers, payload)

    def _http_with_requests(self, requests_module: Any, method: str, url: str, headers: dict[str, str], payload: dict[str, Any] | None) -> HttpResult:
        try:
            response = requests_module.request(method, url, headers=headers, json=payload, timeout=20)
            try:
                data = response.json()
            except ValueError:
                data = {"raw": response.text}
            error_message = None if 200 <= response.status_code < 300 else "El backend respondio error; se muestra JSON recibido."
            return HttpResult(response.status_code, data, error_message)
        except requests_module.RequestException as exc:
            return HttpResult(None, None, f"Excepcion de red: {exc}")

    def _http_with_urllib(self, method: str, url: str, headers: dict[str, str], payload: dict[str, Any] | None) -> HttpResult:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with urllib_request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                return HttpResult(response.status, json.loads(raw) if raw else None)
        except urllib_error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            data: Any
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"raw": raw}
            return HttpResult(exc.code, data, "El backend respondio error; se muestra JSON recibido.")
        except urllib_error.URLError as exc:
            return HttpResult(None, None, f"Excepcion de red: {exc.reason}")
        except TimeoutError as exc:
            return HttpResult(None, None, f"Excepcion de red: {exc}")

    def _extract_id_venta(self, response: Any) -> int | None:
        if not isinstance(response, dict):
            return None
        candidates = [
            response.get("id_venta"),
            response.get("data", {}).get("id_venta") if isinstance(response.get("data"), dict) else None,
            response.get("data", {}).get("venta", {}).get("id_venta") if isinstance(response.get("data"), dict) and isinstance(response.get("data", {}).get("venta"), dict) else None,
        ]
        for candidate in candidates:
            try:
                if candidate is not None:
                    return int(candidate)
            except (TypeError, ValueError):
                continue
        return None

    def _extract_estado_venta(self, response: Any) -> str | None:
        if not isinstance(response, dict):
            return None
        data = response.get("data")
        if isinstance(data, dict):
            venta = data.get("venta")
            if isinstance(venta, dict):
                return venta.get("estado_venta")
            if isinstance(data.get("estado_venta"), str):
                return data.get("estado_venta")
        if isinstance(response.get("estado_venta"), str):
            return response.get("estado_venta")
        return None

    def _final_message(self) -> str:
        if self.state.last_status is None:
            return "Sin confirmacion enviada o con excepcion de red."
        if 200 <= self.state.last_status < 300:
            return "Venta completa confirmada por backend."
        return "Confirmacion rechazada por backend; revisar JSON de error."


def main(page: ft.Page) -> None:
    page.title = "Wizard unico de venta completa"
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO
    app = VentaCompletaUnicaWizardPrototype(page)
    page.add(app.build())


if hasattr(ft, "run"):
    ft.run(main)
else:
    ft.app(target=main)
