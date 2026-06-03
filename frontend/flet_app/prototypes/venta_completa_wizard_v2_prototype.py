"""Prototipo Flet — Wizard Venta Completa V2.

Ejecutar desde ``frontend/flet_app``::

    python prototypes/venta_completa_wizard_v2_prototype.py

Alcance del prototipo:
  - UX tecnica del dominio comercial para confirmar una venta completa.
  - Soporta venta directa y venta desde reserva con el mismo flujo visual.
  - No modifica backend, SQL, pagos, caja, recibos ni tests backend.
  - No calcula cronogramas, interes ni indexacion localmente.
  - Objetos y compradores usan modo demo/manual hasta integrar busquedas reales.
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
    "Objetos de venta",
    "Compradores",
    "Datos comerciales",
    "Forma de pago",
    "Plan de pago",
    "Revision",
    "Confirmar",
    "Resultado",
]
ORIGENES = ("RESERVA", "DIRECTA")
TIPOS_OBJETO = ("INMUEBLE", "UNIDAD_FUNCIONAL")
FORMAS_PAGO = ("CONTADO", "FINANCIADO")
METODOS_TRAMO = {
    "Cuotas fijas / sin interes": "SIN_INTERES",
    "Interes directo": "INTERES_DIRECTO",
    "Indexado por indice": "INDEXACION",
}
PLAN_SUBSTEPS = ("Anticipo", "Tramos de cuotas", "Saldo final / resumen")


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
    text = _clean_text(value).replace(",", ".")
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


def _decimal_payload(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _drop(label: str, options: list[str], value: str | None = None, width: int = 260) -> ft.Dropdown:
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
class ObjetoDraft:
    busqueda_visual: str = ""
    tipo: str = "INMUEBLE"
    id_inmueble: str = ""
    id_unidad_funcional: str = ""
    descripcion: str = ""
    precio_asignado: str = ""


@dataclass
class CompradorDraft:
    busqueda_visual: str = ""
    id_persona: str = ""
    nombre_visual: str = ""
    porcentaje_responsabilidad: str = ""
    id_rol_participacion: str = DEFAULT_ID_ROL_PARTICIPACION_COMPRADOR


@dataclass
class RefuerzoInternoDraft:
    numero_cuota: str = ""
    etiqueta: str = "Refuerzo"
    unidades_refuerzo: str = "1.00"


@dataclass
class TramoCuotasDraft:
    capital_tramo: str = ""
    cantidad_cuotas: str = ""
    primer_vencimiento: str = field(default_factory=_today)
    metodo_label: str = "Cuotas fijas / sin interes"
    tasa_periodica: str = ""
    cantidad_periodos: str = ""
    indice_visual: str = ""
    id_indice_financiero: str = ""
    fecha_base_indice: str = field(default_factory=_today)
    valor_base_indice: str = ""
    usa_refuerzos: bool = False
    refuerzos: list[RefuerzoInternoDraft] = field(default_factory=list)


@dataclass
class WizardState:
    current_step: int = 0
    plan_substep: int = 0
    base_url: str = DEFAULT_BASE_URL
    origen: str = "RESERVA"
    id_reserva_venta: str = ""
    if_match_version: str = ""
    reserva_visual: str = ""
    objetos: list[ObjetoDraft] = field(default_factory=lambda: [ObjetoDraft(precio_asignado="12000000.00")])
    compradores: list[CompradorDraft] = field(default_factory=lambda: [CompradorDraft()])
    codigo_venta: str = "VTA-V2-DEMO-001"
    fecha_venta: str = field(default_factory=_today)
    moneda: str = DEFAULT_MONEDA
    observaciones: str = ""
    forma_pago: str = "CONTADO"
    contado_vencimiento: str = field(default_factory=_today)
    tiene_anticipo: bool = False
    anticipo_importe: str = ""
    anticipo_vencimiento: str = field(default_factory=_today)
    tramos: list[TramoCuotasDraft] = field(default_factory=list)
    tiene_saldo_final: bool = False
    saldo_importe: str = ""
    saldo_vencimiento: str = field(default_factory=_today)
    confirm_observaciones: str = ""
    x_op_id: str = field(default_factory=lambda: str(uuid4()))
    x_usuario_id: str = "1"
    x_sucursal_id: str = "1"
    x_instalacion_id: str = "1"
    show_payload: bool = False
    show_request: bool = True
    loading: bool = False
    last_status: int | None = None
    last_response: Any | None = None
    last_error: str | None = None
    last_request: dict[str, Any] | None = None
    plan_status: int | None = None
    plan_response: Any | None = None
    plan_error: str | None = None
    plan_request: dict[str, Any] | None = None


@dataclass
class HttpResult:
    status_code: int | None
    data: Any | None
    error: str | None = None


class VentaCompletaWizardV2Prototype:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = WizardState()
        self.root = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)

    def build(self) -> ft.Control:
        self._render()
        return self.root

    def _render(self) -> None:
        self.root.controls = [
            ft.Text("Prototipo — Wizard venta completa V2", size=28, weight=ft.FontWeight.W_700),
            ft.Text(
                "Flujo UX definitivo para venta completa del dominio comercial. "
                "No calcula cronograma, interes ni indexacion localmente; confirma contra endpoints reales.",
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
            skipped = index == 5 and self.state.forma_pago == "CONTADO"
            errors = [] if skipped else self._step_errors(index)
            complete = skipped or not errors
            is_current = index == self.state.current_step
            icon = ft.Icons.SKIP_NEXT if skipped else (ft.Icons.CHECK_CIRCLE if complete else ft.Icons.ERROR_OUTLINE)
            color = ft.Colors.BLUE_GREY_400 if skipped else (ft.Colors.GREEN_700 if complete else ft.Colors.RED_700)
            controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon, size=14, color=color),
                            ft.Text(label, size=12, weight=ft.FontWeight.W_700 if is_current else ft.FontWeight.W_400),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                    padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                    border=_border_all(1.5 if is_current else 1, ft.Colors.BLUE_300 if is_current else ft.Colors.BLUE_GREY_100),
                    border_radius=14,
                )
            )
        return ft.Row(controls=controls, wrap=True, spacing=6, run_spacing=4)

    def _step_content(self) -> ft.Control:
        step = self.state.current_step
        if step == 0:
            return self._step_origen()
        if step == 1:
            return self._step_objetos()
        if step == 2:
            return self._step_compradores()
        if step == 3:
            return self._step_datos_comerciales()
        if step == 4:
            return self._step_forma_pago()
        if step == 5:
            return self._step_plan_pago()
        if step == 6:
            return self._step_revision()
        if step == 7:
            return self._step_confirmar()
        return self._step_resultado()

    def _card(self, title: str, controls: list[ft.Control]) -> ft.Control:
        return ft.Container(
            content=ft.Column(controls=[ft.Text(title, size=20, weight=ft.FontWeight.W_700), *controls], spacing=10),
            padding=16,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=12,
        )

    def _notice(self, text: str) -> ft.Control:
        return ft.Container(
            content=ft.Text(text, color=ft.Colors.BLUE_GREY_700),
            padding=10,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=8,
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
        controls: list[ft.Control] = [
            origen,
            self._notice("RESERVA exige id_reserva_venta e If-Match-Version. DIRECTA no pide reserva ni id_venta."),
        ]
        if self.state.origen == "RESERVA":
            controls.extend(
                [
                    ft.Row(
                        controls=[
                            self._field("id_reserva_venta", self.state.id_reserva_venta, lambda v: setattr(self.state, "id_reserva_venta", v), 190),
                            self._field("If-Match-Version", self.state.if_match_version, lambda v: setattr(self.state, "if_match_version", v), 210),
                        ],
                        wrap=True,
                    ),
                    self._field("Datos visuales opcionales de la reserva", self.state.reserva_visual, lambda v: setattr(self.state, "reserva_visual", v), 520),
                ]
            )
        return self._card("Paso 1 — Origen", controls)

    def _set_origen(self, value: str) -> None:
        self.state.origen = value
        if value == "DIRECTA":
            self.state.id_reserva_venta = ""
            self.state.if_match_version = ""
            self.state.reserva_visual = ""

    def _step_objetos(self) -> ft.Control:
        controls: list[ft.Control] = [
            self._notice(
                "Modo demo/manual: la busqueda es visual hasta integrar endpoint de busqueda. "
                "El backend valida solapamiento jerarquico inmueble + UF hija."
            )
        ]
        for index, objeto in enumerate(self.state.objetos):
            controls.append(self._objeto_card(index, objeto))
        controls.extend(
            [
                ft.Row(
                    controls=[
                        ft.Button("Agregar objeto", icon=ft.Icons.ADD, on_click=lambda _: self._add_objeto()),
                        ft.OutlinedButton("Quitar ultimo", on_click=lambda _: self._remove_last(self.state.objetos)),
                    ],
                    wrap=True,
                ),
                ft.Text(f"Total venta derivado de objetos: {_money(self._total_objetos())}", size=18, weight=ft.FontWeight.W_700),
                ft.Text("No se pide monto_total como dato principal; si el contrato lo requiere se completa internamente con este total."),
            ]
        )
        return self._card("Paso 2 — Objetos de venta", controls)

    def _objeto_card(self, index: int, objeto: ObjetoDraft) -> ft.Control:
        tipo = _drop("Tipo", list(TIPOS_OBJETO), objeto.tipo, width=210)
        tipo.on_change = lambda event, o=objeto: self._set_and_render(lambda v: self._set_tipo_objeto(o, v), event.control.value)
        id_control: ft.Control
        if objeto.tipo == "INMUEBLE":
            id_control = self._field("ID backend id_inmueble", objeto.id_inmueble, lambda v, o=objeto: self._set_objeto_inmueble(o, v), 210)
        else:
            id_control = self._field("ID backend id_unidad_funcional", objeto.id_unidad_funcional, lambda v, o=objeto: self._set_objeto_uf(o, v), 250)
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Objeto #{index + 1}", weight=ft.FontWeight.W_700),
                    ft.Row(
                        controls=[
                            self._field("Buscar inmueble o unidad", objeto.busqueda_visual, lambda v, o=objeto: setattr(o, "busqueda_visual", v), 260),
                            tipo,
                            id_control,
                            self._field("Descripcion visual", objeto.descripcion, lambda v, o=objeto: setattr(o, "descripcion", v), 260),
                            self._field("valor asignado / precio_asignado", objeto.precio_asignado, lambda v, o=objeto: setattr(o, "precio_asignado", v), 260),
                        ],
                        wrap=True,
                    ),
                    ft.Text("XOR visual: al elegir INMUEBLE se limpia id_unidad_funcional; al elegir UF se limpia id_inmueble."),
                ],
                spacing=8,
            ),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _set_tipo_objeto(self, objeto: ObjetoDraft, value: str) -> None:
        objeto.tipo = value
        if value == "INMUEBLE":
            objeto.id_unidad_funcional = ""
        else:
            objeto.id_inmueble = ""

    def _set_objeto_inmueble(self, objeto: ObjetoDraft, value: str) -> None:
        objeto.id_inmueble = value
        if _clean_text(value):
            objeto.id_unidad_funcional = ""

    def _set_objeto_uf(self, objeto: ObjetoDraft, value: str) -> None:
        objeto.id_unidad_funcional = value
        if _clean_text(value):
            objeto.id_inmueble = ""

    def _step_compradores(self) -> ft.Control:
        controls: list[ft.Control] = [
            self._notice(
                "Modo demo/manual: la busqueda es visual hasta integrar selector real. "
                "Esto define responsabilidad pactada sobre las obligaciones; no crea cuotas separadas por comprador."
            )
        ]
        for index, comprador in enumerate(self.state.compradores):
            controls.append(self._comprador_card(index, comprador))
        controls.extend(
            [
                ft.Row(
                    controls=[
                        ft.Button("Agregar comprador", icon=ft.Icons.ADD, on_click=lambda _: self._add_comprador()),
                        ft.OutlinedButton("Quitar ultimo", on_click=lambda _: self._remove_last(self.state.compradores)),
                        ft.OutlinedButton("Distribuir en partes iguales", on_click=lambda _: self._distribuir_compradores()),
                    ],
                    wrap=True,
                ),
                ft.Text(f"Suma de responsabilidades: {_money(self._suma_responsabilidades())}%", weight=ft.FontWeight.W_700),
                ft.Text("Un comprador sin porcentaje se asume 100%; varios compradores requieren porcentaje explicito y suma 100%."),
            ]
        )
        return self._card("Paso 3 — Compradores", controls)

    def _comprador_card(self, index: int, comprador: CompradorDraft) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Comprador #{index + 1}", weight=ft.FontWeight.W_700),
                    ft.Row(
                        controls=[
                            self._field("Buscar comprador", comprador.busqueda_visual, lambda v, c=comprador: setattr(c, "busqueda_visual", v), 240),
                            self._field("ID persona backend", comprador.id_persona, lambda v, c=comprador: setattr(c, "id_persona", v), 190),
                            self._field("Nombre mostrado", comprador.nombre_visual, lambda v, c=comprador: setattr(c, "nombre_visual", v), 240),
                            self._field("porcentaje_responsabilidad", comprador.porcentaje_responsabilidad, lambda v, c=comprador: setattr(c, "porcentaje_responsabilidad", v), 250),
                        ],
                        wrap=True,
                    ),
                ],
                spacing=8,
            ),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _step_datos_comerciales(self) -> ft.Control:
        return self._card(
            "Paso 4 — Datos comerciales",
            [
                ft.Row(
                    controls=[
                        self._field("codigo_venta", self.state.codigo_venta, lambda v: setattr(self.state, "codigo_venta", v), 220),
                        self._field("fecha_venta", self.state.fecha_venta, lambda v: setattr(self.state, "fecha_venta", v), 180),
                        self._field("moneda", self.state.moneda, lambda v: setattr(self.state, "moneda", v), 140),
                    ],
                    wrap=True,
                ),
                self._field("observaciones", self.state.observaciones, lambda v: setattr(self.state, "observaciones", v), 560),
                ft.Text(f"Total de venta calculado desde objetos (no editable): {_money(self._total_objetos())}", size=18, weight=ft.FontWeight.W_700),
                ft.Text("Si el contrato requiere monto_total, el payload lo completa internamente con el total derivado."),
            ],
        )

    def _step_forma_pago(self) -> ft.Control:
        forma = _drop("Forma de pago", list(FORMAS_PAGO), self.state.forma_pago, width=220)
        forma.on_change = lambda event: self._set_and_render(self._set_forma_pago, event.control.value)
        controls: list[ft.Control] = [forma]
        if self.state.forma_pago == "CONTADO":
            controls.extend(
                [
                    self._field("fecha de pago / vencimiento", self.state.contado_vencimiento, lambda v: setattr(self.state, "contado_vencimiento", v), 240),
                    self._notice(
                        "CONTADO no muestra el paso 6. Se construye tipo_pago=CONTADO, "
                        "monto_total_plan=total derivado y bloque CONTADO por ese total."
                    ),
                ]
            )
        else:
            controls.append(self._notice("FINANCIADO habilita el subwizard de Plan de pago / financiacion."))
        return self._card("Paso 5 — Forma de pago", controls)

    def _set_forma_pago(self, value: str) -> None:
        self.state.forma_pago = value
        if value == "CONTADO":
            self.state.plan_substep = 0

    def _step_plan_pago(self) -> ft.Control:
        if self.state.forma_pago == "CONTADO":
            return self._card(
                "Paso 6 — Plan de pago",
                [self._notice("No aplica para CONTADO. El wizard saltara este paso al avanzar.")],
            )
        return self._card(
            "Paso 6 — Plan de pago / financiacion",
            [
                self._plan_subwizard_header(),
                self._plan_substep_content(),
                self._plan_subwizard_nav(),
            ],
        )

    def _plan_subwizard_header(self) -> ft.Control:
        controls: list[ft.Control] = []
        for index, label in enumerate(PLAN_SUBSTEPS):
            controls.append(
                ft.Container(
                    content=ft.Text(label, weight=ft.FontWeight.W_700 if self.state.plan_substep == index else ft.FontWeight.W_400),
                    padding=ft.Padding(left=10, top=6, right=10, bottom=6),
                    border=_border_all(1.5 if self.state.plan_substep == index else 1, ft.Colors.BLUE_300 if self.state.plan_substep == index else ft.Colors.BLUE_GREY_100),
                    border_radius=14,
                )
            )
        return ft.Row(controls=controls, wrap=True, spacing=6)

    def _plan_substep_content(self) -> ft.Control:
        if self.state.plan_substep == 0:
            return self._plan_anticipo()
        if self.state.plan_substep == 1:
            return self._plan_tramos()
        return self._plan_saldo_resumen()

    def _plan_anticipo(self) -> ft.Control:
        toggle = ft.Switch(label="Tiene anticipo", value=self.state.tiene_anticipo)
        toggle.on_change = lambda event: self._set_bool_and_render(lambda v: setattr(self.state, "tiene_anticipo", v), bool(event.control.value))
        controls: list[ft.Control] = [toggle]
        if self.state.tiene_anticipo:
            controls.append(
                ft.Row(
                    controls=[
                        self._field("importe anticipo", self.state.anticipo_importe, lambda v: setattr(self.state, "anticipo_importe", v), 190),
                        self._field("vencimiento anticipo", self.state.anticipo_vencimiento, lambda v: setattr(self.state, "anticipo_vencimiento", v), 210),
                    ],
                    wrap=True,
                )
            )
        else:
            controls.append(ft.Text("Sin anticipo: se usa importe 0."))
        controls.append(ft.Text(f"Capital pendiente actual: {_money(self._capital_pendiente())}", weight=ft.FontWeight.W_700))
        return ft.Column(controls=controls, spacing=10)

    def _plan_tramos(self) -> ft.Control:
        controls: list[ft.Control] = [
            self._notice(
                "Al crear un tramo, el capital se precarga con el pendiente. Puede editarse a un valor menor, nunca <= 0 ni mayor al pendiente disponible."
            )
        ]
        for index, tramo in enumerate(self.state.tramos):
            controls.append(self._tramo_card(index, tramo))
        controls.extend(
            [
                ft.Row(
                    controls=[
                        ft.Button("Agregar tramo", icon=ft.Icons.ADD, on_click=lambda _: self._add_tramo()),
                        ft.OutlinedButton("Quitar ultimo tramo", on_click=lambda _: self._remove_last(self.state.tramos)),
                    ],
                    wrap=True,
                ),
                ft.Text(f"Capital pendiente de asignar: {_money(self._capital_pendiente())}", weight=ft.FontWeight.W_700),
            ]
        )
        return ft.Column(controls=controls, spacing=10)

    def _tramo_card(self, index: int, tramo: TramoCuotasDraft) -> ft.Control:
        metodo = _drop("Metodo", list(METODOS_TRAMO.keys()), tramo.metodo_label, width=260)
        metodo.on_change = lambda event, t=tramo: self._set_and_render(lambda v: setattr(t, "metodo_label", v), event.control.value)
        extra: list[ft.Control] = []
        metodo_codigo = METODOS_TRAMO[tramo.metodo_label]
        if metodo_codigo == "INTERES_DIRECTO":
            extra = [
                ft.Row(
                    controls=[
                        self._field("tasa_interes_directo_periodica", tramo.tasa_periodica, lambda v, t=tramo: setattr(t, "tasa_periodica", v), 260),
                        self._field("cantidad_periodos", tramo.cantidad_periodos, lambda v, t=tramo: setattr(t, "cantidad_periodos", v), 210),
                    ],
                    wrap=True,
                ),
                ft.Text("Mapeo tecnico: base_calculo_interes = CAPITAL_INICIAL_BLOQUE."),
            ]
        if metodo_codigo == "INDEXACION":
            extra = [
                ft.Row(
                    controls=[
                        self._field("indice visual", tramo.indice_visual, lambda v, t=tramo: setattr(t, "indice_visual", v), 180),
                        self._field("id_indice_financiero", tramo.id_indice_financiero, lambda v, t=tramo: setattr(t, "id_indice_financiero", v), 220),
                        self._field("fecha_base_indice", tramo.fecha_base_indice, lambda v, t=tramo: setattr(t, "fecha_base_indice", v), 200),
                        self._field("valor_base_indice", tramo.valor_base_indice, lambda v, t=tramo: setattr(t, "valor_base_indice", v), 200),
                    ],
                    wrap=True,
                ),
                ft.Text(
                    "Defaults tecnicos: POR_COEFICIENTE, CAPITAL_INICIAL_BLOQUE, DEFINITIVA, "
                    "ERROR_SI_NO_EXISTE, conserva capital original y genera ajuste por diferencia."
                ),
            ]
        refuerzo_switch = ft.Switch(label="Usa cuotas refuerzo", value=tramo.usa_refuerzos)
        refuerzo_switch.on_change = lambda event, t=tramo: self._set_bool_and_render(lambda v: self._set_usa_refuerzos(t, v), bool(event.control.value))
        refuerzo_controls: list[ft.Control] = [
            refuerzo_switch,
            ft.Text("24 cuotas con 2 refuerzos siguen siendo 24 cuotas totales: 22 normales + 2 refuerzo."),
            ft.Text("No se suman refuerzos por fuera del total del tramo; se envian como cuotas_refuerzo dentro del tramo."),
        ]
        if tramo.usa_refuerzos:
            for ref_index, refuerzo in enumerate(tramo.refuerzos):
                refuerzo_controls.append(self._refuerzo_interno_card(index, ref_index, refuerzo))
            refuerzo_controls.append(
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Agregar refuerzo interno", on_click=lambda _, t=tramo: self._add_refuerzo_interno(t)),
                        ft.OutlinedButton("Quitar ultimo refuerzo", on_click=lambda _, t=tramo: self._remove_last(t.refuerzos)),
                    ],
                    wrap=True,
                )
            )
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Tramo #{index + 1}", weight=ft.FontWeight.W_700),
                    ft.Row(
                        controls=[
                            self._field("Capital del tramo", tramo.capital_tramo, lambda v, t=tramo: setattr(t, "capital_tramo", v), 190),
                            self._field("cantidad total de cuotas", tramo.cantidad_cuotas, lambda v, t=tramo: setattr(t, "cantidad_cuotas", v), 230),
                            self._field("primer vencimiento", tramo.primer_vencimiento, lambda v, t=tramo: setattr(t, "primer_vencimiento", v), 190),
                            ft.Text("periodicidad = MENSUAL", weight=ft.FontWeight.W_700),
                            metodo,
                        ],
                        wrap=True,
                    ),
                    *extra,
                    ft.Divider(),
                    *refuerzo_controls,
                ],
                spacing=8,
            ),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _refuerzo_interno_card(self, tramo_index: int, ref_index: int, refuerzo: RefuerzoInternoDraft) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"Refuerzo interno {tramo_index + 1}.{ref_index + 1}", weight=ft.FontWeight.W_700),
                    self._field("numero_cuota", refuerzo.numero_cuota, lambda v, r=refuerzo: setattr(r, "numero_cuota", v), 160),
                    self._field("etiqueta", refuerzo.etiqueta, lambda v, r=refuerzo: setattr(r, "etiqueta", v), 190),
                    self._field("unidades_refuerzo", refuerzo.unidades_refuerzo, lambda v, r=refuerzo: setattr(r, "unidades_refuerzo", v), 190),
                ],
                wrap=True,
            ),
            padding=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=8,
        )

    def _set_usa_refuerzos(self, tramo: TramoCuotasDraft, value: bool) -> None:
        tramo.usa_refuerzos = value
        if value and not tramo.refuerzos:
            tramo.refuerzos.append(RefuerzoInternoDraft(numero_cuota="1"))
        if not value:
            tramo.refuerzos = []

    def _plan_saldo_resumen(self) -> ft.Control:
        saldo_switch = ft.Switch(label="Tiene saldo final", value=self.state.tiene_saldo_final)
        saldo_switch.on_change = lambda event: self._set_bool_and_render(lambda v: setattr(self.state, "tiene_saldo_final", v), bool(event.control.value))
        rows: list[ft.Control] = [saldo_switch]
        if self.state.tiene_saldo_final:
            rows.append(
                ft.Row(
                    controls=[
                        self._field("importe saldo final", self.state.saldo_importe, lambda v: setattr(self.state, "saldo_importe", v), 190),
                        self._field("vencimiento saldo final", self.state.saldo_vencimiento, lambda v: setattr(self.state, "saldo_vencimiento", v), 220),
                    ],
                    wrap=True,
                )
            )
        rows.append(self._plan_totals_panel())
        return ft.Column(controls=rows, spacing=10)

    def _plan_totals_panel(self) -> ft.Control:
        total = self._total_objetos()
        anticipo = self._anticipo_total()
        tramos = self._tramos_total()
        saldo = self._saldo_total()
        asignado = anticipo + tramos + saldo
        diferencia = total - asignado
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Resumen de asignacion", weight=ft.FontWeight.W_700),
                    ft.Text(f"Total derivado objetos: {_money(total)}"),
                    ft.Text(f"Anticipo: {_money(anticipo)}"),
                    ft.Text(f"Suma tramos: {_money(tramos)}"),
                    ft.Text(f"Saldo final: {_money(saldo)}"),
                    ft.Text(f"Total asignado: {_money(asignado)}", weight=ft.FontWeight.W_700),
                    ft.Text(f"Diferencia: {_money(diferencia)}", color=ft.Colors.GREEN_700 if diferencia == 0 else ft.Colors.RED_700, weight=ft.FontWeight.W_700),
                ],
                spacing=4,
            ),
            padding=12,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
        )

    def _plan_subwizard_nav(self) -> ft.Control:
        return ft.Row(
            controls=[
                ft.OutlinedButton("Anterior subseccion", disabled=self.state.plan_substep == 0, on_click=lambda _: self._move_plan_substep(-1)),
                ft.Button("Siguiente subseccion", disabled=self.state.plan_substep == len(PLAN_SUBSTEPS) - 1, on_click=lambda _: self._move_plan_substep(1)),
            ],
            wrap=True,
        )

    def _step_revision(self) -> ft.Control:
        payload_switch = ft.Switch(label="Ver payload JSON (debug/prototipo)", value=self.state.show_payload)
        payload_switch.on_change = lambda event: self._set_bool_and_render(lambda v: setattr(self.state, "show_payload", v), bool(event.control.value))
        controls: list[ft.Control] = [
            ft.Text("Resumen comercial", size=18, weight=ft.FontWeight.W_700),
            self._commercial_summary(),
            ft.Text("No se muestra ni calcula cronograma local. El cronograma/obligaciones se obtienen del backend."),
            payload_switch,
        ]
        if self.state.show_payload:
            controls.extend([ft.Text("Payload JSON", weight=ft.FontWeight.W_700), _text_json(self._build_payload())])
        return self._card("Paso 7 — Revision", controls)

    def _commercial_summary(self) -> ft.Control:
        lines = [
            f"Origen: {self.state.origen}",
            f"Total derivado: {_money(self._total_objetos())} {self.state.moneda}",
            f"Fecha venta: {self.state.fecha_venta}",
            f"Forma de pago: {self.state.forma_pago}",
            f"Compradores: {len(self.state.compradores)}",
            f"Objetos: {len(self.state.objetos)}",
        ]
        if self.state.forma_pago == "FINANCIADO":
            lines.extend(
                [
                    f"Anticipo: {_money(self._anticipo_total())}",
                    f"Tramos: {len(self.state.tramos)} / {_money(self._tramos_total())}",
                    f"Saldo final: {_money(self._saldo_total())}",
                ]
            )
        return ft.Container(
            content=ft.Column(controls=[ft.Text(item) for item in lines], spacing=3),
            padding=12,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=8,
        )

    def _step_confirmar(self) -> ft.Control:
        request_switch = ft.Switch(label="Mostrar request tecnico/debug", value=self.state.show_request)
        request_switch.on_change = lambda event: self._set_bool_and_render(lambda v: setattr(self.state, "show_request", v), bool(event.control.value))
        controls: list[ft.Control] = [
            self._field("Base URL", self.state.base_url, lambda v: setattr(self.state, "base_url", v), 360),
            ft.Row(
                controls=[
                    self._field("X-Op-Id", self.state.x_op_id, lambda v: setattr(self.state, "x_op_id", v), 360),
                    ft.OutlinedButton("Nuevo X-Op-Id", on_click=lambda _: self._new_op_id()),
                ],
                wrap=True,
            ),
            ft.Row(
                controls=[
                    self._field("X-Usuario-Id", self.state.x_usuario_id, lambda v: setattr(self.state, "x_usuario_id", v), 180),
                    self._field("X-Sucursal-Id", self.state.x_sucursal_id, lambda v: setattr(self.state, "x_sucursal_id", v), 180),
                    self._field("X-Instalacion-Id", self.state.x_instalacion_id, lambda v: setattr(self.state, "x_instalacion_id", v), 190),
                ],
                wrap=True,
            ),
            self._field("observaciones de confirmacion", self.state.confirm_observaciones, lambda v: setattr(self.state, "confirm_observaciones", v), 520),
            request_switch,
            ft.Button("Ejecutar POST real", icon=ft.Icons.SEND, disabled=self.state.loading, on_click=lambda _: self._confirmar()),
            ft.Text("RESERVA envia If-Match-Version; DIRECTA no lo envia.", weight=ft.FontWeight.W_700),
        ]
        if self.state.show_request:
            controls.extend([ft.Text("Request que se ejecutara", weight=ft.FontWeight.W_700), _text_json(self._request_snapshot("POST", self._endpoint_path(), self._headers(), self._build_payload()))])
        return self._card("Paso 8 — Confirmar", controls)

    def _step_resultado(self) -> ft.Control:
        id_venta = self._resolve_id_venta(self.state.last_response)
        estado_venta = self._resolve_estado_venta(self.state.last_response)
        controls: list[ft.Control] = [
            ft.Text(f"Status HTTP: {self.state.last_status if self.state.last_status is not None else '-'}", weight=ft.FontWeight.W_700),
        ]
        if self.state.last_error:
            controls.append(ft.Text(self.state.last_error, color=ft.Colors.RED_700))
        controls.extend(
            [
                ft.Text(f"id_venta: {id_venta if id_venta is not None else '-'}"),
                ft.Text(f"estado_venta: {estado_venta or '-'}"),
                ft.Text("Respuesta JSON", weight=ft.FontWeight.W_700),
                _text_json(self.state.last_response),
            ]
        )
        if self.state.last_request:
            controls.extend([ft.Text("Request ejecutado", weight=ft.FontWeight.W_700), _text_json(self.state.last_request)])
        if id_venta is not None:
            controls.append(ft.Button("Consultar Plan Pago V2", icon=ft.Icons.SEARCH, disabled=self.state.loading, on_click=lambda _, venta_id=id_venta: self._consultar_plan_pago(venta_id)))
        if self.state.plan_request:
            controls.extend([ft.Text("Request consulta Plan Pago V2", weight=ft.FontWeight.W_700), _text_json(self.state.plan_request)])
        if self.state.plan_status is not None or self.state.plan_error or self.state.plan_response is not None:
            controls.append(self._plan_result_panel())
        return self._card("Paso 9 — Resultado", controls)

    def _plan_result_panel(self) -> ft.Control:
        data = self.state.plan_response
        resumen = self._extract_plan_data(data)
        controls: list[ft.Control] = [ft.Text(f"Status consulta: {self.state.plan_status}", weight=ft.FontWeight.W_700)]
        if self.state.plan_error:
            controls.append(ft.Text(self.state.plan_error, color=ft.Colors.RED_700))
        controls.append(ft.Text("Resumen", weight=ft.FontWeight.W_700))
        controls.append(_text_json(self._summarize_plan_response(resumen)))
        controls.append(ft.Text("Respuesta integral Plan Pago V2 (bloques, obligaciones, obligados, indexacion y cuotas_refuerzo si aparecen)", weight=ft.FontWeight.W_700))
        controls.append(_text_json(data))
        return ft.Container(content=ft.Column(controls=controls, spacing=8), padding=12, border=_border_all(1, ft.Colors.BLUE_GREY_100), border_radius=10)

    def _summary_panel(self) -> ft.Control:
        errors = self._step_errors(self.state.current_step)
        total = self._total_objetos()
        assigned = self._assigned_total()
        controls: list[ft.Control] = [
            ft.Text("Panel de control", size=18, weight=ft.FontWeight.W_700),
            ft.Text(f"Origen: {self.state.origen}"),
            ft.Text(f"Forma pago: {self.state.forma_pago}"),
            ft.Text(f"Total derivado: {_money(total)}"),
            ft.Text(f"Total asignado plan: {_money(assigned)}"),
        ]
        if errors:
            controls.append(ft.Text("Validaciones pendientes", color=ft.Colors.RED_700, weight=ft.FontWeight.W_700))
            controls.extend([ft.Text(f"• {error}", color=ft.Colors.RED_700, size=12) for error in errors[:8]])
            if len(errors) > 8:
                controls.append(ft.Text(f"• ... {len(errors) - 8} mas", color=ft.Colors.RED_700, size=12))
        else:
            controls.append(ft.Text("Paso valido", color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_700))
        return ft.Container(content=ft.Column(controls=controls, spacing=6), padding=14, border=_border_all(1, ft.Colors.BLUE_GREY_100), border_radius=12)

    def _nav_buttons(self) -> ft.Control:
        prev_disabled = self.state.current_step == 0 or self.state.loading
        next_disabled = self.state.current_step >= len(STEPS) - 1 or self.state.loading
        return ft.Row(
            controls=[
                ft.OutlinedButton("Anterior", disabled=prev_disabled, on_click=lambda _: self._move_step(-1)),
                ft.Button("Siguiente", disabled=next_disabled, on_click=lambda _: self._move_step(1)),
                ft.OutlinedButton("Ir a revision", disabled=self.state.loading, on_click=lambda _: self._go_review()),
            ],
            wrap=True,
        )

    def _move_step(self, delta: int) -> None:
        target = self.state.current_step + delta
        if delta > 0 and self.state.current_step == 4 and self.state.forma_pago == "CONTADO":
            target = 6
        if delta < 0 and self.state.current_step == 6 and self.state.forma_pago == "CONTADO":
            target = 4
        self.state.current_step = max(0, min(len(STEPS) - 1, target))
        self._render()

    def _move_plan_substep(self, delta: int) -> None:
        self.state.plan_substep = max(0, min(len(PLAN_SUBSTEPS) - 1, self.state.plan_substep + delta))
        self._render()

    def _go_review(self) -> None:
        self.state.current_step = 6
        self._render()

    def _add_objeto(self) -> None:
        self.state.objetos.append(ObjetoDraft())
        self._render()

    def _add_comprador(self) -> None:
        self.state.compradores.append(CompradorDraft())
        self._render()

    def _add_tramo(self) -> None:
        pendiente = self._capital_pendiente()
        self.state.tramos.append(TramoCuotasDraft(capital_tramo=_money(pendiente if pendiente > 0 else Decimal("0"))))
        self._render()

    def _add_refuerzo_interno(self, tramo: TramoCuotasDraft) -> None:
        tramo.refuerzos.append(RefuerzoInternoDraft())
        self._render()

    def _remove_last(self, collection: list[Any]) -> None:
        if collection:
            collection.pop()
        self._render()

    def _distribuir_compradores(self) -> None:
        cantidad = len(self.state.compradores)
        if cantidad == 0:
            return
        base = (Decimal("100") / Decimal(cantidad)).quantize(Decimal("0.01"))
        acumulado = Decimal("0")
        for index, comprador in enumerate(self.state.compradores):
            if index == cantidad - 1:
                comprador.porcentaje_responsabilidad = str(Decimal("100") - acumulado)
            else:
                comprador.porcentaje_responsabilidad = str(base)
                acumulado += base
        self._render()

    def _new_op_id(self) -> None:
        self.state.x_op_id = str(uuid4())
        self._render()

    def _total_objetos(self) -> Decimal:
        return sum((_decimal_or_none(objeto.precio_asignado) or Decimal("0") for objeto in self.state.objetos), Decimal("0"))

    def _suma_responsabilidades(self) -> Decimal:
        if len(self.state.compradores) == 1 and not _clean_text(self.state.compradores[0].porcentaje_responsabilidad):
            return Decimal("100")
        return sum((_decimal_or_none(comprador.porcentaje_responsabilidad) or Decimal("0") for comprador in self.state.compradores), Decimal("0"))

    def _anticipo_total(self) -> Decimal:
        if not self.state.tiene_anticipo:
            return Decimal("0")
        return _decimal_or_none(self.state.anticipo_importe) or Decimal("0")

    def _tramos_total(self) -> Decimal:
        return sum((_decimal_or_none(tramo.capital_tramo) or Decimal("0") for tramo in self.state.tramos), Decimal("0"))

    def _saldo_total(self) -> Decimal:
        if not self.state.tiene_saldo_final:
            return Decimal("0")
        return _decimal_or_none(self.state.saldo_importe) or Decimal("0")

    def _assigned_total(self) -> Decimal:
        if self.state.forma_pago == "CONTADO":
            return self._total_objetos()
        return self._anticipo_total() + self._tramos_total() + self._saldo_total()

    def _capital_pendiente(self) -> Decimal:
        return self._total_objetos() - self._anticipo_total() - self._tramos_total() - self._saldo_total()

    def _step_errors(self, step: int) -> list[str]:
        if step == 0:
            return self._origin_errors()
        if step == 1:
            return self._object_errors()
        if step == 2:
            return self._buyer_errors()
        if step == 3:
            return self._commercial_errors()
        if step == 4:
            return self._payment_form_errors()
        if step == 5:
            return self._plan_errors()
        if step == 6:
            return self._all_errors()
        if step == 7:
            return self._all_errors() + self._header_errors()
        return []

    def _all_errors(self) -> list[str]:
        return self._origin_errors() + self._object_errors() + self._buyer_errors() + self._commercial_errors() + self._payment_form_errors() + self._plan_errors()

    def _origin_errors(self) -> list[str]:
        errors: list[str] = []
        if self.state.origen not in ORIGENES:
            errors.append("Origen requerido.")
        if self.state.origen == "RESERVA":
            if _int_or_none(self.state.id_reserva_venta) is None:
                errors.append("RESERVA requiere id_reserva_venta numerico.")
            if _int_or_none(self.state.if_match_version) is None:
                errors.append("RESERVA requiere If-Match-Version numerico.")
        return errors

    def _object_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.state.objetos:
            return ["Debe cargar al menos un objeto de venta."]
        for index, objeto in enumerate(self.state.objetos, start=1):
            precio = _decimal_or_none(objeto.precio_asignado)
            if precio is None or precio <= 0:
                errors.append(f"Objeto #{index}: precio_asignado requerido y mayor a 0.")
            if objeto.tipo == "INMUEBLE":
                if _int_or_none(objeto.id_inmueble) is None:
                    errors.append(f"Objeto #{index}: id_inmueble requerido para tipo INMUEBLE.")
                if _clean_text(objeto.id_unidad_funcional):
                    errors.append(f"Objeto #{index}: XOR invalido, id_unidad_funcional debe estar vacio.")
            elif objeto.tipo == "UNIDAD_FUNCIONAL":
                if _int_or_none(objeto.id_unidad_funcional) is None:
                    errors.append(f"Objeto #{index}: id_unidad_funcional requerido para tipo UNIDAD_FUNCIONAL.")
                if _clean_text(objeto.id_inmueble):
                    errors.append(f"Objeto #{index}: XOR invalido, id_inmueble debe estar vacio.")
            else:
                errors.append(f"Objeto #{index}: tipo invalido.")
        return errors

    def _buyer_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.state.compradores:
            return ["Debe cargar al menos un comprador."]
        ids: set[int] = set()
        suma = Decimal("0")
        for index, comprador in enumerate(self.state.compradores, start=1):
            id_persona = _int_or_none(comprador.id_persona)
            if id_persona is None:
                errors.append(f"Comprador #{index}: id_persona requerido.")
            elif id_persona in ids:
                errors.append(f"Comprador #{index}: id_persona duplicado.")
            else:
                ids.add(id_persona)
            pct = _decimal_or_none(comprador.porcentaje_responsabilidad)
            if len(self.state.compradores) == 1 and pct is None:
                pct = Decimal("100")
            if pct is None:
                errors.append(f"Comprador #{index}: varios compradores requieren porcentaje_responsabilidad.")
            elif pct <= 0 or pct > 100:
                errors.append(f"Comprador #{index}: porcentaje debe ser > 0 y <= 100.")
            else:
                suma += pct
        if self.state.compradores and suma != Decimal("100"):
            errors.append("La suma de porcentaje_responsabilidad debe ser 100.")
        return errors

    def _commercial_errors(self) -> list[str]:
        errors: list[str] = []
        if not _clean_text(self.state.fecha_venta):
            errors.append("fecha_venta requerida.")
        if not _clean_text(self.state.moneda):
            errors.append("moneda requerida.")
        if self._total_objetos() <= 0:
            errors.append("El total derivado debe ser mayor a 0.")
        return errors

    def _payment_form_errors(self) -> list[str]:
        errors: list[str] = []
        if self.state.forma_pago not in FORMAS_PAGO:
            errors.append("Forma de pago requerida.")
        if self.state.forma_pago == "CONTADO" and not _clean_text(self.state.contado_vencimiento):
            errors.append("CONTADO requiere fecha de pago/vencimiento.")
        return errors

    def _plan_errors(self) -> list[str]:
        if self.state.forma_pago == "CONTADO":
            return []
        errors: list[str] = []
        total = self._total_objetos()
        anticipo = self._anticipo_total()
        saldo = self._saldo_total()
        if self.state.tiene_anticipo:
            if anticipo <= 0:
                errors.append("Anticipo: importe debe ser mayor a 0 si aplica.")
            if not _clean_text(self.state.anticipo_vencimiento):
                errors.append("Anticipo: vencimiento requerido si aplica.")
        if self.state.tiene_saldo_final:
            if saldo <= 0:
                errors.append("Saldo final: importe debe ser mayor a 0 si aplica.")
            if not _clean_text(self.state.saldo_vencimiento):
                errors.append("Saldo final: vencimiento requerido si aplica.")
        total_tramos_previos = Decimal("0")
        for index, tramo in enumerate(self.state.tramos, start=1):
            capital = _decimal_or_none(tramo.capital_tramo)
            pending_before = total - anticipo - saldo - total_tramos_previos
            if capital is None or capital <= 0:
                errors.append(f"Tramo #{index}: capital debe ser mayor a 0.")
            elif capital > pending_before:
                errors.append(f"Tramo #{index}: capital no puede superar el pendiente disponible ({_money(pending_before)}).")
            else:
                total_tramos_previos += capital
            cuotas = _int_or_none(tramo.cantidad_cuotas)
            if cuotas is None or cuotas <= 0:
                errors.append(f"Tramo #{index}: cantidad total de cuotas requerida y mayor a 0.")
            if not _clean_text(tramo.primer_vencimiento):
                errors.append(f"Tramo #{index}: primer vencimiento requerido.")
            metodo = METODOS_TRAMO.get(tramo.metodo_label)
            if metodo is None:
                errors.append(f"Tramo #{index}: metodo requerido.")
            if metodo == "INTERES_DIRECTO":
                tasa = _decimal_or_none(tramo.tasa_periodica)
                periodos = _int_or_none(tramo.cantidad_periodos)
                if tasa is None:
                    errors.append(f"Tramo #{index}: INTERES_DIRECTO requiere tasa_interes_directo_periodica.")
                if periodos is None or periodos <= 0:
                    errors.append(f"Tramo #{index}: INTERES_DIRECTO requiere cantidad_periodos > 0.")
            if metodo == "INDEXACION":
                if _int_or_none(tramo.id_indice_financiero) is None:
                    errors.append(f"Tramo #{index}: INDEXACION requiere id_indice_financiero.")
                if not _clean_text(tramo.fecha_base_indice):
                    errors.append(f"Tramo #{index}: INDEXACION requiere fecha_base_indice.")
                valor_base = _decimal_or_none(tramo.valor_base_indice)
                if valor_base is None or valor_base <= 0:
                    errors.append(f"Tramo #{index}: INDEXACION requiere valor_base_indice > 0.")
            if tramo.usa_refuerzos:
                seen: set[int] = set()
                for ref_index, refuerzo in enumerate(tramo.refuerzos, start=1):
                    numero = _int_or_none(refuerzo.numero_cuota)
                    if numero is None:
                        errors.append(f"Tramo #{index} refuerzo #{ref_index}: numero_cuota requerido.")
                    elif cuotas is not None and (numero < 1 or numero > cuotas):
                        errors.append(f"Tramo #{index} refuerzo #{ref_index}: numero_cuota fuera de rango 1..{cuotas}.")
                    elif numero in seen:
                        errors.append(f"Tramo #{index}: numero_cuota de refuerzo duplicado ({numero}).")
                    else:
                        seen.add(numero)
                    unidades = _decimal_or_none(refuerzo.unidades_refuerzo)
                    if unidades is None or unidades <= 0:
                        errors.append(f"Tramo #{index} refuerzo #{ref_index}: unidades_refuerzo debe ser > 0.")
        if self._assigned_total() != total:
            errors.append("FINANCIADO requiere total asignado igual al total derivado (diferencia = 0).")
        return errors

    def _header_errors(self) -> list[str]:
        errors: list[str] = []
        if not _clean_text(self.state.x_op_id):
            errors.append("X-Op-Id requerido.")
        if _int_or_none(self.state.x_usuario_id) is None:
            errors.append("X-Usuario-Id requerido/numerico.")
        if _int_or_none(self.state.x_sucursal_id) is None:
            errors.append("X-Sucursal-Id requerido/numerico.")
        if _int_or_none(self.state.x_instalacion_id) is None:
            errors.append("X-Instalacion-Id requerido/numerico.")
        return errors

    def _build_payload(self) -> dict[str, Any]:
        total = self._total_objetos()
        generar_venta = {
            "codigo_venta": _clean_text(self.state.codigo_venta) or None,
            "fecha_venta": _clean_text(self.state.fecha_venta),
            "monto_total": _decimal_payload(total),
            "observaciones": _clean_text(self.state.observaciones) or None,
        }
        condiciones = {
            "monto_total": _decimal_payload(total),
            "tipo_plan_financiero": "CONTADO" if self.state.forma_pago == "CONTADO" else "PLAN_PAGO_V2",
            "moneda": _clean_text(self.state.moneda),
            "importe_anticipo": _decimal_payload(self._anticipo_total()) if self.state.forma_pago == "FINANCIADO" else None,
            "fecha_vencimiento_anticipo": _clean_text(self.state.anticipo_vencimiento) if self.state.forma_pago == "FINANCIADO" and self.state.tiene_anticipo else None,
            "importe_saldo": _decimal_payload(self._saldo_total()) if self.state.forma_pago == "FINANCIADO" else None,
            "fecha_vencimiento_saldo": _clean_text(self.state.saldo_vencimiento) if self.state.forma_pago == "FINANCIADO" and self.state.tiene_saldo_final else None,
            "cuotas": [],
        }
        plan_pago_v2 = {
            "tipo_pago": self.state.forma_pago,
            "monto_total_plan": _decimal_payload(total),
            "moneda": _clean_text(self.state.moneda),
            "bloques": self._bloques_payload(),
            "observaciones": "Generado desde prototipo wizard venta completa V2",
        }
        payload: dict[str, Any] = {
            "generar_venta": generar_venta,
            "condiciones_comerciales": condiciones,
            "plan_pago_v2": plan_pago_v2,
            "confirmacion": {"observaciones": _clean_text(self.state.confirm_observaciones) or None},
        }
        objetos = [self._objeto_payload(item) for item in self.state.objetos]
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
                "precio_asignado": _decimal_payload(_decimal_or_none(objeto.precio_asignado)),
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
                "porcentaje_responsabilidad": _decimal_payload(pct),
                "fecha_desde": _clean_text(self.state.fecha_venta) or None,
                "fecha_hasta": None,
                "observaciones": _clean_text(comprador.nombre_visual) or None,
            }
        )

    def _bloques_payload(self) -> list[dict[str, Any]]:
        total = self._total_objetos()
        if self.state.forma_pago == "CONTADO":
            return [
                self._strip_empty(
                    {
                        "tipo_bloque": "CONTADO",
                        "etiqueta_bloque": "Contado",
                        "importe_total_bloque": _decimal_payload(total),
                        "fecha_vencimiento": _clean_text(self.state.contado_vencimiento),
                    }
                )
            ]
        bloques: list[dict[str, Any]] = []
        if self.state.tiene_anticipo:
            bloques.append(
                self._strip_empty(
                    {
                        "tipo_bloque": "ANTICIPO",
                        "etiqueta_bloque": "Anticipo",
                        "importe_total_bloque": _decimal_payload(self._anticipo_total()),
                        "fecha_vencimiento": _clean_text(self.state.anticipo_vencimiento),
                    }
                )
            )
        for index, tramo in enumerate(self.state.tramos, start=1):
            metodo = METODOS_TRAMO[tramo.metodo_label]
            bloque: dict[str, Any] = {
                "tipo_bloque": "TRAMO_CUOTAS",
                "etiqueta_bloque": f"Tramo de cuotas {index}",
                "importe_total_bloque": _decimal_payload(_decimal_or_none(tramo.capital_tramo)),
                "cantidad_cuotas": _int_or_none(tramo.cantidad_cuotas),
                "fecha_primer_vencimiento": _clean_text(tramo.primer_vencimiento),
                "periodicidad": "MENSUAL",
                "regla_redondeo": "ULTIMA_CUOTA",
                "metodo_liquidacion": metodo,
            }
            if metodo == "INTERES_DIRECTO":
                bloque.update(
                    {
                        "tasa_interes_directo_periodica": _decimal_payload(_decimal_or_none(tramo.tasa_periodica)),
                        "cantidad_periodos": _int_or_none(tramo.cantidad_periodos),
                        "base_calculo_interes": "CAPITAL_INICIAL_BLOQUE",
                    }
                )
            if metodo == "INDEXACION":
                bloque.update(
                    {
                        "id_indice_financiero": _int_or_none(tramo.id_indice_financiero),
                        "fecha_base_indice": _clean_text(tramo.fecha_base_indice),
                        "valor_base_indice": _decimal_payload(_decimal_or_none(tramo.valor_base_indice)),
                        "modo_indexacion": "POR_COEFICIENTE",
                        "base_calculo_indexacion": "CAPITAL_INICIAL_BLOQUE",
                        "tipo_generacion_indexada": "DEFINITIVA",
                        "politica_valor_no_disponible": "ERROR_SI_NO_EXISTE",
                        "conserva_capital_original": True,
                        "genera_ajuste_por_diferencia": True,
                    }
                )
            if tramo.usa_refuerzos:
                bloque["cuotas_refuerzo"] = [self._refuerzo_payload(refuerzo) for refuerzo in tramo.refuerzos]
            bloques.append(self._strip_empty(bloque))
        if self.state.tiene_saldo_final:
            bloques.append(
                self._strip_empty(
                    {
                        "tipo_bloque": "SALDO",
                        "etiqueta_bloque": "Saldo final",
                        "importe_total_bloque": _decimal_payload(self._saldo_total()),
                        "fecha_vencimiento": _clean_text(self.state.saldo_vencimiento),
                    }
                )
            )
        return bloques

    def _refuerzo_payload(self, refuerzo: RefuerzoInternoDraft) -> dict[str, Any]:
        return self._strip_empty(
            {
                "numero_cuota": _int_or_none(refuerzo.numero_cuota),
                "etiqueta": _clean_text(refuerzo.etiqueta) or None,
                "unidades_refuerzo": _decimal_payload(_decimal_or_none(refuerzo.unidades_refuerzo)),
            }
        )

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
        errors = self._all_errors() + self._header_errors()
        if errors:
            self.state.last_status = None
            self.state.last_request = None
            self.state.last_response = {"errores_validacion_ux": errors}
            self.state.last_error = "No se envia al backend porque hay errores UX."
            self.state.current_step = 8
            self._render()
            return
        path = self._endpoint_path()
        headers = self._headers()
        payload = self._build_payload()
        self.state.plan_status = None
        self.state.plan_response = None
        self.state.plan_error = None
        self.state.plan_request = None
        self.state.last_request = self._request_snapshot("POST", path, headers, payload)
        self.state.loading = True
        self._render()
        result = self._http_json("POST", path, headers=headers, payload=payload)
        self.state.loading = False
        self.state.last_status = result.status_code
        self.state.last_response = result.data
        self.state.last_error = result.error
        self.state.current_step = 8
        self._render()

    def _consultar_plan_pago(self, id_venta: int) -> None:
        path = f"/api/v1/ventas/{id_venta}/plan-pago-v2"
        self.state.plan_request = self._request_snapshot("GET", path, {}, None)
        self.state.loading = True
        self._render()
        result = self._http_json("GET", path, headers={}, payload=None)
        self.state.loading = False
        self.state.plan_status = result.status_code
        self.state.plan_response = result.data
        self.state.plan_error = result.error
        self._render()

    def _request_snapshot(self, method: str, path: str, headers: dict[str, str], payload: dict[str, Any] | None) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "method": method,
            "url": self._absolute_url(path),
            "headers": headers,
            "nota": "Request real del prototipo; no es simulacion.",
        }
        if payload is not None:
            snapshot["json"] = payload
        return snapshot

    def _absolute_url(self, path: str) -> str:
        return f"{self.state.base_url.rstrip('/')}{path}"

    def _http_json(self, method: str, path: str, headers: dict[str, str], payload: dict[str, Any] | None) -> HttpResult:
        url = self._absolute_url(path)
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
            try:
                data: Any = json.loads(raw)
            except json.JSONDecodeError:
                data = {"raw": raw}
            return HttpResult(exc.code, data, "El backend respondio error; se muestra JSON recibido.")
        except urllib_error.URLError as exc:
            return HttpResult(None, None, f"Excepcion de red: {exc.reason}")

    def _resolve_id_venta(self, data: Any) -> int | None:
        if not isinstance(data, dict):
            return None
        candidates = [
            data.get("id_venta"),
            data.get("venta", {}).get("id_venta") if isinstance(data.get("venta"), dict) else None,
            data.get("data", {}).get("venta", {}).get("id_venta") if isinstance(data.get("data"), dict) and isinstance(data.get("data", {}).get("venta"), dict) else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, int):
                return candidate
            if isinstance(candidate, str) and candidate.isdigit():
                return int(candidate)
        return None

    def _resolve_estado_venta(self, data: Any) -> str | None:
        if not isinstance(data, dict):
            return None
        candidates = [
            data.get("estado_venta"),
            data.get("venta", {}).get("estado_venta") if isinstance(data.get("venta"), dict) else None,
            data.get("data", {}).get("venta", {}).get("estado_venta") if isinstance(data.get("data"), dict) and isinstance(data.get("data", {}).get("venta"), dict) else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, str):
                return candidate
        return None

    def _extract_plan_data(self, data: Any) -> Any:
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data

    def _summarize_plan_response(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {"respuesta": "Sin resumen estructurado disponible"}
        plan = data.get("plan_pago_v2") if isinstance(data.get("plan_pago_v2"), dict) else data
        bloques = plan.get("bloques", []) if isinstance(plan, dict) else []
        obligaciones = plan.get("obligaciones", []) if isinstance(plan, dict) else []
        return {
            "id_plan_pago_venta": plan.get("id_plan_pago_venta") if isinstance(plan, dict) else None,
            "estado_plan_pago": plan.get("estado_plan_pago") if isinstance(plan, dict) else None,
            "cantidad_bloques": len(bloques) if isinstance(bloques, list) else None,
            "cantidad_obligaciones": len(obligaciones) if isinstance(obligaciones, list) else None,
            "incluye_obligados": self._contains_key(data, "obligados"),
            "incluye_indexacion": self._contains_key(data, "indexacion"),
            "incluye_cuotas_refuerzo": self._contains_key(data, "cuotas_refuerzo"),
        }

    def _contains_key(self, value: Any, expected_key: str) -> bool:
        if isinstance(value, dict):
            return expected_key in value or any(self._contains_key(item, expected_key) for item in value.values())
        if isinstance(value, list):
            return any(self._contains_key(item, expected_key) for item in value)
        return False


def main(page: ft.Page) -> None:
    page.title = "Wizard venta completa V2 — Prototipo"
    page.padding = 24
    page.scroll = ft.ScrollMode.AUTO
    app = VentaCompletaWizardV2Prototype(page)
    page.add(app.build())


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
