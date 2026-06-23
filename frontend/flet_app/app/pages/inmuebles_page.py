import json
from typing import Any, Callable

import flet as ft

from app.api_client import ApiClient, ApiResult
from app.inmueble_alta_helpers import (
    ESTADOS_ADMINISTRATIVOS,
    ESTADOS_DATO_CATASTRAL,
    ESTADOS_JURIDICOS,
    build_dato_catastral_payload,
    build_inmueble_payload,
    has_dato_catastral_util,
    should_create_dato_catastral,
    validate_dato_catastral_form,
    validate_form,
)
from app.components.detail_section import detail_section, key_value_grid
from app.components.detail_tabs import detail_tabs
from app.components.entity_table import entity_table
from app.components.error_state import error_state
from app.components.status_badge import status_badge
from app.components.technical_output_panel import (
    build_technical_output_panel,
    format_technical_output,
)


class InmueblesPage:
    def __init__(
        self,
        api: ApiClient,
        on_navigate,
        detail_kind: str | None = None,
        detail_id: int | None = None,
        initial_tab: str | None = None,
    ) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.detail_kind = detail_kind
        self.detail_id = detail_id
        self.initial_tab = initial_tab

    def build(self) -> ft.Control:
        if self.detail_kind == "inmueble" and self.detail_id is not None:
            return InmuebleDetailView(
                self.api, self.on_navigate, self.detail_id
            ).build()
        if self.detail_kind == "unidad" and self.detail_id is not None:
            return UnidadDetailView(self.api, self.on_navigate, self.detail_id).build()
        if self.detail_kind == "create":
            return InmuebleCreateView(self.api, self.on_navigate).build()
        if self.detail_kind == "desarrollo_create":
            return DesarrolloCreateView(self.api, self.on_navigate).build()
        return InmueblesHub(self.api, self.on_navigate, self.initial_tab).build()


