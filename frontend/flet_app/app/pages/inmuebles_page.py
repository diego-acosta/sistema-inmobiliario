import json
from typing import Any, Callable, NamedTuple
from uuid import uuid4

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
from app.components.loading_state import (
    DeferredControlLoader,
    DeferredLoadingContainer,
    loading_state,
    safe_update,
)
from app.components.status_badge import status_badge
from app.components.technical_output_panel import (
    build_technical_output_panel,
    format_technical_output,
)

ESTADOS_ADMINISTRATIVOS_UNIDAD_FUNCIONAL = ("ACTIVA", "INACTIVA")
ESTADOS_OPERATIVOS_UNIDAD_FUNCIONAL = (
    "DISPONIBLE",
    "RESERVADA",
    "NO_DISPONIBLE",
    "USO_INTERNO",
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
            return DeferredLoadingContainer(
                lambda: InmuebleDetailView(
                    self.api, self.on_navigate, self.detail_id
                ).build(),
                message="Cargando ficha de inmueble...",
                error_builder=lambda message: _detail_error(self.on_navigate, message),
            )
        if self.detail_kind == "inmueble_edit" and self.detail_id is not None:
            return DeferredLoadingContainer(
                lambda: InmuebleEditView(
                    self.api, self.on_navigate, self.detail_id
                ).build(),
                message="Cargando edición de inmueble...",
                error_builder=lambda message: _detail_error(self.on_navigate, message),
            )
        if self.detail_kind == "unidad" and self.detail_id is not None:
            return UnidadDetailView(self.api, self.on_navigate, self.detail_id).build()
        if self.detail_kind == "create":
            return InmuebleCreateView(self.api, self.on_navigate).build()
        if self.detail_kind == "unidad_create":
            return UnidadCreateView(self.api, self.on_navigate, self.detail_id).build()
        if self.detail_kind == "desarrollo_create":
            return DesarrolloCreateView(self.api, self.on_navigate).build()
        if self.detail_kind == "desarrollo" and self.detail_id is not None:
            return DeferredLoadingContainer(
                lambda: DesarrolloDetailView(
                    self.api, self.on_navigate, self.detail_id
                ).build(),
                message="Cargando ficha de desarrollo/loteo...",
                error_builder=lambda message: _desarrollo_detail_error(
                    self.on_navigate, message
                ),
            )
        return InmueblesHub(self.api, self.on_navigate, self.initial_tab).build()


class InmueblesHub:
    def __init__(
        self, api: ApiClient, on_navigate, initial_tab: str | None = None
    ) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.initial_tab = initial_tab

    def build(self) -> ft.Control:
        selected_index = (
            2
            if self.initial_tab == "desarrollos"
            else 1 if self.initial_tab == "unidades" else 0
        )
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
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Inmuebles", size=28, weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "Importar inmuebles",
                            icon=ft.Icons.UPLOAD_FILE,
                            on_click=lambda _: self.on_navigate("inmuebles_import_excel"),
                        ),
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
                DeferredControlLoader(
                    self.results, self._load, message="Cargando inmuebles..."
                ),
            ],
            spacing=16,
            expand=True,
        )

    def _on_search(self, _) -> None:
        self.offset = 0
        self.results.controls = [loading_state("Cargando inmuebles...")]
        safe_update(self.results)
        self._load()
        safe_update(self.results)

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
        self.results.controls = [loading_state("Cargando inmuebles...")]
        safe_update(self.results)
        self._load()
        safe_update(self.results)

    def _next(self, _) -> None:
        self.offset += self.limit
        self.results.controls = [loading_state("Cargando inmuebles...")]
        safe_update(self.results)
        self._load()
        safe_update(self.results)


