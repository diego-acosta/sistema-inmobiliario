from typing import Any, Callable

import flet as ft

from app.api_client import ApiClient
from app.components.detail_section import detail_section, key_value_grid
from app.components.detail_tabs import detail_tabs
from app.components.entity_table import entity_table
from app.components.error_state import error_state
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
            return VentaDetailView(self.api, self.on_navigate, self.detail_id).build()
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
        self._load()
        return ft.Column(
            controls=[
                ft.Text("Ventas", size=28, weight=ft.FontWeight.W_700),
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
                self.results,
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _on_search(self, _) -> None:
        self.offset = _safe_int(self.offset_field.value)
        self.limit = _safe_limit_int(self.limit_field.value, default=20)
        self._load()
        self.results.update()

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
                    lambda _, id_venta=id_venta: self.on_navigate(
                        "venta_detail", id_venta=id_venta
                    )
                )
                if id_venta is not None
                else None,
            )
        ]

    def _previous(self, _) -> None:
        self.offset = max(0, self.offset - self.limit)
        self.offset_field.value = str(self.offset)
        self._load()
        self.results.update()

    def _next(self, _) -> None:
        if self.limit <= 0:
            return
        self.offset += self.limit
        self.offset_field.value = str(self.offset)
        self._load()
        self.results.update()


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
        return ft.Column(
            controls=[
                _back_row(self.on_navigate),
                ft.Row(
                    controls=[
                        ft.Text(
                            _venta_title(data),
                            size=30,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Container(expand=True),
                        status_badge(_text_or_none(data.get("estado_venta"))),
                    ]
                ),
                _venta_header(data),
                detail_tabs(
                    [
                        (
                            "Resumen",
                            [
                                detail_section("Datos base", [_base_venta(data)]),
                                detail_section(
                                    "Reserva origen",
                                    [_reserva_origen(data.get("reserva_origen"))],
                                ),
                            ],
                        ),
                        (
                            "Objetos",
                            [
                                detail_section(
                                    "Objetos de venta",
                                    [_objetos_table(data.get("objetos"))],
                                )
                            ],
                        ),
                        (
                            "Partes / compradores",
                            [
                                detail_section(
                                    "Partes / compradores",
                                    [_partes_table(data.get("partes"))],
                                )
                            ],
                        ),
                        (
                            "Condiciones comerciales",
                            [
                                detail_section(
                                    "Condiciones comerciales",
                                    [
                                        _condiciones_comerciales(
                                            data.get("condiciones_comerciales")
                                        )
                                    ],
                                )
                            ],
                        ),
                        (
                            "Financiero",
                            [
                                detail_section(
                                    "Relacion financiera",
                                    [
                                        _relacion_financiera(
                                            data.get("relacion_financiera"),
                                            data.get("resumen_financiero"),
                                        )
                                    ],
                                ),
                                detail_section(
                                    "Obligaciones",
                                    [
                                        _obligaciones_table(
                                            data.get("obligaciones_financieras")
                                        )
                                    ],
                                ),
                                detail_section(
                                    "Resumen financiero",
                                    [
                                        _resumen_financiero(
                                            data.get("resumen_financiero")
                                        )
                                    ],
                                ),
                            ],
                        ),
                        (
                            "Instrumentos y cierre",
                            [
                                detail_section(
                                    "Instrumentos",
                                    [_table_any(data.get("instrumentos_compraventa"))],
                                ),
                                detail_section(
                                    "Cesiones", [_table_any(data.get("cesiones"))]
                                ),
                                detail_section(
                                    "Escrituraciones",
                                    [_table_any(data.get("escrituraciones"))],
                                ),
                            ],
                        ),
                        (
                            "Integracion inmobiliaria",
                            [
                                detail_section(
                                    "Integracion inmobiliaria",
                                    [
                                        _integration_view(
                                            data.get("integracion_inmobiliaria")
                                        )
                                    ],
                                )
                            ],
                        ),
                    ]
                ),
            ],
            spacing=14,
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


def _base_venta(data: dict[str, Any]) -> ft.Control:
    return key_value_grid(
        [
            ("Codigo", data.get("codigo_venta")),
            ("Estado", data.get("estado_venta")),
            ("Fecha venta", data.get("fecha_venta")),
            ("Monto total", data.get("monto_total")),
            ("Moneda", data.get("moneda")),
            ("Tipo plan financiero", data.get("tipo_plan_financiero")),
            ("Observaciones", data.get("observaciones")),
        ]
    )


def _venta_header(data: dict[str, Any]) -> ft.Control:
    resumen = data.get("resumen_financiero")
    resumen_data = resumen if isinstance(resumen, dict) else {}
    return ft.Container(
        content=key_value_grid(
            [
                ("Venta", _venta_title(data)),
                ("Estado", data.get("estado_venta")),
                ("Fecha venta", data.get("fecha_venta")),
                ("Monto total", data.get("monto_total")),
                ("Moneda", data.get("moneda")),
                ("Tipo plan financiero", data.get("tipo_plan_financiero")),
                ("Comprador principal", _partes_resumen(data.get("partes"))),
                (
                    "Saldo pendiente",
                    resumen_data.get("saldo_pendiente")
                    or resumen_data.get("saldo_pendiente_total"),
                ),
            ]
        ),
        padding=16,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _reserva_origen(value: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("Sin reserva origen.")
    return _dict_grid(value)


def _objetos_table(value: object) -> ft.Control:
    rows = []
    for item in _safe_list(value):
        rows.append(
            {
                "codigo_nombre": _object_display(item),
                "precio_asignado": item.get("precio_asignado"),
                "observaciones": item.get("observaciones"),
            }
        )
    if not rows:
        return ft.Text("Sin objetos de venta registrados.")
    return entity_table(
        columns=[
            ("Codigo / nombre", "codigo_nombre"),
            ("Precio asignado", "precio_asignado"),
            ("Observaciones", "observaciones"),
        ],
        rows=rows,
    )


def _condiciones_comerciales(value: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("Sin condiciones comerciales registradas.")
    cuotas = _safe_list(value.get("cuotas"))
    controls: list[ft.Control] = [
        key_value_grid(
            [
                ("Monto total", value.get("monto_total")),
                ("Moneda", value.get("moneda")),
                ("Tipo plan financiero", value.get("tipo_plan_financiero")),
                ("Importe anticipo", value.get("importe_anticipo")),
                ("Vencimiento anticipo", value.get("fecha_vencimiento_anticipo")),
                ("Importe saldo", value.get("importe_saldo")),
                ("Vencimiento saldo", value.get("fecha_vencimiento_saldo")),
                ("Observaciones", value.get("observaciones")),
            ]
        ),
        ft.Text("Cuotas", weight=ft.FontWeight.W_600),
        _cuotas_table(cuotas),
    ]
    return ft.Column(controls=controls, spacing=10)


def _cuotas_table(rows: list[dict[str, Any]]) -> ft.Control:
    if not rows:
        return ft.Text("Sin cuotas.")
    return entity_table(
        columns=[
            ("Numero", "numero_cuota"),
            ("Importe", "importe_cuota"),
            ("Vencimiento", "fecha_vencimiento"),
            ("Moneda", "moneda"),
            ("Observaciones", "observaciones"),
        ],
        rows=rows,
    )


def _partes_table(value: object) -> ft.Control:
    rows = []
    for item in _safe_list(value):
        rows.append(
            {
                "display_name": item.get("display_name") or _party_display(item),
                "rol": _join_values(item.get("codigo_rol"), item.get("nombre_rol")),
                "tipo_relacion": item.get("tipo_relacion") or "venta",
                "vigencia": _vigencia(item),
            }
        )
    if not rows:
        return ft.Text("Sin partes registradas.")
    return entity_table(
        columns=[
            ("Nombre", "display_name"),
            ("Rol", "rol"),
            ("Tipo relacion", "tipo_relacion"),
            ("Vigencia", "vigencia"),
        ],
        rows=rows,
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


def _obligaciones_table(value: object) -> ft.Control:
    rows = []
    for item in _safe_list(value):
        rows.append(
            {
                "fecha_emision": item.get("fecha_emision"),
                "fecha_vencimiento": item.get("fecha_vencimiento"),
                "estado_obligacion": item.get("estado_obligacion"),
                "importe_total": item.get("importe_total"),
                "saldo_pendiente": item.get("saldo_pendiente"),
                "moneda": item.get("moneda"),
                "composiciones": _nested_summary(
                    item.get("composiciones"),
                    "nombre_concepto_financiero",
                    "importe_componente",
                ),
                "obligados": _nested_summary(
                    item.get("obligados"),
                    "rol_obligado",
                    "porcentaje_responsabilidad",
                ),
            }
        )
    if not rows:
        return ft.Text("Sin obligaciones registradas.")
    return entity_table(
        columns=[
            ("Emision", "fecha_emision"),
            ("Vencimiento", "fecha_vencimiento"),
            ("Estado", "estado_obligacion"),
            ("Importe total", "importe_total"),
            ("Saldo pendiente", "saldo_pendiente"),
            ("Moneda", "moneda"),
            ("Composiciones", "composiciones"),
            ("Obligados", "obligados"),
        ],
        rows=rows,
    )


def _resumen_financiero(value: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("Sin resumen financiero.")
    return key_value_grid(
        [
            ("Cantidad obligaciones", value.get("cantidad_obligaciones")),
            ("Saldo total", value.get("saldo_total")),
            ("Saldo pendiente", value.get("saldo_pendiente")),
            ("Cantidad vencidas", value.get("cantidad_vencidas")),
            ("Cantidad canceladas", value.get("cantidad_canceladas")),
            ("Cantidad anuladas", value.get("cantidad_anuladas")),
        ]
    )


def _table_any(value: object) -> ft.Control:
    rows = _safe_list(value)
    if not rows:
        return ft.Text("Sin registros.")
    keys = _first_visible_keys(rows, limit=8)
    if not keys:
        return ft.Text("Sin campos disponibles.")
    compact_rows = [
        {key: _compact(row.get(key)) for key in keys}
        for row in rows
    ]
    return entity_table(columns=[(key, key) for key in keys], rows=compact_rows)


def _dict_grid(value: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("Sin datos.")
    return key_value_grid([(key, _compact(item)) for key, item in value.items()])


def _list_payload(data: object) -> tuple[list[dict[str, Any]], int]:
    if isinstance(data, dict):
        raw_items = data.get("items", data.get("data", []))
        total = _safe_int(data.get("total", len(raw_items) if isinstance(raw_items, list) else 0))
    elif isinstance(data, list):
        raw_items = data
        total = len(data)
    else:
        raw_items = []
        total = 0
    items = [item for item in raw_items if isinstance(item, dict)] if isinstance(raw_items, list) else []
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
        str(part)
        for part in (item.get("nombre"), item.get("apellido"))
        if part
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


def _nested_summary(value: object, label_key: str, amount_key: str) -> str:
    parts = []
    for item in _safe_list(value):
        label = item.get(label_key)
        amount = item.get(amount_key)
        parts.append(_join_values(label, amount))
    return "; ".join(part for part in parts if part) or "-"


def _vigencia(item: dict[str, Any]) -> str:
    desde = item.get("fecha_desde") or "-"
    hasta = item.get("fecha_hasta") or "-"
    return f"{desde} / {hasta}"


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
    return str(data.get("codigo_venta") or "Ficha de venta")


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
