from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Literal

import flet as ft

from app.api_client import ApiClient, ApiResult
from app.components.detail_section import detail_section, key_value_grid
from app.components.entity_table import entity_table
from app.components.error_state import error_state
from app.components.loading_state import (
    DeferredControlLoader,
    DeferredLoadingContainer,
    loading_state,
    safe_update,
)
from app.components.status_badge import status_badge


class VentasPage:
    def __init__(
        self,
        api: ApiClient,
        on_navigate,
        detail_id: int | None = None,
    ) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.detail_id = detail_id

    def build(self) -> ft.Control:
        if self.detail_id is not None:
            return DeferredLoadingContainer(
                lambda: VentaDetailView(
                    self.api, self.on_navigate, self.detail_id
                ).build(),
                message="Cargando ficha de venta...",
                error_builder=lambda message: _detail_error(self.on_navigate, message),
            )
        return VentasListView(self.api, self.on_navigate).build()


class VentasListView:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.q = ft.TextField(label="Buscar", width=220)
        self.estado_venta = ft.TextField(label="Estado", width=130)
        self.id_persona = ft.TextField(label="ID parte", width=120)
        self.rol_codigo = ft.TextField(label="Rol", width=110)
        self.id_inmueble = ft.TextField(label="ID inmueble", width=120)
        self.id_unidad_funcional = ft.TextField(label="ID unidad", width=120)
        self.tipo_plan_financiero = ft.TextField(label="Plan financiero", width=150)
        self.con_saldo = ft.TextField(label="Con saldo", width=120)
        self.limit_field = ft.TextField(label="Limite", value="20", width=100)
        self.offset_field = ft.TextField(label="Offset", value="0", width=100)
        self.limit = 20
        self.offset = 0
        self.total = 0
        self.results = ft.Column(spacing=12, expand=True)

    def build(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Ventas", size=28, weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        ft.Button(
                            "Nueva venta",
                            icon=ft.Icons.ADD,
                            on_click=lambda _: self.on_navigate("venta_create_wizard"),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        self.q,
                        self.estado_venta,
                        self.id_persona,
                        self.rol_codigo,
                        self.id_inmueble,
                        self.id_unidad_funcional,
                        self.tipo_plan_financiero,
                        self.con_saldo,
                        self.limit_field,
                        self.offset_field,
                        ft.ElevatedButton("Buscar", on_click=self._on_search),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                DeferredControlLoader(
                    self.results, self._load, message="Cargando ventas..."
                ),
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _on_search(self, _) -> None:
        self.offset = _safe_int(self.offset_field.value)
        self.limit = _safe_limit_int(self.limit_field.value, default=20)
        self.results.controls = [loading_state("Cargando ventas...")]
        safe_update(self.results)
        self._load()
        safe_update(self.results)

    def _load(self) -> None:
        self.results.controls.clear()
        con_saldo, bool_error = _parse_bool_or_none(self.con_saldo.value)
        if bool_error is not None:
            self.results.controls.append(error_state(bool_error))
            return

        result = self.api.get_ventas(
            q=self.q.value,
            estado_venta=self.estado_venta.value,
            id_persona=_safe_int_or_none(self.id_persona.value),
            rol_codigo=self.rol_codigo.value,
            id_inmueble=_safe_int_or_none(self.id_inmueble.value),
            id_unidad_funcional=_safe_int_or_none(self.id_unidad_funcional.value),
            tipo_plan_financiero=self.tipo_plan_financiero.value,
            con_saldo=con_saldo,
            limit=self.limit,
            offset=self.offset,
        )
        if not result.success:
            self.results.controls.append(error_state(result.error_message or "Error"))
            return

        items, self.total = _list_payload(result.data)
        rows = [_venta_row(item) for item in items]
        if not rows:
            self.results.controls.append(_empty("No hay ventas para los filtros."))
        else:
            self.results.controls.append(
                entity_table(
                    columns=[
                        ("Codigo", "codigo_venta"),
                        ("Estado", "estado_venta"),
                        ("Fecha", "fecha_venta"),
                        ("Monto total", "monto_total"),
                        ("Moneda", "moneda"),
                        ("Plan", "tipo_plan_financiero"),
                        ("Comprador", "comprador_resumen"),
                        ("Objetos", "objetos_resumen"),
                        ("Saldo pendiente", "saldo_pendiente"),
                    ],
                    rows=rows,
                    actions=self._row_actions,
                )
            )
        self.results.controls.append(
            _pagination(self.total, self.limit, self.offset, self._previous, self._next)
        )

    def _row_actions(self, row: dict[str, Any]) -> list[ft.Control]:
        id_venta = row.get("id_venta")
        return [
            ft.TextButton(
                "Abrir ficha",
                disabled=id_venta is None,
                on_click=(
                    (
                        lambda _, id_venta=id_venta: self.on_navigate(
                            "venta_detail", id_venta=id_venta
                        )
                    )
                    if id_venta is not None
                    else None
                ),
            )
        ]

    def _previous(self, _) -> None:
        self.offset = max(0, self.offset - self.limit)
        self.offset_field.value = str(self.offset)
        self.results.controls = [loading_state("Cargando ventas...")]
        safe_update(self.results)
        self._load()
        safe_update(self.results)

    def _next(self, _) -> None:
        if self.limit <= 0:
            return
        self.offset += self.limit
        self.offset_field.value = str(self.offset)
        self.results.controls = [loading_state("Cargando ventas...")]
        safe_update(self.results)
        self._load()
        safe_update(self.results)


class VentaDetailView:
    def __init__(self, api: ApiClient, on_navigate, id_venta: int) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.id_venta = id_venta

    def build(self) -> ft.Control:
        result = self.api.get_venta_detalle_integral(self.id_venta)
        if not result.success:
            return _detail_error(self.on_navigate, result.error_message)

        data = result.data if isinstance(result.data, dict) else {}
        technical_detail = _technical_detail_collapsible(data)
        return ft.Column(
            controls=[
                _back_row(self.on_navigate),
                _venta_operativa_header(data),
                _summary_cards(data),
                detail_section(
                    "Plan Pago V2",
                    [
                        DeferredLoadingContainer(
                            lambda: _plan_pago_v2_integral_view(
                                self.api.get_plan_pago_venta_v2_integral(self.id_venta)
                            ),
                            message="Cargando Plan Pago V2...",
                        )
                    ],
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            col={"sm": 12, "md": 7, "lg": 7},
                            content=ft.Column(
                                controls=[
                                    detail_section(
                                        "Resumen de venta", [_base_venta(data)]
                                    ),
                                    detail_section(
                                        "Objeto vendido",
                                        [
                                            _objetos_operativos(
                                                data.get("objetos"), data.get("moneda")
                                            )
                                        ],
                                    ),
                                    detail_section(
                                        "Comprador / compradores",
                                        [_partes_operativas(data.get("partes"))],
                                    ),
                                ],
                                spacing=12,
                            ),
                        ),
                        ft.Container(
                            col={"sm": 12, "md": 5, "lg": 5},
                            content=ft.Column(
                                controls=[
                                    detail_section(
                                        "Plan de pago / obligaciones",
                                        [_plan_obligaciones_operativas(data)],
                                    ),
                                    detail_section(
                                        "Origen",
                                        [_origen_operativo(data.get("reserva_origen"))],
                                    ),
                                ],
                                spacing=12,
                            ),
                        ),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
                technical_detail,
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )


def _venta_row(item: dict[str, Any]) -> dict[str, Any]:
    relacion = item.get("relacion_financiera")
    if not isinstance(relacion, dict):
        relacion = {}
    return {
        "id_venta": item.get("id_venta"),
        "codigo_venta": item.get("codigo_venta"),
        "estado_venta": item.get("estado_venta"),
        "fecha_venta": item.get("fecha_venta"),
        "monto_total": item.get("monto_total"),
        "moneda": item.get("moneda"),
        "tipo_plan_financiero": item.get("tipo_plan_financiero"),
        "comprador_resumen": _partes_resumen(item.get("comprador_resumen")),
        "objetos_resumen": _objetos_resumen(item.get("objetos_resumen")),
        "saldo_pendiente": relacion.get("saldo_pendiente_total", "-"),
    }


def _venta_operativa_header(data: dict[str, Any]) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Text(_venta_title(data), size=30, weight=ft.FontWeight.W_700),
                    ft.Text(_venta_subtitle(data), color=ft.Colors.BLUE_GREY_600),
                ],
                spacing=2,
                expand=True,
            ),
            status_badge(_text_or_none(data.get("estado_venta"))),
        ],
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _venta_subtitle(data: dict[str, Any]) -> str:
    parts = [
        (
            "Desde reserva"
            if isinstance(data.get("reserva_origen"), dict)
            and data.get("reserva_origen")
            else "Venta directa"
        ),
        _format_date(data.get("fecha_venta")),
        _compact(data.get("moneda")),
    ]
    return " · ".join(part for part in parts if part and part != "-")


