from typing import Any, Callable

import flet as ft

from app.api_client import ApiClient
from app.components.detail_section import detail_section, key_value_grid
from app.components.entity_table import entity_table
from app.components.error_state import error_state
from app.components.status_badge import status_badge


class InmueblesPage:
    def __init__(
        self,
        api: ApiClient,
        on_navigate,
        detail_kind: str | None = None,
        detail_id: int | None = None,
    ) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.detail_kind = detail_kind
        self.detail_id = detail_id

    def build(self) -> ft.Control:
        if self.detail_kind == "inmueble" and self.detail_id is not None:
            return InmuebleDetailView(self.api, self.on_navigate, self.detail_id).build()
        if self.detail_kind == "unidad" and self.detail_id is not None:
            return UnidadDetailView(self.api, self.on_navigate, self.detail_id).build()
        return InmueblesHub(self.api, self.on_navigate).build()


class InmueblesHub:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate

    def build(self) -> ft.Control:
        return ft.Tabs(
            selected_index=0,
            expand=True,
            tabs=[
                ft.Tab(
                    text="Inmuebles",
                    content=InmueblesListView(self.api, self.on_navigate).build(),
                ),
                ft.Tab(
                    text="Unidades funcionales",
                    content=UnidadesListView(self.api, self.on_navigate).build(),
                ),
            ],
        )