class DesarrollosListView:
    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.results = ft.Column(spacing=12, expand=True)

    def build(self) -> ft.Control:
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
                DeferredControlLoader(
                    self.results, self._load, message="Cargando desarrollos..."
                ),
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
                actions=self._row_actions,
            )
        )

    def _row_actions(self, row: dict[str, Any]) -> list[ft.Control]:
        id_desarrollo = row.get("id_desarrollo")
        return [
            ft.TextButton(
                "Abrir ficha",
                disabled=id_desarrollo is None,
                on_click=(
                    (
                        lambda _, id_desarrollo=id_desarrollo: self.on_navigate(
                            "desarrollo_detail", id_desarrollo=id_desarrollo
                        )
                    )
                    if id_desarrollo is not None
                    else None
                ),
            )
        ]


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
        self.current_op_id: str | None = None
        self.current_payload_fingerprint: str | None = None
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
        fingerprint = _payload_fingerprint(payload)
        if (
            self.current_op_id is None
            or self.current_payload_fingerprint != fingerprint
        ):
            self.current_op_id = str(uuid4())
            self.current_payload_fingerprint = fingerprint
        self.save_button.disabled = True
        self.save_button.update()
        result = self.api.crear_desarrollo(payload, op_id=self.current_op_id)
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
        self.current_op_id = None
        self.current_payload_fingerprint = None
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
        self.calle = ft.TextField(label="Calle", width=260)
        self.altura = ft.TextField(label="Altura", width=160)
        self.superficie = ft.TextField(label="Superficie", width=160)
        self.id_desarrollo = ft.Dropdown(
            label="Desarrollo / loteo",
            width=360,
            options=[],
            hint_text="Sin desarrollo/loteo",
        )
        self.desarrollos_help = ft.Text(
            "El desarrollo/loteo permite agrupar inmuebles para futuras consultas e importaciones.",
            color=ft.Colors.BLUE_GREY_700,
        )
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
        self._load_desarrollos()
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
                        [self.calle, self.altura],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Row(
                        [self.superficie, self.id_desarrollo],
                        wrap=True,
                        spacing=10,
                    ),
                    self.desarrollos_help,
                    ft.Row(
                        [self.manzana, self.lote],
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

    def _load_desarrollos(self) -> None:
        result = self.api.get_desarrollos()
        if not result.success:
            self.id_desarrollo.options = []
            self.id_desarrollo.value = None
            self.desarrollos_help.value = (
                "No se pudieron cargar los desarrollos/loteos. "
                "Podés guardar el inmueble sin desarrollo."
            )
            self.desarrollos_help.color = ft.Colors.RED_800
            return

        items, _total = _list_payload(result.data)
        self.id_desarrollo.options = [
            ft.dropdown.Option(
                str(item["id_desarrollo"]),
                _desarrollo_option_label(item),
            )
            for item in items
            if item.get("id_desarrollo") is not None
        ]
        self.id_desarrollo.value = None
        if self.id_desarrollo.options:
            self.desarrollos_help.value = "El desarrollo/loteo permite agrupar inmuebles para futuras consultas e importaciones."
            self.desarrollos_help.color = ft.Colors.BLUE_GREY_700
        else:
            self.desarrollos_help.value = "No hay desarrollos cargados. Podés crear uno desde la pestaña Desarrollos."
            self.desarrollos_help.color = ft.Colors.BLUE_GREY_700

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
            "calle": self.calle.value,
            "altura": self.altura.value,
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
        self.id_desarrollo.value = None
        self.estado_administrativo.value = "ACTIVO"
        self.estado_juridico.value = "REGULAR"
        self.estado_dato.value = "ACTIVO"
        self.mostrar_avanzados = False
        self.toggle_avanzados.text = self._toggle_text()
        self.avanzados.visible = False
        self.message.visible = False
        self.technical.visible = False


class UnidadCreateView:
    def __init__(self, api: ApiClient, on_navigate, id_inmueble: int | None) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.id_inmueble = id_inmueble

    def build(self) -> ft.Control:
        form = UnidadCreateForm(
            self.api,
            on_navigate=self.on_navigate,
            id_inmueble=self.id_inmueble,
        )
        return ft.Column(
            controls=[form.build()],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )


class UnidadCreateForm:
    def __init__(self, api: ApiClient, on_navigate, id_inmueble: int | None) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.prefilled_id_inmueble = id_inmueble
        self.inmuebles_by_id: dict[str, dict[str, Any]] = {}
        self.id_inmueble = ft.Dropdown(
            label="Inmueble padre *",
            width=420,
            options=[],
            disabled=id_inmueble is not None,
        )
        self.inmueble_help = ft.Text(
            "Cargando inmuebles...", color=ft.Colors.BLUE_GREY_700
        )
        self.codigo_unidad = ft.TextField(
            label="Código de unidad funcional *", width=260
        )
        self.nombre_unidad = ft.TextField(label="Nombre / descripción", width=320)
        self.superficie = ft.TextField(label="Superficie", width=160)
        self.estado_administrativo = ft.Dropdown(
            label="Estado administrativo *",
            value="ACTIVA",
            width=220,
            options=[
                ft.dropdown.Option(v) for v in ESTADOS_ADMINISTRATIVOS_UNIDAD_FUNCIONAL
            ],
        )
        self.estado_operativo = ft.Dropdown(
            label="Estado operativo *",
            value="DISPONIBLE",
            width=220,
            options=[
                ft.dropdown.Option(v) for v in ESTADOS_OPERATIVOS_UNIDAD_FUNCIONAL
            ],
        )
        self.observaciones = ft.TextField(
            label="Observaciones", multiline=True, min_lines=2, max_lines=3
        )
        self.message = ft.Container(visible=False)
        self.technical = ft.Column(spacing=4, visible=False)
        self.save_button = ft.FilledButton(
            "Guardar unidad funcional", icon=ft.Icons.SAVE, on_click=self._save
        )
        self.new_button = ft.FilledTonalButton(
            "Nueva alta", icon=ft.Icons.ADD, on_click=self._new_create, visible=False
        )
        self.created_id_unidad_funcional: int | None = None
        self.current_op_id: str | None = None
        self.current_payload_fingerprint: str | None = None
        self.root: ft.Control | None = None

    def build(self) -> ft.Control:
        self._load_inmuebles()
        self.root = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Nueva unidad funcional",
                                size=20,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Container(expand=True),
                            ft.TextButton(
                                (
                                    "Volver a ficha"
                                    if self.prefilled_id_inmueble
                                    else "Volver a unidades"
                                ),
                                on_click=self._go_back,
                            ),
                        ],
                    ),
                    ft.Text(
                        "La unidad funcional se crea como subrecurso del inmueble padre existente.",
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    self.id_inmueble,
                    self.inmueble_help,
                    ft.Row(
                        controls=[
                            self.codigo_unidad,
                            self.nombre_unidad,
                            self.superficie,
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Row(
                        controls=[self.estado_administrativo, self.estado_operativo],
                        wrap=True,
                        spacing=10,
                    ),
                    self.observaciones,
                    ft.Row(
                        controls=[
                            self.save_button,
                            self.new_button,
                            ft.OutlinedButton(
                                "Limpiar", icon=ft.Icons.CLEAR, on_click=self._clear
                            ),
                            ft.OutlinedButton(
                                (
                                    "Volver a ficha del inmueble"
                                    if self.prefilled_id_inmueble
                                    else "Volver al listado"
                                ),
                                icon=ft.Icons.ARROW_BACK,
                                on_click=self._go_back,
                            ),
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton(
                                "Abrir ficha UF creada",
                                icon=ft.Icons.OPEN_IN_NEW,
                                visible=False,
                                data="open_created",
                                on_click=self._open_created,
                            )
                        ]
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

    def _load_inmuebles(self) -> None:
        result = self.api.listar_inmuebles(limit=500, offset=0)
        if not result.success:
            self.id_inmueble.options = []
            self.inmueble_help.value = (
                result.error_message or "No se pudieron cargar los inmuebles."
            )
            self.inmueble_help.color = ft.Colors.RED_800
            return
        items, _total = _list_payload(result.data)
        self.inmuebles_by_id = {
            str(item["id_inmueble"]): item
            for item in items
            if item.get("id_inmueble") is not None
        }
        self.id_inmueble.options = [
            ft.dropdown.Option(key, _inmueble_option_label(item))
            for key, item in self.inmuebles_by_id.items()
        ]
        if self.prefilled_id_inmueble is not None:
            selected = str(self.prefilled_id_inmueble)
            self.id_inmueble.value = selected
            item = self.inmuebles_by_id.get(selected)
            self.inmueble_help.value = (
                f"Inmueble padre precargado: {_inmueble_option_label(item)}"
                if item
                else f"Inmueble padre precargado: ID {self.prefilled_id_inmueble}"
            )
            self.inmueble_help.color = ft.Colors.BLUE_GREY_700
        elif self.id_inmueble.options:
            self.inmueble_help.value = (
                "Seleccioná el inmueble padre para asociar la UF."
            )
            self.inmueble_help.color = ft.Colors.BLUE_GREY_700
        else:
            self.inmueble_help.value = (
                "No hay inmuebles cargados para asociar unidades funcionales."
            )
            self.inmueble_help.color = ft.Colors.RED_800

    def _current_values(self) -> dict[str, str | None]:
        return {
            "id_inmueble": self.id_inmueble.value,
            "codigo_unidad": self.codigo_unidad.value,
            "nombre_unidad": self.nombre_unidad.value,
            "superficie": self.superficie.value,
            "estado_administrativo": self.estado_administrativo.value,
            "estado_operativo": self.estado_operativo.value,
            "observaciones": self.observaciones.value,
        }

    def _save(self, _) -> None:
        values = self._current_values()
        errors = _validate_unidad_form(values)
        id_inmueble = _safe_int_or_none(values.get("id_inmueble"))
        if errors or id_inmueble is None:
            self._show_message(
                "\n".join(errors or ["Seleccioná un inmueble padre válido."]),
                success=False,
            )
            self.message.update()
            return
        payload = _build_unidad_payload(values)
        fingerprint = _payload_fingerprint(
            {"id_inmueble": id_inmueble, "payload": payload}
        )
        if (
            self.current_op_id is None
            or self.current_payload_fingerprint != fingerprint
        ):
            self.current_op_id = str(uuid4())
            self.current_payload_fingerprint = fingerprint
        self.save_button.disabled = True
        self.save_button.update()
        result = self.api.crear_unidad_funcional(
            id_inmueble, payload, op_id=self.current_op_id
        )
        if result.success:
            self.created_id_unidad_funcional = _safe_int_or_none(
                (result.data or {}).get("id_unidad_funcional")
                if isinstance(result.data, dict)
                else None
            )
            self._show_message("Unidad funcional creada correctamente", success=True)
            self._show_technical(payload, result)
            self.save_button.disabled = True
            self.new_button.visible = True
            self._set_open_created_visible(self.created_id_unidad_funcional is not None)
        else:
            self._show_message(_format_api_error(result), success=False)
            self._show_technical(payload, result)
            self.save_button.disabled = False
        self.save_button.update()
        self.new_button.update()
        self.message.update()
        self.technical.update()
        if self.root is not None:
            self.root.update()

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
                (
                    "nota técnica",
                    "id_inmueble viaja en path; la UF usa estados administrativo y operativo propios del contrato backend.",
                ),
                ("payload UF enviado", payload),
                ("op_id usado", self.current_op_id),
                ("response UF", result.data),
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
        self._clear_form(clear_parent=self.prefilled_id_inmueble is None)
        self.save_button.disabled = False
        self.new_button.visible = False
        self._set_open_created_visible(False)
        if self.root is not None:
            self.root.update()

    def _clear(self, _) -> None:
        self._clear_form(clear_parent=self.prefilled_id_inmueble is None)
        if self.root is not None:
            self.root.update()

    def _clear_form(self, *, clear_parent: bool) -> None:
        if clear_parent:
            self.id_inmueble.value = None
        self.codigo_unidad.value = ""
        self.nombre_unidad.value = ""
        self.superficie.value = ""
        self.estado_administrativo.value = "ACTIVA"
        self.estado_operativo.value = "DISPONIBLE"
        self.observaciones.value = ""
        self.created_id_unidad_funcional = None
        self.current_op_id = None
        self.current_payload_fingerprint = None
        self.message.visible = False
        self.technical.visible = False

    def _go_back(self, _) -> None:
        if self.prefilled_id_inmueble is not None:
            self.on_navigate("inmueble_detail", id_inmueble=self.prefilled_id_inmueble)
        else:
            self.on_navigate("unidades_funcionales")

    def _open_created(self, _) -> None:
        if self.created_id_unidad_funcional is not None:
            self.on_navigate(
                "unidad_detail", id_unidad_funcional=self.created_id_unidad_funcional
            )

    def _set_open_created_visible(self, visible: bool) -> None:
        if self.root is None:
            return
        content = getattr(self.root, "content", None)
        controls = getattr(content, "controls", [])
        for control in controls:
            if isinstance(control, ft.Row):
                for child in control.controls:
                    if getattr(child, "data", None) == "open_created":
                        child.visible = visible
                        return


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
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Unidades funcionales", size=28, weight=ft.FontWeight.W_700
                        ),
                        ft.Container(expand=True),
                        ft.FilledButton(
                            "Nueva unidad funcional",
                            icon=ft.Icons.ADD_HOME_WORK,
                            on_click=lambda _: self.on_navigate("unidad_create"),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
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
                DeferredControlLoader(
                    self.results,
                    self._load,
                    message="Cargando unidades funcionales...",
                ),
            ],
            spacing=16,
            expand=True,
        )

    def _on_search(self, _) -> None:
        self.offset = 0
        self.results.controls = [loading_state("Cargando unidades funcionales...")]
        safe_update(self.results)
        self._load()
        safe_update(self.results)

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
        self.results.controls = [loading_state("Cargando unidades funcionales...")]
        safe_update(self.results)
        self._load()
        safe_update(self.results)

    def _next(self, _) -> None:
        self.offset += self.limit
        self.results.controls = [loading_state("Cargando unidades funcionales...")]
        safe_update(self.results)
        self._load()
        safe_update(self.results)


class DesarrolloInmueblesLoadResult(NamedTuple):
    items: list[dict[str, Any]]
    total: int | None
    complete: bool
    error_message: str | None


def _load_all_desarrollo_inmuebles(
    api: ApiClient, id_desarrollo: int, page_size: int = 500
) -> DesarrolloInmueblesLoadResult:
    items: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    offset = 0
    total: int | None = None
    total_is_reliable = False

    while True:
        result = api.listar_inmuebles(
            id_desarrollo=id_desarrollo, limit=page_size, offset=offset
        )
        if not result.success:
            base_message = (
                result.error_message
                or "No se pudieron cargar todos los inmuebles asociados."
            )
            if items:
                base_message = (
                    f"Carga parcial: se cargaron {len(items)}"
                    + (f" de {total}" if total is not None else "")
                    + f" inmuebles/lotes asociados. {base_message}"
                )
            return DesarrolloInmueblesLoadResult(items, total, False, base_message)

        page_items, page_total = _list_payload(result.data)
        if _list_payload_has_total(result.data):
            total = page_total
            total_is_reliable = True
        elif total is None:
            total = None

        filtered_page = [
            item
            for item in page_items
            if _safe_int(item.get("id_desarrollo")) == id_desarrollo
        ]
        new_items: list[dict[str, Any]] = []
        for item in filtered_page:
            id_inmueble = _safe_int_or_none(item.get("id_inmueble"))
            if id_inmueble is None:
                new_items.append(item)
                continue
            if id_inmueble in seen_ids:
                continue
            seen_ids.add(id_inmueble)
            new_items.append(item)
        items.extend(new_items)

        if total_is_reliable and total is not None and len(items) >= total:
            return DesarrolloInmueblesLoadResult(items, total, True, None)
        if not page_items:
            resolved_total = total if total_is_reliable else len(items)
            return DesarrolloInmueblesLoadResult(items, resolved_total, True, None)
        if not total_is_reliable and len(page_items) < page_size:
            return DesarrolloInmueblesLoadResult(items, len(items), True, None)
        if page_items and not new_items:
            return DesarrolloInmueblesLoadResult(
                items,
                total,
                False,
                "Carga parcial: el backend devolvió una página repetida y se detuvo la carga para evitar duplicados.",
            )

        offset += page_size


class DesarrolloDetailView:
    def __init__(self, api: ApiClient, on_navigate, id_desarrollo: int) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.id_desarrollo = id_desarrollo

    def build(self) -> ft.Control:
        desarrollo_result = self.api.get_desarrollo(self.id_desarrollo)
        if not desarrollo_result.success:
            return _desarrollo_detail_error(
                self.on_navigate, desarrollo_result.error_message
            )
        data = _unwrap_data(desarrollo_result.data)
        inmuebles_result = _load_all_desarrollo_inmuebles(
            self.api, self.id_desarrollo, page_size=500
        )
        inmuebles = inmuebles_result.items
        inmuebles_error = inmuebles_result.error_message

        return ft.Column(
            controls=[
                ft.TextButton(
                    "Volver a desarrollos",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda _: self.on_navigate("desarrollos"),
                ),
                ft.Row(
                    controls=[
                        ft.Text(
                            f"Desarrollo / Loteo {_desarrollo_title(data)}",
                            size=30,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Container(expand=True),
                        status_badge(_text_or_none(data.get("estado_desarrollo"))),
                    ]
                ),
                detail_section("Datos principales", [_base_desarrollo(data)]),
                detail_section(
                    "Resumen de inmuebles/lotes asociados",
                    [
                        _desarrollo_resumen_inmuebles(
                            inmuebles,
                            inmuebles_result.total,
                            inmuebles_result.complete,
                            inmuebles_error,
                        )
                    ],
                ),
                detail_section(
                    "Inmuebles/lotes asociados",
                    [
                        _desarrollo_inmuebles_table(
                            inmuebles, inmuebles_error, self.on_navigate
                        )
                    ],
                ),
            ],
            spacing=14,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )


class InmuebleEditView:
    def __init__(self, api: ApiClient, on_navigate, id_inmueble: int) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.id_inmueble = id_inmueble
        self.message = ft.Text(visible=False)
        self.save_button = ft.FilledButton(
            "Guardar", icon=ft.Icons.SAVE, on_click=self._save
        )
        self.data: dict[str, Any] = {}
        self.dato: dict[str, Any] | None = None
        self.datos_catastrales_load_failed = False

    def build(self) -> ft.Control:
        result = self.api.get_inmueble_detalle_integral(self.id_inmueble)
        if not result.success:
            return _detail_error(self.on_navigate, result.error_message)
        self.data = result.data if isinstance(result.data, dict) else {}
        catastral_result = self.api.listar_datos_catastrales_registrales_inmueble(
            self.id_inmueble
        )
        self.datos_catastrales_load_failed = not catastral_result.success
        datos = (
            catastral_result.data
            if catastral_result.success and isinstance(catastral_result.data, list)
            else []
        )
        self.dato = (
            None
            if self.datos_catastrales_load_failed
            else _select_dato_catastral_editable(datos)
        )
        inmueble = _inmueble_data(self.data)
        self.codigo_inmueble = ft.TextField(
            label="Código",
            value=_field_text(inmueble.get("codigo_inmueble")),
            disabled=True,
        )
        self.nombre_inmueble = ft.TextField(
            label="Nombre",
            value=_field_text(
                inmueble.get("nombre_inmueble") or inmueble.get("nombre")
            ),
        )
        self.calle = ft.TextField(
            label="Calle", value=_field_text(inmueble.get("calle"))
        )
        self.altura = ft.TextField(
            label="Altura", value=_field_text(inmueble.get("altura"))
        )
        self.superficie = ft.TextField(
            label="Superficie", value=_field_text(inmueble.get("superficie"))
        )
        self.estado_administrativo = ft.Dropdown(
            label="Estado administrativo",
            value=_field_text(inmueble.get("estado_administrativo"))
            or ESTADOS_ADMINISTRATIVOS[0],
            options=[ft.dropdown.Option(value) for value in ESTADOS_ADMINISTRATIVOS],
        )
        self.estado_juridico = ft.Dropdown(
            label="Estado jurídico",
            value=_field_text(inmueble.get("estado_juridico")) or ESTADOS_JURIDICOS[0],
            options=[ft.dropdown.Option(value) for value in ESTADOS_JURIDICOS],
        )
        self.observaciones = ft.TextField(
            label="Observaciones",
            value=_field_text(inmueble.get("observaciones")),
            multiline=True,
        )
        self.catastral_fields: dict[str, ft.Control] = {}
        for field_name, label in (
            ("manzana", "Manzana"),
            ("lote", "Lote"),
            ("parcela", "Parcela"),
            ("nomenclatura_catastral", "Nomenclatura catastral"),
            ("partida_inmobiliaria", "Partida inmobiliaria"),
            ("matricula", "Matrícula"),
            ("folio_real", "Folio real"),
            ("circunscripcion", "Circunscripción"),
            ("seccion", "Sección"),
            ("chacra", "Chacra"),
            ("quinta", "Quinta"),
            ("fraccion", "Fracción"),
            ("subparcela", "Subparcela"),
            ("superficie_titulo", "Superficie título"),
            ("superficie_mensura", "Superficie mensura"),
            ("medidas", "Medidas"),
            ("situacion_posesoria", "Situación posesoria"),
            ("situacion_dominial", "Situación dominial"),
            ("organismo_origen", "Organismo origen"),
            ("fecha_desde", "Fecha desde"),
            ("fecha_hasta", "Fecha hasta"),
            ("observaciones", "Observaciones catastrales/registrales"),
        ):
            self.catastral_fields[field_name] = ft.TextField(
                label=label,
                value=_field_text((self.dato or {}).get(field_name)),
                multiline=field_name in {"medidas", "observaciones"},
                disabled=self.datos_catastrales_load_failed,
            )
        self.catastral_fields["estado_dato"] = ft.Dropdown(
            label="Estado dato",
            value=_field_text((self.dato or {}).get("estado_dato")) or "ACTIVO",
            options=[ft.dropdown.Option(value) for value in ESTADOS_DATO_CATASTRAL],
            disabled=self.datos_catastrales_load_failed,
        )
        catastral_controls: list[ft.Control] = []
        if self.datos_catastrales_load_failed:
            catastral_controls.append(
                ft.Text(
                    "No se pudieron cargar los datos catastrales/registrales "
                    "existentes. Para evitar duplicados, esta sección queda "
                    "bloqueada hasta recargar la ficha."
                )
            )
        elif self.dato is None:
            catastral_controls.append(
                ft.Text(
                    "Este inmueble no tiene dato catastral/registral cargado. "
                    "Completá los campos y al guardar se creará uno nuevo."
                )
            )
        else:
            catastral_controls.append(
                ft.Text("Editando dato catastral/registral existente.")
            )
        catastral_controls.extend(self.catastral_fields.values())
        return ft.Column(
            controls=[
                _back_row(self.on_navigate),
                ft.Text(
                    f"Editar inmueble {_inmueble_title(self.data)}",
                    size=28,
                    weight=ft.FontWeight.W_700,
                ),
                detail_section(
                    "Datos básicos",
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Container(content=control, col={"sm": 12, "md": 6})
                                for control in (
                                    self.codigo_inmueble,
                                    self.nombre_inmueble,
                                    self.calle,
                                    self.altura,
                                    self.superficie,
                                    self.estado_administrativo,
                                    self.estado_juridico,
                                    self.observaciones,
                                )
                            ],
                            spacing=12,
                            run_spacing=12,
                        )
                    ],
                ),
                detail_section(
                    "Datos catastrales / registrales",
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Container(content=control, col={"sm": 12, "md": 6})
                                for control in catastral_controls
                            ],
                            spacing=12,
                            run_spacing=12,
                        )
                    ],
                ),
                ft.Row(
                    [
                        self.save_button,
                        ft.OutlinedButton(
                            "Cancelar",
                            on_click=lambda _: self.on_navigate(
                                "inmueble_detail", id_inmueble=self.id_inmueble
                            ),
                        ),
                    ]
                ),
                self.message,
            ],
            spacing=14,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _save(self, _) -> None:
        inmueble = _inmueble_data(self.data)
        errors = validate_form(self._inmueble_values(inmueble))
        if not self.datos_catastrales_load_failed:
            errors.extend(validate_dato_catastral_form(self._dato_values()))
        if errors:
            self._show_message("\n".join(errors), success=False)
            return
        op_id = str(uuid4())
        results: list[tuple[str, ApiResult]] = []
        basic_payload = self._basic_payload(inmueble)
        if basic_payload:
            version = _inmueble_version_registro(self.data, inmueble)
            if version <= 0:
                self._show_message(
                    "No se pudo determinar version_registro del inmueble.",
                    success=False,
                )
                return
            results.append(
                (
                    "datos básicos",
                    self.api.actualizar_inmueble(
                        self.id_inmueble, basic_payload, version, op_id=op_id
                    ),
                )
            )
        dato_payload = self._dato_payload()
        if self.datos_catastrales_load_failed:
            dato_payload = {}
        elif self.dato is None:
            dato_values = self._dato_values()
            if should_create_dato_catastral(True, dato_values):
                dato_payload = build_dato_catastral_payload(
                    dato_values, incluir_avanzados=True
                )
                results.append(
                    (
                        "crear datos catastrales/registrales",
                        self.api.crear_dato_catastral_registral_inmueble(
                            self.id_inmueble, dato_payload, op_id=op_id
                        ),
                    )
                )
        elif dato_payload:
            version = _safe_int(self.dato.get("version_registro"))
            id_dato = _safe_int(self.dato.get("id_dato_catastral_registral"))
            if version <= 0 or id_dato <= 0:
                self._show_message(
                    "No se pudo determinar versión o identificador del dato catastral/registral.",
                    success=False,
                )
                return
            results.append(
                (
                    "actualizar datos catastrales/registrales",
                    self.api.actualizar_dato_catastral_registral_inmueble(
                        self.id_inmueble,
                        id_dato,
                        dato_payload,
                        version,
                        op_id=op_id,
                    ),
                )
            )
        if not results:
            self._show_message("No hay cambios para guardar.", success=True)
            return
        failures = [
            f"{name}: {_format_api_error(result)}"
            for name, result in results
            if not result.success
        ]
        if failures:
            self._show_message(
                "Algunas partes no se pudieron guardar:\n" + "\n".join(failures),
                success=False,
            )
            return
        self._show_message("Cambios guardados correctamente.", success=True)
        self.on_navigate("inmueble_detail", id_inmueble=self.id_inmueble)

    def _inmueble_values(self, inmueble: dict[str, Any]) -> dict[str, str | None]:
        return {
            "codigo_inmueble": _field_text(inmueble.get("codigo_inmueble")),
            "nombre_inmueble": self.nombre_inmueble.value,
            "calle": self.calle.value,
            "altura": self.altura.value,
            "superficie": self.superficie.value,
            "id_desarrollo": _field_text(inmueble.get("id_desarrollo")),
            "estado_administrativo": self.estado_administrativo.value,
            "estado_juridico": self.estado_juridico.value,
            "observaciones": self.observaciones.value,
        }

    def _basic_payload(self, inmueble: dict[str, Any]) -> dict[str, Any]:
        payload = build_inmueble_payload(self._inmueble_values(inmueble))
        for field_name in (
            "nombre_inmueble",
            "calle",
            "altura",
            "observaciones",
            "superficie",
        ):
            if not str(getattr(self, field_name).value or "").strip():
                payload[field_name] = None
        if _field_text(inmueble.get("id_desarrollo")) == "":
            payload["id_desarrollo"] = None
        comparable = {key: _field_text(value) for key, value in payload.items()}
        current = {key: _field_text(inmueble.get(key)) for key in payload}
        return payload if comparable != current else {}

    def _dato_values(self) -> dict[str, str | None]:
        return {
            key: getattr(control, "value", None)
            for key, control in self.catastral_fields.items()
        }

    def _dato_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for field_name, control in self.catastral_fields.items():
            value = getattr(control, "value", None)
            current = (self.dato or {}).get(field_name)
            if _field_text(value) == _field_text(current):
                continue
            clean_value = str(value or "").strip()
            if field_name in {"superficie_titulo", "superficie_mensura"} and clean_value:
                payload[field_name] = clean_value
            elif field_name == "estado_dato":
                payload[field_name] = clean_value or "ACTIVO"
            else:
                payload[field_name] = clean_value or None
        return payload

    def _show_message(self, text: str, *, success: bool) -> None:
        self.message.value = text
        self.message.visible = True
        self.message.color = ft.Colors.GREEN_700 if success else ft.Colors.RED_800
        safe_update(self.message)


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
        catastral_result = self.api.listar_datos_catastrales_registrales_inmueble(
            self.id_inmueble
        )
        datos_catastrales = (
            catastral_result.data
            if catastral_result.success and isinstance(catastral_result.data, list)
            else _extract_datos_catastrales(data)
        )
        catastral_control = (
            _datos_catastrales_registrales(datos_catastrales)
            if catastral_result.success
            else _catastral_read_error(catastral_result.error_message)
        )
        return ft.Column(
            controls=[
                _inmueble_operational_header(self.on_navigate, data),
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            "Editar",
                            icon=ft.Icons.EDIT,
                            on_click=lambda _: self.on_navigate(
                                "inmueble_edit", id_inmueble=self.id_inmueble
                            ),
                        ),
                        ft.FilledButton(
                            "Nueva UF",
                            icon=ft.Icons.ADD_HOME_WORK,
                            on_click=lambda _: self.on_navigate(
                                "unidad_create", id_inmueble=self.id_inmueble
                            ),
                        ),
                    ],
                ),
                _inmueble_summary_cards(data, datos_catastrales),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            col={"sm": 12, "md": 8},
                            content=ft.Column(
                                controls=[
                                    detail_section(
                                        "Datos del inmueble", [_base_inmueble(data)]
                                    ),
                                    detail_section(
                                        "Datos catastrales / registrales",
                                        [catastral_control],
                                    ),
                                ],
                                spacing=12,
                            ),
                        ),
                        ft.Container(
                            col={"sm": 12, "md": 4},
                            content=ft.Column(
                                controls=[
                                    detail_section(
                                        "Estado operativo",
                                        [_estado_operativo_inmueble(data)],
                                    ),
                                    detail_section(
                                        "Relaciones asociadas",
                                        [_relaciones_asociadas_inmueble(data)],
                                    ),
                                    detail_section(
                                        "Historial", [_historial_inmueble(data)]
                                    ),
                                ],
                                spacing=12,
                            ),
                        ),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
                _inmueble_technical_detail(data, datos_catastrales),
            ],
            spacing=14,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
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
                                ),
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