def _summary_cards(data: dict[str, Any]) -> ft.Control:
    resumen = data.get("resumen_financiero")
    resumen_data = resumen if isinstance(resumen, dict) else {}
    condiciones = data.get("condiciones_comerciales")
    condiciones_data = condiciones if isinstance(condiciones, dict) else {}
    moneda = condiciones_data.get("moneda") or data.get("moneda")
    saldo_pendiente = resumen_data.get("saldo_pendiente") or resumen_data.get(
        "saldo_pendiente_total"
    )
    cantidad_obligaciones = resumen_data.get("cantidad_obligaciones")
    if cantidad_obligaciones is None:
        cantidad_obligaciones = len(_safe_list(data.get("obligaciones_financieras")))
    return ft.Row(
        controls=[
            _metric_card(
                "Total venta",
                _format_money(
                    moneda,
                    condiciones_data.get("monto_total") or data.get("monto_total"),
                ),
            ),
            _metric_card("Saldo pendiente", _format_money(moneda, saldo_pendiente)),
            _metric_card(
                "Forma de pago",
                condiciones_data.get("tipo_plan_financiero")
                or data.get("tipo_plan_financiero"),
            ),
            _metric_card("Obligaciones", cantidad_obligaciones),
        ],
        spacing=12,
        run_spacing=12,
        wrap=True,
    )


def _metric_card(label: str, value: object) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(label, size=12, color=ft.Colors.BLUE_GREY_600),
                ft.Text(_compact(value), size=18, weight=ft.FontWeight.W_700),
            ],
            spacing=4,
        ),
        padding=14,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=8,
        width=190,
    )


def _base_venta(data: dict[str, Any]) -> ft.Control:
    return key_value_grid(
        [
            ("Codigo", data.get("codigo_venta")),
            ("Estado", data.get("estado_venta")),
            ("Fecha venta", _format_date(data.get("fecha_venta"))),
            ("Moneda", data.get("moneda")),
            ("Tipo plan financiero", data.get("tipo_plan_financiero")),
            ("Observaciones", data.get("observaciones")),
        ]
    )


def _objetos_table(value: object, moneda: object = None) -> ft.Control:
    rows = []
    for item in _safe_list(value):
        rows.append(
            {
                "tipo_objeto": item.get("tipo_objeto") or _tipo_objeto(item),
                "id_inmueble": item.get("id_inmueble"),
                "id_unidad_funcional": item.get("id_unidad_funcional"),
                "codigo_descripcion": _object_display(item),
                "precio_asignado": _format_money(
                    item.get("moneda") or moneda, item.get("precio_asignado")
                ),
            }
        )
    if not rows:
        return ft.Text("Sin objetos de venta registrados.")
    return entity_table(
        columns=[
            ("Tipo objeto", "tipo_objeto"),
            ("ID inmueble", "id_inmueble"),
            ("ID unidad", "id_unidad_funcional"),
            ("Codigo / descripcion", "codigo_descripcion"),
            ("Precio asignado", "precio_asignado"),
        ],
        rows=rows,
    )


