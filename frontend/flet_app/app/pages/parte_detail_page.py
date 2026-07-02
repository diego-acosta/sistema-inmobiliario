from datetime import date, datetime
from typing import Any
from uuid import uuid4

import flet as ft

from app.api_client import ApiClient, ApiResult
from app.components.detail_section import detail_section, key_value_grid
from app.components.detail_tabs import detail_tabs
from app.components.entity_table import entity_table
from app.components.error_state import error_state
from app.components.status_badge import status_badge


class ParteDetailPage:
    def __init__(self, api: ApiClient, id_persona: int, on_navigate) -> None:
        self.api = api
        self.id_persona = id_persona
        self.on_navigate = on_navigate
        self.data: dict[str, Any] = {}
        self.edit_panel = ft.Container(visible=False)
        self.edit_message = ft.Text("", visible=False)
        self.edit_fields: dict[str, ft.TextField] = {}
        self.editing_basic_data = False
        self.basic_data_card: ft.Container | None = None
        self.active_modal_kind: str | None = None
        self.active_modal_row: dict[str, Any] = {}
        self.modal_fields: dict[str, ft.TextField | ft.Checkbox] = {}
        self.modal_message = ft.Text("", visible=False)
        self.active_dialog: ft.AlertDialog | None = None

    def build(self) -> ft.Control:
        result = self.api.get_persona_detalle_integral(self.id_persona)
        if not result.success:
            return ft.Column(
                controls=[
                    ft.TextButton(
                        "Volver al listado",
                        on_click=lambda _: self.on_navigate("partes"),
                    ),
                    error_state(
                        result.error_message or "No se pudo cargar la ficha de parte."
                    ),
                ],
                spacing=12,
            )

        estado_cuenta_result = self.api.get_estado_cuenta_persona(self.id_persona)
        data = result.data or {}
        if not isinstance(data, dict):
            return ft.Column(
                controls=[
                    ft.TextButton(
                        "Volver al listado",
                        on_click=lambda _: self.on_navigate("partes"),
                    ),
                    error_state("La ficha de parte devolvio un formato inesperado."),
                ],
                spacing=12,
            )

        self.data = data
        return ft.Container(
            expand=True,
            content=ft.Column(
                controls=[
                    self._header_card(data),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    self._datos_principales_card(data),
                                    self._admin_card(
                                        "Dirección",
                                        [self._domicilios_resumen(data.get("domicilios", []))],
                                        height=145,
                                        scroll_body=True,
                                        action=ft.TextButton("Agregar dirección", on_click=lambda e: self._open_domicilio_dialog(e)),
                                    ),
                                    ft.Row(
                                        controls=[
                                            self._admin_card(
                                                "Teléfonos",
                                                [self._telefonos_resumen(data.get("contactos", []))],
                                                expand=1,
                                                height=140,
                                                scroll_body=True,
                                                action=ft.TextButton("Agregar teléfono", on_click=lambda e: self._open_contacto_dialog("telefono", e)),
                                            ),
                                            self._admin_card(
                                                "Mail",
                                                [self._mails_resumen(data.get("contactos", []))],
                                                expand=1,
                                                height=140,
                                                scroll_body=True,
                                                action=ft.TextButton("Agregar mail", on_click=lambda e: self._open_contacto_dialog("email", e)),
                                            ),
                                        ],
                                        spacing=14,
                                    ),
                                ],
                                spacing=14,
                                expand=3,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            ),
                            self._admin_card(
                                "Participaciones",
                                [
                                    self._participaciones_resumen(
                                        data.get("participaciones", [])
                                    )
                                ],
                                expand=2,
                                height=578,
                                scroll_body=True,
                            ),
                        ],
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    self._admin_card(
                        "Estado de cuenta resumido",
                        [self._resumen_cuenta_dashboard(data, estado_cuenta_result)],
                        height=172,
                    ),
                    self._admin_card(
                        "Datos técnicos",
                        [self._datos_tecnicos(data)],
                        height=96,
                        low_emphasis=True,
                    ),
                ],
                spacing=14,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    def _header_card(self, data: dict[str, Any]) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(
                        self._display_name(data),
                        size=24,
                        weight=ft.FontWeight.W_700,
                    ),
                    ft.Container(expand=True),
                    status_badge(data.get("estado_persona")),
                    ft.TextButton(
                        "Volver al listado",
                        on_click=lambda _: self.on_navigate("partes"),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
        )


    def _datos_principales_card(self, data: dict[str, Any]) -> ft.Container:
        card = self._admin_card(
            "Datos principales",
            self._datos_principales_controls(data),
            height=self._datos_principales_height(),
            action=self._datos_principales_action(),
        )
        self.basic_data_card = card
        return card

    def _datos_principales_controls(self, data: dict[str, Any]) -> list[ft.Control]:
        return [self._datos_base(data)]

    def _datos_principales_height(self) -> int:
        return 265

    def _datos_principales_action(self) -> ft.Control | None:
        return ft.ElevatedButton(
            "Editar datos principales",
            on_click=lambda event: self._open_basic_edit(event),
        )

    def _open_basic_edit(self, event: object = None) -> None:
        self.active_modal_kind = "datos_principales"
        self.active_modal_row = {}
        self.modal_fields = {}
        self.modal_message = ft.Text("", visible=False)
        self.active_dialog = self._basic_data_dialog()
        self._open_modal(event)

    def _build_basic_edit_fields(self) -> None:
        data = self.data
        self.edit_message.visible = False
        self.edit_fields = {
            "tipo_persona": ft.TextField(
                label="Tipo de persona",
                value=str(data.get("tipo_persona") or ""),
                width=170,
                dense=True,
            ),
            "estado_persona": ft.TextField(
                label="Estado",
                value=str(data.get("estado_persona") or ""),
                width=150,
                dense=True,
            ),
            "nombre": ft.TextField(
                label="Nombre",
                value=str(data.get("nombre") or ""),
                width=210,
                dense=True,
            ),
            "apellido": ft.TextField(
                label="Apellido",
                value=str(data.get("apellido") or ""),
                width=210,
                dense=True,
            ),
            "fecha_nacimiento": ft.TextField(
                label="Fecha nacimiento/constitución",
                value=str(data.get("fecha_nacimiento") or ""),
                width=220,
                dense=True,
            ),
            "razon_social": ft.TextField(
                label="Razón social",
                value=str(data.get("razon_social") or ""),
                width=260,
                dense=True,
            ),
            "observaciones": ft.TextField(
                label="Observaciones",
                value=str(data.get("observaciones") or ""),
                multiline=True,
                min_lines=2,
                max_lines=3,
                dense=True,
            ),
        }

    def _basic_edit_form(self) -> ft.Control:
        if not self.edit_fields:
            self._build_basic_edit_fields()
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        self.edit_fields["tipo_persona"],
                        self.edit_fields["estado_persona"],
                    ],
                    spacing=10,
                    wrap=True,
                ),
                ft.Row(
                    controls=[
                        self.edit_fields["nombre"],
                        self.edit_fields["apellido"],
                    ],
                    spacing=10,
                    wrap=True,
                ),
                ft.Row(
                    controls=[
                        self.edit_fields["fecha_nacimiento"],
                        self.edit_fields["razon_social"],
                    ],
                    spacing=10,
                    wrap=True,
                ),
                self.edit_fields["observaciones"],
                self.edit_message,
                ft.Row(
                    controls=[
                        ft.ElevatedButton("Guardar", on_click=self._save_basic_edit),
                        ft.TextButton("Cancelar", on_click=self._cancel_basic_edit),
                    ],
                    spacing=10,
                ),
            ],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )

    def _refresh_basic_data_card(self) -> None:
        mounted_card = self.basic_data_card
        if mounted_card is None:
            return
        replacement = self._admin_card(
            "Datos principales",
            self._datos_principales_controls(self.data),
            height=self._datos_principales_height(),
            action=self._datos_principales_action(),
        )
        mounted_card.content = replacement.content
        mounted_card.height = replacement.height
        self._safe_update(mounted_card)

    def _cancel_basic_edit(self, _) -> None:
        self.editing_basic_data = False
        self.edit_fields = {}
        self.edit_message.visible = False
        self._refresh_basic_data_card()

    def _save_basic_edit(self, _) -> None:
        version = self.data.get("version_registro")
        if version is None:
            self._show_modal_error("No se pudo editar la ficha. Recargá e intentá nuevamente.")
            return
        payload = {
            "tipo_persona": self._modal_value("tipo_persona"),
            "nombre": self._modal_value("nombre") or None,
            "apellido": self._modal_value("apellido") or None,
            "razon_social": self._modal_value("razon_social") or None,
            "fecha_nacimiento": self._modal_value("fecha_nacimiento") or None,
            "estado_persona": self._modal_value("estado_persona"),
            "observaciones": self._modal_value("observaciones") or None,
        }
        result = self.api.actualizar_persona(self.id_persona, payload, int(version), op_id=str(uuid4()))
        if not result.success:
            self._show_modal_error(self._friendly_save_error(result, "No se pudieron guardar los datos principales."))
            return
        for row, numero, tipo in (
            (self._documento_identidad_row(self.data), self._modal_value("documento_identidad"), "DNI"),
            (self._identificacion_fiscal_row(self.data), self._modal_value("identificacion_fiscal"), "CUIT"),
        ):
            current = self._documento_numero(row) if row else ""
            if numero == current:
                continue
            doc_result = self._save_documento_principal(row, numero, tipo)
            if not doc_result.success:
                self._show_modal_error(self._friendly_save_error(doc_result, "Los datos base se guardaron, pero no se pudo guardar el documento."))
                return
        self._finish_modal_save(result)

    def _clean_field(self, key: str) -> str:
        return (self.edit_fields[key].value or "").strip()

    def _show_edit_error(self, message: str) -> None:
        self.edit_message.value = message
        self.edit_message.color = ft.Colors.RED_700
        self.edit_message.visible = True
        self._safe_update(self.edit_message)

    def _safe_update(self, control: ft.Control) -> None:
        try:
            control.update()
        except AssertionError:
            pass


    def _admin_card(
        self,
        title: str,
        controls: list[ft.Control],
        *,
        expand: int | bool | None = None,
        height: int | None = None,
        scroll_body: bool = False,
        action: ft.Control | None = None,
        low_emphasis: bool = False,
    ) -> ft.Control:
        body = (
            ft.Column(controls=controls, spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
            if scroll_body
            else ft.Column(controls=controls, spacing=8)
        )
        header_controls: list[ft.Control] = [
            ft.Text(
                title,
                size=14 if low_emphasis else 17,
                weight=ft.FontWeight.W_700 if not low_emphasis else ft.FontWeight.W_600,
                color=ft.Colors.BLUE_GREY_700 if low_emphasis else ft.Colors.BLUE_GREY_900,
            )
        ]
        if action is not None:
            header_controls.extend([ft.Container(expand=True), action])

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=header_controls,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    body,
                ],
                spacing=10,
            ),
            height=height,
            padding=12 if low_emphasis else 14,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=10,
            bgcolor=ft.Colors.BLUE_GREY_50 if low_emphasis else ft.Colors.WHITE,
            expand=expand,
        )

    def _datos_base(self, data: dict[str, Any]) -> ft.Control:
        return self._filtered_key_value_grid(
            [
                ("Tipo persona", data.get("tipo_persona")),
                ("Nombre", data.get("nombre")),
                ("Apellido", data.get("apellido")),
                ("Razón social", data.get("razon_social")),
                ("Documento de identidad", self._documento_principal(data)),
                ("CUIT/CUIL/CDI", data.get("cuit_cuil") or data.get("cuit") or data.get("cuil") or data.get("cdi")),
                ("Fecha de nacimiento", data.get("fecha_nacimiento")),
                ("Estado", data.get("estado_persona")),
                ("Observaciones", data.get("observaciones")),
            ]
        )

    def _datos_tecnicos(self, data: dict[str, Any]) -> ft.Control:
        return self._filtered_key_value_grid(
            [
                ("id_persona", data.get("id_persona") or self.id_persona),
                ("version_registro", data.get("version_registro")),
                ("uid_global", data.get("uid_global")),
                ("Última modificación", data.get("updated_at") or data.get("fecha_modificacion")),
            ]
        )

    def _estado_financiero(self, data: dict[str, Any]) -> ft.Control:
        raw_resumen = data.get("resumen_financiero") or {}
        resumen = raw_resumen if isinstance(raw_resumen, dict) else {}
        obligaciones_activas = (
            resumen.get("obligaciones_activas")
            or resumen.get("cantidad_obligaciones_activas")
            or resumen.get("cantidad_obligaciones")
        )
        ultimo_pago = resumen.get("ultimo_pago") or resumen.get("fecha_ultimo_pago")
        mora = resumen.get("mora") or resumen.get("mora_calculada") or resumen.get("total_mora")
        return ft.Row(
            controls=[
                self._summary_card(
                    "Saldo pendiente",
                    self._format_money(resumen.get("saldo_pendiente_total")),
                    accent=True,
                ),
                self._summary_card(
                    "Obligaciones activas",
                    self._format_count(obligaciones_activas),
                ),
                self._summary_card("Último pago", ultimo_pago or "-"),
                self._summary_card("Mora", self._format_money(mora)),
            ],
            wrap=True,
            spacing=10,
            run_spacing=10,
        )

    def _filtered_key_value_grid(self, items: list[tuple[str, object]]) -> ft.Control:
        visible = [
            (label, value)
            for label, value in items
            if not self._is_empty_value(value)
        ]
        if not visible:
            return ft.Text("Sin informacion complementaria.")
        return key_value_grid(visible)

    def _is_empty_value(self, value: object) -> bool:
        if value is None:
            return True
        if value == "":
            return True
        if value == "-":
            return True
        if isinstance(value, (list, dict)) and not value:
            return True
        return False

    def _format_count(self, value: object) -> str:
        if self._is_empty_value(value):
            return "-"
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value)

    def _obligaciones_table(self, data: dict[str, Any]) -> ft.Control:
        raw_obligaciones = data.get("obligaciones_financieras") or []
        obligaciones = self._dict_rows(raw_obligaciones)
        if not obligaciones:
            return ft.Text("Sin obligaciones financieras.")
        return entity_table(
            columns=[
                ("Origen", "tipo_origen"),
                ("Rol", "rol_obligado"),
                ("Estado", "estado_obligacion"),
                ("Vencimiento", "fecha_vencimiento"),
                ("Saldo", "saldo_pendiente"),
            ],
            rows=obligaciones,
        )

    def _resumen_cuenta_dashboard(self, data: dict[str, Any], result) -> ft.Control:
        payload = result.data if result.success else None
        resumen = self._as_dict(payload.get("resumen")) if isinstance(payload, dict) else {}
        obligaciones = self._dashboard_obligaciones(payload)
        pagable = next((item for item in obligaciones if self._deuda_pagable(item)), None)
        saldo_total = self._first_present(
            resumen, ["saldo_total", "saldo_pendiente_total", "saldo_pendiente"]
        )
        mora = self._first_present(resumen, ["mora_calculada", "mora", "total_mora"])
        ultimo_pago = self._first_present(resumen, ["ultimo_pago", "fecha_ultimo_pago"])
        metricas = ft.Row(
            controls=[
                self._summary_card("Saldo pendiente total", self._format_money(saldo_total)),
                self._summary_card("Saldo vencido", self._format_money(resumen.get("saldo_vencido"))),
                self._summary_card("Obligaciones activas", self._format_count(len(obligaciones))),
                self._summary_card("Mora", self._format_money(mora)),
                self._summary_card("Último pago", ultimo_pago or "-"),
            ],
            wrap=True,
            spacing=10,
            run_spacing=10,
        )
        action_panel = ft.Container()
        controls: list[ft.Control] = [metricas]
        if not obligaciones and self._estado_cuenta_sin_deuda(resumen, [], []):
            controls.append(ft.Text("Sin deuda registrada", color=ft.Colors.BLUE_GREY_700))
        if pagable is not None:
            def show_payment(_) -> None:
                action_panel.content = detail_section(
                    "Registrar pago", [self._registrar_pago_panel(pagable)]
                )
                action_panel.visible = True
                action_panel.update()

            controls.append(ft.TextButton("Pagar", on_click=show_payment))
        controls.append(action_panel)
        return ft.Column(controls=controls, spacing=8)

    def _dashboard_obligaciones(self, payload: object) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return self._dedupe_obligaciones(self._dict_rows(payload))
        if not isinstance(payload, dict):
            return []
        grupos = self._dict_rows(payload.get("grupos_deuda"))
        relaciones = self._flatten_relaciones(grupos)
        return self._obligaciones_estado_cuenta(payload, relaciones)

    def _estado_cuenta_compact(self, result) -> list[ft.Control]:
        estado_area = ft.Container()
        notice_area = ft.Container()

        def refresh_estado_cuenta(payment_payload: object | None = None) -> None:
            refreshed = self.api.get_estado_cuenta_persona(self.id_persona)
            estado_area.content = ft.Column(
                controls=self._estado_cuenta_controls(
                    refreshed, on_refresh=refresh_estado_cuenta
                ),
                spacing=12,
            )
            if payment_payload is not None:
                notice_area.content = self._pago_result(payment_payload)
                notice_area.visible = True
                notice_area.update()
            estado_area.update()

        estado_area.content = ft.Column(
            controls=self._estado_cuenta_controls(
                result, on_refresh=refresh_estado_cuenta
            ),
            spacing=12,
        )
        return [notice_area, estado_area]

    def _estado_cuenta_tab(self, data: dict[str, Any], result) -> list[ft.Control]:
        estado_area = ft.Container()
        notice_area = ft.Container()

        def refresh_estado_cuenta(payment_payload: object | None = None) -> None:
            refreshed = self.api.get_estado_cuenta_persona(self.id_persona)
            estado_area.content = ft.Column(
                controls=self._estado_cuenta_controls(
                    refreshed, on_refresh=refresh_estado_cuenta
                ),
                spacing=12,
            )
            if payment_payload is not None:
                notice_area.content = self._pago_result(payment_payload)
                notice_area.visible = True
                notice_area.update()
            estado_area.update()

        estado_area.content = ft.Column(
            controls=self._estado_cuenta_controls(
                result, on_refresh=refresh_estado_cuenta
            ),
            spacing=12,
        )
        return [
            detail_tabs(
                [
                    (
                        "General",
                        [
                            detail_section(
                                "Estado de cuenta general",
                                [notice_area, estado_area],
                            ),
                            self._simular_pago_contextual(),
                        ],
                    ),
                    (
                        "Contratos",
                        [
                            self._estado_cuenta_origen_panel(
                                "contrato_alquiler",
                                self._related_origins(data, "contrato_alquiler"),
                                "Sin contratos asociados",
                            )
                        ],
                    ),
                    (
                        "Ventas",
                        [
                            self._estado_cuenta_origen_panel(
                                "venta",
                                self._related_origins(data, "venta"),
                                "Sin ventas asociadas",
                            )
                        ],
                    ),
                ]
            )
        ]

    def _estado_cuenta_controls(self, result, on_refresh=None) -> list[ft.Control]:
        if not result.success:
            return [
                error_state(
                    result.error_message
                    or "No se pudo cargar el estado de cuenta."
                )
            ]

        payload = result.data
        if isinstance(payload, list):
            rows = self._dedupe_obligaciones(self._dict_rows(payload))
            if not rows:
                return [ft.Text("Sin deuda registrada")]
            return [self._deudas_operativas_table(rows, on_refresh=on_refresh)]

        if not isinstance(payload, dict):
            return [ft.Text("Sin deuda registrada")]

        resumen = self._as_dict(payload.get("resumen"))
        grupos = self._dict_rows(payload.get("grupos_deuda"))
        relaciones = self._flatten_relaciones(grupos)
        obligaciones = self._obligaciones_estado_cuenta(payload, relaciones)

        controls: list[ft.Control] = [
            ft.Text("Resumen general", weight=ft.FontWeight.W_600),
            self._estado_cuenta_resumen(payload, resumen),
        ]

        if self._estado_cuenta_sin_deuda(resumen, grupos, obligaciones):
            controls.append(ft.Text("Sin deuda registrada"))
            return controls

        if obligaciones:
            controls.extend(
                [
                    ft.Text("Conceptos a pagar", weight=ft.FontWeight.W_600),
                    self._deudas_operativas_table(obligaciones, on_refresh=on_refresh),
                ]
            )
        elif relaciones:
            controls.append(
                ft.Text(
                    "Sin conceptos exigibles detallados para mostrar.",
                    color=ft.Colors.BLUE_GREY_700,
                )
            )

        if len(controls) == 2:
            extra_rows = self._dedupe_obligaciones(self._dict_rows(payload.get("items")))
            if extra_rows:
                controls.append(
                    self._deudas_operativas_table(extra_rows, on_refresh=on_refresh)
                )

        return controls

    def _deudas_operativas_table(
        self, obligaciones: list[dict[str, Any]], on_refresh=None
    ) -> ft.Control:
        detalle_panel = ft.Container(visible=False)
        rows = [
            self._deuda_operativa_row(obligacion)
            for obligacion in obligaciones
            if isinstance(obligacion, dict)
        ]
        if not rows:
            return ft.Text("Sin deudas pendientes.")

        def show_detail(row: dict[str, Any]):
            def handler(_) -> None:
                deuda = row.get("_deuda")
                title = f"Detalle de {self._deuda_label(deuda)}" if isinstance(deuda, dict) else "Detalle de deuda"
                detalle_panel.content = detail_section(
                    title,
                    [self._deuda_detalle(deuda)],
                )
                detalle_panel.visible = True
                detalle_panel.update()

            return handler

        def show_payment(row: dict[str, Any]):
            def handler(_) -> None:
                deuda = row.get("_deuda")

                def close_payment() -> None:
                    detalle_panel.visible = False
                    detalle_panel.content = None
                    detalle_panel.update()

                detalle_panel.content = detail_section(
                    "Registrar pago",
                    [
                        self._registrar_pago_panel(
                            deuda,
                            on_refresh=on_refresh,
                            on_cancel=close_payment,
                        )
                    ],
                )
                detalle_panel.visible = True
                detalle_panel.update()

            return handler

        return ft.Column(
            controls=[
                entity_table(
                    columns=[
                        ("Concepto", "concepto"),
                        ("Origen", "origen"),
                        ("Vencimiento", "vencimiento"),
                        ("Estado", "estado"),
                        ("Saldo", "saldo"),
                        ("Mora", "mora"),
                        ("Total", "total"),
                    ],
                    rows=rows,
                    actions=lambda row: [
                        ft.TextButton("Ver detalle", on_click=show_detail(row)),
                        *(
                            [
                                ft.TextButton("Pagar", on_click=show_payment(row)),
                            ]
                            if self._deuda_pagable(row.get("_deuda"))
                            else []
                        ),
                    ],
                ),
                detalle_panel,
            ],
            spacing=12,
        )

    def _deuda_operativa_row(self, obligacion: dict[str, Any]) -> dict[str, Any]:
        return {
            "concepto": self._deuda_label(obligacion),
            "origen": self._origen_label(obligacion),
            "vencimiento": obligacion.get("fecha_vencimiento"),
            "estado": self._debt_status_badge(
                obligacion.get("estado_obligacion")
                or obligacion.get("estado")
                or obligacion.get("estado_relacion_generadora")
            ),
            "saldo": self._format_money(
                obligacion.get("saldo_pendiente") or obligacion.get("saldo_total")
            ),
            "mora": self._format_money(obligacion.get("mora_calculada")),
            "total": self._format_money(
                obligacion.get("total_con_mora")
            or obligacion.get("total_a_cubrir")
            or obligacion.get("saldo_pendiente")
                or obligacion.get("saldo_total")
            ),
            "_deuda": obligacion,
        }

    def _deuda_detalle(self, value: object) -> ft.Control:
        deuda = value if isinstance(value, dict) else {}
        composiciones = self._dict_rows(deuda.get("composiciones"))
        obligados = self._dict_rows(deuda.get("obligados"))

        controls: list[ft.Control] = [
            key_value_grid(
                [
                    ("Concepto", self._deuda_label(deuda)),
                    ("Origen", self._origen_label(deuda)),
                    ("Vencimiento", deuda.get("fecha_vencimiento")),
                    (
                        "Estado",
                        deuda.get("estado_obligacion") or deuda.get("estado"),
                    ),
                    (
                        "Saldo",
                        self._format_money(
                            deuda.get("saldo_pendiente") or deuda.get("saldo_total")
                        ),
                    ),
                    ("Mora / punitorio", self._format_money(deuda.get("mora_calculada"))),
                    (
                        "Total",
                        self._format_money(
                            deuda.get("total_con_mora")
                            or deuda.get("total_a_cubrir")
                            or deuda.get("saldo_pendiente")
                        ),
                    ),
                ]
            )
        ]

        if composiciones:
            controls.extend(
                [
                    ft.Text("Detalle de conceptos", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Concepto", "concepto"),
                            ("Importe", "importe"),
                            ("Saldo", "saldo"),
                            ("Estado", "estado"),
                        ],
                        rows=[
                            {
                                "concepto": self._concepto_label(item),
                                "importe": self._format_money(
                                    item.get("importe_componente")
                                ),
                                "saldo": self._format_money(
                                    item.get("saldo_componente")
                                ),
                                "estado": self._debt_status_badge(
                                    item.get("estado_composicion_obligacion")
                                    or item.get("estado")
                                ),
                            }
                            for item in composiciones
                        ],
                    ),
                ]
            )
        else:
            controls.append(ft.Text("Sin detalle de conceptos."))

        if obligados:
            controls.extend(
                [
                    ft.Text("Responsables", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Rol", "rol"),
                            ("Porcentaje", "porcentaje"),
                            ("Saldo responsabilidad", "saldo_responsabilidad"),
                        ],
                        rows=[
                            {
                                "rol": item.get("rol_obligado")
                                or item.get("codigo_rol")
                                or item.get("rol"),
                                "porcentaje": item.get("porcentaje_responsabilidad"),
                                "saldo_responsabilidad": self._format_money(
                                    item.get("saldo_responsabilidad")
                                    or item.get("saldo_pendiente_responsabilidad")
                                ),
                            }
                            for item in obligados
                        ],
                    ),
                ]
            )

        return ft.Column(controls=controls, spacing=10)

    def _origenes_deuda_table(self, relaciones: list[dict[str, Any]]) -> ft.Control:
        rows = [
            {
                "origen": self._origen_label(relacion),
                "categoria": self._categoria_origen(relacion),
                "saldo": self._format_money(
                    relacion.get("saldo_total") or relacion.get("saldo_pendiente")
                ),
                "estado": self._debt_status_badge(
                    relacion.get("estado_relacion_generadora")
                    or relacion.get("estado")
                ),
            }
            for relacion in relaciones
        ]
        if not rows:
            return ft.Text("Sin origenes de deuda.")
        return entity_table(
            columns=[
                ("Origen", "origen"),
                ("Categoria", "categoria"),
                ("Saldo", "saldo"),
                ("Estado", "estado"),
            ],
            rows=rows,
        )

    def _simular_pago_contextual(self) -> ft.Control:
        panel = ft.Container(visible=False)

        def toggle(_) -> None:
            panel.visible = not panel.visible
            panel.update()

        panel.content = self._simular_pago_section()
        return detail_section(
            "Accion de cuenta corriente",
            [
                ft.OutlinedButton("Simular pago", on_click=toggle),
                panel,
            ],
        )

    def _simular_pago_section(self) -> ft.Control:
        monto = ft.TextField(
            label="Monto",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180,
        )
        fecha_corte = ft.TextField(
            label="Fecha de calculo",
            value=date.today().isoformat(),
            width=180,
        )
        result_area = ft.Container(content=ft.Text("Sin simulacion ejecutada."))

        def show_error(message: str) -> None:
            result_area.content = error_state(message)
            result_area.update()

        def on_submit(_) -> None:
            monto_value = self._parse_positive_float(monto.value)
            if monto_value is None:
                show_error("El monto es obligatorio y debe ser mayor que cero.")
                return

            result = self.api.simular_pago_persona(
                self.id_persona,
                monto=monto_value,
                fecha_corte=fecha_corte.value or None,
            )
            if not result.success:
                show_error(result.error_message or "No se pudo simular el pago.")
                return

            result_area.content = self._simulacion_result(result.data)
            result_area.update()

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Simulacion global de pago",
                        size=16,
                        weight=ft.FontWeight.W_700,
                    ),
                    ft.Text(
                        "No registra pagos ni modifica saldos.",
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
                    ),
                    ft.Row(
                        controls=[
                            monto,
                            ft.Column(
                                controls=[
                                    fecha_corte,
                                    ft.Text(
                                        "Se usa para calcular deuda, mora y vencimientos.",
                                        size=11,
                                        color=ft.Colors.BLUE_GREY_600,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                    ft.ElevatedButton("Simular", on_click=on_submit),
                    result_area,
                ],
                spacing=10,
            ),
            padding=14,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
            bgcolor=ft.Colors.WHITE,
        )

    def _registrar_pago_panel(
        self, value: object, on_refresh=None, on_cancel=None
    ) -> ft.Control:
        deuda = value if isinstance(value, dict) else {}
        id_obligacion = self._parse_optional_int(deuda.get("id_obligacion_financiera"))
        saldo_actual = self._deuda_saldo(deuda)
        monto = ft.TextField(
            label="Monto",
            value=str(saldo_actual) if saldo_actual > 0 else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180,
        )
        fecha_pago = ft.TextField(
            label="Fecha de pago",
            value=date.today().isoformat(),
            width=180,
        )
        confirm_area = ft.Container(visible=False)
        result_area = ft.Container()
        sending_payment = False

        def show_error(message: str) -> None:
            result_area.content = error_state(message)
            result_area.update()

        def reset_confirmation() -> None:
            confirm_area.visible = False
            confirm_area.content = None
            confirm_area.update()

        def validate() -> tuple[float, str] | None:
            if id_obligacion is None:
                show_error("No se pudo identificar la deuda seleccionada.")
                return None
            if saldo_actual <= 0:
                show_error("La deuda seleccionada no tiene saldo pendiente.")
                return None
            monto_value = self._parse_positive_float(monto.value)
            if monto_value is None:
                show_error("El monto es obligatorio y debe ser mayor que cero.")
                return None
            fecha_pago_value = self._parse_iso_date(fecha_pago.value)
            if fecha_pago_value is None:
                show_error(
                    "La fecha de pago es obligatoria y debe tener formato AAAA-MM-DD."
                )
                return None
            return monto_value, fecha_pago_value

        def execute_payment(
            monto_value: float, fecha_pago_value: str, submit_button: ft.Control
        ) -> None:
            nonlocal sending_payment
            if sending_payment:
                return
            sending_payment = True
            submit_button.disabled = True
            submit_button.update()
            op_id = str(uuid4())
            result = self.api.registrar_pago_persona(
                self.id_persona,
                monto=monto_value,
                fecha_pago=fecha_pago_value,
                alcance_pago="OBLIGACION",
                id_obligacion_financiera=id_obligacion,
                id_relacion_generadora=None,
                op_id=op_id,
            )
            if not result.success:
                sending_payment = False
                submit_button.disabled = False
                submit_button.update()
                confirm_area.visible = False
                show_error(result.error_message or "No se pudo registrar el pago.")
                return

            confirm_area.visible = False
            confirm_area.content = None
            confirm_area.update()
            if on_refresh is not None:
                if on_cancel is not None:
                    on_cancel()
                on_refresh(result.data)
                return
            result_area.content = self._pago_result(result.data)
            result_area.update()

        def ask_confirmation(_) -> None:
            validated = validate()
            if validated is None:
                return
            monto_value, _ = validated

            def confirm_and_execute(event) -> None:
                current_values = validate()
                if current_values is not None:
                    current_monto, current_fecha_pago = current_values
                    execute_payment(current_monto, current_fecha_pago, event.control)

            controls: list[ft.Control] = [
                ft.Text(
                    "Esta accion registrara un pago real y modificara saldos. Confirmar?",
                    color=ft.Colors.RED_900,
                    weight=ft.FontWeight.W_600,
                )
            ]
            if monto_value > saldo_actual:
                controls.append(
                    ft.Text(
                        (
                            "El monto supera el saldo visible; el excedente "
                            "puede quedar como remanente."
                        ),
                        size=12,
                        color=ft.Colors.ORANGE_900,
                    )
                )
            controls.append(
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Confirmar y registrar",
                            on_click=confirm_and_execute,
                        ),
                        ft.TextButton("Cancelar", on_click=lambda _: reset_confirmation()),
                    ],
                    spacing=8,
                    wrap=True,
                )
            )
            confirm_area.content = ft.Container(
                content=ft.Column(controls=controls, spacing=8),
                padding=10,
                border=ft.border.all(1, ft.Colors.RED_100),
                border_radius=6,
                bgcolor=ft.Colors.RED_50,
            )
            confirm_area.visible = True
            confirm_area.update()

        return ft.Container(
            content=ft.Column(
                controls=[
                    self._filtered_key_value_grid(
                        [
                            ("Concepto", self._deuda_label(deuda)),
                            ("Origen", self._origen_label(deuda)),
                            ("Saldo actual", self._format_money(saldo_actual)),
                        ]
                    ),
                    ft.Row(controls=[monto, fecha_pago], spacing=10, wrap=True),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "Confirmar pago", on_click=ask_confirmation
                            ),
                            ft.TextButton(
                                "Cancelar",
                                on_click=lambda _: (
                                    on_cancel() if on_cancel is not None else reset_confirmation()
                                ),
                            ),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    confirm_area,
                    result_area,
                ],
                spacing=10,
            ),
            padding=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
            bgcolor=ft.Colors.WHITE,
        )

    def _pago_result(self, payload: object) -> ft.Control:
        data = payload if isinstance(payload, dict) else {}
        obligaciones = self._dict_rows(data.get("obligaciones_pagadas"))
        remanente = self._to_number(data.get("remanente"))
        controls: list[ft.Control] = [
            ft.Text(
                "Pago registrado. Estado de cuenta actualizado.",
                weight=ft.FontWeight.W_700,
                color=ft.Colors.GREEN_900,
            ),
            self._filtered_key_value_grid(
                [
                    ("Codigo de pago", data.get("codigo_pago_grupo")),
                    ("Monto aplicado", self._format_money(data.get("monto_aplicado"))),
                    ("Remanente", self._format_money(data.get("remanente"))),
                    ("Aplicaciones", len(obligaciones) if obligaciones else None),
                ]
            ),
        ]
        if obligaciones:
            controls.extend(
                [
                    ft.Text("Aplicaciones", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Obligacion", "id_obligacion_financiera"),
                            ("Movimiento", "id_movimiento_financiero"),
                            ("Aplicado", "monto_aplicado"),
                            ("Estado", "estado_resultante"),
                        ],
                        rows=[
                            {
                                "id_obligacion_financiera": item.get(
                                    "id_obligacion_financiera"
                                ),
                                "id_movimiento_financiero": item.get(
                                    "id_movimiento_financiero"
                                ),
                                "monto_aplicado": self._format_money(
                                    item.get("monto_aplicado")
                                ),
                                "estado_resultante": item.get("estado_resultante"),
                            }
                            for item in obligaciones
                        ],
                    ),
                ]
            )
        if remanente > 0:
            controls.append(
                ft.Text(
                    "El pago dejo remanente no aplicado.",
                    color=ft.Colors.ORANGE_900,
                    weight=ft.FontWeight.W_600,
                )
            )
        return ft.Container(
            content=ft.Column(controls=controls, spacing=8),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREEN_100),
            border_radius=6,
            bgcolor=ft.Colors.GREEN_50,
        )

    def _deuda_pagable(self, value: object) -> bool:
        deuda = value if isinstance(value, dict) else {}
        return (
            self._parse_optional_int(deuda.get("id_obligacion_financiera")) is not None
            and self._deuda_saldo(deuda) > 0
        )

    def _deuda_saldo(self, deuda: dict[str, Any]) -> float:
        return self._to_number(
            deuda.get("saldo_pendiente")
            or deuda.get("saldo_total")
            or deuda.get("total_a_cubrir")
            or deuda.get("total_con_mora")
        )

    def _simulacion_result(self, payload: object) -> ft.Control:
        if isinstance(payload, list):
            rows = self._dict_rows(payload)
            if not rows:
                return ft.Text("La simulacion no devolvio deudas afectadas.")
            return self._simulacion_deudas_table(rows)

        if not isinstance(payload, dict):
            return error_state("La simulacion devolvio una respuesta inesperada.")

        detalle = self._dict_rows(payload.get("detalle"))
        mora = payload.get("mora_calculada")
        if mora is None:
            mora = self._sum_field(detalle, "mora_calculada")
        controls: list[ft.Control] = [
            ft.Row(
                controls=[
                    self._summary_card(
                        "Total considerado",
                        self._format_money(payload.get("total_deuda_considerada")),
                        accent=True,
                    ),
                    self._summary_card(
                        "Monto ingresado",
                        self._format_money(payload.get("monto_ingresado")),
                    ),
                    self._summary_card(
                        "Monto aplicado",
                        self._format_money(payload.get("monto_aplicado")),
                    ),
                    self._summary_card(
                        "Remanente",
                        self._format_money(payload.get("remanente")),
                    ),
                    self._summary_card("Mora / punitorio", self._format_money(mora)),
                ],
                wrap=True,
                spacing=10,
                run_spacing=10,
            )
        ]

        if detalle:
            controls.extend(
                [
                    ft.Text("Deudas afectadas", weight=ft.FontWeight.W_600),
                    self._simulacion_deudas_table(detalle),
                ]
            )
        else:
            controls.append(ft.Text("La simulacion no devolvio deudas afectadas."))

        return ft.Column(controls=controls, spacing=10)

    def _simulacion_deudas_table(self, rows: list[dict[str, Any]]) -> ft.Control:
        deudas = self._dict_rows(rows)
        if not deudas:
            return ft.Text("La simulacion no devolvio deudas afectadas.")
        return entity_table(
            columns=[
                ("Concepto", "concepto"),
                ("Origen", "origen"),
                ("Vencimiento", "vencimiento"),
                ("Estado", "estado"),
                ("Total deuda", "total_deuda"),
                ("Aplicado", "aplicado"),
                ("Saldo posterior", "saldo_posterior"),
            ],
            rows=[
                {
                    "concepto": self._deuda_label(item),
                    "origen": self._origen_label(item),
                    "vencimiento": item.get("fecha_vencimiento") or "-",
                    "estado": self._debt_status_badge(
                        item.get("estado_obligacion") or item.get("estado")
                    ),
                    "total_deuda": self._format_money(
                        item.get("total_a_cubrir")
                        or item.get("total_con_mora")
                        or item.get("saldo_pendiente")
                    ),
                    "aplicado": self._format_money(item.get("monto_aplicado")),
                    "saldo_posterior": self._format_money(
                        item.get("saldo_restante_simulado")
                    ),
                }
                for item in deudas
            ],
        )

    def _estado_cuenta_resumen(
        self, payload: dict[str, Any], resumen: dict[str, Any]
    ) -> ft.Control:
        items = [
            (
                "Saldo total",
                self._first_present(resumen, ["saldo_total", "saldo_pendiente_total"]),
            ),
            ("Saldo vencido", resumen.get("saldo_vencido")),
            ("Saldo futuro", resumen.get("saldo_futuro")),
            ("Mora / punitorio", resumen.get("mora_calculada")),
            ("Total con mora", resumen.get("total_con_mora")),
            ("Saldo locativo", resumen.get("saldo_locativo")),
            ("Saldo venta", resumen.get("saldo_venta")),
            ("Saldo trasladados", resumen.get("saldo_trasladados")),
            ("Saldo otros", resumen.get("saldo_otros")),
        ]
        cards = [
            self._summary_card(label, value)
            for label, value in items
            if value is not None or label in {"Saldo total", "Saldo vencido", "Saldo futuro"}
        ]
        controls: list[ft.Control] = []
        if payload.get("fecha_corte"):
            controls.append(
                ft.Text(
                    f"Fecha de corte: {payload.get('fecha_corte')}",
                    size=12,
                    color=ft.Colors.BLUE_GREY_700,
                )
            )
        controls.append(ft.Row(controls=cards, wrap=True, spacing=10, run_spacing=10))
        return ft.Column(controls=controls, spacing=8)

    def _summary_card(
        self, label: str, value: object, *, accent: bool = False
    ) -> ft.Control:
        display_value = (
            str(value)
            if isinstance(value, str)
            and (
                value.startswith("$")
                or value == "-"
                or label.lower().startswith("cantidad")
                or "obligaciones" in label.lower()
            )
            else self._format_money(value)
        )
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(label, size=11 if not accent else 12, color=ft.Colors.BLUE_GREY_700),
                    ft.Text(
                        display_value,
                        size=16 if not accent else 20,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.BLUE_900 if accent else ft.Colors.BLUE_GREY_900,
                    ),
                ],
                spacing=2,
            ),
            width=230 if accent else 170,
            padding=14 if accent else 12,
            border=ft.border.all(1, ft.Colors.BLUE_200 if accent else ft.Colors.BLUE_GREY_100),
            border_radius=6,
            bgcolor=ft.Colors.BLUE_50 if accent else ft.Colors.WHITE,
        )

    def _estado_cuenta_sin_deuda(
        self,
        resumen: dict[str, Any],
        grupos: list[dict[str, Any]],
        obligaciones: list[dict[str, Any]],
    ) -> bool:
        if grupos or obligaciones:
            return False
        saldo_keys = [
            "saldo_total",
            "saldo_pendiente_total",
            "saldo_vencido",
            "saldo_futuro",
            "mora_calculada",
            "total_con_mora",
        ]
        return not any(self._to_number(resumen.get(key)) for key in saldo_keys)

    def _flatten_relaciones(
        self, grupos: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for grupo in grupos:
            grupo_codigo = grupo.get("grupo_origen_deuda")
            for relacion in self._dict_rows(grupo.get("relaciones")):
                row = dict(relacion)
                row["grupo_origen_deuda"] = grupo_codigo
                rows.append(row)
        return rows

    def _flatten_composiciones(
        self,
        obligaciones: list[dict[str, Any]],
        relaciones: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        source_obligaciones = list(obligaciones)
        if not source_obligaciones:
            for relacion in relaciones:
                source_obligaciones.extend(self._dict_rows(relacion.get("obligaciones")))
        for obligacion in source_obligaciones:
            id_obligacion = obligacion.get("id_obligacion_financiera")
            for composicion in self._dict_rows(obligacion.get("composiciones")):
                row = dict(composicion)
                row.setdefault("id_obligacion_financiera", id_obligacion)
                rows.append(row)
        return rows

    def _obligaciones_estado_cuenta(
        self, payload: dict[str, Any], relaciones: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rows = [
            dict(item)
            for item in self._dict_rows(payload.get("obligaciones"))
            if self._is_obligacion_row(item)
        ]
        for relacion in relaciones:
            nested = self._dict_rows(relacion.get("obligaciones"))
            if nested:
                for obligacion in nested:
                    if not self._is_obligacion_row(obligacion):
                        continue
                    row = dict(obligacion)
                    row.setdefault("tipo_origen", relacion.get("tipo_origen"))
                    row.setdefault("id_origen", relacion.get("id_origen"))
                    row.setdefault(
                        "descripcion_origen", relacion.get("descripcion_origen")
                    )
                    row["_relacion_context"] = relacion
                    rows.append(row)
        return self._dedupe_obligaciones(rows)

    def _dedupe_obligaciones(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        unique: dict[tuple[object, ...], dict[str, Any]] = {}
        for row in rows:
            if not self._is_obligacion_row(row):
                continue
            key = self._obligacion_key(row)
            if key not in unique:
                unique[key] = row
                continue
            current = unique[key]
            if not self._dict_rows(current.get("composiciones")) and self._dict_rows(
                row.get("composiciones")
            ):
                current["composiciones"] = row.get("composiciones")
            if not self._dict_rows(current.get("obligados")) and self._dict_rows(
                row.get("obligados")
            ):
                current["obligados"] = row.get("obligados")
            if not current.get("_relacion_context") and row.get("_relacion_context"):
                current["_relacion_context"] = row.get("_relacion_context")
        return list(unique.values())

    def _is_obligacion_row(self, row: dict[str, Any]) -> bool:
        if row.get("id_obligacion_financiera") is not None:
            return True
        if row.get("fecha_vencimiento") is not None and (
            row.get("saldo_pendiente") is not None
            or row.get("importe_total") is not None
            or row.get("total_con_mora") is not None
        ):
            return True
        if self._dict_rows(row.get("composiciones")) and (
            row.get("saldo_pendiente") is not None
            or row.get("estado_obligacion") is not None
        ):
            return True
        return False

    def _obligacion_key(self, row: dict[str, Any]) -> tuple[object, ...]:
        id_obligacion = row.get("id_obligacion_financiera")
        if id_obligacion is not None:
            return ("id", id_obligacion)
        return (
            "natural",
            row.get("tipo_origen"),
            row.get("id_origen"),
            row.get("fecha_vencimiento"),
            row.get("saldo_pendiente") or row.get("saldo_total"),
            row.get("estado_obligacion") or row.get("estado"),
        )

    def _deuda_label(self, deuda: dict[str, Any]) -> str:
        cuota = self._first_present(
            deuda,
            ["numero_cuota", "nro_cuota", "cuota", "orden", "numero"],
        )
        if cuota is not None:
            return f"Cuota {cuota}"

        composiciones = self._dict_rows(deuda.get("composiciones"))
        concepto = self._main_concept(composiciones) or deuda
        code = str(
            concepto.get("codigo_concepto_financiero")
            or concepto.get("codigo_concepto")
            or deuda.get("codigo_concepto_financiero")
            or ""
        ).upper()
        tipo_origen = str(deuda.get("tipo_origen") or "").lower()

        if code == "CANON_LOCATIVO" or tipo_origen == "contrato_alquiler":
            return self._alquiler_label(deuda.get("fecha_vencimiento"))
        if code == "ANTICIPO_VENTA":
            return "Anticipo"
        if code == "CAPITAL_VENTA":
            if self._looks_like_sale_balance(deuda, concepto):
                return "Saldo de venta"
            return "Capital de venta"
        if code in {"SERVICIO_RECUPERADO", "SERVICIO_TRASLADADO"}:
            return self._named_concept(concepto, "Servicio trasladado")
        if code == "IMPUESTO_TRASLADADO":
            return self._named_concept(concepto, "Impuesto trasladado")
        if tipo_origen == "venta":
            return "Cuota de venta"
        label = self._concepto_label(concepto)
        return label if label != "Deuda" else "Concepto pendiente"

    def _main_concept(self, composiciones: list[dict[str, Any]]) -> dict[str, Any]:
        accessory = {"PUNITORIO", "INTERES_FINANCIERO"}
        for item in composiciones:
            code = str(item.get("codigo_concepto_financiero") or "").upper()
            if code and code not in accessory:
                return item
        return composiciones[0] if composiciones else {}

    def _concepto_label(self, item: dict[str, Any]) -> str:
        explicit = (
            item.get("nombre_concepto_financiero")
            or item.get("nombre_concepto")
            or item.get("descripcion")
        )
        if explicit:
            return str(explicit)
        code = str(
            item.get("codigo_concepto_financiero")
            or item.get("codigo_concepto")
            or ""
        ).upper()
        labels = {
            "CAPITAL_VENTA": "Capital de venta",
            "ANTICIPO_VENTA": "Anticipo",
            "CANON_LOCATIVO": "Alquiler",
            "SERVICIO_RECUPERADO": "Servicio trasladado",
            "SERVICIO_TRASLADADO": "Servicio trasladado",
            "IMPUESTO_TRASLADADO": "Impuesto trasladado",
            "PUNITORIO": "Punitorio",
            "INTERES_FINANCIERO": "Interes",
        }
        return labels.get(code, code.replace("_", " ").capitalize() if code else "Deuda")

    def _origen_label(self, item: dict[str, Any]) -> str:
        relacion = self._as_dict(item.get("_relacion_context"))
        data = {**relacion, **item}
        for key, prefix in (
            ("codigo_venta", "Venta"),
            ("codigo_contrato", "Contrato"),
            ("codigo_contrato_alquiler", "Contrato"),
        ):
            if data.get(key):
                return f"{prefix} {data[key]}"
        if data.get("descripcion_origen"):
            cleaned = self._clean_origin_description(data["descripcion_origen"])
            if cleaned:
                return cleaned

        tipo_origen = str(data.get("tipo_origen") or "").lower()
        grupo = str(data.get("grupo_origen_deuda") or "").lower()
        if tipo_origen == "venta":
            return "Venta"
        if tipo_origen == "contrato_alquiler":
            return "Contrato de alquiler"
        if tipo_origen in {"factura_servicio", "liquidacion_recupero"}:
            return "Servicio / recupero"
        if tipo_origen == "liquidacion_impuesto_trasladado":
            return "Impuesto trasladado"
        if "venta" in grupo:
            return "Venta"
        if "locativo" in grupo or "alquiler" in grupo:
            return "Contrato de alquiler"
        if "traslad" in grupo or "servicio" in grupo:
            return "Servicio / recupero"
        return "Otro origen"

    def _clean_origin_description(self, value: object) -> str:
        text = str(value or "").strip()
        lowered = text.lower()
        if "relacion financiera" in lowered or "relación financiera" in lowered:
            if "venta" in lowered:
                return "Venta"
            if "contrato" in lowered or "alquiler" in lowered:
                return "Contrato de alquiler"
            return ""
        return text

    def _categoria_origen(self, item: dict[str, Any]) -> str:
        tipo = str(item.get("tipo_origen") or "").lower()
        grupo = str(item.get("grupo_origen_deuda") or "").lower()
        if tipo == "venta" or "venta" in grupo:
            return "Venta"
        if tipo == "contrato_alquiler" or "locativo" in grupo:
            return "Locativo"
        if "impuesto" in tipo:
            return "Impuesto trasladado"
        if "servicio" in tipo or "recupero" in tipo:
            return "Servicio / recupero"
        return "Otro"

    def _alquiler_label(self, value: object) -> str:
        if not value:
            return "Alquiler"
        try:
            parsed = datetime.fromisoformat(str(value)[:10])
        except ValueError:
            return "Alquiler"
        months = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        return f"Alquiler {months[parsed.month - 1]}"

    def _named_concept(self, item: dict[str, Any], fallback: str) -> str:
        return str(
            item.get("nombre_servicio")
            or item.get("nombre_impuesto")
            or item.get("nombre_concepto_financiero")
            or item.get("descripcion")
            or fallback
        )

    def _looks_like_sale_balance(
        self, deuda: dict[str, Any], concepto: dict[str, Any]
    ) -> bool:
        text = " ".join(
            str(value or "").lower()
            for value in (
                deuda.get("tipo_plan_financiero"),
                deuda.get("descripcion"),
                deuda.get("descripcion_origen"),
                concepto.get("descripcion"),
                concepto.get("nombre_concepto_financiero"),
            )
        )
        return "saldo" in text or "anticipo_y_saldo" in text

    def _grupo_row(self, grupo: dict[str, Any]) -> dict[str, Any]:
        row = dict(grupo)
        row["cantidad_relaciones"] = len(self._dict_rows(grupo.get("relaciones")))
        return row

    def _generic_table(self, rows: list[dict[str, Any]]) -> ft.Control:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if (
                    key not in keys
                    and not isinstance(row.get(key), (dict, list))
                    and not self._is_technical_id(key)
                ):
                    keys.append(key)
                if len(keys) >= 6:
                    break
            if len(keys) >= 6:
                break
        if not keys:
            return ft.Text("Sin deuda registrada")
        return entity_table(columns=[(self._friendly_label(key), key) for key in keys], rows=rows)

    def _friendly_generic_table(
        self,
        rows: list[dict[str, Any]],
        *,
        empty_message: str = "Sin registros.",
    ) -> ft.Control:
        visible_keys: list[str] = []
        display_rows: list[dict[str, Any]] = []
        for row in rows:
            display_row: dict[str, Any] = {}
            for key, value in row.items():
                if self._is_technical_id(key) or isinstance(value, (dict, list)):
                    continue
                if self._is_empty_value(value):
                    continue
                if key not in visible_keys:
                    visible_keys.append(key)
                display_row[key] = self._display_generic_value(key, value)
                if len(visible_keys) >= 6:
                    break
            if display_row:
                display_rows.append(display_row)
        if not display_rows or not visible_keys:
            return ft.Text(empty_message)
        return entity_table(
            columns=[(self._friendly_label(key), key) for key in visible_keys[:6]],
            rows=display_rows,
        )

    def _as_dict(self, value: object) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _first_present(self, data: dict[str, Any], keys: list[str]) -> object:
        for key in keys:
            if data.get(key) is not None:
                return data.get(key)
        return None

    def _to_number(self, value: object) -> float:
        try:
            if isinstance(value, str) and "," in value:
                value = value.replace(".", "").replace(",", ".")
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _format_money(self, value: object) -> str:
        if self._is_empty_value(value):
            return "-"
        if isinstance(value, (int, float)):
            amount = float(value)
        else:
            try:
                text = str(value).strip()
                if "," in text:
                    text = text.replace(".", "").replace(",", ".")
                amount = float(text)
            except (TypeError, ValueError):
                return str(value)
        formatted = f"{amount:,.2f}"
        formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
        return f"$ {formatted}"

    def _display_generic_value(self, key: str, value: object) -> object:
        lowered = key.lower()
        if isinstance(value, bool):
            return "Si" if value else "No"
        if any(token in lowered for token in ("monto", "saldo", "importe", "total", "mora")):
            return self._format_money(value)
        if lowered.startswith("fecha_"):
            return value
        return value

    def _debt_status_badge(self, value: object) -> ft.Control:
        text = str(value or "Sin estado")
        normalized = text.upper()
        color = ft.Colors.BLUE_GREY_100
        text_color = ft.Colors.BLUE_GREY_900
        if normalized in {"VENCIDA", "VENCIDO", "EN_MORA", "MORA"}:
            color = ft.Colors.RED_100
            text_color = ft.Colors.RED_900
        elif normalized in {"EMITIDA", "EMITIDO", "PENDIENTE"}:
            color = ft.Colors.BLUE_50
            text_color = ft.Colors.BLUE_900
        elif normalized in {"CANCELADA", "CANCELADO", "PAGADA", "PAGADO"}:
            color = ft.Colors.GREEN_100
            text_color = ft.Colors.GREEN_900
        elif normalized in {"ANULADA", "ANULADO"}:
            color = ft.Colors.BLUE_GREY_100
            text_color = ft.Colors.BLUE_GREY_700
        return ft.Container(
            content=ft.Text(text, size=12, color=text_color),
            bgcolor=color,
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
        )

    def _parse_iso_date(self, value: object) -> str | None:
        if self._is_empty_value(value):
            return None
        try:
            return datetime.strptime(str(value).strip(), "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None

    def _parse_positive_float(self, value: object) -> float | None:
        try:
            parsed = float(str(value or "").replace(",", "."))
        except ValueError:
            return None
        return parsed if parsed > 0 else None

    def _parse_optional_int(self, value: object) -> int | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = int(raw)
        except ValueError:
            return None
        return parsed if parsed > 0 else None

    def _sum_field(self, rows: list[dict[str, Any]], key: str) -> float:
        return sum(self._to_number(row.get(key)) for row in rows)



    def _contacto_kind(self, contacto: dict[str, Any]) -> str:
        value = str(contacto.get("tipo_contacto") or "").upper()
        raw = str(self._contacto_value(contacto)).lower()
        if "MAIL" in value or "EMAIL" in value or "@" in raw:
            return "email"
        if any(token in value for token in ("TEL", "WHATSAPP", "CEL")):
            return "telefono"
        return "otro"

    def _contacto_value(self, contacto: dict[str, Any]) -> str:
        return str(contacto.get("valor_contacto") or contacto.get("valor") or contacto.get("contacto") or "Sin contacto informado.")

    def _principal_label(self, row: dict[str, Any]) -> str:
        return "Principal" if self._is_principal(row) else "Secundario"

    def _contactos_resumen(self, rows: object) -> ft.Control:
        contactos = self._dict_rows(rows)
        if not contactos:
            return ft.Text("Sin contactos registrados.")
        emails = [c for c in contactos if self._contacto_kind(c) == "email"]
        telefonos = [c for c in contactos if self._contacto_kind(c) == "telefono"]
        otros = [c for c in contactos if c not in emails and c not in telefonos]
        controls: list[ft.Control] = []
        for title, items in (("Emails", emails), ("Teléfonos", telefonos), ("Otros contactos", otros)):
            if items:
                controls.extend([ft.Text(title, weight=ft.FontWeight.W_600), self._card_list([self._info_card(title=self._principal_label(item), subtitle=self._contacto_value(item), principal=False) for item in items])])
        return ft.Column(controls=controls, spacing=8)

    def _telefonos_resumen(self, rows: object) -> ft.Control:
        telefonos = [
            contacto
            for contacto in self._dict_rows(rows)
            if self._contacto_kind(contacto) == "telefono"
        ]
        return self._contactos_lista(telefonos, "Sin teléfonos registrados.")

    def _mails_resumen(self, rows: object) -> ft.Control:
        mails = [
            contacto
            for contacto in self._dict_rows(rows)
            if self._contacto_kind(contacto) == "email"
        ]
        return self._contactos_lista(mails, "Sin mails registrados.")

    def _contactos_lista(
        self, contactos: list[dict[str, Any]], empty_message: str
    ) -> ft.Control:
        if not contactos:
            return ft.Text(empty_message)
        return self._card_list([
            self._info_card(
                title=self._principal_label(contacto),
                subtitle=self._contacto_value(contacto),
                principal=False,
                extra=contacto.get("observaciones"),
                action=ft.TextButton("Editar", on_click=lambda e, row=contacto: self._open_contacto_dialog(self._contacto_kind(row), e, row)),
            )
            for contacto in contactos
        ])

    def _open_contacto_dialog(
        self, kind: str, event: object = None, row: dict[str, Any] | None = None
    ) -> None:
        self.active_modal_kind = kind
        self.active_modal_row = row or {}
        self.modal_fields = {}
        self.modal_message = ft.Text("", visible=False)
        self.active_dialog = self._contacto_dialog(kind, self.active_modal_row)
        self._open_modal(event)

    def _open_domicilio_dialog(
        self, event: object = None, row: dict[str, Any] | None = None
    ) -> None:
        self.active_modal_kind = "domicilio"
        self.active_modal_row = row or {}
        self.modal_fields = {}
        self.modal_message = ft.Text("", visible=False)
        self.active_dialog = self._domicilio_dialog(self.active_modal_row)
        self._open_modal(event)

    def _open_modal(self, event: object = None) -> None:
        if self.active_dialog is None:
            return
        self.active_dialog.open = True
        page = getattr(event, "page", None)
        if page is None:
            return
        if hasattr(page, "open"):
            try:
                page.open(self.active_dialog)
                return
            except TypeError:
                pass
        page.dialog = self.active_dialog
        self._safe_update(page)

    def _close_modal(self, event: object = None) -> None:
        if self.active_dialog is not None:
            self.active_dialog.open = False
        self.active_modal_kind = None
        self.active_modal_row = {}
        self.modal_fields = {}
        page = getattr(event, "page", None)
        if page is not None:
            self._safe_update(page)

    def _contacto_dialog(self, kind: str, row: dict[str, Any]) -> ft.AlertDialog:
        title = "Editar mail" if row and kind == "email" else "Agregar mail" if kind == "email" else "Editar teléfono" if row else "Agregar teléfono"
        self.modal_fields = {
            "valor_contacto": ft.TextField(label="Mail" if kind == "email" else "Teléfono", value=self._contacto_value(row) if row else "", dense=True),
            "observaciones": ft.TextField(label="Observaciones", value=str(row.get("observaciones") or ""), dense=True, multiline=True),
            "es_principal": ft.Checkbox(label="Principal", value=self._is_principal(row)),
        }
        return ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Column(
                controls=[
                    self.modal_fields["valor_contacto"],
                    self.modal_fields["observaciones"],
                    self.modal_fields["es_principal"],
                    self.modal_message,
                ],
                spacing=8,
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._close_modal),
                ft.ElevatedButton("Guardar", on_click=lambda _: self._save_contacto(kind)),
            ],
        )

    def _basic_data_dialog(self) -> ft.AlertDialog:
        data = self.data
        self.modal_fields = {
            "tipo_persona": ft.TextField(label="Tipo persona", value=str(data.get("tipo_persona") or ""), dense=True),
            "estado_persona": ft.TextField(label="Estado", value=str(data.get("estado_persona") or ""), dense=True),
            "nombre": ft.TextField(label="Nombre", value=str(data.get("nombre") or ""), dense=True),
            "apellido": ft.TextField(label="Apellido", value=str(data.get("apellido") or ""), dense=True),
            "razon_social": ft.TextField(label="Razón social", value=str(data.get("razon_social") or ""), dense=True),
            "fecha_nacimiento": ft.TextField(label="Fecha nacimiento / constitución", value=str(data.get("fecha_nacimiento") or ""), dense=True),
            "documento_identidad": ft.TextField(label="Documento de identidad", value=self._documento_numero(self._documento_identidad_row(data)), dense=True),
            "identificacion_fiscal": ft.TextField(label="Identificación fiscal", value=self._documento_numero(self._identificacion_fiscal_row(data)) or str(data.get("cuit_cuil") or data.get("cuit") or data.get("cuil") or data.get("cdi") or ""), dense=True),
            "observaciones": ft.TextField(label="Observaciones", value=str(data.get("observaciones") or ""), dense=True, multiline=True, min_lines=2),
        }
        return ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar datos principales"),
            content=ft.Column(
                controls=[
                    self.modal_fields["tipo_persona"],
                    self.modal_fields["estado_persona"],
                    self.modal_fields["nombre"],
                    self.modal_fields["apellido"],
                    self.modal_fields["razon_social"],
                    self.modal_fields["fecha_nacimiento"],
                    self.modal_fields["documento_identidad"],
                    self.modal_fields["identificacion_fiscal"],
                    self.modal_fields["observaciones"],
                    self.modal_message,
                ],
                spacing=8,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._close_modal),
                ft.ElevatedButton("Guardar", on_click=self._save_basic_edit),
            ],
        )

    def _domicilio_dialog(self, row: dict[str, Any]) -> ft.AlertDialog:
        self.modal_fields = {
            "direccion": ft.TextField(label="Calle / dirección", value=str(row.get("direccion") or row.get("calle") or ""), dense=True),
            "localidad": ft.TextField(label="Localidad", value=str(row.get("localidad") or ""), dense=True),
            "provincia": ft.TextField(label="Provincia", value=str(row.get("provincia") or ""), dense=True),
            "pais": ft.TextField(label="País", value=str(row.get("pais") or ""), dense=True),
            "codigo_postal": ft.TextField(label="Código postal", value=str(row.get("codigo_postal") or ""), dense=True),
            "observaciones": ft.TextField(label="Observaciones", value=str(row.get("observaciones") or ""), dense=True, multiline=True),
            "es_principal": ft.Checkbox(label="Principal", value=self._is_principal(row)),
        }
        return ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar dirección" if row else "Agregar dirección"),
            content=ft.Column(
                controls=[
                    self.modal_fields["direccion"],
                    self.modal_fields["localidad"],
                    self.modal_fields["provincia"],
                    self.modal_fields["pais"],
                    self.modal_fields["codigo_postal"],
                    self.modal_fields["observaciones"],
                    self.modal_fields["es_principal"],
                    self.modal_message,
                ],
                spacing=8,
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._close_modal),
                ft.ElevatedButton("Guardar", on_click=self._save_domicilio),
            ],
        )

    def _modal_value(self, key: str) -> str:
        field = self.modal_fields[key]
        return str(getattr(field, "value", "") or "").strip()

    def _modal_bool(self, key: str) -> bool:
        return bool(getattr(self.modal_fields[key], "value", False))

    def _show_modal_error(self, message: str) -> None:
        self.modal_message.value = message
        self.modal_message.color = ft.Colors.RED_700
        self.modal_message.visible = True
        self._safe_update(self.modal_message)

    def _save_contacto(self, kind: str) -> None:
        valor = self._modal_value("valor_contacto")
        if not valor or (kind == "email" and "@" not in valor):
            self._show_modal_error("Ingresá un mail válido." if kind == "email" else "Ingresá un teléfono.")
            return
        row = self.active_modal_row or {}
        payload = {"tipo_contacto": "EMAIL" if kind == "email" else "TELEFONO", "valor_contacto": valor, "es_principal": self._modal_bool("es_principal"), "observaciones": self._modal_value("observaciones") or None}
        if row:
            version = row.get("version_registro")
            if version is None:
                self._show_modal_error("No se pudo editar este dato. Recargá la ficha e intentá nuevamente.")
                return
            result = self.api.actualizar_persona_contacto(self.id_persona, int(row.get("id_persona_contacto")), payload, int(version), op_id=str(uuid4()))
        else:
            result = self.api.crear_persona_contacto(self.id_persona, payload, op_id=str(uuid4()))
        self._finish_modal_save(result)

    def _save_domicilio(self, _) -> None:
        if not (self._modal_value("direccion") or self._modal_value("localidad")):
            self._show_modal_error("Ingresá al menos calle/dirección o localidad.")
            return
        row = self.active_modal_row or {}
        payload = {"tipo_domicilio": row.get("tipo_domicilio") or "REAL", "direccion": self._modal_value("direccion") or None, "localidad": self._modal_value("localidad") or None, "provincia": self._modal_value("provincia") or None, "pais": self._modal_value("pais") or None, "codigo_postal": self._modal_value("codigo_postal") or None, "es_principal": self._modal_bool("es_principal"), "observaciones": self._modal_value("observaciones") or None}
        if row:
            version = row.get("version_registro")
            if version is None:
                self._show_modal_error("No se pudo editar este dato. Recargá la ficha e intentá nuevamente.")
                return
            result = self.api.actualizar_persona_domicilio(self.id_persona, int(row.get("id_persona_domicilio")), payload, int(version), op_id=str(uuid4()))
        else:
            result = self.api.crear_persona_domicilio(self.id_persona, payload, op_id=str(uuid4()))
        self._finish_modal_save(result)

    def _finish_modal_save(self, result: Any) -> None:
        if not result.success:
            self._show_modal_error(result.error_message or "No se pudo guardar.")
            return
        refreshed = self.api.get_persona_detalle_integral(self.id_persona)
        if refreshed.success and isinstance(refreshed.data, dict):
            self.data = refreshed.data
        else:
            self._show_modal_error(
                "Los datos se guardaron, pero no se pudo recargar la ficha. Volvé a abrirla desde el listado."
            )
            return
        self._close_modal()
        self.on_navigate("parte_detail", id_persona=self.id_persona)

    def _domicilios_resumen(self, rows: object) -> ft.Control:
        domicilios = self._dict_rows(rows)
        if not domicilios:
            return ft.Text("Sin domicilios registrados.")
        return self._card_list([
            self._info_card(
                title=self._principal_label(domicilio),
                subtitle=self._format_address(domicilio),
                principal=False,
                extra=domicilio.get("observaciones"),
                action=ft.TextButton("Editar", on_click=lambda e, row=domicilio: self._open_domicilio_dialog(e, row)),
            )
            for domicilio in domicilios
        ])

    def _participaciones_resumen(self, rows: object) -> ft.Control:
        participaciones = self._dict_rows(rows)
        if not participaciones:
            return ft.Text("Sin roles ni participaciones.")

        ventas = [
            item
            for item in participaciones
            if self._participacion_bucket(item) == "Ventas"
        ]
        alquileres = [
            item
            for item in participaciones
            if self._participacion_bucket(item) == "Alquileres"
        ]
        otros = [
            item
            for item in participaciones
            if self._participacion_bucket(item) == "Otros"
        ]

        controls: list[ft.Control] = []
        if ventas:
            controls.append(self._participacion_table("Ventas", ventas))
        if alquileres:
            controls.append(self._participacion_table("Alquileres", alquileres))
        if otros:
            controls.append(self._participacion_table("Otros", otros))
        return ft.Column(controls=controls, spacing=10)

    def _participacion_table(
        self, title: str, rows: list[dict[str, Any]]
    ) -> ft.Control:
        table_rows = [self._participacion_table_row(item) for item in rows]
        return ft.Column(
            controls=[
                ft.Text(title, weight=ft.FontWeight.W_600),
                entity_table(
                    columns=[
                        ("Tipo", "tipo"),
                        ("Referencia", "referencia"),
                        ("Estado", "estado"),
                    ],
                    rows=table_rows,
                    actions=lambda row: [self._participacion_nav_action(row["_source"])],
                ),
            ],
            spacing=6,
        )

    def _participacion_table_row(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "tipo": self._participacion_tipo_label(
                item.get("tipo_relacion") or item.get("tipo_origen")
            ),
            "referencia": self._participacion_referencia(item),
            "estado": self._participacion_estado(item),
            "_source": item,
        }

    def _participacion_rol_label(self, item: dict[str, Any]) -> str:
        return self._friendly_label(
            item.get("nombre_rol")
            or item.get("rol")
            or item.get("codigo_rol")
            or "Participación"
        )

    def _participacion_referencia(self, item: dict[str, Any]) -> str:
        return str(
            item.get("descripcion_origen")
            or item.get("codigo_origen")
            or item.get("codigo_venta")
            or item.get("codigo_contrato")
            or item.get("codigo")
            or item.get("id_relacion")
            or item.get("id_origen")
            or "-"
        )

    def _participacion_estado(self, item: dict[str, Any]) -> str:
        return str(
            item.get("estado")
            or item.get("estado_relacion")
            or item.get("estado_origen")
            or "-"
        )

    def _participacion_bucket(self, item: dict[str, Any]) -> str:
        tipo = str(item.get("tipo_relacion") or item.get("tipo_origen") or "").lower()
        text = " ".join(
            str(item.get(key) or "").lower()
            for key in ("tipo_relacion", "tipo_origen", "descripcion_origen", "codigo_rol")
        )
        if tipo in self._participacion_tipos_venta() or "venta" in text or "reserva" in text or "escritur" in text or "cesion" in text or "cesión" in text:
            return "Ventas"
        if tipo in self._participacion_tipos_alquiler() or "alquiler" in text or "locat" in text or "contrato" in text:
            return "Alquileres"
        return "Otros"

    def _participacion_tipos_venta(self) -> set[str]:
        return {
            "venta",
            "reserva_venta",
            "cesion",
            "escrituracion",
            "rescision_venta",
        }

    def _participacion_tipos_alquiler(self) -> set[str]:
        return {
            "contrato_alquiler",
            "solicitud_alquiler",
            "reserva_locativa",
            "rescision_finalizacion_alquiler",
            "entrega_restitucion_inmueble",
        }

    def _participacion_tipo_label(self, value: object) -> str:
        labels = {
            "reserva_venta": "Reserva de venta",
            "venta": "Venta",
            "contrato_alquiler": "Contrato de alquiler",
            "solicitud_alquiler": "Solicitud de alquiler",
            "reserva_locativa": "Reserva locativa",
            "cesion": "Cesión",
            "escrituracion": "Escrituración",
            "rescision_venta": "Rescisión de venta",
            "rescision_finalizacion_alquiler": "Rescisión/finalización de alquiler",
            "entrega_restitucion_inmueble": "Entrega/restitución",
        }
        normalized = str(value or "").strip().lower()
        return labels.get(normalized, self._friendly_label(value))

    def _participacion_nav_action(self, item: dict[str, Any]) -> ft.Control:
        tipo = str(item.get("tipo_relacion") or item.get("tipo_origen") or "").lower()
        route: str | None = None
        params: dict[str, Any] = {}
        if tipo == "venta":
            id_venta = self._parse_optional_int(
                item.get("id_venta") or item.get("id_origen") or item.get("id_relacion")
            )
            if id_venta is not None:
                route = "venta_detail"
                params = {"id_venta": id_venta}
        elif tipo == "contrato_alquiler":
            id_contrato = self._parse_optional_int(
                item.get("id_contrato_alquiler")
                or item.get("id_origen")
                or item.get("id_relacion")
            )
            if id_contrato is not None:
                route = "contrato_detail"
                params = {"id_contrato_alquiler": id_contrato}

        if route is None:
            return ft.TextButton("Ver", disabled=True)
        return ft.TextButton(
            "Ver",
            on_click=lambda _, route=route, params=params: self.on_navigate(
                route, **params
            ),
        )

    def _participacion_label(self, item: dict[str, Any]) -> str:
        rol = self._participacion_rol_label(item)
        origen = self._participacion_origen_label(item)
        inmueble = item.get("lote") or item.get("unidad") or item.get("inmueble")
        label = f"{rol} en {origen}"
        if inmueble:
            label = f"{label} — {inmueble}"
        return label


    def _participacion_origen_label(self, item: dict[str, Any]) -> str:
        raw = (
            item.get("descripcion_origen")
            or item.get("codigo_venta")
            or item.get("codigo_contrato")
            or item.get("codigo")
            or item.get("tipo_relacion")
            or item.get("tipo_origen")
            or "origen asociado"
        )
        normalized = str(raw).strip().lower()
        labels = {
            "reserva_venta": "reserva de venta",
            "venta": "venta",
            "contrato_alquiler": "contrato de alquiler",
            "solicitud_alquiler": "solicitud de alquiler",
            "reserva_locativa": "reserva locativa",
            "cesion": "cesión",
            "escrituracion": "escrituración",
            "rescision_venta": "rescisión de venta",
            "rescision_finalizacion_alquiler": "rescisión/finalización de alquiler",
            "entrega_restitucion_inmueble": "entrega/restitución",
        }
        return labels.get(normalized, self._friendly_label(raw))

    def _participaciones_table(self, rows: object) -> ft.Control:
        rows = self._dict_rows(rows)
        if not rows:
            return ft.Text("Sin roles ni participaciones.")
        return entity_table(
            columns=[
                ("Tipo", "tipo_relacion"),
                ("Rol", "codigo_rol"),
                ("Desde", "fecha_desde"),
                ("Hasta", "fecha_hasta"),
            ],
            rows=rows,
        )

    def _estado_cuenta_origen_panel(
        self,
        tipo_origen: str,
        origins: list[dict[str, Any]],
        empty_message: str,
    ) -> ft.Control:
        result_area = ft.Container(content=ft.Text("Seleccione un origen."))

        def load_origin(row: dict[str, Any]):
            def handler(_) -> None:
                id_origen = self._parse_optional_int(row.get("id_origen"))
                if id_origen is None:
                    result_area.content = error_state(
                        "No se pudo identificar el origen seleccionado."
                    )
                    result_area.update()
                    return
                result = self.api.get_estado_cuenta_persona(
                    self.id_persona,
                    tipo_origen=tipo_origen,
                    id_origen=id_origen,
                )
                result_area.content = ft.Column(
                    controls=self._estado_cuenta_controls(result),
                    spacing=12,
                )
                result_area.update()

            return handler

        if not origins:
            return ft.Column(controls=[ft.Text(empty_message)], spacing=12)

        rows = [
            {
                "id_origen": item.get("id_origen"),
                "origen": item.get("descripcion_origen")
                or item.get("codigo")
                or item.get("codigo_contrato")
                or item.get("codigo_venta")
                or item.get("label")
                or "Origen asociado",
                "tipo": item.get("tipo_origen") or tipo_origen,
                "saldo": item.get("saldo_total") or item.get("saldo_pendiente"),
            }
            for item in origins
        ]

        return ft.Column(
            controls=[
                entity_table(
                    columns=[
                        ("Origen", "origen"),
                        ("Tipo", "tipo"),
                        ("Saldo", "saldo"),
                    ],
                    rows=rows,
                    actions=lambda row: [
                        ft.TextButton("Ver estado", on_click=load_origin(row))
                    ],
                ),
                result_area,
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _related_origins(
        self, data: dict[str, Any], expected_tipo: str
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        usos = (
            data.get("usos_transversales")
            if isinstance(data.get("usos_transversales"), dict)
            else {}
        )

        if expected_tipo == "contrato_alquiler":
            for item in self._dict_rows(usos.get("contratos_locativos")):
                rows.append(self._origin_from_item(item, expected_tipo))
        if expected_tipo == "venta":
            for item in self._dict_rows(usos.get("comprador_ventas")):
                rows.append(self._origin_from_item(item, expected_tipo))

        for item in self._dict_rows(data.get("participaciones")):
            tipo = item.get("tipo_relacion") or item.get("tipo_origen")
            if tipo == expected_tipo:
                rows.append(self._origin_from_item(item, expected_tipo))

        unique: dict[int, dict[str, Any]] = {}
        fallback: list[dict[str, Any]] = []
        for row in rows:
            id_origen = self._parse_optional_int(row.get("id_origen"))
            if id_origen is None:
                fallback.append(row)
            else:
                unique.setdefault(id_origen, row)
        return list(unique.values()) + fallback

    def _origin_from_item(
        self, item: dict[str, Any], expected_tipo: str
    ) -> dict[str, Any]:
        id_origen = (
            item.get("id_origen")
            or item.get("id_relacion")
            or item.get("id_contrato_alquiler")
            or item.get("id_venta")
        )
        return {
            "id_origen": id_origen,
            "tipo_origen": item.get("tipo_origen")
            or item.get("tipo_relacion")
            or expected_tipo,
            "descripcion_origen": item.get("descripcion_origen")
            or item.get("codigo_contrato")
            or item.get("codigo_venta")
            or item.get("codigo")
            or item.get("nombre")
            or item.get("label"),
            "saldo_total": item.get("saldo_total") or item.get("saldo_pendiente"),
        }

    def _usos_transversales(self, data: dict[str, Any]) -> ft.Control:
        raw_usos = data.get("usos_transversales") or {}
        usos = raw_usos if isinstance(raw_usos, dict) else {}
        rows = [
            ("Ventas como comprador", len(usos.get("comprador_ventas") or [])),
            ("Contratos locativos", len(usos.get("contratos_locativos") or [])),
            ("Servicios responsable", len(usos.get("servicios_responsable") or [])),
        ]
        return key_value_grid(rows)

    def _simple_table(self, rows: object) -> ft.Control:
        rows = self._dict_rows(rows)
        if not rows:
            return ft.Text("Sin registros.")
        keys = [key for key in rows[0].keys() if not self._is_technical_id(key)][:6]
        if not keys:
            return ft.Text("Sin campos visibles.")
        return entity_table(columns=[(key, key) for key in keys], rows=rows)

    def _documentos_table(self, rows: object) -> ft.Control:
        documentos = self._dict_rows(rows)
        if not documentos:
            return ft.Text("Sin documentos registrados.")
        return self._card_list(
            [
                self._info_card(
                    title=self._label_documento_tipo(
                        documento.get("tipo_documento")
                        or documento.get("tipo_documento_persona")
                    ),
                    subtitle=self._join_secondary(
                        documento.get("numero_documento"),
                        documento.get("pais_emision"),
                    )
                    or "Sin numero informado.",
                    principal=self._is_principal(documento),
                )
                for documento in documentos
            ]
        )

    def _contactos_table(self, rows: object) -> ft.Control:
        contactos = self._dict_rows(rows)
        if not contactos:
            return ft.Text("Sin contactos registrados.")
        return self._card_list(
            [
                self._info_card(
                    title=self._contacto_title(contacto),
                    subtitle=(
                        contacto.get("valor_contacto")
                        or contacto.get("valor")
                        or contacto.get("contacto")
                        or "Sin contacto informado."
                    ),
                    principal=self._is_principal(contacto),
                )
                for contacto in contactos
            ]
        )

    def _domicilios_table(self, rows: object) -> ft.Control:
        domicilios = self._dict_rows(rows)
        if not domicilios:
            return ft.Text("Sin domicilios registrados.")
        return self._card_list(
            [
                self._info_card(
                    title=self._label_domicilio_tipo(domicilio.get("tipo_domicilio")),
                    subtitle=self._format_address(domicilio),
                    principal=self._is_principal(domicilio),
                    extra=domicilio.get("observaciones"),
                )
                for domicilio in domicilios
            ]
        )

    def _card_list(self, controls: list[ft.Control]) -> ft.Control:
        return ft.Column(controls=controls, spacing=8)

    def _info_card(
        self,
        *,
        title: object,
        subtitle: object,
        principal: bool = False,
        extra: object = None,
        action: ft.Control | None = None,
    ) -> ft.Control:
        header_controls: list[ft.Control] = [
            ft.Text(str(title or "Sin tipo"), weight=ft.FontWeight.W_600)
        ]
        if principal:
            header_controls.append(self._principal_badge())
        if action is not None:
            header_controls.extend([ft.Container(expand=True), action])

        body_controls: list[ft.Control] = [
            ft.Row(
                controls=header_controls,
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(str(subtitle or "-"), selectable=True),
        ]
        if extra not in (None, ""):
            body_controls.append(
                ft.Text(str(extra), size=12, color=ft.Colors.BLUE_GREY_700)
            )

        return ft.Container(
            content=ft.Column(controls=body_controls, spacing=4),
            padding=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
            bgcolor=ft.Colors.WHITE,
        )

    def _principal_badge(self) -> ft.Control:
        return ft.Container(
            content=ft.Text("Principal", size=11, color=ft.Colors.GREEN_900),
            bgcolor=ft.Colors.GREEN_100,
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
        )

    def _contacto_title(self, contacto: dict[str, Any]) -> str:
        label = self._label_contacto_tipo(contacto.get("tipo_contacto"))
        if self._is_principal(contacto):
            return f"{label} principal"
        return label

    def _label_documento_tipo(self, value: object) -> str:
        return self._friendly_label(value)

    def _label_contacto_tipo(self, value: object) -> str:
        labels = {
            "EMAIL": "Email",
            "E_MAIL": "Email",
            "MAIL": "Email",
            "TELEFONO": "Teléfono",
            "TEL": "Teléfono",
            "WHATSAPP": "WhatsApp",
        }
        return self._mapped_label(value, labels)

    def _label_domicilio_tipo(self, value: object) -> str:
        labels = {
            "REAL": "Domicilio real",
            "LEGAL": "Domicilio legal",
            "FISCAL": "Domicilio fiscal",
            "POSTAL": "Domicilio postal",
        }
        return self._mapped_label(value, labels)

    def _mapped_label(self, value: object, labels: dict[str, str]) -> str:
        text = str(value or "").strip()
        if not text:
            return "Sin tipo"
        normalized = text.upper().replace(" ", "_")
        return labels.get(normalized, self._friendly_label(text))

    def _friendly_label(self, value: object) -> str:
        text = str(value or "").strip()
        if not text:
            return "Sin tipo"
        return text.replace("_", " ").capitalize()

    def _format_address(self, domicilio: dict[str, Any]) -> str:
        parts = [
            domicilio.get("direccion") or domicilio.get("calle") or domicilio.get("domicilio"),
            domicilio.get("localidad"),
            domicilio.get("provincia"),
            domicilio.get("pais"),
        ]
        address = ", ".join(str(part) for part in parts if part not in (None, ""))
        postal = domicilio.get("codigo_postal")
        if postal not in (None, ""):
            address = f"{address} ({postal})" if address else f"({postal})"
        return address or "Sin direccion informada."

    def _is_principal(self, row: dict[str, Any]) -> bool:
        value = row.get("es_principal", row.get("principal"))
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"true", "1", "si", "sí", "s"}

    def _dict_rows(self, rows: object) -> list[dict[str, Any]]:
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def _display_name(self, data: dict[str, Any]) -> str:
        if data.get("display_name"):
            return str(data["display_name"])
        if data.get("razon_social"):
            return str(data["razon_social"])
        parts = [data.get("nombre"), data.get("apellido")]
        value = " ".join(part for part in parts if part)
        return value or "Ficha de parte"

    def _join_secondary(self, *values: object) -> str:
        return " · ".join(str(value) for value in values if value not in (None, ""))

    def _documento_principal(self, data: dict[str, Any]) -> object:
        principal = self._documento_identidad_row(data)
        return (
            principal.get("numero_documento")
            or principal.get("documento")
            or principal.get("valor")
        ) if principal else None

    def _documento_identidad_row(self, data: dict[str, Any]) -> dict[str, Any] | None:
        documentos = self._dict_rows(data.get("documentos"))
        identidad = [doc for doc in documentos if str(doc.get("tipo_documento") or "").upper() not in {"CUIT", "CUIL", "CDI"}]
        if not identidad:
            return None
        return next((item for item in identidad if item.get("es_principal") or item.get("principal")), identidad[0])

    def _identificacion_fiscal_row(self, data: dict[str, Any]) -> dict[str, Any] | None:
        documentos = self._dict_rows(data.get("documentos"))
        return next((doc for doc in documentos if str(doc.get("tipo_documento") or "").upper() in {"CUIT", "CUIL", "CDI"}), None)

    def _documento_numero(self, row: dict[str, Any] | None) -> str:
        if not row:
            return ""
        return str(row.get("numero_documento") or row.get("documento") or row.get("valor") or "").strip()

    def _save_documento_principal(self, row: dict[str, Any] | None, numero: str, tipo: str) -> Any:
        if not numero and row is None:
            return ApiResult(True)
        payload = {
            "tipo_documento": str((row or {}).get("tipo_documento") or tipo).upper(),
            "numero_documento": numero,
            "pais_emision": (row or {}).get("pais_emision"),
            "es_principal": bool((row or {}).get("es_principal", tipo == "DNI")),
            "observaciones": (row or {}).get("observaciones"),
        }
        if row:
            version = row.get("version_registro")
            if version is None:
                return ApiResult(False, error_message="No se pudo editar el documento. Recargá la ficha e intentá nuevamente.")
            return self.api.actualizar_persona_documento(self.id_persona, int(row.get("id_persona_documento")), payload, int(version), op_id=str(uuid4()))
        return self.api.crear_persona_documento(self.id_persona, payload, op_id=str(uuid4()))

    def _friendly_save_error(self, result: Any, fallback: str) -> str:
        if getattr(result, "status_code", None) in {409, 412} or getattr(result, "error_code", None) == "CONCURRENCY_ERROR":
            return "Otro usuario modificó estos datos. Recargá la ficha e intentá nuevamente."
        return getattr(result, "error_message", None) or fallback

    def _contacto_principal(self, data: dict[str, Any]) -> object:
        contactos = self._dict_rows(data.get("contactos"))
        if not contactos:
            return None
        principal = next(
            (
                item
                for item in contactos
                if item.get("es_principal") or item.get("principal")
            ),
            contactos[0],
        )
        return (
            principal.get("valor_contacto")
            or principal.get("valor")
            or principal.get("contacto")
        )

    def _is_technical_id(self, key: str) -> bool:
        return key.startswith("id_") or key in {"uid_global", "version_registro"}
