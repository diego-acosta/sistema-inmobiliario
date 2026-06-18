"""Buscador visual reutilizable para wizards Flet.

Alcance:
  - Componente/prototipo UI aislado; recibe registros ya normalizados por la
    pantalla que lo usa y no llama al backend por si mismo.
  - Sirve para validar UX de busqueda y seleccion con datos provistos por la UI.
  - No define ownership de dominios ni reemplaza contratos reales de API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

import flet as ft


SelectorKind = Literal["reserva", "objeto", "persona"]
SelectionCallback = Callable[[dict[str, Any] | None], None]
SELECTABLE_OBJECT_STATUS = "DISPONIBLE"


def object_availability_status(value: Any) -> str:
    """Normaliza el estado operativo usado solo por la UX preventiva."""

    return _clean(value).upper()


def is_object_selectable_status(value: Any) -> bool:
    """Solo DISPONIBLE bloquea/desbloquea seleccion; sin estado conserva seleccion."""

    status = object_availability_status(value)
    return not status or status == SELECTABLE_OBJECT_STATUS


def object_availability_warning(value: Any) -> str | None:
    status = object_availability_status(value)
    if not status:
        return "Disponibilidad no informada; el backend validará la operación."
    if status == SELECTABLE_OBJECT_STATUS:
        return None
    return "Objeto reservado/no disponible; no puede seleccionarse para una venta directa."


def object_occupancy_status(value: Any) -> str:
    """Normaliza la ocupación actual informada por backend para la UX preventiva."""

    return object_availability_status(value)


def has_current_object_occupancy(value: Any) -> bool:
    """Bloquea cualquier ocupación vigente; permite solo ausencia o sin ocupación explícita."""

    status = object_occupancy_status(value)
    return bool(status and status not in {"SIN_OCUPACION", "SIN OCUPACION", "SIN OCUPACIÓN"})


def is_object_selectable(disponibilidad: Any, ocupacion: Any = None) -> bool:
    return is_object_selectable_status(disponibilidad) and not has_current_object_occupancy(ocupacion)


def object_selection_warning(disponibilidad: Any, ocupacion: Any = None) -> str | None:
    if has_current_object_occupancy(ocupacion):
        return "Objeto con ocupación vigente; no puede seleccionarse para una venta directa."
    return object_availability_warning(disponibilidad)


@dataclass(frozen=True)
class SearchSelectorRecord:
    """Registro normalizado para pintar y devolver una seleccion."""

    data: dict[str, Any]
    primary_text: str
    secondary_text: str
    technical_secondary_text: str
    summary_text: str
    search_text: str
    selection_payload: dict[str, Any]


def _border_all(width: int | float, color: ft.ColorValue) -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _join_visible(parts: list[Any], separator: str = " — ") -> str:
    return separator.join(part for part in (_clean(value) for value in parts) if part)


def _search_blob(*values: Any) -> str:
    return " ".join(_clean(value).lower() for value in values if _clean(value))


def reserva_record(data: dict[str, Any]) -> SearchSelectorRecord:
    """Adapta una reserva de venta demo al contrato visual del buscador."""

    codigo = _clean(data.get("codigo_reserva"))
    comprador = _clean(data.get("comprador")) or _clean(data.get("reservante"))
    objeto = _clean(data.get("objeto"))
    estado = _clean(data.get("estado"))
    version = data.get("version_registro")
    primary = _join_visible([codigo, comprador, objeto])
    secondary = _join_visible(
        [f"Estado: {estado}" if estado else "", f"version_registro: {version}" if version is not None else ""]
    )
    summary = _clean(data.get("resumen")) or _join_visible([comprador, objeto, estado])
    return SearchSelectorRecord(
        data=data,
        primary_text=primary,
        secondary_text=secondary,
        technical_secondary_text=secondary,
        summary_text=summary,
        search_text=_search_blob(codigo, comprador, objeto, estado, summary, data.get("id_reserva_venta")),
        selection_payload={
            "tipo": "RESERVA",
            "id_reserva_venta": data.get("id_reserva_venta"),
            "version_registro": version,
            "texto_visual": primary,
            "source": data.get("source") or "demo",
            "persisted": bool(data.get("persisted", False)),
        },
    )


def objeto_record(data: dict[str, Any]) -> SearchSelectorRecord:
    """Adapta un inmueble o unidad funcional al contrato visual del buscador."""

    tipo_objeto = _clean(data.get("tipo_objeto"))
    codigo = _clean(data.get("codigo"))
    descripcion = _clean(data.get("descripcion"))
    disponibilidad = _clean(data.get("estado")) or _clean(data.get("disponibilidad"))
    ocupacion = data.get("ocupacion_actual")
    estado_administrativo = _clean(data.get("estado_administrativo"))
    inmueble_padre = _clean(data.get("inmueble_padre"))
    primary_parts = [codigo, descripcion]
    if tipo_objeto == "UNIDAD_FUNCIONAL" and inmueble_padre:
        primary_parts.append(inmueble_padre)
    primary = _join_visible(primary_parts)
    id_correspondiente = data.get("id_unidad_funcional") if tipo_objeto == "UNIDAD_FUNCIONAL" else data.get("id_inmueble")
    tipo_label = {"INMUEBLE": "Inmueble", "UNIDAD_FUNCIONAL": "Unidad funcional"}.get(tipo_objeto, tipo_objeto)
    secondary = _join_visible([f"Tipo: {tipo_label}" if tipo_label else ""])
    technical_secondary = _join_visible(
        [
            f"Tipo: {tipo_objeto}" if tipo_objeto else "",
            f"id_inmueble: {data.get('id_inmueble')}" if data.get("id_inmueble") is not None else "",
            f"id_unidad_funcional: {data.get('id_unidad_funcional')}" if data.get("id_unidad_funcional") is not None else "",
            f"estado_administrativo: {estado_administrativo}" if estado_administrativo else "",
            f"ocupacion_actual: {_clean(ocupacion)}" if _clean(ocupacion) else "",
        ]
    )
    summary = _clean(data.get("resumen")) or primary
    payload: dict[str, Any] = {
        "tipo": "OBJETO_INMOBILIARIO",
        "tipo_objeto": tipo_objeto,
        "texto_visual": primary,
        "source": data.get("source") or "backend",
        "persisted": bool(data.get("persisted", False)),
    }
    if tipo_objeto == "UNIDAD_FUNCIONAL":
        payload["id_unidad_funcional"] = id_correspondiente
    else:
        payload["id_inmueble"] = id_correspondiente
    payload["estado"] = disponibilidad
    payload["ocupacion_actual"] = ocupacion
    if estado_administrativo:
        payload["estado_administrativo"] = estado_administrativo
    return SearchSelectorRecord(
        data=data,
        primary_text=primary,
        secondary_text=secondary,
        technical_secondary_text=technical_secondary,
        summary_text=summary,
        search_text=_search_blob(
            codigo,
            descripcion,
            disponibilidad,
            inmueble_padre,
            tipo_objeto,
            data.get("id_inmueble"),
            data.get("id_unidad_funcional"),
        ),
        selection_payload=payload,
    )


def persona_record(data: dict[str, Any]) -> SearchSelectorRecord:
    """Adapta una persona/comprador al contrato visual del buscador."""

    nombre = _join_visible([data.get("nombre"), data.get("apellido")], " ") or _clean(data.get("razon_social"))
    documento = _clean(data.get("documento"))
    codigo = _clean(data.get("codigo_persona"))
    primary = _join_visible([nombre, documento]) or codigo
    estado = _clean(data.get("estado")) or "activa"
    secondary = f"Persona {estado.lower()}"
    technical_secondary = _join_visible(
        [
            f"Codigo: {codigo}" if codigo else "",
            f"id_persona: {data.get('id_persona')}" if data.get("id_persona") is not None else "",
        ]
    )
    summary = _clean(data.get("resumen")) or codigo or primary
    return SearchSelectorRecord(
        data=data,
        primary_text=primary,
        secondary_text=secondary,
        technical_secondary_text=technical_secondary,
        summary_text=summary,
        search_text=_search_blob(codigo, nombre, documento, summary, data.get("id_persona")),
        selection_payload={
            "tipo": "PERSONA",
            "id_persona": data.get("id_persona"),
            "texto_visual": primary,
            "source": data.get("source") or "backend",
            "persisted": bool(data.get("persisted", False)),
        },
    )


_RECORD_FACTORY: dict[SelectorKind, Callable[[dict[str, Any]], SearchSelectorRecord]] = {
    "reserva": reserva_record,
    "objeto": objeto_record,
    "persona": persona_record,
}


class SearchSelectorDemo:
    """Buscador configurable para seleccion de reservas, objetos y personas.

    El callback ``on_selection_change`` recibe el payload simple del registro seleccionado
    o ``None`` al limpiar la seleccion. El componente conserva los registros recibidos en
    memoria y no consulta endpoints por si mismo.
    """

    def __init__(
        self,
        *,
        title: str,
        placeholder: str,
        records: list[dict[str, Any]],
        selector_kind: SelectorKind,
        on_selection_change: SelectionCallback | None = None,
        show_technical_details: bool = True,
    ) -> None:
        self.title = title
        self.placeholder = placeholder
        self.selector_kind = selector_kind
        self.on_selection_change = on_selection_change
        self.show_technical_details = show_technical_details
        self._records = [_RECORD_FACTORY[selector_kind](record) for record in records]
        self._selected: SearchSelectorRecord | None = None

        self.search_field = ft.TextField(
            label=placeholder,
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search_change,
        )
        self.results_column = ft.Column(spacing=8)
        self.selected_panel = ft.Container(visible=False)
        self.clear_button = ft.OutlinedButton(
            "Limpiar seleccion",
            icon=ft.Icons.CLOSE,
            on_click=self._clear_selection,
            disabled=True,
        )
        self.root = ft.Container(
            padding=16,
            border=_border_all(1, ft.Colors.BLUE_GREY_100),
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(title, size=20, weight=ft.FontWeight.W_700, expand=True),
                            self.clear_button,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(
                        "Busca por codigo, nombre, descripcion o documento visible.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_600,
                    ),
                    self.search_field,
                    self.selected_panel,
                    self.results_column,
                ],
                spacing=10,
            ),
        )
        self._refresh_results()

    @property
    def selected_payload(self) -> dict[str, Any] | None:
        if self._selected is None:
            return None
        return dict(self._selected.selection_payload)

    def view(self) -> ft.Control:
        return self.root

    def set_show_technical_details(self, show: bool) -> None:
        self.show_technical_details = show
        self._refresh_selection_panel()
        self._refresh_results()

    def _on_search_change(self, _: ft.ControlEvent) -> None:
        self._refresh_results()
        self.root.update()

    def _select_record(self, record: SearchSelectorRecord) -> None:
        if self.selector_kind == "objeto" and not is_object_selectable(record.selection_payload.get("estado"), record.selection_payload.get("ocupacion_actual")):
            return
        self._selected = record
        self._refresh_selection_panel()
        self._refresh_results()
        if self.on_selection_change is not None:
            self.on_selection_change(self.selected_payload)
        self.root.update()

    def _clear_selection(self, _: ft.ControlEvent | None = None) -> None:
        self._selected = None
        self._refresh_selection_panel()
        self._refresh_results()
        if self.on_selection_change is not None:
            self.on_selection_change(None)
        self.root.update()

    def _matching_records(self) -> list[SearchSelectorRecord]:
        query = _clean(self.search_field.value).lower()
        if not query:
            return list(self._records)
        terms = [term for term in query.split() if term]
        return [record for record in self._records if all(term in record.search_text for term in terms)]

    def _refresh_results(self) -> None:
        records = self._matching_records()
        if not records:
            self.results_column.controls = [
                ft.Container(
                    padding=12,
                    bgcolor=ft.Colors.BLUE_GREY_50,
                    border_radius=8,
                    content=ft.Text("No se encontraron registros disponibles.", color=ft.Colors.BLUE_GREY_700),
                )
            ]
            return
        self.results_column.controls = [self._build_result_row(record) for record in records]

    def _refresh_selection_panel(self) -> None:
        self.clear_button.disabled = self._selected is None
        if self._selected is None:
            self.selected_panel.visible = False
            self.selected_panel.content = None
            return
        self.selected_panel.visible = True
        self.selected_panel.padding = 12
        self.selected_panel.border_radius = 8
        self.selected_panel.bgcolor = ft.Colors.GREEN_50
        self.selected_panel.border = _border_all(1, ft.Colors.GREEN_200)
        self.selected_panel.content = ft.Column(
            controls=[
                ft.Text("Seleccionado", weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_800),
                ft.Text(self._selected.primary_text, weight=ft.FontWeight.W_600),
                ft.Text(
                    self._selected.technical_secondary_text if self.show_technical_details else self._selected.secondary_text,
                    size=12,
                    color=ft.Colors.BLUE_GREY_700,
                ),
            ],
            spacing=3,
        )

    def _build_result_row(self, record: SearchSelectorRecord) -> ft.Control:
        is_selected = self._selected == record
        if self.selector_kind == "objeto":
            return self._build_object_result_row(record, is_selected)
        if self.selector_kind == "persona":
            return self._build_person_result_row(record, is_selected)
        return ft.Container(
            padding=12,
            border_radius=10,
            border=_border_all(1, ft.Colors.GREEN_300 if is_selected else ft.Colors.BLUE_GREY_100),
            bgcolor=ft.Colors.GREEN_50 if is_selected else ft.Colors.WHITE,
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(record.primary_text, weight=ft.FontWeight.W_700),
                            *(
                                [ft.Text(record.summary_text, size=12, color=ft.Colors.BLUE_GREY_700)]
                                if record.summary_text and record.summary_text != record.primary_text
                                else []
                            ),
                            ft.Text(
                                record.technical_secondary_text if self.show_technical_details else record.secondary_text,
                                size=11,
                                color=ft.Colors.BLUE_GREY_500,
                            ),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.Button(
                        "Seleccionar" if not is_selected else "Seleccionado",
                        icon=ft.Icons.CHECK if is_selected else ft.Icons.CHECK_CIRCLE_OUTLINE,
                        disabled=is_selected,
                        on_click=lambda _, selected_record=record: self._select_record(selected_record),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _build_object_result_row(self, record: SearchSelectorRecord, is_selected: bool) -> ft.Control:
        estado = _clean(record.data.get("estado")) or _clean(record.data.get("disponibilidad"))
        ocupacion = record.data.get("ocupacion_actual")
        estado_upper = object_availability_status(estado)
        is_selectable = is_object_selectable(estado, ocupacion)
        warning_text = object_selection_warning(estado, ocupacion)
        is_warning = warning_text is not None
        return ft.Container(
            padding=12,
            border_radius=10,
            border=_border_all(1, ft.Colors.GREEN_300 if is_selected else ft.Colors.AMBER_200 if is_warning else ft.Colors.BLUE_GREY_100),
            bgcolor=ft.Colors.GREEN_50 if is_selected else ft.Colors.AMBER_50 if is_warning else ft.Colors.WHITE,
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(record.primary_text, weight=ft.FontWeight.W_700),
                            *(
                                [ft.Text(record.summary_text, size=12, color=ft.Colors.BLUE_GREY_700)]
                                if record.summary_text and record.summary_text != record.primary_text
                                else []
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        record.technical_secondary_text if self.show_technical_details else record.secondary_text,
                                        size=11,
                                        color=ft.Colors.BLUE_GREY_500,
                                    ),
                                    *(
                                        [
                                            ft.Container(
                                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                                border_radius=999,
                                                bgcolor=ft.Colors.AMBER_100 if is_warning else ft.Colors.GREEN_100,
                                                border=_border_all(1, ft.Colors.AMBER_300 if is_warning else ft.Colors.GREEN_300),
                                                content=ft.Text(estado_upper, size=10, weight=ft.FontWeight.W_700),
                                            )
                                        ]
                                        if estado_upper
                                        else []
                                    ),
                                ],
                                spacing=8,
                                wrap=True,
                            ),
                            *(
                                [
                                    ft.Text(
                                        warning_text or "",
                                        size=11,
                                        color=ft.Colors.AMBER_900,
                                    )
                                ]
                                if is_warning
                                else []
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Button(
                        "Seleccionar" if (is_selectable and not is_selected) else "Seleccionado" if is_selected else "No disponible",
                        icon=ft.Icons.CHECK if is_selected else ft.Icons.BLOCK if not is_selectable else ft.Icons.CHECK_CIRCLE_OUTLINE,
                        disabled=is_selected or not is_selectable,
                        on_click=lambda _, selected_record=record: self._select_record(selected_record),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _build_person_result_row(self, record: SearchSelectorRecord, is_selected: bool) -> ft.Control:
        return ft.Container(
            padding=12,
            border_radius=10,
            border=_border_all(1, ft.Colors.GREEN_300 if is_selected else ft.Colors.BLUE_GREY_100),
            bgcolor=ft.Colors.GREEN_50 if is_selected else ft.Colors.WHITE,
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(record.primary_text, weight=ft.FontWeight.W_700),
                            ft.Row(
                                controls=[
                                    ft.Text(record.secondary_text, size=12, color=ft.Colors.BLUE_GREY_700),
                                    *(
                                        [ft.Text(record.summary_text, size=12, color=ft.Colors.BLUE_GREY_700)]
                                        if record.summary_text
                                        and record.summary_text not in {record.primary_text, record.secondary_text}
                                        else []
                                    ),
                                ],
                                spacing=8,
                                wrap=True,
                            ),
                            *(
                                [
                                    ft.Text(record.technical_secondary_text, size=11, color=ft.Colors.BLUE_GREY_500)
                                ]
                                if self.show_technical_details
                                else []
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Button(
                        "Seleccionar" if not is_selected else "Seleccionado",
                        icon=ft.Icons.CHECK if is_selected else ft.Icons.CHECK_CIRCLE_OUTLINE,
                        disabled=is_selected,
                        on_click=lambda _, selected_record=record: self._select_record(selected_record),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )


def create_search_selector_demo(
    *,
    title: str,
    placeholder: str,
    records: list[dict[str, Any]],
    selector_kind: SelectorKind,
    on_selection_change: SelectionCallback | None = None,
    show_technical_details: bool = True,
) -> SearchSelectorDemo:
    """Factory explicita para crear buscadores desde pantallas prototipo."""

    return SearchSelectorDemo(
        title=title,
        placeholder=placeholder,
        records=records,
        selector_kind=selector_kind,
        on_selection_change=on_selection_change,
        show_technical_details=show_technical_details,
    )