def _objetos_operativos(value: object, moneda: object = None) -> ft.Control:
    rows = _safe_list(value)
    if not rows:
        return ft.Text("Sin objetos de venta registrados.")
    if len(rows) == 1:
        return _single_object_card(rows[0], moneda)
    return _objetos_table(rows, moneda)


def _single_object_card(item: dict[str, Any], moneda: object = None) -> ft.Control:
    return _compact_card(
        [
            ("Codigo / descripcion", _object_display(item)),
            ("Tipo objeto", item.get("tipo_objeto") or _tipo_objeto(item)),
            ("ID inmueble", item.get("id_inmueble")),
            ("ID unidad funcional", item.get("id_unidad_funcional")),
            (
                "Precio asignado",
                _format_money(
                    item.get("moneda") or moneda, item.get("precio_asignado")
                ),
            ),
        ]
    )


def _plan_obligaciones_operativas(data: dict[str, Any]) -> ft.Control:
    condiciones = data.get("condiciones_comerciales")
    condiciones_data = condiciones if isinstance(condiciones, dict) else {}
    resumen = data.get("resumen_financiero")
    resumen_data = resumen if isinstance(resumen, dict) else {}
    moneda = condiciones_data.get("moneda") or data.get("moneda")
    saldo_pendiente = resumen_data.get("saldo_pendiente") or resumen_data.get(
        "saldo_pendiente_total"
    )
    obligaciones = _safe_list(data.get("obligaciones_financieras"))
    cantidad_obligaciones = resumen_data.get("cantidad_obligaciones")
    if cantidad_obligaciones is None:
        cantidad_obligaciones = len(obligaciones)

    return ft.Column(
        controls=[
            key_value_grid(
                [
                    (
                        "Tipo de plan",
                        condiciones_data.get("tipo_plan_financiero")
                        or data.get("tipo_plan_financiero"),
                    ),
                    (
                        "Monto total",
                        _format_money(
                            moneda,
                            condiciones_data.get("monto_total")
                            or data.get("monto_total"),
                        ),
                    ),
                    ("Saldo pendiente", _format_money(moneda, saldo_pendiente)),
                    ("Cantidad obligaciones", cantidad_obligaciones),
                ]
            ),
            _obligaciones_operativas_table(obligaciones),
        ],
        spacing=10,
    )


def _obligaciones_operativas_table(rows: list[dict[str, Any]]) -> ft.Control:
    if not rows:
        return ft.Text("Sin obligaciones registradas.")
    if len(rows) == 1:
        return _single_obligation_card(rows[0])
    formatted_rows = [
        {
            **row,
            "fecha_vencimiento": _format_date(row.get("fecha_vencimiento")),
            "importe_total": _format_money(row.get("moneda"), row.get("importe_total")),
            "saldo_pendiente": _format_money(
                row.get("moneda"), row.get("saldo_pendiente")
            ),
        }
        for row in rows
    ]
    return entity_table(
        columns=[
            ("Vencimiento", "fecha_vencimiento"),
            ("Estado", "estado_obligacion"),
            ("Importe", "importe_total"),
            ("Saldo", "saldo_pendiente"),
            ("Moneda", "moneda"),
        ],
        rows=formatted_rows,
    )


def _single_obligation_card(item: dict[str, Any]) -> ft.Control:
    return _compact_card(
        [
            ("Vencimiento", _format_date(item.get("fecha_vencimiento"))),
            ("Estado", item.get("estado_obligacion")),
            ("Importe", _format_money(item.get("moneda"), item.get("importe_total"))),
            ("Saldo", _format_money(item.get("moneda"), item.get("saldo_pendiente"))),
            ("Moneda", item.get("moneda")),
        ]
    )


def _plan_pago_v2_readonly(value: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("La venta no tiene plan de pago V2 generado.")

    return ft.Column(
        controls=[
            key_value_grid(
                [
                    ("ID plan", value.get("id_plan_pago_venta")),
                    ("Metodo", value.get("metodo_plan_pago")),
                    ("Estado", value.get("estado_plan_pago")),
                    ("Tipo pago", value.get("tipo_pago")),
                    ("Monto total plan", value.get("monto_total_plan")),
                    ("Moneda", value.get("moneda")),
                ]
            ),
            _bloques_plan_table(_safe_list(value.get("bloques"))),
        ],
        spacing=10,
    )


def _bloques_plan_table(rows: list[dict[str, Any]]) -> ft.Control:
    if not rows:
        return ft.Text("Sin bloques de plan expuestos.")
    return entity_table(
        columns=[
            ("Numero", "numero_bloque"),
            ("Tipo", "tipo_bloque"),
            ("Etiqueta", "etiqueta_bloque"),
            ("Estado", "estado_bloque"),
            ("Importe total", "importe_total_bloque"),
            ("Cuotas", "cantidad_cuotas"),
            ("Importe cuota", "importe_cuota"),
            ("Vencimiento", "fecha_vencimiento"),
            ("Obligaciones", "obligaciones_resumen"),
        ],
        rows=[
            {
                **row,
                "obligaciones_resumen": _nested_count(row.get("obligaciones")),
            }
            for row in rows
        ],
    )


def _plan_pago_v2_integral_view(result: ApiResult) -> ft.Control:
    if not result.success:
        if result.status_code == 404 and result.error_code == "NOT_FOUND_PLAN_PAGO_V2":
            return ft.Text("La venta no tiene un Plan Pago V2 materializado.")
        return error_state(
            result.error_message or "No se pudo consultar el Plan Pago V2."
        )
    data = result.data if isinstance(result.data, dict) else {}
    if not data:
        return ft.Text("La venta no tiene un Plan Pago V2 materializado.")

    resumen = data.get("resumen") if isinstance(data.get("resumen"), dict) else {}
    plan = (
        data.get("plan_pago_venta")
        if isinstance(data.get("plan_pago_venta"), dict)
        else {}
    )
    corridas = _safe_list(data.get("corridas_indexacion"))
    bloques = _safe_list(data.get("bloques"))
    controls: list[ft.Control] = [
        ft.Text(
            "Consulta read-only QUERY_READLIKE: sin acciones de preparación, aplicación ni confirmación.",
            color=ft.Colors.BLUE_GREY_600,
        ),
        _plan_pago_v2_summary(plan, resumen),
        _plan_pago_v2_interface_states(resumen, corridas),
        ft.Text("Cuotas", size=16, weight=ft.FontWeight.W_700),
        _plan_pago_v2_blocks(bloques),
        ft.Text("Historial de corridas", size=16, weight=ft.FontWeight.W_700),
        _plan_pago_v2_corridas(corridas, plan.get("moneda")),
    ]
    return ft.Column(controls=controls, spacing=12)


def _plan_pago_v2_summary(plan: dict[str, Any], resumen: dict[str, Any]) -> ft.Control:
    """Presenta exclusivamente agregados entregados por el contrato read-only."""
    moneda = plan.get("moneda")
    items = [
        ("Importe vigente total", _format_money(moneda, resumen.get("total_obligaciones"))),
        ("Capital total", _format_money(moneda, resumen.get("total_capital"))),
        ("Ajuste total", _format_money(moneda, resumen.get("total_ajuste_indexacion"))),
        ("Bloques", _dash(resumen.get("cantidad_bloques"))),
        ("Obligaciones", _dash(resumen.get("cantidad_obligaciones"))),
        ("Indexadas", _dash(resumen.get("cantidad_obligaciones_con_indexacion"))),
        (
            "Proyectadas sin índice",
            _dash(resumen.get("cantidad_obligaciones_proyectadas_sin_indexacion")),
        ),
    ]
    # Una columna estática evita mediciones reactivas de ResponsiveRow durante scroll.
    return ft.Column(
        [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(label, color=ft.Colors.BLUE_GREY_700),
                        ft.Text(value, size=17, weight=ft.FontWeight.W_700),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=10,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=8,
            )
            for label, value in items
        ],
        spacing=6,
    )