def _list_payload_has_total(data: object) -> bool:
    return isinstance(data, dict) and "total" in data


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
        "direccion": item.get("direccion") or _format_inmueble_direccion(item),
        "superficie": item.get("superficie"),
        "manzana": item.get("manzana"),
        "lote": item.get("lote"),
    }



def _format_inmueble_direccion(item: dict[str, Any]) -> str | None:
    parts = [
        str(item.get(field) or "").strip()
        for field in ("calle", "altura")
        if str(item.get(field) or "").strip()
    ]
    return " ".join(parts) if parts else None

def _desarrollo_option_label(item: dict[str, Any]) -> str:
    codigo = str(item.get("codigo_desarrollo") or "").strip()
    nombre = str(item.get("nombre_desarrollo") or "").strip()
    if codigo and nombre:
        return f"{codigo} — {nombre}"
    return codigo or nombre or f"Desarrollo #{item.get('id_desarrollo')}"


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


def _payload_fingerprint(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


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


def _inmueble_option_label(item: dict[str, Any] | None) -> str:
    if not item:
        return "Inmueble no cargado"
    codigo = str(item.get("codigo_inmueble") or "").strip()
    nombre = str(item.get("nombre_inmueble") or item.get("nombre") or "").strip()
    if codigo and nombre:
        return f"{codigo} — {nombre}"
    return codigo or nombre or f"Inmueble #{item.get('id_inmueble')}"


def _validate_unidad_form(values: dict[str, str | None]) -> list[str]:
    errors: list[str] = []
    if _safe_int_or_none(values.get("id_inmueble")) is None:
        errors.append("Inmueble padre es requerido.")
    if not str(values.get("codigo_unidad") or "").strip():
        errors.append("Código de unidad funcional es requerido.")
    estado_administrativo = str(values.get("estado_administrativo") or "").strip()
    if not estado_administrativo:
        errors.append("Estado administrativo es requerido.")
    elif estado_administrativo not in ESTADOS_ADMINISTRATIVOS_UNIDAD_FUNCIONAL:
        errors.append("Estado administrativo debe ser ACTIVA o INACTIVA.")
    estado_operativo = str(values.get("estado_operativo") or "").strip()
    if not estado_operativo:
        errors.append("Estado operativo es requerido.")
    elif estado_operativo not in ESTADOS_OPERATIVOS_UNIDAD_FUNCIONAL:
        errors.append("Estado operativo no es válido para unidad funcional.")
    superficie = str(values.get("superficie") or "").strip()
    if superficie:
        try:
            float(superficie)
        except ValueError:
            errors.append("Superficie debe ser numérica.")
    return errors


def _build_unidad_payload(values: dict[str, str | None]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    mapping = {
        "codigo_unidad": "codigo_unidad",
        "nombre_unidad": "nombre_unidad",
        "superficie": "superficie",
        "estado_administrativo": "estado_administrativo",
        "estado_operativo": "estado_operativo",
        "observaciones": "observaciones",
    }
    for source, target in mapping.items():
        value = str(values.get(source) or "").strip()
        if value:
            payload[target] = value
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


def _unwrap_data(data: object) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return data["data"]
    return data if isinstance(data, dict) else {}


def _desarrollo_title(data: dict[str, Any]) -> str:
    return str(
        data.get("codigo_desarrollo")
        or data.get("nombre_desarrollo")
        or data.get("id_desarrollo")
        or ""
    )


def _base_desarrollo(data: dict[str, Any]) -> ft.Control:
    return key_value_grid(
        [
            ("id_desarrollo", data.get("id_desarrollo")),
            ("codigo_desarrollo", data.get("codigo_desarrollo")),
            ("nombre_desarrollo", data.get("nombre_desarrollo")),
            ("descripcion", data.get("descripcion")),
            ("estado_desarrollo", data.get("estado_desarrollo")),
            ("observaciones", data.get("observaciones")),
            ("uid_global", data.get("uid_global")),
            ("version_registro", data.get("version_registro")),
        ]
    )


def _desarrollo_resumen_inmuebles(
    inmuebles: list[dict[str, Any]],
    total: int | None,
    complete: bool,
    error_message: str | None,
) -> ft.Control:
    if error_message and not inmuebles:
        return error_state(error_message)
    total_label = (
        total if complete and total is not None else f"{len(inmuebles)} cargados"
    )
    counts: dict[str, object] = {"Total": total_label}
    if not complete:
        counts["Estado de carga"] = "Parcial; el total definitivo no está confirmado"
        if total is not None:
            counts["Total informado por backend"] = total
    for item in inmuebles:
        label = _inmueble_estado_resumen(item)
        current_count = counts.get(label, 0)
        counts[label] = (current_count if isinstance(current_count, int) else 0) + 1
    controls: list[ft.Control] = [
        key_value_grid([(key, value) for key, value in counts.items()])
    ]
    if error_message:
        controls.append(
            ft.Text(
                error_message,
                color=ft.Colors.ORANGE_900,
                weight=ft.FontWeight.W_600,
            )
        )
    return ft.Column(controls=controls, spacing=8)


def _inmueble_estado_resumen(item: dict[str, Any]) -> str:
    disponibilidad = _validity_label(
        item.get("disponibilidad_actual"), item.get("disponibilidad_ambigua")
    )
    if disponibilidad and disponibilidad != "Sin vigente":
        return disponibilidad
    return str(item.get("estado_administrativo") or "Otros estados")


def _desarrollo_inmuebles_table(
    inmuebles: list[dict[str, Any]], error_message: str | None, on_navigate
) -> ft.Control:
    if error_message and not inmuebles:
        return ft.Text("No se puede mostrar el listado asociado en este momento.")
    if not inmuebles:
        return ft.Text("No hay inmuebles/lotes asociados a este desarrollo.")
    rows = [_inmueble_row(item) for item in inmuebles]

    def actions(row: dict[str, Any]) -> list[ft.Control]:
        id_inmueble = row.get("id_inmueble")
        return [
            ft.TextButton(
                "Abrir ficha",
                disabled=id_inmueble is None,
                on_click=(
                    (
                        lambda _, id_inmueble=id_inmueble: on_navigate(
                            "inmueble_detail", id_inmueble=id_inmueble
                        )
                    )
                    if id_inmueble is not None
                    else None
                ),
            )
        ]

    controls: list[ft.Control] = []
    if error_message:
        controls.append(
            ft.Text(
                "Listado parcial por error de carga; las filas visibles se pueden abrir.",
                color=ft.Colors.ORANGE_900,
                weight=ft.FontWeight.W_600,
            )
        )
    controls.append(
        entity_table(
            columns=[
                ("Código", "codigo"),
                ("Nombre", "nombre"),
                ("Estado administrativo", "estado_administrativo"),
                ("Estado jurídico", "estado_juridico"),
                ("Disponibilidad", "disponibilidad"),
                ("Ocupación", "ocupacion"),
                ("Superficie", "superficie"),
                ("Manzana", "manzana"),
                ("Lote", "lote"),
            ],
            rows=rows,
            actions=actions,
        )
    )
    return ft.Column(controls=controls, spacing=8)


def _desarrollo_detail_error(on_navigate, message: str | None) -> ft.Control:
    return ft.Column(
        controls=[
            ft.TextButton(
                "Volver a desarrollos", on_click=lambda _: on_navigate("desarrollos")
            ),
            error_state(message or "No se pudo cargar la ficha del desarrollo."),
        ],
        spacing=12,
    )


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


def _inmueble_operational_header(on_navigate, data: dict[str, Any]) -> ft.Control:
    inmueble = _inmueble_data(data)
    desarrollo = (
        data.get("desarrollo") if isinstance(data.get("desarrollo"), dict) else None
    )
    subtitle_parts = [
        _desarrollo_label(desarrollo, inmueble),
        _display_or_none(inmueble.get("estado_juridico")),
        _format_surface(inmueble.get("superficie")),
    ]
    subtitle = " · ".join(part for part in subtitle_parts if part)
    return ft.Column(
        controls=[
            _back_row(on_navigate),
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(
                                _inmueble_title(data),
                                size=30,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                subtitle or "Sin datos operativos principales",
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                        ],
                        spacing=2,
                    ),
                    ft.Container(expand=True),
                    status_badge(_text_or_none(inmueble.get("estado_administrativo"))),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ],
        spacing=8,
    )


def _inmueble_summary_cards(
    data: dict[str, Any], datos_catastrales: list[dict[str, Any]]
) -> ft.Control:
    inmueble = _inmueble_data(data)
    desarrollo = (
        data.get("desarrollo") if isinstance(data.get("desarrollo"), dict) else None
    )
    catastral = _first_catastral(datos_catastrales)
    cards = [
        ("Desarrollo/loteo", _desarrollo_label(desarrollo, inmueble) or "Sin asociar"),
        ("Manzana / Lote", _manzana_lote_label(catastral)),
        ("Superficie", _format_surface(inmueble.get("superficie")) or "Sin cargar"),
        ("Estado jurídico", _loaded_or_empty(inmueble.get("estado_juridico"))),
        (
            "Disponibilidad",
            _validity_label(
                data.get("disponibilidad_actual"), data.get("disponibilidad_ambigua")
            ),
        ),
        (
            "Ocupación",
            _validity_label(
                data.get("ocupacion_actual"), data.get("ocupacion_ambigua")
            ),
        ),
    ]
    return ft.ResponsiveRow(
        controls=[
            ft.Container(
                col={"sm": 12, "md": 6, "lg": 2},
                content=_summary_card(title, value),
            )
            for title, value in cards
        ],
        spacing=12,
        run_spacing=12,
    )


def _summary_card(title: str, value: object) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=12, color=ft.Colors.BLUE_GREY_700),
                ft.Text(
                    str(value), size=16, weight=ft.FontWeight.W_600, selectable=True
                ),
            ],
            spacing=4,
        ),
        padding=12,
        border=_safe_border(1, ft.Colors.BLUE_GREY_100),
        border_radius=8,
    )