class InmueblesListView:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.q = ft.TextField(label="Buscar", width=260)
        self.estado_administrativo = ft.TextField(label="Estado admin.", width=160)
        self.estado_juridico = ft.TextField(label="Estado juridico", width=160)
        self.disponibilidad_actual = ft.TextField(label="Disponibilidad", width=160)
        self.ocupacion_actual = ft.TextField(label="Ocupacion", width=160)
        self.limit = 20
        self.offset = 0
        self.total = 0
        self.results = ft.Column(spacing=12, expand=True)
        self.page_info = ft.Text("")

    def build(self) -> ft.Control:
        self._load()
        return ft.Column(
            controls=[
                ft.Text("Inmuebles", size=28, weight=ft.FontWeight.W_700),
                ft.Row(
                    controls=[
                        self.q,
                        self.estado_administrativo,
                        self.estado_juridico,
                        self.disponibilidad_actual,
                        self.ocupacion_actual,
                        ft.ElevatedButton("Buscar", on_click=self._on_search),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                self.results,
            ],
            spacing=16,
            expand=True,
        )

    def _on_search(self, _) -> None:
        self.offset = 0
        self._load()
        self.results.update()

    def _load(self) -> None:
        result = self.api.get_inmuebles(
            q=self.q.value,
            estado_administrativo=self.estado_administrativo.value,
            estado_juridico=self.estado_juridico.value,
            disponibilidad_actual=self.disponibilidad_actual.value,
            ocupacion_actual=self.ocupacion_actual.value,
            limit=self.limit,
            offset=self.offset,
        )
        self.results.controls.clear()
        if not result.success:
            self.results.controls.append(error_state(result.error_message or "Error"))
            return
        items, self.total = _list_payload(result.data)
        rows = [_inmueble_row(item) for item in items]
        if not rows:
            self.results.controls.append(_empty("No hay inmuebles para los filtros."))
        else:
            self.results.controls.append(
                entity_table(
                    columns=[
                        ("Codigo", "codigo"),
                        ("Nombre", "nombre"),
                        ("Estado admin.", "estado_administrativo"),
                        ("Estado juridico", "estado_juridico"),
                        ("Disponibilidad", "disponibilidad"),
                        ("Ocupacion", "ocupacion"),
                        ("Unidades", "cantidad_unidades"),
                    ],
                    rows=rows,
                    actions=self._row_actions,
                )
            )
        self.results.controls.append(
            _pagination(self.total, self.limit, self.offset, self._previous, self._next)
        )

    def _row_actions(self, row: dict[str, Any]) -> list[ft.Control]:
        id_inmueble = row.get("id_inmueble")
        return [
            ft.TextButton(
                "Abrir ficha",
                disabled=id_inmueble is None,
                on_click=(
                    lambda _, id_inmueble=id_inmueble: self.on_navigate(
                        "inmueble_detail", id_inmueble=id_inmueble
                    )
                )
                if id_inmueble is not None
                else None,
            )
        ]

    def _previous(self, _) -> None:
        self.offset = max(0, self.offset - self.limit)
        self._load()
        self.results.update()

    def _next(self, _) -> None:
        self.offset += self.limit
        self._load()
        self.results.update()


class UnidadesListView:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.q = ft.TextField(label="Buscar", width=240)
        self.id_inmueble = ft.TextField(label="ID inmueble", width=130)
        self.estado_administrativo = ft.TextField(label="Estado admin.", width=150)
        self.estado_operativo = ft.TextField(label="Estado operativo", width=160)
        self.disponibilidad_actual = ft.TextField(label="Disponibilidad", width=150)
        self.ocupacion_actual = ft.TextField(label="Ocupacion", width=150)
        self.limit = 20
        self.offset = 0
        self.total = 0
        self.results = ft.Column(spacing=12, expand=True)

    def build(self) -> ft.Control:
        self._load()
        return ft.Column(
            controls=[
                ft.Text("Unidades funcionales", size=28, weight=ft.FontWeight.W_700),
                ft.Row(
                    controls=[
                        self.q,
                        self.id_inmueble,
                        self.estado_administrativo,
                        self.estado_operativo,
                        self.disponibilidad_actual,
                        self.ocupacion_actual,
                        ft.ElevatedButton("Buscar", on_click=self._on_search),
                    ],
                    wrap=True,
                    spacing=10,
                ),
                self.results,
            ],
            spacing=16,
            expand=True,
        )

    def _on_search(self, _) -> None:
        self.offset = 0
        self._load()
        self.results.update()

    def _load(self) -> None:
        result = self.api.get_unidades_funcionales(
            q=self.q.value,
            id_inmueble=_safe_int_or_none(self.id_inmueble.value),
            estado_administrativo=self.estado_administrativo.value,
            estado_operativo=self.estado_operativo.value,
            disponibilidad_actual=self.disponibilidad_actual.value,
            ocupacion_actual=self.ocupacion_actual.value,
            limit=self.limit,
            offset=self.offset,
        )
        self.results.controls.clear()
        if not result.success:
            self.results.controls.append(error_state(result.error_message or "Error"))
            return
        items, self.total = _list_payload(result.data)
        rows = [_unidad_row(item) for item in items]
        if not rows:
            self.results.controls.append(
                _empty("No hay unidades funcionales para los filtros.")
            )
        else:
            self.results.controls.append(
                entity_table(
                    columns=[
                        ("Codigo", "codigo"),
                        ("Inmueble", "inmueble"),
                        ("Nombre", "nombre"),
                        ("Estado admin.", "estado_administrativo"),
                        ("Estado operativo", "estado_operativo"),
                        ("Disponibilidad", "disponibilidad"),
                        ("Ocupacion", "ocupacion"),
                    ],
                    rows=rows,
                    actions=self._row_actions,
                )
            )
        self.results.controls.append(
            _pagination(self.total, self.limit, self.offset, self._previous, self._next)
        )

    def _row_actions(self, row: dict[str, Any]) -> list[ft.Control]:
        id_unidad = row.get("id_unidad_funcional")
        return [
            ft.TextButton(
                "Abrir ficha",
                disabled=id_unidad is None,
                on_click=(
                    lambda _, id_unidad=id_unidad: self.on_navigate(
                        "unidad_detail", id_unidad_funcional=id_unidad
                    )
                )
                if id_unidad is not None
                else None,
            )
        ]

    def _previous(self, _) -> None:
        self.offset = max(0, self.offset - self.limit)
        self._load()
        self.results.update()

    def _next(self, _) -> None:
        self.offset += self.limit
        self._load()
        self.results.update()


class InmuebleDetailView:
    def __init__(self, api: ApiClient, on_navigate, id_inmueble: int) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.id_inmueble = id_inmueble

    def build(self) -> ft.Control:
        result = self.api.get_inmueble_detalle_integral(self.id_inmueble)
        if not result.success:
            return _detail_error(self.on_navigate, result.error_message)
        data = result.data if isinstance(result.data, dict) else {}
        return ft.Column(
            controls=[
                _back_row(self.on_navigate),
                ft.Row(
                    controls=[
                        ft.Text(_inmueble_title(data), size=30, weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        status_badge(_text_or_none(data.get("estado_administrativo"))),
                    ]
                ),
                detail_section("Datos base", [_base_inmueble(data)]),
                detail_section("Resumen operativo", [_dict_grid(data.get("resumen_operativo"))]),
                detail_section("Disponibilidad / ocupacion actual", [_current_states(data)]),
                detail_section("Unidades funcionales", [_table_any(data.get("unidades_funcionales"))]),
                detail_section("Servicios", [_table_any(data.get("servicios"))]),
                detail_section("Responsables de servicio", [_table_any(data.get("responsables_servicio"))]),
                detail_section("Reservas de venta", [_table_any(data.get("reservas_venta"))]),
                detail_section("Ventas", [_table_any(data.get("ventas"))]),
                detail_section("Reservas locativas", [_table_any(data.get("reservas_locativas"))]),
                detail_section("Contratos de alquiler", [_table_any(data.get("contratos_alquiler"))]),
                detail_section("Trazabilidad de integracion", [_traceability(data.get("trazabilidad_integracion"))]),
                detail_section("Historial de disponibilidad", [_table_any(data.get("disponibilidades"))]),
                detail_section("Historial de ocupacion", [_table_any(data.get("ocupaciones"))]),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )


class UnidadDetailView:
    def __init__(self, api: ApiClient, on_navigate, id_unidad: int) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.id_unidad = id_unidad

    def build(self) -> ft.Control:
        result = self.api.get_unidad_funcional_detalle_integral(self.id_unidad)
        if not result.success:
            return _detail_error(self.on_navigate, result.error_message)
        data = result.data if isinstance(result.data, dict) else {}
        return ft.Column(
            controls=[
                _back_row(self.on_navigate),
                ft.Row(
                    controls=[
                        ft.Text(_unidad_title(data), size=30, weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        status_badge(_text_or_none(data.get("estado_operativo"))),
                    ]
                ),
                detail_section("Datos base", [_base_unidad(data)]),
                detail_section("Inmueble padre", [_dict_grid(data.get("inmueble"))]),
                detail_section("Resumen operativo", [_dict_grid(data.get("resumen_operativo"))]),
                detail_section("Disponibilidad / ocupacion actual", [_current_states(data)]),
                detail_section("Servicios", [_table_any(data.get("servicios"))]),
                detail_section("Responsables de servicio", [_table_any(data.get("responsables_servicio"))]),
                detail_section("Reservas de venta", [_table_any(data.get("reservas_venta"))]),
                detail_section("Ventas", [_table_any(data.get("ventas"))]),
                detail_section("Reservas locativas", [_table_any(data.get("reservas_locativas"))]),
                detail_section("Contratos de alquiler", [_table_any(data.get("contratos_alquiler"))]),
                detail_section("Trazabilidad de integracion", [_traceability(data.get("trazabilidad_integracion"))]),
                detail_section("Historial de disponibilidad", [_table_any(data.get("disponibilidades"))]),
                detail_section("Historial de ocupacion", [_table_any(data.get("ocupaciones"))]),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )


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


def _inmueble_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id_inmueble": item.get("id_inmueble"),
        "codigo": item.get("codigo_inmueble"),
        "nombre": item.get("nombre_inmueble") or item.get("nombre"),
        "estado_administrativo": item.get("estado_administrativo"),
        "estado_juridico": item.get("estado_juridico"),
        "disponibilidad": _validity_label(
            item.get("disponibilidad_actual"), item.get("disponibilidad_ambigua")
        ),
        "ocupacion": _validity_label(
            item.get("ocupacion_actual"), item.get("ocupacion_ambigua")
        ),
        "cantidad_unidades": item.get("cantidad_unidades_funcionales"),
    }


def _unidad_row(item: dict[str, Any]) -> dict[str, Any]:
    inmueble = item.get("inmueble") if isinstance(item.get("inmueble"), dict) else {}
    return {
        "id_unidad_funcional": item.get("id_unidad_funcional"),
        "codigo": item.get("codigo_unidad_funcional") or item.get("codigo_unidad"),
        "inmueble": inmueble.get("codigo_inmueble") or item.get("id_inmueble"),
        "nombre": item.get("nombre_unidad") or item.get("nombre"),
        "estado_administrativo": item.get("estado_administrativo"),
        "estado_operativo": item.get("estado_operativo"),
        "disponibilidad": _validity_label(
            item.get("disponibilidad_actual"), item.get("disponibilidad_ambigua")
        ),
        "ocupacion": _validity_label(
            item.get("ocupacion_actual"), item.get("ocupacion_ambigua")
        ),
    }


def _validity_label(value: object, ambiguous: object) -> str:
    if bool(ambiguous):
        return "Ambigua"
    if not isinstance(value, dict) or not value:
        return "Sin vigente"
    return str(
        value.get("estado_disponibilidad")
        or value.get("tipo_ocupacion")
        or value.get("estado_ocupacion")
        or value.get("estado")
        or value.get("id_disponibilidad")
        or value.get("id_ocupacion")
        or "Vigente"
    )


def _current_states(data: dict[str, Any]) -> ft.Control:
    return key_value_grid(
        [
            (
                "Disponibilidad actual",
                _validity_label(
                    data.get("disponibilidad_actual"),
                    data.get("disponibilidad_ambigua"),
                ),
            ),
            (
                "Ocupacion actual",
                _validity_label(
                    data.get("ocupacion_actual"),
                    data.get("ocupacion_ambigua"),
                ),
            ),
        ]
    )


def _base_inmueble(data: dict[str, Any]) -> ft.Control:
    return key_value_grid(
        [
            ("ID", data.get("id_inmueble")),
            ("Codigo", data.get("codigo_inmueble")),
            ("Nombre", data.get("nombre_inmueble") or data.get("nombre")),
            ("Tipo", data.get("tipo_inmueble")),
            ("Direccion", data.get("direccion")),
            ("Ubicacion", data.get("ubicacion")),
            ("Superficie", data.get("superficie")),
            ("Estado administrativo", data.get("estado_administrativo")),
            ("Estado juridico", data.get("estado_juridico")),
            ("Observaciones", data.get("observaciones")),
        ]
    )


def _base_unidad(data: dict[str, Any]) -> ft.Control:
    return key_value_grid(
        [
            ("ID", data.get("id_unidad_funcional")),
            ("ID inmueble", data.get("id_inmueble")),
            ("Codigo", data.get("codigo_unidad_funcional") or data.get("codigo_unidad")),
            ("Nombre", data.get("nombre_unidad") or data.get("nombre")),
            ("Tipo", data.get("tipo_unidad")),
            ("Superficie", data.get("superficie")),
            ("Estado administrativo", data.get("estado_administrativo")),
            ("Estado operativo", data.get("estado_operativo")),
            ("Observaciones", data.get("observaciones")),
        ]
    )


def _dict_grid(value: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("Sin datos.")
    return key_value_grid([(key, _compact(item)) for key, item in value.items()])


def _table_any(value: object) -> ft.Control:
    rows = _safe_list(value)
    if not rows:
        return ft.Text("Sin registros.")
    keys = _first_keys(rows, limit=8)
    if not keys:
        return ft.Text("Sin campos disponibles.")
    return entity_table(columns=[(key, key) for key in keys], rows=rows)


def _traceability(value: object) -> ft.Control:
    if isinstance(value, dict):
        events = value.get("eventos")
        ventas = value.get("ventas")
        if isinstance(events, list) and events:
            return _table_any(events)
        if isinstance(ventas, list) and ventas:
            return _table_any(ventas)
        return _dict_grid(value)
    return _table_any(value)


def _first_keys(rows: list[dict[str, Any]], limit: int) -> list[str]:
    keys: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)
            if len(keys) >= limit:
                return keys
    return keys


def _safe_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _compact(value: object) -> str:
    if isinstance(value, dict):
        for key in (
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


def _pagination(
    total: int,
    limit: int,
    offset: int,
    on_previous: Callable,
    on_next: Callable,
) -> ft.Control:
    start = offset + 1 if total else 0
    end = min(offset + limit, total)
    return ft.Row(
        controls=[
            ft.OutlinedButton("Anterior", disabled=offset <= 0, on_click=on_previous),
            ft.Text(f"{start}-{end} de {total}"),
            ft.OutlinedButton(
                "Siguiente",
                disabled=offset + limit >= total,
                on_click=on_next,
            ),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _detail_error(on_navigate, message: str | None) -> ft.Control:
    return ft.Column(
        controls=[
            ft.TextButton("Volver a Inmuebles", on_click=lambda _: on_navigate("inmuebles")),
            error_state(message or "No se pudo cargar la ficha."),
        ],
        spacing=12,
    )


def _back_row(on_navigate) -> ft.Control:
    return ft.Row(
        controls=[
            ft.TextButton("Volver a Inmuebles", on_click=lambda _: on_navigate("inmuebles")),
        ]
    )


def _empty(message: str) -> ft.Control:
    return ft.Container(
        content=ft.Text(message),
        padding=16,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _inmueble_title(data: dict[str, Any]) -> str:
    return str(
        data.get("nombre_inmueble")
        or data.get("nombre")
        or data.get("codigo_inmueble")
        or "Ficha de inmueble"
    )


def _unidad_title(data: dict[str, Any]) -> str:
    return str(
        data.get("nombre_unidad")
        or data.get("nombre")
        or data.get("codigo_unidad_funcional")
        or data.get("codigo_unidad")
        or "Ficha de unidad funcional"
    )


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_int_or_none(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None