def _plan_pago_v2_interface_states(resumen: dict[str, Any], corridas: list[dict[str, Any]]) -> ft.Control:
    counts = {"Pendientes": 0, "Aplicadas": 0, "Fallidas": 0}
    for corrida in corridas:
        estado = str(corrida.get("estado_corrida") or "").upper()
        if estado == "PENDIENTE_APLICACION": counts["Pendientes"] += 1
        elif estado == "APLICADA": counts["Aplicadas"] += 1
        elif estado == "FALLIDA": counts["Fallidas"] += 1
    return ft.Row([ft.Column([ft.Text(label, color=ft.Colors.BLUE_GREY_700), status_badge(str(value))], spacing=3) for label, value in counts.items()], wrap=True, spacing=20)


def _plan_pago_v2_blocks(bloques: list[dict[str, Any]]) -> ft.Control:
    """Aplana bloques para que las cuotas sean la estructura principal de lectura."""
    obligaciones: list[dict[str, Any]] = []
    for bloque in bloques:
        contexto = {
            "numero_bloque": bloque.get("numero_bloque"),
            "etiqueta_bloque": bloque.get("etiqueta_bloque"),
            "metodo_liquidacion": bloque.get("metodo_liquidacion"),
            "indexacion": bloque.get("indexacion"),
        }
        obligaciones.extend(
            {**obligacion, "_bloque": contexto}
            for obligacion in _safe_list(bloque.get("obligaciones"))
        )
    obligaciones.sort(
        key=lambda item: (
            item.get("fecha_vencimiento") or "",
            item.get("numero_cuota_asociada") or 0,
            item.get("numero_obligacion") or 0,
            item.get("id_obligacion_financiera") or 0,
        )
    )
    return _plan_pago_v2_obligaciones(obligaciones)

def _plan_pago_v2_obligaciones(obligaciones: list[dict[str, Any]]) -> ft.Control:
    if not obligaciones:
        return ft.Text("Sin obligaciones en el bloque.")
    rows: list[ft.Control] = [
        ft.Row(
            [
                ft.Text("", width=32), ft.Text("N°", width=55),
                ft.Text("Vencimiento", width=95), ft.Text("Total cuota", width=145),
                ft.Text("Estado obligación", width=130), ft.Text("Estado pago", width=110),
                ft.Text("Indexación"),
            ],
            spacing=6,
        )
    ]
    for visual_order, obligacion in enumerate(obligaciones, start=1):
        rows.append(_plan_pago_v2_cuota_row(obligacion, visual_order=visual_order))
    return ft.Column(rows, spacing=2)


def _plan_pago_v2_cuota_row(obligacion: dict[str, Any], *, visual_order: int) -> ft.Control:
    composiciones = _safe_list(obligacion.get("composiciones"))
    details = ft.Container(
        data=f"composicion-{obligacion.get('id_obligacion_financiera')}",
        content=_plan_pago_v2_composition_rows(obligacion, composiciones),
        visible=False,
        padding=8,
        bgcolor=ft.Colors.BLUE_GREY_50,
        border_radius=4,
    )
    button = ft.IconButton(data=f"toggle-composicion-{obligacion.get('id_obligacion_financiera')}", icon=ft.Icons.ADD, tooltip="Ver composición")

    def toggle(_: ft.ControlEvent) -> None:
        details.visible = not details.visible
        button.icon = ft.Icons.REMOVE if details.visible else ft.Icons.ADD
        button.tooltip = "Ocultar composición" if details.visible else "Ver composición"
        safe_update(button)
        safe_update(details)

    button.on_click = toggle
    numero = obligacion.get("numero_cuota_asociada") or obligacion.get("numero_obligacion")
    return ft.Column(
        [
            ft.Row(
                controls=[
                    button,
                    ft.Text(str(visual_order), width=55),
                    ft.Text(_format_date(obligacion.get("fecha_vencimiento")), width=95),
                    ft.Text(_format_money(obligacion.get("moneda"), obligacion.get("importe_vigente")), width=125),
                    status_badge(_estado_obligacion_label(obligacion.get("estado_obligacion"))),
                    status_badge(_estado_pago_label(obligacion)),
                    status_badge(_obligacion_indexacion_label(obligacion)),
                ],
                data=f"cuota-{obligacion.get('id_obligacion_financiera')}",
                spacing=6,
            ),
            details,
        ],
        spacing=2,
    )


