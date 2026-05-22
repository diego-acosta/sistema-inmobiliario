from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import flet as ft

from app.api_client import ApiClient


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
    if_match_version_reserva: str = ""
    reserva_search_codigo: str = ""
    reserva_search_results: list[dict[str, Any]] = field(default_factory=list)
    reserva_search_error: str = ""
    reserva_search_total: int = 0
    reserva_seleccionada: dict[str, Any] | None = None
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
    backend_resultado: dict[str, Any] | None = None
    backend_error: str = ""
    id_venta_generada: int | None = None
    confirmando_backend: bool = False


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
    def __init__(self, api: ApiClient, on_navigate: Callable[..., None]) -> None:
        self.api = api
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
        if field_name in {"id_reserva_venta", "if_match_version_reserva"}:
            self.state.reserva_seleccionada = None
        self._clear_backend_status()
        self._render()

    def _set_tipo_pago(self, value: str | None) -> None:
        self.state.tipo_pago = value or "FINANCIADO"
        self.state.preview_generado = False
        self._clear_backend_status()
        self._render()

    def _go(self, delta: int) -> None:
        self.state.current_step = max(0, min(len(STEPS) - 1, self.state.current_step + delta))
        self._render()

    def _add_objeto_demo(self, _: Any) -> None:
        next_id = len(self.state.objetos) + 1
        self.state.objetos.append(ObjetoVentaDraft(tipo_objeto="UNIDAD_FUNCIONAL" if next_id % 2 == 0 else "TERRENO", id_objeto=str(next_id), descripcion=f"Objeto demo {next_id}", precio_asignado="1000000.00"))
        self._clear_backend_status()
        self._render()

    def _remove_objeto(self, _: Any) -> None:
        if self.state.objetos:
            self.state.objetos.pop()
        self._clear_backend_status()
        self._render()

    def _add_objeto_manual_reserva(self, _: Any) -> None:
        self.state.objetos.append(
            ObjetoVentaDraft(
                tipo_objeto="TERRENO",
                id_objeto="",
                descripcion="Objeto manual desde reserva",
                precio_asignado=self.state.monto_total,
            )
        )
        self._clear_backend_status()
        self._render()

    def _set_objeto_draft(self, index: int, field_name: str, value: str) -> None:
        if index < 0 or index >= len(self.state.objetos):
            return
        setattr(self.state.objetos[index], field_name, value or "")
        self._clear_backend_status()
        self._render()

    def _add_comprador_demo(self, _: Any) -> None:
        next_id = len(self.state.compradores) + 1
        self.state.compradores.append(CompradorDraft(id_persona=str(next_id), nombre=f"Comprador demo {next_id}"))
        self._clear_backend_status()
        self._render()

    def _remove_comprador(self, _: Any) -> None:
        if self.state.compradores:
            self.state.compradores.pop()
        self._clear_backend_status()
        self._render()

    def _add_bloque(self, tipo: str) -> None:
        label = {"ANTICIPO": "Anticipo", "TRAMO_CUOTAS": "Tramo", "REFUERZO": "Refuerzo"}.get(tipo, tipo)
        self.state.bloques.append(BloquePlanDraft(tipo_bloque=tipo, etiqueta=label, importe="1000000.00", vencimiento=_format_ar_date(date.today()), cantidad_cuotas="6" if tipo == "TRAMO_CUOTAS" else "", primer_vencimiento=_format_ar_date(date.today()) if tipo == "TRAMO_CUOTAS" else ""))
        self.state.preview_generado = False
        self._clear_backend_status()
        self._render()

    def _remove_bloque(self, _: Any) -> None:
        if self.state.bloques:
            self.state.bloques.pop()
        self.state.preview_generado = False
        self._clear_backend_status()
        self._render()

    def _generate_preview(self, _: Any) -> None:
        self.state.preview_generado = True
        self._render()

    def _confirm_simulated(self, _: Any) -> None:
        self.state.confirmacion_simulada = True
        self._render()

    def _clear_backend_status(self) -> None:
        self.state.backend_resultado = None
        self.state.backend_error = ""
        self.state.id_venta_generada = None

    def _buscar_reservas(self, _: Any) -> None:
        self.state.reserva_search_error = ""
        self.state.reserva_search_results = []
        self.state.reserva_search_total = 0
        codigo = self.state.reserva_search_codigo.strip()
        result = self.api.get_reservas_venta(
            codigo_reserva=codigo or None,
            estado_reserva="confirmada",
            limit=20,
            offset=0,
        )
        if not result.success:
            self.state.reserva_search_error = (
                result.error_message or "No se pudieron buscar reservas."
            )
            self._render()
            return

        data = result.data if isinstance(result.data, dict) else {}
        self.state.reserva_search_results = data.get("items", []) or []
        self.state.reserva_search_total = int(data.get("total") or 0)
        if not self.state.reserva_search_results:
            self.state.reserva_search_error = "No se encontraron reservas confirmadas."
        self._render()

    def _seleccionar_reserva(self, reserva: dict[str, Any]) -> None:
        self.state.reserva_seleccionada = reserva
        self.state.id_reserva_venta = str(reserva.get("id_reserva_venta") or "")
        self.state.if_match_version_reserva = str(reserva.get("version_registro") or "")
        self._sync_objetos_desde_reserva(reserva)
        self._clear_backend_status()
        self._render()

    def _sync_objetos_desde_reserva(self, reserva: dict[str, Any]) -> None:
        objetos = reserva.get("objetos") or []
        if not objetos:
            self.state.objetos = []
            return

        precio_default = _money(_decimal_or_zero(self.state.monto_total))
        precio_por_objeto = precio_default if len(objetos) == 1 else ""
        self.state.objetos = [
            ObjetoVentaDraft(
                tipo_objeto=(
                    "UNIDAD_FUNCIONAL"
                    if objeto.get("id_unidad_funcional") is not None
                    else "TERRENO"
                ),
                id_objeto=str(
                    objeto.get("id_unidad_funcional")
                    or objeto.get("id_inmueble")
                    or ""
                ),
                descripcion=str(objeto.get("observaciones") or "Objeto de reserva"),
                precio_asignado=str(objeto.get("precio_asignado") or precio_por_objeto),
            )
            for objeto in objetos
        ]

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

    def _confirmar_desde_reserva_backend(self, _: Any) -> None:
        reserva_id = _int_or_zero(self.state.id_reserva_venta)
        if_match = _int_or_zero(self.state.if_match_version_reserva)
        if reserva_id <= 0 or if_match <= 0:
            self.state.backend_error = "Debe indicarse ID de reserva e If-Match-Version validos."
            self._render()
            return

        self.state.confirmando_backend = True
        self.state.backend_error = ""
        self.state.backend_resultado = None
        self.state.id_venta_generada = None
        self._render()

        result = self.api.confirmar_venta_completa_desde_reserva(
            reserva_id,
            if_match,
            self._build_confirmar_desde_reserva_payload(),
        )
        self.state.confirmando_backend = False
        if not result.success:
            self.state.backend_error = _api_error_text(result)
            self._render()
            return

        self.state.backend_resultado = result.data if isinstance(result.data, dict) else {}
        venta_data = self.state.backend_resultado.get("venta", {})
        self.state.id_venta_generada = venta_data.get("id_venta")
        self._render()

    def _build_confirmar_desde_reserva_payload(self) -> dict[str, Any]:
        anticipo = self._primer_bloque_importe("ANTICIPO")
        saldo = (_decimal_or_zero(self.state.monto_total) - anticipo).quantize(Decimal("0.01"))
        anticipo_fecha = self._primer_bloque_fecha("ANTICIPO")
        saldo_fecha = self._primer_fecha_saldo()
        objetos_payload = self._condiciones_objetos_payload()
        return {
            "generar_venta": {
                "codigo_venta": self.state.codigo_venta.strip(),
                "fecha_venta": _datetime_iso_or_raw(self.state.fecha_venta),
                "monto_total": _money(_decimal_or_zero(self.state.monto_total)),
                "observaciones": self.state.observaciones or None,
            },
            "condiciones_comerciales": {
                "monto_total": _money(_decimal_or_zero(self.state.monto_total)),
                "tipo_plan_financiero": "ANTICIPO_Y_SALDO" if anticipo > 0 and saldo > 0 else "CONTADO",
                "moneda": self.state.moneda.strip().upper() or "ARS",
                "importe_anticipo": _money(anticipo) if anticipo > 0 and saldo > 0 else None,
                "fecha_vencimiento_anticipo": anticipo_fecha if anticipo > 0 and saldo > 0 else None,
                "importe_saldo": _money(saldo) if anticipo > 0 and saldo > 0 else None,
                "fecha_vencimiento_saldo": saldo_fecha if anticipo > 0 and saldo > 0 else None,
                "cuotas": [],
                "objetos": objetos_payload,
            },
            "plan_pago_v2": {
                "tipo_pago": self.state.tipo_pago,
                "monto_total_plan": _money(_decimal_or_zero(self.state.monto_total)),
                "moneda": self.state.moneda.strip().upper() or "ARS",
                "bloques": [self._bloque_payload(bloque) for bloque in self.state.bloques],
                "observaciones": self.state.condiciones_generales or None,
            },
            "confirmacion": {
                "observaciones": self.state.observaciones or self.state.condiciones_generales or None,
            },
        }

    def _condiciones_objetos_payload(self) -> list[dict[str, Any]]:
        return [
            payload
            for payload in (self._objeto_payload(objeto) for objeto in self.state.objetos)
            if (
                (payload["id_inmueble"] is not None)
                != (payload["id_unidad_funcional"] is not None)
            )
            and _decimal_or_zero(payload["precio_asignado"]) > 0
        ]

    def _objeto_payload(self, objeto: ObjetoVentaDraft) -> dict[str, Any]:
        id_objeto = _int_or_zero(objeto.id_objeto)
        tipo = objeto.tipo_objeto.strip().upper()
        is_unidad = tipo in {"UNIDAD_FUNCIONAL", "UF"}
        return {
            "id_inmueble": None if is_unidad else id_objeto,
            "id_unidad_funcional": id_objeto if is_unidad else None,
            "precio_asignado": _money(_decimal_or_zero(objeto.precio_asignado)),
        }

    def _bloque_payload(self, bloque: BloquePlanDraft) -> dict[str, Any]:
        tipo = bloque.tipo_bloque.strip().upper()
        return {
            "tipo_bloque": tipo,
            "etiqueta_bloque": bloque.etiqueta or None,
            "importe_total_bloque": _money(_decimal_or_zero(bloque.importe)),
            "fecha_vencimiento": _date_iso_or_none(bloque.vencimiento),
            "cantidad_cuotas": _int_or_none(bloque.cantidad_cuotas),
            "importe_cuota": None,
            "fecha_primer_vencimiento": _date_iso_or_none(bloque.primer_vencimiento),
            "periodicidad": "MENSUAL" if tipo == "TRAMO_CUOTAS" else None,
            "regla_redondeo": "ULTIMA_CUOTA" if tipo == "TRAMO_CUOTAS" else None,
            "observaciones": None,
        }

    def _primer_bloque_importe(self, tipo_bloque: str) -> Decimal:
        for bloque in self.state.bloques:
            if bloque.tipo_bloque.strip().upper() == tipo_bloque:
                return _decimal_or_zero(bloque.importe)
        return Decimal("0.00")

    def _primer_bloque_fecha(self, tipo_bloque: str) -> str | None:
        for bloque in self.state.bloques:
            if bloque.tipo_bloque.strip().upper() == tipo_bloque:
                return _date_iso_or_none(bloque.vencimiento)
        return None

    def _primer_fecha_saldo(self) -> str | None:
        for bloque in self.state.bloques:
            if bloque.tipo_bloque.strip().upper() != "ANTICIPO":
                return _date_iso_or_none(bloque.primer_vencimiento) or _date_iso_or_none(bloque.vencimiento)
        return _date_iso_or_none(self.state.fecha_venta)

    def _set_origen(self, value: str | None) -> None:
        self.state.origen_venta = value if value in {ORIGEN_DIRECTA, ORIGEN_RESERVA} else ORIGEN_DIRECTA
        self.state.confirmacion_simulada = False
        self._clear_backend_status()
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
                    "Ingresa la reserva confirmada y su version actual para ejecutar la confirmacion completa.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                ft.Row(
                    controls=[
                        ft.TextField(
                            label="Buscar por codigo de reserva",
                            value=self.state.reserva_search_codigo,
                            width=280,
                            on_change=lambda e: self._set("reserva_search_codigo", e.control.value),
                        ),
                        ft.Button(
                            "Buscar reservas",
                            icon=ft.Icons.SEARCH,
                            on_click=self._buscar_reservas,
                        ),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                self._reservas_resultados(),
                self._reserva_seleccionada_box(),
                ft.Row(
                    controls=[
                        ft.TextField(
                            label="ID reserva de venta",
                            value=self.state.id_reserva_venta,
                            width=220,
                            on_change=lambda e: self._set("id_reserva_venta", e.control.value),
                        ),
                        ft.TextField(
                            label="If-Match-Version reserva",
                            value=self.state.if_match_version_reserva,
                            width=220,
                            on_change=lambda e: self._set("if_match_version_reserva", e.control.value),
                        ),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                ft.Row(
                    controls=[
                        ft.TextField(label="Codigo / referencia", value=self.state.codigo_venta, width=220, on_change=lambda e: self._set("codigo_venta", e.control.value)),
                        ft.TextField(label="Fecha venta", value=self.state.fecha_venta, width=160, on_change=lambda e: self._set("fecha_venta", e.control.value)),
                        ft.TextField(label="Moneda", value=self.state.moneda, width=110, on_change=lambda e: self._set("moneda", e.control.value.upper())),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                ft.Text("Los objetos cargados en el wizard se enviaran como condiciones comerciales de la venta generada."),
                self._validation_box(1),
            ],
        )

    def _reservas_resultados(self) -> ft.Control:
        if self.state.reserva_search_error:
            return ft.Text(self.state.reserva_search_error, color=ft.Colors.RED_700)
        if not self.state.reserva_search_results:
            return ft.Text("Busca por codigo o lista las reservas confirmadas disponibles.", color=ft.Colors.BLUE_GREY_700)

        rows: list[ft.DataRow] = []
        for reserva in self.state.reserva_search_results:
            objetos = reserva.get("objetos") or []
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(reserva.get("id_reserva_venta", "-")))),
                        ft.DataCell(ft.Text(str(reserva.get("codigo_reserva", "-")))),
                        ft.DataCell(ft.Text(str(reserva.get("estado_reserva", "-")))),
                        ft.DataCell(ft.Text(str(reserva.get("version_registro", "-")))),
                        ft.DataCell(ft.Text(_short_date(reserva.get("fecha_reserva")))),
                        ft.DataCell(ft.Text(str(len(objetos)))),
                        ft.DataCell(
                            ft.TextButton(
                                "Seleccionar",
                                on_click=lambda _, item=reserva: self._seleccionar_reserva(item),
                            )
                        ),
                    ]
                )
            )
        return ft.Column(
            controls=[
                ft.Text(f"Reservas encontradas: {len(rows)} de {self.state.reserva_search_total}"),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("ID")),
                        ft.DataColumn(ft.Text("Codigo")),
                        ft.DataColumn(ft.Text("Estado")),
                        ft.DataColumn(ft.Text("Version")),
                        ft.DataColumn(ft.Text("Fecha")),
                        ft.DataColumn(ft.Text("Objetos")),
                        ft.DataColumn(ft.Text("Accion")),
                    ],
                    rows=rows,
                ),
            ],
            spacing=8,
        )

    def _reserva_seleccionada_box(self) -> ft.Control:
        reserva = self.state.reserva_seleccionada
        if not reserva:
            return ft.Text("")

        objetos = reserva.get("objetos") or []
        return ft.Column(
            controls=[
                ft.Text("Reserva seleccionada", weight=ft.FontWeight.W_700),
                _kv_grid([
                    ("Codigo", str(reserva.get("codigo_reserva") or "-")),
                    ("Estado", str(reserva.get("estado_reserva") or "-")),
                    ("Fecha", _short_date(reserva.get("fecha_reserva"))),
                    ("Vencimiento", _short_date(reserva.get("fecha_vencimiento"))),
                    ("Version", str(reserva.get("version_registro") or "-")),
                    ("Objetos", str(len(objetos))),
                    ("Comprador", "No incluido en listado backend"),
                ]),
                _simple_table(
                    ["Inmueble", "Unidad funcional", "Observaciones"],
                    [
                        [
                            str(objeto.get("id_inmueble") or "-"),
                            str(objeto.get("id_unidad_funcional") or "-"),
                            str(objeto.get("observaciones") or "-"),
                        ]
                        for objeto in objetos
                    ],
                )
                if objetos
                else ft.Text("La reserva seleccionada no trajo objetos en el listado."),
            ],
            spacing=8,
        )

    def _step_objetos(self) -> ft.Control:
        desde_reserva = self.state.origen_venta == ORIGEN_RESERVA
        actions = (
            [self._objetos_reserva_editor()]
            if desde_reserva
            else [
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Agregar objeto demo", icon=ft.Icons.ADD, disabled=desde_reserva, on_click=self._add_objeto_demo),
                        ft.OutlinedButton("Quitar ultimo", icon=ft.Icons.DELETE_OUTLINE, disabled=desde_reserva, on_click=self._remove_objeto),
                    ],
                    spacing=10,
                )
            ]
        )
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
                *actions,
                self._validation_box(2),
            ],
        )

    def _objetos_reserva_editor(self) -> ft.Control:
        rows: list[ft.Control] = []
        for index, objeto in enumerate(self.state.objetos):
            rows.append(
                ft.Row(
                    controls=[
                        ft.TextField(
                            label="Tipo",
                            value=objeto.tipo_objeto,
                            width=170,
                            on_change=lambda e, i=index: self._set_objeto_draft(i, "tipo_objeto", e.control.value.upper()),
                        ),
                        ft.TextField(
                            label="ID inmueble/UF",
                            value=objeto.id_objeto,
                            width=140,
                            on_change=lambda e, i=index: self._set_objeto_draft(i, "id_objeto", e.control.value),
                        ),
                        ft.TextField(
                            label="Precio asignado",
                            value=objeto.precio_asignado,
                            width=180,
                            on_change=lambda e, i=index: self._set_objeto_draft(i, "precio_asignado", e.control.value),
                        ),
                    ],
                    wrap=True,
                    spacing=8,
                )
            )
        return ft.Column(
            controls=[
                ft.Text(
                    "Para TERRENO se envia id_inmueble. Para UNIDAD_FUNCIONAL se envia id_unidad_funcional.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                *rows,
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Agregar objeto manual", icon=ft.Icons.ADD, on_click=self._add_objeto_manual_reserva),
                        ft.OutlinedButton("Quitar ultimo", icon=ft.Icons.DELETE_OUTLINE, on_click=self._remove_objeto),
                    ],
                    spacing=10,
                ),
            ],
            spacing=8,
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
        actions: list[ft.Control]
        if self.state.origen_venta == ORIGEN_RESERVA:
            actions = [
                ft.Button(
                    "Confirmar venta completa desde reserva",
                    icon=ft.Icons.CHECK_CIRCLE,
                    disabled=bool(errors) or self.state.confirmando_backend,
                    on_click=self._confirmar_desde_reserva_backend,
                ),
                self._backend_result_box(),
            ]
        else:
            actions = [
                ft.Button("Confirmar venta completa (simulado)", icon=ft.Icons.CHECK_CIRCLE, disabled=bool(errors), on_click=self._confirm_simulated),
                ft.Text("Venta directa sin reserva todavia no tiene backend real. Confirmacion simulada." if self.state.confirmacion_simulada else ""),
            ]
        return self._card(
            "Paso 7 - Revision y confirmacion final",
            [
                ft.Text("Revisa toda la venta y el cronograma antes de confirmar."),
                _kv_grid([
                    ("Origen", self._origen_label()),
                    ("ID reserva", reserva_value),
                    ("If-Match reserva", self.state.if_match_version_reserva or "-" if self.state.origen_venta == ORIGEN_RESERVA else "-"),
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
                ft.Text("Objetos que se enviaran a condiciones_comerciales", weight=ft.FontWeight.W_700),
                _simple_table(
                    ["Inmueble", "Unidad funcional", "Precio asignado"],
                    [
                        [
                            str(objeto["id_inmueble"] or "-"),
                            str(objeto["id_unidad_funcional"] or "-"),
                            str(objeto["precio_asignado"]),
                        ]
                        for objeto in self._condiciones_objetos_payload()
                    ],
                ),
                ft.Text("Cronograma preview", weight=ft.FontWeight.W_700),
                _simple_table(["Bloque", "Etiqueta", "Vencimiento", "Importe"], preview),
                ft.Text("Alertas", weight=ft.FontWeight.W_700),
                ft.Column([ft.Text(error, color=ft.Colors.RED_700) for error in errors] or [ft.Text("Sin alertas bloqueantes.", color=ft.Colors.GREEN_700)]),
                *actions,
            ],
        )

    def _backend_result_box(self) -> ft.Control:
        if self.state.confirmando_backend:
            return ft.Row(
                controls=[
                    ft.ProgressRing(width=18, height=18),
                    ft.Text("Confirmando venta completa..."),
                ],
                spacing=10,
            )
        if self.state.backend_error:
            return ft.Text(self.state.backend_error, color=ft.Colors.RED_700)
        if not self.state.backend_resultado:
            return ft.Text("")

        reserva = self.state.backend_resultado.get("reserva_venta", {})
        venta = self.state.backend_resultado.get("venta", {})
        plan = self.state.backend_resultado.get("plan_pago_v2", {})
        obligaciones = self.state.backend_resultado.get("obligaciones", {})
        return ft.Column(
            controls=[
                ft.Text("Venta completa confirmada.", color=ft.Colors.GREEN_700, weight=ft.FontWeight.W_700),
                _kv_grid([
                    ("Venta", f"{venta.get('id_venta', '-')}, {venta.get('estado_venta', '-')}"),
                    ("Reserva", f"{reserva.get('id_reserva_venta', '-')}, {reserva.get('estado_reserva', '-')}"),
                    ("Plan", f"{plan.get('id_plan_pago_venta', '-')}, {plan.get('estado_plan_pago', '-')}"),
                    ("Obligaciones", str(obligaciones.get("cantidad", "-"))),
                ]),
                ft.Button(
                    "Abrir ficha de venta",
                    icon=ft.Icons.OPEN_IN_NEW,
                    disabled=self.state.id_venta_generada is None,
                    on_click=lambda _: self.on_navigate("venta_detail", id_venta=self.state.id_venta_generada),
                ),
            ],
            spacing=10,
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
                    ("If-Match reserva", self.state.if_match_version_reserva or "-" if self.state.origen_venta == ORIGEN_RESERVA else "-"),
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
                ft.Text("- venta directa sin reserva sigue sin backend real"),
                ft.Text("- objetos desde reserva se cargan manualmente como referencia"),
                ft.Text("- el preview local no es cronograma oficial"),
                ft.Text("- el backend genera el Plan Pago V2 definitivo"),
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
            if _int_or_zero(self.state.id_reserva_venta) <= 0:
                errors.append("El ID de reserva debe ser numerico y mayor a cero.")
            if _int_or_zero(self.state.if_match_version_reserva) <= 0:
                errors.append("Debe indicarse If-Match-Version numerico de la reserva.")
            if not self.state.codigo_venta.strip():
                errors.append("El codigo/referencia es requerido.")
            if _date_or_none(self.state.fecha_venta) is None:
                errors.append("La fecha debe tener formato dd/mm/aaaa o ISO.")
            if not self.state.moneda.strip():
                errors.append("La moneda es requerida.")
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
            if (
                self.state.origen_venta == ORIGEN_RESERVA
                and not self._condiciones_objetos_payload()
            ):
                errors.append("Debe existir al menos un objeto valido para condiciones_comerciales.objetos.")
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


def _int_or_none(value: object) -> int | None:
    parsed = _int_or_zero(value)
    return parsed if parsed > 0 else None


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


def _date_iso_or_none(value: object) -> str | None:
    parsed = _date_or_none(value)
    return parsed.isoformat() if parsed is not None else None


def _date_iso_or_raw(value: object) -> str:
    parsed = _date_or_none(value)
    return parsed.isoformat() if parsed is not None else str(value or "").strip()


def _datetime_iso_or_raw(value: object) -> str:
    parsed = _date_or_none(value)
    return f"{parsed.isoformat()}T00:00:00" if parsed is not None else str(value or "").strip()


def _short_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    return text[:10]


def _format_ar_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _api_error_text(result: Any) -> str:
    lines = ["No se pudo confirmar la venta completa desde la reserva."]
    if getattr(result, "status_code", None) is not None:
        lines.append(f"status_code: {result.status_code}")
    if getattr(result, "error_code", None):
        lines.append(f"error_code: {result.error_code}")
    if getattr(result, "error_message", None):
        lines.append(f"error_message: {result.error_message}")
    details = getattr(result, "error_details", None)
    if isinstance(details, dict):
        errors = details.get("errors")
        if errors:
            if isinstance(errors, list):
                lines.append("details.errors: " + ", ".join(str(error) for error in errors))
            else:
                lines.append(f"details.errors: {errors}")
        extra = {key: value for key, value in details.items() if key != "errors"}
        if extra:
            lines.append(f"details: {extra}")
    elif details is not None:
        lines.append(f"details: {details}")
    return "\n".join(lines)