def _estado_operativo_inmueble(data: dict[str, Any]) -> ft.Control:
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
                "Ocupación actual",
                _validity_label(
                    data.get("ocupacion_actual"), data.get("ocupacion_ambigua")
                ),
            ),
            ("Unidades funcionales", len(_safe_list(data.get("unidades_funcionales")))),
            ("Servicios asociados", len(_safe_list(data.get("servicios")))),
        ]
    )


def _relaciones_asociadas_inmueble(data: dict[str, Any]) -> ft.Control:
    collections = [
        ("Unidades funcionales", "unidades_funcionales"),
        ("Servicios", "servicios"),
        ("Reservas de venta", "reservas_venta"),
        ("Ventas", "ventas"),
        ("Reservas locativas", "reservas_locativas"),
        ("Contratos de alquiler", "contratos_alquiler"),
    ]
    controls: list[ft.Control] = [
        key_value_grid(
            [(label, len(_safe_list(data.get(key)))) for label, key in collections]
        )
    ]
    for label, key in collections:
        rows = _safe_list(data.get(key))
        if rows:
            controls.append(ft.Text(label, weight=ft.FontWeight.W_600))
            controls.append(_table_any(rows))
    return ft.Column(controls=controls, spacing=10)


def _historial_inmueble(data: dict[str, Any]) -> ft.Control:
    disponibilidades = _safe_list(data.get("disponibilidades"))
    ocupaciones = _safe_list(data.get("ocupaciones"))
    if not disponibilidades and not ocupaciones:
        return ft.Text("Sin historial de disponibilidad/ocupación.")
    controls: list[ft.Control] = []
    if disponibilidades:
        controls.extend(
            [
                ft.Text("Disponibilidad", weight=ft.FontWeight.W_600),
                _table_any(disponibilidades),
            ]
        )
    if ocupaciones:
        controls.extend(
            [ft.Text("Ocupación", weight=ft.FontWeight.W_600), _table_any(ocupaciones)]
        )
    return ft.Column(controls=controls, spacing=10)