def _plan_pago_v2_composition_rows(
    obligacion: dict[str, Any], composiciones: list[dict[str, Any]]
) -> ft.Control:
    if not composiciones:
        return ft.Text("Sin composición financiera expuesta.")
    rows: list[ft.Control] = [
        ft.Text("Composición de la cuota", weight=ft.FontWeight.W_600)
    ]
    for composicion in composiciones:
        codigo = str(composicion.get("codigo_concepto_financiero") or "")
        porcentaje = _porcentaje_ajuste_presentacion(obligacion, composicion)
        rows.append(
            ft.Row(
                [
                    ft.Text(_dash(codigo), width=180),
                    ft.Text(_format_money(composicion.get("moneda_componente"), composicion.get("importe_componente")), width=140),
                    ft.Text(porcentaje),
                ],
                spacing=8,
            )
        )
    bloque = obligacion.get("_bloque") if isinstance(obligacion.get("_bloque"), dict) else {}
    indice = bloque.get("indexacion") if isinstance(bloque.get("indexacion"), dict) else {}
    if bloque:
        rows.extend([ft.Text("Configuración del tramo", color=ft.Colors.BLUE_GREY_700), key_value_grid([("Método", _dash(bloque.get("metodo_liquidacion"))), ("Índice", _dash(indice.get("codigo_indice_financiero"))), ("Fecha base", _format_date(indice.get("fecha_base_indice"))), ("Valor base", _format_coefficient(indice.get("valor_base_indice")))])])
    rows.extend([ft.Text("Referencia original", color=ft.Colors.BLUE_GREY_700), key_value_grid([("Número dentro del tramo", _dash(obligacion.get("numero_cuota_asociada"))), ("Número de obligación", _dash(obligacion.get("numero_obligacion"))), ("ID obligación", _dash(obligacion.get("id_obligacion_financiera"))), ("Bloque", _dash(bloque.get("numero_bloque")))])])
    return ft.Column(rows, spacing=4)


def _porcentaje_ajuste_presentacion(
    obligacion: dict[str, Any], composicion: dict[str, Any]
) -> str:
    if composicion.get("codigo_concepto_financiero") != "AJUSTE_INDEXACION":
        return "—"
    try:
        capital = Decimal(str(obligacion.get("capital_original")))
        ajuste = Decimal(str(composicion.get("importe_componente")))
    except (InvalidOperation, TypeError, ValueError):
        return "—"
    if capital <= 0:
        return "—"
    return f"{_format_decimal((ajuste / capital) * Decimal('100'), decimal_places=2)}%"


def _estado_obligacion_label(value: object) -> str:
    labels = {
        "PROYECTADA": "Proyectada", "EMITIDA": "Emitida", "EXIGIBLE": "Exigible",
        "VENCIDA": "Vencida", "PARCIALMENTE_CANCELADA": "Parcialmente pagada",
        "CANCELADA": "Pagada", "ANULADA": "Anulada", "REEMPLAZADA": "Reemplazada",
    }
    raw = str(value or "").upper()
    return labels.get(raw, _dash(value))


def _estado_pago_label(obligacion: dict[str, Any]) -> str:
    estado = str(obligacion.get("estado_obligacion") or "").upper()
    if estado == "CANCELADA": return "Pagada"
    if estado == "PARCIALMENTE_CANCELADA": return "Parcial"
    if estado == "ANULADA": return "Anulada"
    if estado == "REEMPLAZADA": return "Reemplazada"
    try:
        total = Decimal(str(obligacion.get("importe_vigente")))
        saldo = Decimal(str(obligacion.get("saldo_pendiente")))
    except (InvalidOperation, TypeError, ValueError):
        return "—"
    if saldo == 0: return "Pagada"
    if total > 0 and 0 < saldo < total: return "Parcial"
    if saldo == total: return "Pendiente"
    return "—"

def _plan_pago_v2_corridas(
    corridas: list[dict[str, Any]], moneda: object
) -> ft.Control:
    if not corridas:
        return ft.Text("Sin corridas de indexación registradas.")

    controls: list[ft.Control] = []
    for corrida in corridas:
        details = [
            ("Cálculo", _format_timestamp(corrida.get("fecha_preparacion"))),
            ("Fecha de corte", _format_date(corrida.get("fecha_corte"))),
            ("Período", _format_date(corrida.get("periodo_aplicado"))),
            ("Índice", _dash(corrida.get("codigo_indice_financiero"))),
            (
                "Analizada / elegible / excluida / aplicada",
                " / ".join(
                    _dash(corrida.get(field))
                    for field in (
                        "cantidad_analizada",
                        "cantidad_elegible",
                        "cantidad_excluida",
                        "cantidad_aplicada",
                    )
                ),
            ),
            (
                "Capital / ajuste / importe",
                " / ".join(
                    _format_money(moneda, corrida.get(field))
                    for field in (
                        "capital_analizado_total",
                        "ajuste_total",
                        "importe_total",
                    )
                ),
            ),
        ]
        children: list[ft.Control] = [
            ft.Column(
                [
                    ft.Text("Corrida de indexación", size=16, weight=ft.FontWeight.W_700),
                    status_badge(_corrida_estado_label(corrida.get("estado_corrida"))),
                ],
                spacing=4,
            ),
            key_value_grid(details),
        ]
        if any(corrida.get(field) for field in ("codigo_error", "etapa_error", "diagnostico_tecnico")):
            children.append(
                ft.Container(
                    content=key_value_grid(
                        [
                            ("Error de corrida", _dash(corrida.get("codigo_error"))),
                            ("Etapa", _dash(corrida.get("etapa_error"))),
                            ("Diagnóstico", _dash(corrida.get("diagnostico_tecnico"))),
                        ]
                    ),
                    padding=10,
                    bgcolor=ft.Colors.RED_50,
                    border_radius=8,
                )
            )
        for title, field, kind in (
            ("Obligaciones afectadas", "obligaciones_afectadas", "affected"),
            ("Exclusiones", "exclusiones", "exclusion"),
            ("Errores por obligación", "errores", "error"),
        ):
            rows = _safe_list(corrida.get(field))
            if rows:
                children.append(_corrida_detalles(title, rows, kind=kind))
        children.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Datos técnicos", color=ft.Colors.BLUE_GREY_700),
                        key_value_grid(
                            [
                                ("ID corrida", corrida.get("id_corrida_indexacion_financiera")),
                                ("Origen técnico", _dash(corrida.get("origen_corrida"))),
                            ]
                        ),
                    ],
                    spacing=4,
                ),
                padding=8,
                bgcolor=ft.Colors.BLUE_GREY_50,
                border_radius=6,
            )
        )
        controls.append(
            ft.Container(
                content=ft.Column(children, spacing=9),
                padding=14,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
                border_radius=10,
            )
        )
    return ft.Column(controls, spacing=12)