class InmueblesHub:
    def __init__(
        self, api: ApiClient, on_navigate, initial_tab: str | None = None
    ) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.initial_tab = initial_tab

    def build(self) -> ft.Control:
        selected_index = 2 if self.initial_tab == "desarrollos" else 0
        return detail_tabs(
            [
                ("Inmuebles", [InmueblesListView(self.api, self.on_navigate).build()]),
                (
                    "Unidades funcionales",
                    [UnidadesListView(self.api, self.on_navigate).build()],
                ),
                (
                    "Desarrollos",
                    [DesarrollosListView(self.api, self.on_navigate).build()],
                ),
            ],
            selected_index=selected_index,
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
                ft.Row(
                    controls=[
                        ft.Text("Inmuebles", size=28, weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        ft.FilledButton(
                            "Nuevo inmueble",
                            icon=ft.Icons.ADD_HOME,
                            on_click=lambda _: self.on_navigate("inmueble_create"),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
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
                    (
                        lambda _, id_inmueble=id_inmueble: self.on_navigate(
                            "inmueble_detail", id_inmueble=id_inmueble
                        )
                    )
                    if id_inmueble is not None
                    else None
                ),
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


class DesarrollosListView:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.results = ft.Column(spacing=12, expand=True)

    def build(self) -> ft.Control:
        self._load()
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Desarrollos / Loteos",
                            size=28,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Container(expand=True),
                        ft.FilledButton(
                            "Nuevo desarrollo",
                            icon=ft.Icons.ADD_BUSINESS,
                            on_click=lambda _: self.on_navigate("desarrollo_create"),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.results,
            ],
            spacing=16,
            expand=True,
        )

    def _load(self) -> None:
        result = self.api.get_desarrollos()
        self.results.controls.clear()
        if not result.success:
            self.results.controls.append(
                error_state(
                    result.error_message or "No se pudieron cargar los desarrollos."
                )
            )
            return
        items, _total = _list_payload(result.data)
        rows = [_desarrollo_row(item) for item in items]
        if not rows:
            self.results.controls.append(_empty("No hay desarrollos/loteos cargados."))
            return
        self.results.controls.append(
            entity_table(
                columns=[
                    ("Código", "codigo"),
                    ("Nombre", "nombre"),
                    ("Estado", "estado"),
                    ("Descripción", "descripcion"),
                    ("Observaciones", "observaciones"),
                ],
                rows=rows,
            )
        )


class DesarrolloCreateView:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate

    def build(self) -> ft.Control:
        form = DesarrolloCreateForm(
            self.api,
            on_close=lambda: self.on_navigate("desarrollos"),
        )
        return ft.Column(
            controls=[form.build()],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )


class DesarrolloCreateForm:
    def __init__(self, api: ApiClient, on_close: Callable[[], None]) -> None:
        self.api = api
        self.on_close = on_close
        self.codigo_desarrollo = ft.TextField(label="Código desarrollo *", width=260)
        self.nombre_desarrollo = ft.TextField(label="Nombre desarrollo *", width=320)
        self.descripcion = ft.TextField(
            label="Descripción", multiline=True, min_lines=2, max_lines=3
        )
        self.estado_desarrollo = ft.Dropdown(
            label="Estado desarrollo *",
            value="ACTIVO",
            width=220,
            options=[ft.dropdown.Option(v) for v in ("ACTIVO", "INACTIVO")],
        )
        self.observaciones = ft.TextField(
            label="Observaciones", multiline=True, min_lines=2, max_lines=3
        )
        self.message = ft.Container(visible=False)
        self.technical = ft.Column(spacing=4, visible=False)
        self.save_button = ft.FilledButton(
            "Guardar desarrollo", icon=ft.Icons.SAVE, on_click=self._save
        )
        self.new_button = ft.FilledTonalButton(
            "Nueva alta", icon=ft.Icons.ADD, on_click=self._new_create, visible=False
        )
        self.root: ft.Control | None = None

    def build(self) -> ft.Control:
        self.root = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Nuevo desarrollo / loteo",
                                size=20,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Container(expand=True),
                            ft.TextButton(
                                "Volver a desarrollos",
                                on_click=lambda _: self.on_close(),
                            ),
                        ]
                    ),
                    ft.Row(
                        [
                            self.codigo_desarrollo,
                            self.nombre_desarrollo,
                            self.estado_desarrollo,
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    self.descripcion,
                    self.observaciones,
                    ft.Row(
                        [
                            self.save_button,
                            self.new_button,
                            ft.OutlinedButton(
                                "Limpiar", icon=ft.Icons.CLEAR, on_click=self._clear
                            ),
                            ft.OutlinedButton(
                                "Volver a desarrollos",
                                icon=ft.Icons.ARROW_BACK,
                                on_click=lambda _: self.on_close(),
                            ),
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                    self.message,
                    self.technical,
                ],
                spacing=12,
            ),
            padding=16,
            bgcolor=ft.Colors.WHITE,
            border=_safe_border(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
        )
        return self.root

    def _current_values(self) -> dict[str, str | None]:
        return {
            "codigo_desarrollo": self.codigo_desarrollo.value,
            "nombre_desarrollo": self.nombre_desarrollo.value,
            "descripcion": self.descripcion.value,
            "estado_desarrollo": self.estado_desarrollo.value,
            "observaciones": self.observaciones.value,
        }

    def _save(self, _) -> None:
        values = self._current_values()
        errors = _validate_desarrollo_form(values)
        if errors:
            self._show_message("\n".join(errors), success=False)
            self.message.update()
            return
        payload = _build_desarrollo_payload(values)
        self.save_button.disabled = True
        self.save_button.update()
        result = self.api.crear_desarrollo(payload)
        if result.success:
            self._show_message("Desarrollo creado correctamente", success=True)
            self._show_technical(payload, result)
            self.save_button.disabled = True
            self.new_button.visible = True
        else:
            self._show_message(_format_api_error(result), success=False)
            self._show_technical(payload, result)
            self.save_button.disabled = False
        self.save_button.update()
        self.new_button.update()
        self.message.update()
        self.technical.update()

    def _show_message(self, text: str, *, success: bool) -> None:
        self.message.content = ft.Text(
            text, color=ft.Colors.GREEN_800 if success else ft.Colors.RED_800
        )
        self.message.bgcolor = ft.Colors.GREEN_50 if success else ft.Colors.RED_50
        self.message.padding = 12
        self.message.border_radius = 6
        self.message.visible = True

    def _show_technical(self, payload: dict[str, Any], result: ApiResult) -> None:
        technical_text = format_technical_output(
            [
                ("payload desarrollo enviado", payload),
                ("response desarrollo", result.data),
                (
                    "errores backend",
                    (
                        "Sin errores backend."
                        if result.success
                        else _format_api_error(result)
                    ),
                ),
            ]
        )
        self.technical.controls = [build_technical_output_panel(technical_text)]
        self.technical.visible = True

    def _new_create(self, _) -> None:
        self._clear_form()
        self.save_button.disabled = False
        self.new_button.visible = False
        if self.root is not None:
            self.root.update()

    def _clear(self, _) -> None:
        self._clear_form()
        if self.root is not None:
            self.root.update()

    def _clear_form(self) -> None:
        self.codigo_desarrollo.value = ""
        self.nombre_desarrollo.value = ""
        self.descripcion.value = ""
        self.estado_desarrollo.value = "ACTIVO"
        self.observaciones.value = ""
        self.message.visible = False
        self.technical.visible = False


class InmuebleCreateView:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate

    def build(self) -> ft.Control:
        form = InmuebleCreateForm(
            self.api,
            on_close=lambda: self.on_navigate("inmuebles"),
            on_created=lambda: None,
        )
        return ft.Column(
            controls=[form.build()],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )


class InmuebleCreateForm:
    def __init__(
        self,
        api: ApiClient,
        on_close: Callable[[], None],
        on_created: Callable[[], None],
    ) -> None:
        self.api = api
        self.on_close = on_close
        self.on_created = on_created
        self.mostrar_avanzados = False
        self.codigo_inmueble = ft.TextField(label="Código de inmueble *", width=260)
        self.nombre_inmueble = ft.TextField(label="Nombre inmueble", width=260)
        self.superficie = ft.TextField(label="Superficie", width=160)
        self.id_desarrollo = ft.TextField(label="ID desarrollo", width=160)
        self.manzana = ft.TextField(label="Manzana", width=160)
        self.lote = ft.TextField(label="Lote", width=160)
        self.estado_administrativo = ft.Dropdown(
            label="Estado administrativo *",
            value="ACTIVO",
            width=200,
            options=[ft.dropdown.Option(v) for v in ESTADOS_ADMINISTRATIVOS],
        )
        self.estado_juridico = ft.Dropdown(
            label="Estado jurídico *",
            value="REGULAR",
            width=200,
            options=[ft.dropdown.Option(v) for v in ESTADOS_JURIDICOS],
        )
        self.observaciones = ft.TextField(
            label="Observaciones", multiline=True, min_lines=2, max_lines=3
        )
        self.toggle_avanzados = ft.OutlinedButton(
            self._toggle_text(), on_click=self._toggle
        )
        self.avanzados = ft.Column(visible=False, spacing=10)
        self.nomenclatura_catastral = ft.TextField(
            label="Nomenclatura catastral", width=260
        )
        self.partida_inmobiliaria = ft.TextField(
            label="Partida inmobiliaria", width=260
        )
        self.matricula = ft.TextField(label="Matrícula", width=220)
        self.folio_real = ft.TextField(label="Folio real", width=220)
        self.circunscripcion = ft.TextField(label="Circunscripción", width=180)
        self.seccion = ft.TextField(label="Sección", width=180)
        self.parcela = ft.TextField(label="Parcela", width=180)
        self.superficie_titulo = ft.TextField(label="Superficie título", width=180)
        self.superficie_mensura = ft.TextField(label="Superficie mensura", width=180)
        self.medidas = ft.TextField(label="Medidas")
        self.situacion_posesoria = ft.TextField(label="Situación posesoria", width=260)
        self.situacion_dominial = ft.TextField(label="Situación dominial", width=260)
        self.estado_dato = ft.Dropdown(
            label="Estado dato",
            value="ACTIVO",
            width=180,
            options=[ft.dropdown.Option(v) for v in ESTADOS_DATO_CATASTRAL],
        )
        self.observaciones_catastrales = ft.TextField(
            label="Observaciones catastrales", multiline=True, min_lines=2, max_lines=3
        )
        self.message = ft.Container(visible=False)
        self.technical = ft.Column(spacing=4, visible=False)
        self.save_button = ft.FilledButton(
            "Guardar inmueble", icon=ft.Icons.SAVE, on_click=self._save
        )
        self.new_button = ft.FilledTonalButton(
            "Nueva alta", icon=ft.Icons.ADD, on_click=self._new_create, visible=False
        )
        self.root: ft.Control | None = None

    def build(self) -> ft.Control:
        self.avanzados.controls = [
            ft.Row(
                [self.nomenclatura_catastral, self.partida_inmobiliaria],
                wrap=True,
                spacing=10,
            ),
            ft.Row(
                [self.matricula, self.folio_real, self.circunscripcion, self.seccion],
                wrap=True,
                spacing=10,
            ),
            ft.Row(
                [
                    self.parcela,
                    self.superficie_titulo,
                    self.superficie_mensura,
                    self.estado_dato,
                ],
                wrap=True,
                spacing=10,
            ),
            self.medidas,
            ft.Row(
                [self.situacion_posesoria, self.situacion_dominial],
                wrap=True,
                spacing=10,
            ),
            self.observaciones_catastrales,
        ]
        self.root = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Nuevo inmueble", size=20, weight=ft.FontWeight.W_700
                            ),
                            ft.Container(expand=True),
                            ft.TextButton(
                                "Volver a inmuebles", on_click=lambda _: self.on_close()
                            ),
                        ]
                    ),
                    ft.Text(
                        "Manzana y lote se guardan como dato catastral asociado; no se envían linderos.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    self.codigo_inmueble,
                    self.nombre_inmueble,
                    ft.Row(
                        [self.superficie, self.id_desarrollo, self.manzana, self.lote],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Row(
                        [self.estado_administrativo, self.estado_juridico],
                        wrap=True,
                        spacing=10,
                    ),
                    self.observaciones,
                    ft.Divider(),
                    ft.Text(
                        "Datos catastrales/registrales avanzados",
                        weight=ft.FontWeight.W_700,
                    ),
                    self.toggle_avanzados,
                    self.avanzados,
                    ft.Row(
                        [
                            self.save_button,
                            self.new_button,
                            ft.OutlinedButton(
                                "Limpiar", icon=ft.Icons.CLEAR, on_click=self._clear
                            ),
                        ],
                        spacing=10,
                    ),
                    self.message,
                    self.technical,
                ],
                spacing=12,
            ),
            padding=16,
            bgcolor=ft.Colors.WHITE,
            border=_safe_border(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
        )
        return self.root

    def _toggle_text(self) -> str:
        return (
            "Ocultar datos catastrales/registrales avanzados"
            if self.mostrar_avanzados
            else "Mostrar datos catastrales/registrales avanzados"
        )

    def _toggle(self, _) -> None:
        self.mostrar_avanzados = not self.mostrar_avanzados
        self.toggle_avanzados.text = self._toggle_text()
        self.avanzados.visible = self.mostrar_avanzados
        self.avanzados.update()
        self.toggle_avanzados.update()

    def _current_values(self) -> dict[str, str | None]:
        return {
            "codigo_inmueble": self.codigo_inmueble.value,
            "nombre_inmueble": self.nombre_inmueble.value,
            "superficie": self.superficie.value,
            "id_desarrollo": self.id_desarrollo.value,
            "estado_administrativo": self.estado_administrativo.value,
            "estado_juridico": self.estado_juridico.value,
            "observaciones": self.observaciones.value,
        }

    def _current_dato_values(self) -> dict[str, str | None]:
        return {
            "nomenclatura_catastral": self.nomenclatura_catastral.value,
            "partida_inmobiliaria": self.partida_inmobiliaria.value,
            "matricula": self.matricula.value,
            "folio_real": self.folio_real.value,
            "circunscripcion": self.circunscripcion.value,
            "seccion": self.seccion.value,
            "manzana": self.manzana.value,
            "lote": self.lote.value,
            "parcela": self.parcela.value,
            "superficie_titulo": self.superficie_titulo.value,
            "superficie_mensura": self.superficie_mensura.value,
            "medidas": self.medidas.value,
            "situacion_posesoria": self.situacion_posesoria.value,
            "situacion_dominial": self.situacion_dominial.value,
            "estado_dato": self.estado_dato.value,
            "observaciones": self.observaciones_catastrales.value,
        }

    def _save(self, _) -> None:
        values = self._current_values()
        dato_values = self._current_dato_values()
        errors = validate_form(values)
        if self.mostrar_avanzados:
            errors.extend(validate_dato_catastral_form(dato_values))
        if self.mostrar_avanzados and not has_dato_catastral_util(
            dato_values, incluir_avanzados=True
        ):
            errors.append(
                "Cargá al menos un dato catastral/registral o ocultá la sección avanzada."
            )
        if errors:
            self._show_message("\n".join(errors), success=False)
            self.message.update()
            return
        inmueble_payload = build_inmueble_payload(values)
        dato_payload = (
            build_dato_catastral_payload(
                dato_values, incluir_avanzados=self.mostrar_avanzados
            )
            if should_create_dato_catastral(self.mostrar_avanzados, dato_values)
            else None
        )
        self.save_button.disabled = True
        self.save_button.update()
        inmueble_result = self.api.crear_inmueble(inmueble_payload)
        dato_result: ApiResult | None = None
        if inmueble_result.success and dato_payload is not None:
            id_inmueble = (
                (inmueble_result.data or {}).get("id_inmueble")
                if isinstance(inmueble_result.data, dict)
                else None
            )
            dato_result = (
                self.api.crear_dato_catastral_registral_inmueble(
                    int(id_inmueble), dato_payload
                )
                if id_inmueble is not None
                else ApiResult(
                    success=False,
                    error_message="El backend no devolvió id_inmueble para asociar el dato catastral/registral.",
                )
            )
        self.save_button.disabled = False
        if inmueble_result.success:
            messages = ["Inmueble creado correctamente"]
            if dato_payload is not None:
                if dato_result and dato_result.success:
                    messages.append(
                        "Datos de manzana/lote guardados correctamente"
                        if set(dato_payload) <= {"estado_dato", "manzana", "lote"}
                        else "Datos catastrales/registrales creados correctamente"
                    )
                else:
                    messages.append(
                        "El inmueble fue creado, pero no se pudieron guardar los datos catastrales/registrales"
                    )
                    if dato_result:
                        messages.append(_format_api_error(dato_result))
            self._show_message(
                "\n".join(messages),
                success=not (dato_result and not dato_result.success),
            )
            self._show_technical(
                inmueble_payload, inmueble_result.data, dato_payload, dato_result
            )
            self.save_button.disabled = True
            self.new_button.visible = True
            self.on_created()
        else:
            self._show_message(_format_api_error(inmueble_result), success=False)
            self._show_technical(
                inmueble_payload, inmueble_result, dato_payload, dato_result
            )
        self.save_button.update()
        self.new_button.update()
        self.message.update()
        self.technical.update()

    def _show_message(self, text: str, *, success: bool) -> None:
        self.message.content = ft.Text(
            text, color=ft.Colors.GREEN_800 if success else ft.Colors.RED_800
        )
        self.message.bgcolor = ft.Colors.GREEN_50 if success else ft.Colors.RED_50
        self.message.padding = 12
        self.message.border_radius = 6
        self.message.visible = True

    def _show_technical(
        self,
        inmueble_payload: dict[str, Any],
        inmueble_response: object,
        dato_payload: dict[str, Any] | None,
        dato_result: ApiResult | None,
    ) -> None:
        inmueble_data = (
            inmueble_response.data
            if isinstance(inmueble_response, ApiResult)
            else inmueble_response
        )
        backend_errors = (
            "\n".join(
                _format_api_error(r)
                for r in (inmueble_response, dato_result)
                if isinstance(r, ApiResult) and not r.success
            )
            or "Sin errores backend."
        )
        technical_text = format_technical_output(
            [
                (
                    "nota técnica",
                    "Manzana/lote no van en payload inmueble; "
                    "sí van en payload catastral asociado.",
                ),
                ("payload inmueble enviado", inmueble_payload),
                ("response inmueble", inmueble_data),
                ("payload catastral enviado", dato_payload),
                ("response catastral", dato_result.data if dato_result else None),
                ("errores backend", backend_errors),
            ]
        )
        self.technical.controls = [build_technical_output_panel(technical_text)]
        self.technical.visible = True

    def _new_create(self, _) -> None:
        self._clear_form()
        self.save_button.disabled = False
        self.new_button.visible = False
        if self.root is not None:
            self.root.update()

    def _clear(self, _) -> None:
        self._clear_form()
        if self.root is not None:
            self.root.update()

    def _clear_form(self) -> None:
        for control in (
            self.codigo_inmueble,
            self.nombre_inmueble,
            self.superficie,
            self.id_desarrollo,
            self.manzana,
            self.lote,
            self.observaciones,
            self.nomenclatura_catastral,
            self.partida_inmobiliaria,
            self.matricula,
            self.folio_real,
            self.circunscripcion,
            self.seccion,
            self.parcela,
            self.superficie_titulo,
            self.superficie_mensura,
            self.medidas,
            self.situacion_posesoria,
            self.situacion_dominial,
            self.observaciones_catastrales,
        ):
            control.value = ""
        self.estado_administrativo.value = "ACTIVO"
        self.estado_juridico.value = "REGULAR"
        self.estado_dato.value = "ACTIVO"
        self.mostrar_avanzados = False
        self.toggle_avanzados.text = self._toggle_text()
        self.avanzados.visible = False
        self.message.visible = False
        self.technical.visible = False


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
                    (
                        lambda _, id_unidad=id_unidad: self.on_navigate(
                            "unidad_detail", id_unidad_funcional=id_unidad
                        )
                    )
                    if id_unidad is not None
                    else None
                ),
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
                        ft.Text(
                            _inmueble_title(data), size=30, weight=ft.FontWeight.W_700
                        ),
                        ft.Container(expand=True),
                        status_badge(_text_or_none(data.get("estado_administrativo"))),
                    ]
                ),
                _inmueble_header(data),
                detail_tabs(
                    [
                        (
                            "Resumen",
                            [
                                detail_section("Datos base", [_base_inmueble(data)]),
                                detail_section(
                                    "Resumen operativo",
                                    [_dict_grid(data.get("resumen_operativo"))],
                                ),
                            ],
                        ),
                        (
                            "Disponibilidad / ocupacion",
                            [
                                detail_section(
                                    "Disponibilidad / ocupacion actual",
                                    [_current_states(data)],
                                ),
                                detail_section(
                                    "Historial de disponibilidad",
                                    [_table_any(data.get("disponibilidades"))],
                                ),
                                detail_section(
                                    "Historial de ocupacion",
                                    [_table_any(data.get("ocupaciones"))],
                                ),
                            ],
                        ),
                        (
                            "Servicios / responsables",
                            [
                                detail_section(
                                    "Servicios", [_table_any(data.get("servicios"))]
                                ),
                                detail_section(
                                    "Responsables de servicio",
                                    [_table_any(data.get("responsables_servicio"))],
                                ),
                            ],
                        ),
                        (
                            "Operaciones asociadas",
                            [
                                detail_section(
                                    "Unidades funcionales",
                                    [_table_any(data.get("unidades_funcionales"))],
                                ),
                                detail_section(
                                    "Reservas de venta",
                                    [_table_any(data.get("reservas_venta"))],
                                ),
                                detail_section(
                                    "Ventas", [_table_any(data.get("ventas"))]
                                ),
                                detail_section(
                                    "Reservas locativas",
                                    [_table_any(data.get("reservas_locativas"))],
                                ),
                                detail_section(
                                    "Contratos de alquiler",
                                    [_table_any(data.get("contratos_alquiler"))],
                                ),
                            ],
                        ),
                        (
                            "Trazabilidad",
                            [
                                detail_section(
                                    "Trazabilidad de integracion",
                                    [
                                        _traceability(
                                            data.get("trazabilidad_integracion")
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
                        ft.Text(
                            _unidad_title(data), size=30, weight=ft.FontWeight.W_700
                        ),
                        ft.Container(expand=True),
                        status_badge(_text_or_none(data.get("estado_operativo"))),
                    ]
                ),
                _unidad_header(data),
                detail_tabs(
                    [
                        (
                            "Resumen",
                            [
                                detail_section("Datos base", [_base_unidad(data)]),
                                detail_section(
                                    "Inmueble padre",
                                    [_dict_grid(data.get("inmueble"))],
                                ),
                                detail_section(
                                    "Resumen operativo",
                                    [_dict_grid(data.get("resumen_operativo"))],
                                ),
                            ],
                        ),
                        (
                            "Disponibilidad / ocupacion",
                            [
                                detail_section(
                                    "Disponibilidad / ocupacion actual",
                                    [_current_states(data)],
                                ),
                                detail_section(
                                    "Historial de disponibilidad",
                                    [_table_any(data.get("disponibilidades"))],
                                ),
                                detail_section(
                                    "Historial de ocupacion",
                                    [_table_any(data.get("ocupaciones"))],
                                ),
                            ],
                        ),
                        (
                            "Servicios / responsables",
                            [
                                detail_section(
                                    "Servicios", [_table_any(data.get("servicios"))]
                                ),
                                detail_section(
                                    "Responsables de servicio",
                                    [_table_any(data.get("responsables_servicio"))],
                                ),
                            ],
                        ),
                        (
                            "Operaciones asociadas",
                            [
                                detail_section(
                                    "Reservas de venta",
                                    [_table_any(data.get("reservas_venta"))],
                                ),
                                detail_section(
                                    "Ventas", [_table_any(data.get("ventas"))]
                                ),
                                detail_section(
                                    "Reservas locativas",
                                    [_table_any(data.get("reservas_locativas"))],
                                ),
                                detail_section(
                                    "Contratos de alquiler",
                                    [_table_any(data.get("contratos_alquiler"))],
                                ),
                            ],
                        ),
                        (
                            "Trazabilidad",
                            [
                                detail_section(
                                    "Trazabilidad de integracion",
                                    [
                                        _traceability(
                                            data.get("trazabilidad_integracion")
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


def _safe_border(width: int, color: str) -> Any | None:
    border_cls = getattr(ft, "Border", None)
    border_all = getattr(border_cls, "all", None) if border_cls is not None else None
    if callable(border_all):
        return border_all(width, color)

    legacy_border = getattr(ft, "border", None)
    legacy_border_all = (
        getattr(legacy_border, "all", None) if legacy_border is not None else None
    )
    if callable(legacy_border_all):
        return legacy_border_all(width, color)

    return None


def _format_api_error(result: ApiResult) -> str:
    parts = []
    if result.status_code is not None:
        parts.append(f"status_code={result.status_code}")
    if result.error_code:
        parts.append(f"error_code={result.error_code}")
    if result.error_message:
        parts.append(f"error_message={result.error_message}")
    if result.error_details:
        parts.append(
            "error_details="
            + json.dumps(result.error_details, ensure_ascii=False, default=str)
        )
    return " | ".join(parts) or "No se pudo crear el inmueble."


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


def _desarrollo_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id_desarrollo": item.get("id_desarrollo"),
        "codigo": item.get("codigo_desarrollo"),
        "nombre": item.get("nombre_desarrollo"),
        "estado": item.get("estado_desarrollo"),
        "descripcion": item.get("descripcion"),
        "observaciones": item.get("observaciones"),
    }


def _validate_desarrollo_form(values: dict[str, str | None]) -> list[str]:
    errors: list[str] = []
    if not str(values.get("codigo_desarrollo") or "").strip():
        errors.append("Código desarrollo es requerido.")
    if not str(values.get("nombre_desarrollo") or "").strip():
        errors.append("Nombre desarrollo es requerido.")
    if not str(values.get("estado_desarrollo") or "").strip():
        errors.append("Estado desarrollo es requerido.")
    return errors


def _build_desarrollo_payload(values: dict[str, str | None]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in (
        "codigo_desarrollo",
        "nombre_desarrollo",
        "descripcion",
        "estado_desarrollo",
        "observaciones",
    ):
        value = str(values.get(key) or "").strip()
        if value:
            payload[key] = value
    return payload


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
            (
                "Codigo",
                data.get("codigo_unidad_funcional") or data.get("codigo_unidad"),
            ),
            ("Nombre", data.get("nombre_unidad") or data.get("nombre")),
            ("Tipo", data.get("tipo_unidad")),
            ("Superficie", data.get("superficie")),
            ("Estado administrativo", data.get("estado_administrativo")),
            ("Estado operativo", data.get("estado_operativo")),
            ("Observaciones", data.get("observaciones")),
        ]
    )


def _inmueble_header(data: dict[str, Any]) -> ft.Control:
    return ft.Container(
        content=key_value_grid(
            [
                ("Inmueble", _inmueble_title(data)),
                ("Estado administrativo", data.get("estado_administrativo")),
                ("Estado juridico", data.get("estado_juridico")),
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
                ("Cantidad de unidades", data.get("cantidad_unidades_funcionales")),
            ]
        ),
        padding=16,
        border=_safe_border(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _unidad_header(data: dict[str, Any]) -> ft.Control:
    return ft.Container(
        content=key_value_grid(
            [
                ("Unidad", _unidad_title(data)),
                ("Inmueble padre", _compact(data.get("inmueble"))),
                ("Estado administrativo", data.get("estado_administrativo")),
                ("Estado operativo", data.get("estado_operativo")),
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
        ),
        padding=16,
        border=_safe_border(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def _dict_grid(value: object) -> ft.Control:
    if not isinstance(value, dict) or not value:
        return ft.Text("Sin datos.")
    return key_value_grid([(key, _compact(item)) for key, item in value.items()])


def _table_any(value: object) -> ft.Control:
    rows = _safe_list(value)
    if not rows:
        return ft.Text("Sin registros.")
    keys = _first_visible_keys(rows, limit=8)
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


def _first_visible_keys(rows: list[dict[str, Any]], limit: int) -> list[str]:
    keys = [
        key
        for key in _first_keys(rows, limit=limit + 8)
        if not key.startswith("id_") and key not in {"uid_global", "version_registro"}
    ]
    return keys[:limit]


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
            ft.TextButton(
                "Volver a Inmuebles", on_click=lambda _: on_navigate("inmuebles")
            ),
            error_state(message or "No se pudo cargar la ficha."),
        ],
        spacing=12,
    )


def _back_row(on_navigate) -> ft.Control:
    return ft.Row(
        controls=[
            ft.TextButton(
                "Volver a Inmuebles", on_click=lambda _: on_navigate("inmuebles")
            ),
        ]
    )


def _empty(message: str) -> ft.Control:
    return ft.Container(
        content=ft.Text(message),
        padding=16,
        border=_safe_border(1, ft.Colors.BLUE_GREY_100),
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
