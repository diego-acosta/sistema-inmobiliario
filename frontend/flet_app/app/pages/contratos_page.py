from typing import Any, Callable

import flet as ft

from app.api_client import ApiClient
from app.components.detail_section import detail_section, key_value_grid
from app.components.entity_table import entity_table
from app.components.error_state import error_state
from app.components.status_badge import status_badge


class ContratosPage:
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
            return ContratoDetailView(self.api, self.on_navigate, self.detail_id).build()
        return ContratosListView(self.api, self.on_navigate).build()


class ContratosListView:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.q = ft.TextField(label="Buscar", width=230)
        self.estado_contrato = ft.TextField(label="Estado", width=130)
        self.id_persona = ft.TextField(label="ID parte", width=120)
        self.rol_codigo = ft.TextField(label="Rol", width=120)
        self.id_inmueble = ft.TextField(label="ID inmueble", width=120)
        self.id_unidad_funcional = ft.TextField(label="ID unidad", width=120)
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
                ft.Text("Contratos de alquiler", size=28, weight=ft.FontWeight.W_700),
                ft.Row(
                    controls=[
                        self.q,
                        self.estado_contrato,
                        self.id_persona,
                        self.rol_codigo,
                        self.id_inmueble,
                        self.id_unidad_funcional,
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

        result = self.api.get_contratos_alquiler(
            q=self.q.value,
            estado_contrato=self.estado_contrato.value,
            id_persona=_safe_int_or_none(self.id_persona.value),
            rol_codigo=self.rol_codigo.value,
            id_inmueble=_safe_int_or_none(self.id_inmueble.value),
            id_unidad_funcional=_safe_int_or_none(self.id_unidad_funcional.value),
            con_saldo=con_saldo,
            limit=self.limit,
            offset=self.offset,
        )
        if not result.success:
            self.results.controls.append(error_state(result.error_message or "Error"))
            return

        items, self.total = _list_payload(result.data)
        rows = [_contrato_row(item) for item in items]
        if not rows:
            self.results.controls.append(_empty("No hay contratos para los filtros."))
        else:
            self.results.controls.append(
                entity_table(
                    columns=[
                        ("Codigo", "codigo_contrato"),
                        ("Estado", "estado_contrato"),
                        ("Inicio", "fecha_inicio"),
                        ("Fin", "fecha_fin"),
                        ("Partes", "partes_resumen"),
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
        id_contrato = row.get("id_contrato_alquiler")
        return [
            ft.TextButton(
                "Abrir ficha",
                disabled=id_contrato is None,
                on_click=(
                    lambda _, id_contrato=id_contrato: self.on_navigate(
                        "contrato_detail", id_contrato_alquiler=id_contrato
                    )
                )
                if id_contrato is not None
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


class ContratoDetailView:
    def __init__(
        self, api: ApiClient, on_navigate, id_contrato_alquiler: int
    ) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.id_contrato_alquiler = id_contrato_alquiler

    def build(self) -> ft.Control:
        result = self.api.get_contrato_alquiler_detalle_integral(
            self.id_contrato_alquiler
        )
        if not result.success:
            return _detail_error(self.on_navigate, result.error_message)

        data = result.data if isinstance(result.data, dict) else {}
        return ft.Column(
            controls=[
                _back_row(self.on_navigate),
                ft.Row(
                    controls=[
                        ft.Text(
                            _contrato_title(data),
                            size=30,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Container(expand=True),
                        status_badge(_text_or_none(data.get("estado_contrato"))),
                    ]
                ),
                detail_section("Datos base", [_base_contrato(data)]),
                detail_section("Objetos locativos", [_objetos_table(data.get("objetos"))]),
                detail_section("Partes", [_partes_table(data.get("partes"))]),
                detail_section(
                    "Condiciones economicas",
                    [_condiciones_table(data.get("condiciones_economicas_alquiler"))],
                ),
                detail_section("Entrega / restitucion", [_entrega_restitucion(data)]),
                detail_section(
                    "Relacion financiera",
                    [_relacion_financiera(data.get("relacion_financiera"), data.get("resumen_financiero"))],
                ),
                detail_section(
                    "Obligaciones",
                    [_obligaciones_table(data.get("obligaciones_financieras"))],
                ),
                detail_section(
                    "Resumen financiero",
                    [_resumen_financiero(data.get("resumen_financiero"))],
                ),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )


def _contrato_row(item: dict[str, Any]) -> dict[str, Any]:
    relacion = item.get("relacion_financiera")
    if not isinstance(relacion, dict):
        relacion = {}
    return {
        "id_contrato_alquiler": item.get("id_contrato_alquiler"),
        "codigo_contrato": item.get("codigo_contrato"),
        "estado_contrato": item.get("estado_contrato"),
        "fecha_inicio": item.get("fecha_inicio"),
        "fecha_fin": item.get("fecha_fin"),
        "partes_resumen": _partes_resumen(item.get("partes_resumen")),
        "objetos_resumen": _objetos_resumen(item.get("objetos_resumen")),
        "saldo_pendiente": relacion.get("saldo_pendiente_total", "-"),
    }


def _base_contrato(data: dict[str, Any]) -> ft.Control:
    return key_value_grid(
        [
            ("ID", data.get("id_contrato_alquiler")),
            ("Codigo", data.get("codigo_contrato")),
            ("Estado", data.get("estado_contrato")),
            ("Fecha inicio", data.get("fecha_inicio")),
            ("Fecha fin", data.get("fecha_fin")),
            ("Observaciones", data.get("observaciones")),
        ]
    )


def _objetos_table(value: object) -> ft.Control:
    rows = []
    for item in _safe_list(value):
        rows.append(
            {
                "id_inmueble": item.get("id_inmueble"),
                "id_unidad_funcional": item.get("id_unidad_funcional"),
                "codigo_nombre": _object_display(item),
                "tipo_objeto": item.get("tipo_objeto") or _object_type(item),
            }
        )
    if not rows:
        return ft.Text("Sin objetos locativos registrados.")
    return entity_table(
        columns=[
            ("ID inmueble", "id_inmueble"),
            ("ID unidad", "id_unidad_funcional"),
            ("Codigo / nombre", "codigo_nombre"),
            ("Tipo", "tipo_objeto"),
        ],
        rows=rows,
    )


def _partes_table(value: object) -> ft.Control:
    rows = []
    for item in _safe_list(value):
        rows.append(
            {
                "id_persona": item.get("id_persona"),
                "display_name": item.get("display_name") or _party_display(item),
                "rol": _join_values(item.get("codigo_rol"), item.get("nombre_rol")),
                "tipo_relacion": item.get("tipo_relacion") or "contrato_alquiler",
                "vigencia": _vigencia(item),
            }
        )
    if not rows:
        return ft.Text("Sin partes registradas.")
    return entity_table(
        columns=[
            ("ID parte", "id_persona"),
            ("Nombre", "display_name"),
            ("Rol", "rol"),
            ("Tipo relacion", "tipo_relacion"),
            ("Vigencia", "vigencia"),
        ],
        rows=rows,
    )


def _condiciones_table(value: object) -> ft.Control:
    rows = []
    for item in _safe_list(value):
        rows.append(
            {
                "canon_base": item.get("canon_base") or item.get("monto_base"),
                "moneda": item.get("moneda"),
                "periodicidad": item.get("periodicidad"),
                "fecha_desde": item.get("fecha_desde"),
                "fecha_hasta": item.get("fecha_hasta"),
                "otros": _extra_fields(
                    item,
                    {
                        "id_condicion_economica",
                        "uid_global",
                        "version_registro",
                        "id_contrato_alquiler",
                        "canon_base",
                        "monto_base",
                        "moneda",
                        "periodicidad",
                        "fecha_desde",
                        "fecha_hasta",
                        "created_at",
                        "updated_at",
                        "deleted_at",
                    },
                ),
            }
        )
    if not rows:
        return ft.Text("Sin condiciones economicas registradas.")
    return entity_table(
        columns=[
            ("Canon/base", "canon_base"),
            ("Moneda", "moneda"),
            ("Periodicidad", "periodicidad"),
            ("Desde", "fecha_desde"),
            ("Hasta", "fecha_hasta"),
            ("Otros", "otros"),
        ],
        rows=rows,
    )


def _entrega_restitucion(data: dict[str, Any]) -> ft.Control:
    entrega = data.get("entrega_locativa")
    restitucion = data.get("restitucion_locativa")
    if not isinstance(entrega, dict) and not isinstance(restitucion, dict):
        return ft.Text("Sin entrega/restitucion registrada.")
    rows: list[ft.Control] = []
    if isinstance(entrega, dict):
        rows.append(ft.Text("Entrega", weight=ft.FontWeight.W_600))
        rows.append(_dict_grid(entrega))
    if isinstance(restitucion, dict):
        rows.append(ft.Text("Restitucion", weight=ft.FontWeight.W_600))
        rows.append(_dict_grid(restitucion))
    return ft.Column(controls=rows, spacing=10)


def _relacion_financiera(value: object, resumen: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("Sin relacion financiera registrada.")
    resumen_data = resumen if isinstance(resumen, dict) else {}
    return key_value_grid(
        [
            ("ID relacion", value.get("id_relacion_generadora")),
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
                "id_obligacion_financiera": item.get("id_obligacion_financiera"),
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
            ("ID", "id_obligacion_financiera"),
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


def _object_type(item: dict[str, Any]) -> str:
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


def _extra_fields(item: dict[str, Any], excluded: set[str]) -> str:
    values = [
        f"{key}: {_compact(value)}"
        for key, value in item.items()
        if key not in excluded and value is not None
    ]
    return "; ".join(values) or "-"


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
            "codigo_contrato",
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
            ft.TextButton(
                "Volver a Contratos",
                on_click=lambda _: on_navigate("contratos"),
            ),
            error_state(message or "No se pudo cargar la ficha."),
        ],
        spacing=12,
    )


def _back_row(on_navigate) -> ft.Control:
    return ft.Row(
        controls=[
            ft.TextButton(
                "Volver a Contratos",
                on_click=lambda _: on_navigate("contratos"),
            ),
        ]
    )


def _empty(message: str) -> ft.Control:
    return ft.Container(
        content=ft.Text(message),
        padding=16,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _contrato_title(data: dict[str, Any]) -> str:
    return str(data.get("codigo_contrato") or "Ficha de contrato")


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