def _corrida_detalles(
    title: str,
    rows: list[dict[str, Any]],
    *,
    kind: Literal["affected", "exclusion", "error"],
) -> ft.Control:
    """Renderiza cada colección del contrato sin mezclarlas entre sí."""
    colors = {
        "affected": ft.Colors.BLUE_GREY_50,
        "exclusion": ft.Colors.AMBER_50,
        "error": ft.Colors.RED_50,
    }
    detail_controls: list[ft.Control] = [ft.Text(title, weight=ft.FontWeight.W_600)]
    for row in rows:
        # El DTO read-only sólo expone estos campos; no se derivan importes ni versiones.
        detail_controls.append(
            ft.Container(
                content=key_value_grid(
                    [
                        ("Obligación", _dash(row.get("id_obligacion_financiera"))),
                        ("Elegibilidad", _dash(row.get("estado_elegibilidad"))),
                        ("Motivo", _dash(row.get("motivo_exclusion"))),
                        ("Código de error", _dash(row.get("codigo_error"))),
                        ("Detalle", _dash(row.get("detalle_controlado"))),
                    ]
                ),
                padding=8,
                bgcolor=colors[kind],
                border_radius=6,
            )
        )
    return ft.Column(detail_controls, spacing=5)

def _corrida_estado_label(value: object) -> str:
    return {"PENDIENTE_APLICACION":"Pendiente", "APLICADA":"Aplicada", "FALLIDA":"Fallida"}.get(str(value or "").upper(), _dash(value))

def _obligacion_indexacion_label(obligacion: dict[str, Any]) -> str:
    estado = str(obligacion.get("estado_indexacion_presentacion") or "").upper()
    if estado in {"CON_ERROR", "EXCLUIDA"}:
        return _estado_indexacion_label(estado)
    if obligacion.get("origen_indexacion") == "CORRIDA_POSTERIOR":
        return "Ajustada por corrida"
    return _estado_indexacion_label(estado)


def _estado_indexacion_label(value: object) -> str:
    labels = {
        "NO_REQUIERE_INDICE": "Sin indexación",
        "PROYECTADA_SIN_INDICE": "Proyectada sin índice",
        "CON_INDICE_APLICADO": "Indexada al nacimiento",
        "EXCLUIDA": "Excluida",
        "CON_ERROR": "Con error",
    }
    raw = str(value or "")
    return labels.get(raw, raw or "Sin estado")


def _origen_indexacion_label(value: object) -> str:
    labels = {
        "AL_NACIMIENTO": "Al nacimiento",
        "CORRIDA_POSTERIOR": "Corrida posterior",
    }
    raw = str(value or "")
    return labels.get(raw, _dash(raw))