def _inmueble_technical_detail(
    data: dict[str, Any], datos_catastrales: list[dict[str, Any]]
) -> ft.Control:
    return ft.ExpansionTile(
        title=ft.Text("Detalle técnico"),
        subtitle=ft.Text("Mostrar detalle"),
        controls=[
            build_technical_output_panel(
                format_technical_output(
                    [
                        ("detalle integral", data),
                        ("datos catastrales / registrales", datos_catastrales),
                    ]
                )
            )
        ],
    )


def _first_catastral(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return rows[0] if rows else {}


def _manzana_lote_label(row: dict[str, Any]) -> str:
    manzana = _display_or_none(row.get("manzana")) or "Sin cargar"
    lote = _display_or_none(row.get("lote")) or "Sin cargar"
    return f"{manzana} / {lote}"


def _display_or_none(value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def _format_surface(value: object) -> str | None:
    text = _display_or_none(value)
    if text is None:
        return None
    try:
        number = float(text)
    except ValueError:
        return f"{text} m²" if "m" not in text.lower() else text
    if number.is_integer():
        return f"{int(number)} m²"
    return f"{number:g} m²"


def _format_date(value: object) -> str | None:
    text = _display_or_none(value)
    if text is None:
        return None
    date_part = text[:10]
    pieces = date_part.split("-")
    if len(pieces) == 3 and all(pieces):
        year, month, day = pieces
        return f"{day}/{month}/{year}"
    return text


def _inmueble_data(data: dict[str, Any]) -> dict[str, Any]:
    inmueble = data.get("inmueble")
    return inmueble if isinstance(inmueble, dict) else data


def _desarrollo_label(
    desarrollo: dict[str, Any] | None, inmueble: dict[str, Any]
) -> str | None:
    if desarrollo:
        parts = [
            desarrollo.get("codigo_desarrollo"),
            desarrollo.get("nombre_desarrollo"),
        ]
        return " — ".join(str(part) for part in parts if part) or str(
            desarrollo.get("id_desarrollo")
        )
    if inmueble.get("id_desarrollo") is not None:
        return f"ID {inmueble.get('id_desarrollo')}"
    return None


def _field_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _inmueble_version_registro(data: dict[str, Any], inmueble: dict[str, Any]) -> int:
    return (
        _safe_int(inmueble.get("version_registro"))
        or _safe_int(data.get("version_registro"))
        or _safe_int(data.get("inmueble_version_registro"))
    )


def _select_dato_catastral_editable(
    rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not rows:
        return None
    for row in rows:
        if row.get("estado_dato") == "ACTIVO":
            return row
    return rows[0]


def _extract_datos_catastrales(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "datos_catastrales_registrales",
        "datos_catastrales",
        "dato_catastral_registral",
    ):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
    return []


def _catastral_read_error(message: str | None) -> ft.Control:
    return ft.Text(
        message or "No se pudieron cargar los datos catastrales/registrales asociados."
    )


def _datos_catastrales_registrales(rows: list[dict[str, Any]]) -> ft.Control:
    if not rows:
        return ft.Text(
            "No hay datos catastrales/registrales asociados a este inmueble."
        )
    controls: list[ft.Control] = []
    for index, row in enumerate(rows, start=1):
        if len(rows) > 1:
            controls.append(
                ft.Text(
                    f"Dato catastral/registral #{index}", weight=ft.FontWeight.W_600
                )
            )
        controls.append(_catastral_grid(row))
    return ft.Column(controls=controls, spacing=10)


def _catastral_grid(row: dict[str, Any]) -> ft.Control:
    primary_fields = [
        ("Manzana", "manzana"),
        ("Lote", "lote"),
        ("Parcela", "parcela"),
        ("Nomenclatura catastral", "nomenclatura_catastral"),
        ("Partida inmobiliaria", "partida_inmobiliaria"),
        ("Matrícula", "matricula"),
        ("Folio real", "folio_real"),
    ]
    secondary_fields = [
        ("Circunscripción", "circunscripcion"),
        ("Sección", "seccion"),
        ("Chacra", "chacra"),
        ("Quinta", "quinta"),
        ("Fracción", "fraccion"),
        ("Subparcela", "subparcela"),
        ("Superficie título", "superficie_titulo"),
        ("Superficie mensura", "superficie_mensura"),
        ("Medidas", "medidas"),
        ("Situación posesoria", "situacion_posesoria"),
        ("Situación dominial", "situacion_dominial"),
        ("Organismo origen", "organismo_origen"),
        ("Fecha desde", "fecha_desde"),
        ("Fecha hasta", "fecha_hasta"),
        ("Estado dato", "estado_dato"),
        ("Observaciones", "observaciones"),
    ]
    primary = [
        (label, _format_catastral_value(key, row.get(key), relevant=True))
        for label, key in primary_fields
    ]
    secondary = [
        (label, _format_catastral_value(key, row.get(key), relevant=False))
        for label, key in secondary_fields
        if _display_or_none(row.get(key)) is not None
    ]
    controls: list[ft.Control] = [key_value_grid(primary)]
    if secondary:
        controls.append(
            ft.ExpansionTile(
                title=ft.Text("Datos secundarios"),
                subtitle=ft.Text(f"{len(secondary)} campos cargados"),
                controls=[key_value_grid(secondary)],
            )
        )
    return ft.Column(controls=controls, spacing=8)


def _format_catastral_value(key: str, value: object, *, relevant: bool) -> str:
    if _display_or_none(value) is None:
        return "Sin cargar" if relevant else ""
    if key in {"superficie_titulo", "superficie_mensura"}:
        return _format_surface(value) or "Sin cargar"
    if key in {"fecha_desde", "fecha_hasta"}:
        return _format_date(value) or "Sin cargar"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def _loaded_or_empty(value: object) -> str:
    return _display_or_none(value) or "Sin cargar"


def _resumen_operativo_inmueble(data: dict[str, Any]) -> ft.Control:
    resumen = (
        data.get("resumen_operativo")
        if isinstance(data.get("resumen_operativo"), dict)
        else {}
    )
    inmueble = _inmueble_data(data)
    merged = {
        **resumen,
        "cantidad_unidades_funcionales": inmueble.get("cantidad_unidades_funcionales")
        or data.get("cantidad_unidades_funcionales")
        or len(_safe_list(data.get("unidades_funcionales"))),
    }
    return _dict_grid(merged)


def _base_inmueble(data: dict[str, Any]) -> ft.Control:
    inmueble = _inmueble_data(data)
    desarrollo = (
        data.get("desarrollo") if isinstance(data.get("desarrollo"), dict) else None
    )
    rows = _compact_key_values(
        [
            ("Código", inmueble.get("codigo_inmueble"), True),
            (
                "Nombre",
                inmueble.get("nombre_inmueble") or inmueble.get("nombre"),
                False,
            ),
            ("Desarrollo/loteo", _desarrollo_label(desarrollo, inmueble), True),
            ("Dirección", inmueble.get("direccion") or _format_inmueble_direccion(inmueble), False),
            ("Superficie", _format_surface(inmueble.get("superficie")), True),
            ("Estado administrativo", inmueble.get("estado_administrativo"), True),
            ("Estado jurídico", inmueble.get("estado_juridico"), True),
            ("Observaciones", inmueble.get("observaciones"), False),
        ]
    )
    return key_value_grid(rows)


def _compact_key_values(
    items: list[tuple[str, object, bool]],
) -> list[tuple[str, object]]:
    rows: list[tuple[str, object]] = []
    for label, value, relevant in items:
        formatted = _display_or_none(value)
        if formatted is None and not relevant:
            continue
        rows.append((label, formatted or "Sin cargar"))
    return rows


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
    inmueble = _inmueble_data(data)
    return ft.Container(
        content=key_value_grid(
            [
                ("Inmueble", _inmueble_title(data)),
                ("Estado administrativo", inmueble.get("estado_administrativo")),
                ("Estado juridico", inmueble.get("estado_juridico")),
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
                (
                    "Cantidad de unidades",
                    inmueble.get("cantidad_unidades_funcionales")
                    or data.get("cantidad_unidades_funcionales")
                    or len(_safe_list(data.get("unidades_funcionales"))),
                ),
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
    inmueble = _inmueble_data(data)
    return str(
        inmueble.get("nombre_inmueble")
        or inmueble.get("nombre")
        or inmueble.get("codigo_inmueble")
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