def _corrida_ref(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "—"
    parts = [
        f"ID {value.get('id_corrida_indexacion_financiera')}",
        str(value.get("estado_corrida") or ""),
        str(value.get("origen_corrida") or ""),
        str(value.get("estado_elegibilidad") or ""),
    ]
    if value.get("codigo_error"):
        parts.append(str(value.get("codigo_error")))
    return " · ".join(p for p in parts if p and p != "None")


def _format_coefficient(value: object) -> str:
    return _format_decimal(value, decimal_places=None, max_decimal_places=8) or "—"


def _dash(value: object) -> str:
    return "—" if value in (None, "", "-") else str(value)


def _tecnica_minima(data: dict[str, Any]) -> ft.Control:
    return key_value_grid(
        [
            ("ID venta", data.get("id_venta")),
            ("UID global", data.get("uid_global")),
            ("Version registro", data.get("version_registro")),
            ("Created at", data.get("created_at")),
            ("Updated at", data.get("updated_at")),
            ("Deleted at", data.get("deleted_at")),
        ]
    )


def _partes_table(value: object) -> ft.Control:
    rows = []
    for item in _safe_list(value):
        rows.append(
            {
                "id_persona": item.get("id_persona"),
                "display_name": item.get("display_name") or _party_display(item),
                "rol": _join_values(item.get("codigo_rol"), item.get("nombre_rol")),
                "participacion": _party_participacion(item),
                "tipo_relacion": item.get("tipo_relacion") or "venta",
            }
        )
    if not rows:
        return ft.Text("Sin partes registradas.")
    return entity_table(
        columns=[
            ("ID persona", "id_persona"),
            ("Nombre / razon social", "display_name"),
            ("Rol", "rol"),
            ("Participacion", "participacion"),
            ("Tipo relacion", "tipo_relacion"),
        ],
        rows=rows,
    )


def _partes_operativas(value: object) -> ft.Control:
    rows = _safe_list(value)
    if not rows:
        return ft.Text("Sin partes registradas.")
    if len(rows) == 1:
        return _single_buyer_card(rows[0])
    return _partes_table(rows)


def _single_buyer_card(item: dict[str, Any]) -> ft.Control:
    return _compact_card(
        [
            ("Nombre / razon social", item.get("display_name") or _party_display(item)),
            ("Rol", _join_values(item.get("codigo_rol"), item.get("nombre_rol"))),
            ("Participacion", _party_participacion(item)),
            ("Tipo relacion", item.get("tipo_relacion") or "venta"),
        ]
    )


def _party_participacion(item: dict[str, Any]) -> object:
    return _format_percent(
        item.get("porcentaje_responsabilidad")
        or item.get("porcentaje_participacion")
        or item.get("porcentaje")
        or item.get("participacion"),
    )


def _origen_operativo(value: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return _compact_card(
            [
                ("Origen", "Venta directa"),
                ("Reserva", "Sin reserva origen registrada."),
            ]
        )

    rows = [
        ("ID reserva venta", value.get("id_reserva_venta")),
        (
            "Estado reserva",
            value.get("estado_reserva_venta") or value.get("estado_reserva"),
        ),
    ]
    if value.get("codigo_reserva") not in (None, ""):
        rows.append(("Codigo reserva", value.get("codigo_reserva")))
    return _compact_card(rows)


def _compact_card(rows: list[tuple[str, object]]) -> ft.Control:
    return ft.Container(
        content=key_value_grid(rows),
        padding=12,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=8,
    )


def _integration_view(value: object) -> ft.Control:
    if isinstance(value, dict):
        events = value.get("eventos")
        if isinstance(events, list) and events:
            return _table_any(events)
        return _dict_grid(value)
    return _table_any(value)


def _relacion_financiera(value: object, resumen: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("Sin relacion financiera registrada.")
    resumen_data = resumen if isinstance(resumen, dict) else {}
    return key_value_grid(
        [
            ("Tipo origen", value.get("tipo_origen")),
            ("Estado", value.get("estado_relacion_generadora") or value.get("estado")),
            ("Cantidad obligaciones", resumen_data.get("cantidad_obligaciones")),
            ("Saldo total", resumen_data.get("saldo_total")),
            ("Saldo pendiente", resumen_data.get("saldo_pendiente")),
        ]
    )


def _technical_detail_collapsible(data: dict[str, Any]) -> ft.Control:
    body = ft.Column(
        controls=_technical_detail_controls(data),
        spacing=10,
        visible=False,
    )
    toggle = ft.TextButton("Mostrar detalle", icon=ft.Icons.EXPAND_MORE)

    def _toggle_detail(_) -> None:
        body.visible = not body.visible
        toggle.text = "Ocultar detalle" if body.visible else "Mostrar detalle"
        toggle.icon = ft.Icons.EXPAND_LESS if body.visible else ft.Icons.EXPAND_MORE
        body.update()
        toggle.update()

    toggle.on_click = _toggle_detail
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Detalle tecnico",
                            weight=ft.FontWeight.W_700,
                            size=18,
                        ),
                        ft.Container(expand=True),
                        toggle,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                body,
            ],
            spacing=8,
        ),
        padding=12,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=8,
    )


def _technical_detail_controls(data: dict[str, Any]) -> list[ft.Control]:
    controls: list[ft.Control] = [
        detail_section("Informacion tecnica minima", [_tecnica_minima(data)])
    ]
    if isinstance(data.get("plan_pago_v2"), dict) and data.get("plan_pago_v2"):
        controls.append(
            detail_section(
                "Plan Pago V2 por bloques",
                [_plan_pago_v2_readonly(data.get("plan_pago_v2"))],
            )
        )
    if isinstance(data.get("relacion_financiera"), dict) and data.get(
        "relacion_financiera"
    ):
        controls.append(
            detail_section(
                "Relacion financiera",
                [
                    _relacion_financiera(
                        data.get("relacion_financiera"),
                        data.get("resumen_financiero"),
                    )
                ],
            )
        )
    for title, key in (
        ("Instrumentos", "instrumentos_compraventa"),
        ("Cesiones", "cesiones"),
        ("Escrituraciones", "escrituraciones"),
    ):
        if _safe_list(data.get(key)):
            controls.append(detail_section(title, [_table_any(data.get(key))]))
    integracion = data.get("integracion_inmobiliaria")
    if integracion:
        controls.append(
            detail_section("Integracion inmobiliaria", [_integration_view(integracion)])
        )
    return controls


def _table_any(value: object) -> ft.Control:
    rows = _safe_list(value)
    if not rows:
        return ft.Text("Sin registros.")
    keys = _first_visible_keys(rows, limit=8)
    if not keys:
        return ft.Text("Sin campos disponibles.")
    compact_rows = [{key: _compact(row.get(key)) for key in keys} for row in rows]
    return entity_table(columns=[(key, key) for key in keys], rows=compact_rows)


def _dict_grid(value: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("Sin datos.")
    return key_value_grid([(key, _compact(item)) for key, item in value.items()])


def _list_payload(data: object) -> tuple[list[dict[str, Any]], int]:
    if isinstance(data, dict):
        raw_items = data.get("items", data.get("data", []))
        total = _safe_int(
            data.get("total", len(raw_items) if isinstance(raw_items, list) else 0)
        )
    elif isinstance(data, list):
        raw_items = data
        total = len(data)
    else:
        raw_items = []
        total = 0
    items = (
        [item for item in raw_items if isinstance(item, dict)]
        if isinstance(raw_items, list)
        else []
    )
    return items, total


def _safe_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _first_keys(rows: list[dict[str, Any]], limit: int) -> list[str]:
    keys: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)
            if len(keys) >= limit:
                return keys
    return keys


def _first_visible_keys(rows: list[dict[str, Any]], limit: int) -> list[str]:
    keys = [
        key
        for key in _first_keys(rows, limit=limit + 8)
        if not key.startswith("id_") and key not in {"uid_global", "version_registro"}
    ]
    return keys[:limit]


def _partes_resumen(value: object) -> str:
    parts = []
    for item in _safe_list(value):
        name = item.get("display_name") or _party_display(item)
        role = item.get("codigo_rol") or item.get("nombre_rol")
        parts.append(_join_values(role, name))
    return "; ".join(part for part in parts if part) or "-"


def _objetos_resumen(value: object) -> str:
    objects = []
    for item in _safe_list(value):
        display = _object_display(item)
        if display and display != "-":
            objects.append(display)
    return "; ".join(objects) or "-"


def _party_display(item: dict[str, Any]) -> str:
    razon = item.get("razon_social")
    if razon:
        return str(razon)
    display = " ".join(
        str(part) for part in (item.get("nombre"), item.get("apellido")) if part
    )
    return display or str(item.get("codigo_persona") or item.get("id_persona") or "-")


def _object_display(item: dict[str, Any]) -> str:
    for key in (
        "codigo_inmueble",
        "nombre_inmueble",
        "codigo_unidad_funcional",
        "codigo_unidad",
        "nombre_unidad",
        "nombre",
    ):
        if item.get(key):
            return str(item[key])
    if item.get("id_unidad_funcional") is not None:
        return f"Unidad {item.get('id_unidad_funcional')}"
    if item.get("id_inmueble") is not None:
        return f"Inmueble {item.get('id_inmueble')}"
    return "-"


def _tipo_objeto(item: dict[str, Any]) -> str:
    if item.get("id_unidad_funcional") is not None:
        return "unidad_funcional"
    if item.get("id_inmueble") is not None:
        return "inmueble"
    return "-"


def _nested_summary(value: object, label_key: str, amount_key: str) -> str:
    parts = []
    for item in _safe_list(value):
        label = item.get(label_key)
        amount = item.get(amount_key)
        parts.append(_join_values(label, amount))
    return "; ".join(part for part in parts if part) or "-"


def _nested_count(value: object) -> str:
    if not isinstance(value, list):
        return "-"
    count = len(value)
    if count == 1:
        return "1 registro"
    return f"{count} registros"


def _join_values(*values: object) -> str:
    return " - ".join(str(value) for value in values if value not in (None, ""))


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _compact(value: object) -> str:
    if isinstance(value, dict):
        for key in (
            "codigo_venta",
            "codigo_inmueble",
            "codigo_unidad_funcional",
            "codigo_unidad",
            "display_name",
            "nombre",
            "estado",
        ):
            if value.get(key):
                return str(value[key])
        return f"{len(value)} campos"
    if isinstance(value, list):
        return f"{len(value)} registros"
    if value is None:
        return "-"
    return str(value)


def _format_money(moneda: object, amount: object) -> str:
    amount_text = _format_decimal(amount, decimal_places=2)
    if amount_text is None:
        return "-"
    moneda_text = _compact(moneda)
    if moneda_text == "-":
        return amount_text
    return f"{moneda_text} {amount_text}"


def _format_date(value: object) -> str:
    if value in (None, "", "-"):
        return "-"
    text = str(value).strip()
    date_part = text[:10]
    parts = date_part.split("-")
    if len(parts) != 3:
        return text
    year, month, day = parts
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return text
    if len(year) != 4 or len(month) != 2 or len(day) != 2:
        return text
    return f"{day}/{month}/{year}"


def _format_timestamp(value: object) -> str:
    if value in (None, "", "-"):
        return "-"
    text = str(value).strip().replace("T", " ")
    if len(text) >= 16 and text[4:5] == "-" and text[7:8] == "-":
        return f"{_format_date(text[:10])} {text[11:16]}"
    return _format_date(text)


def _format_number(value: object) -> str:
    if value in (None, "", "-"):
        return "-"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return _compact(value)
    decimals = max(0, -number.as_tuple().exponent)
    if number == number.to_integral():
        decimals = 0
    text = f"{number:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(value: object) -> str:
    formatted = _format_decimal(value, decimal_places=None, max_decimal_places=2)
    if formatted is None:
        return "-"
    return f"{formatted}%"


def _format_decimal(
    value: object,
    *,
    decimal_places: int | None,
    max_decimal_places: int | None = None,
) -> str | None:
    if value in (None, "", "-"):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if decimal_places is not None:
        quantizer = Decimal("1").scaleb(-decimal_places)
        number = number.quantize(quantizer)
        decimals = decimal_places
    else:
        number = number.normalize()
        decimals = max(0, -number.as_tuple().exponent)
        if max_decimal_places is not None:
            decimals = min(decimals, max_decimal_places)
            quantizer = Decimal("1").scaleb(-decimals)
            number = number.quantize(quantizer)
    text = f"{number:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_bool_or_none(value: object) -> tuple[bool | None, str | None]:
    text = str(value or "").strip().lower()
    if not text:
        return None, None
    if text in {"true", "si", "sí", "1"}:
        return True, None
    if text in {"false", "no", "0"}:
        return False, None
    return None, "Con saldo acepta: true/si/1 o false/no/0."


def _pagination(
    total: int,
    limit: int,
    offset: int,
    on_previous: Callable,
    on_next: Callable,
) -> ft.Control:
    start = offset + 1 if total and limit > 0 else 0
    end = min(offset + limit, total) if limit > 0 else 0
    return ft.Row(
        controls=[
            ft.OutlinedButton("Anterior", disabled=offset <= 0, on_click=on_previous),
            ft.Text(f"{start}-{end} de {total}"),
            ft.OutlinedButton(
                "Siguiente",
                disabled=limit <= 0 or offset + limit >= total,
                on_click=on_next,
            ),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _detail_error(on_navigate, message: str | None) -> ft.Control:
    return ft.Column(
        controls=[
            ft.TextButton("Volver a Ventas", on_click=lambda _: on_navigate("ventas")),
            error_state(message or "No se pudo cargar la ficha."),
        ],
        spacing=12,
    )


def _back_row(on_navigate) -> ft.Control:
    return ft.Row(
        controls=[
            ft.TextButton("Volver a Ventas", on_click=lambda _: on_navigate("ventas")),
        ]
    )


def _empty(message: str) -> ft.Control:
    return ft.Container(
        content=ft.Text(message),
        padding=16,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _venta_title(data: dict[str, Any]) -> str:
    codigo = data.get("codigo_venta") or data.get("id_venta")
    return f"Venta {codigo}" if codigo not in (None, "") else "Ficha de venta"


def _safe_int(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_limit_int(value: object, default: int) -> int:
    try:
        number = int(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        return default
    return min(100, max(0, number))


def _safe_int_or_none(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None
