from datetime import date, datetime
from typing import Any

import flet as ft

from app.api_client import ApiClient
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

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.TextButton(
                            "Volver al listado",
                            on_click=lambda _: self.on_navigate("partes"),
                        ),
                    ]
                ),
                self._header_card(data),
                detail_tabs(
                    [
                        (
                            "Resumen",
                            [
                                detail_section(
                                    "Informacion general", [self._datos_base(data)]
                                ),
                                detail_section(
                                    "Resumen financiero de parte",
                                    [self._estado_financiero(data)],
                                ),
                            ],
                        ),
                        (
                            "Documentacion y contacto",
                            [
                                detail_section(
                                    "Documentos",
                                    [self._documentos_table(data.get("documentos", []))],
                                ),
                                detail_section(
                                    "Contactos",
                                    [self._contactos_table(data.get("contactos", []))],
                                ),
                                detail_section(
                                    "Domicilios",
                                    [self._domicilios_table(data.get("domicilios", []))],
                                ),
                            ],
                        ),
                        (
                            "Roles / participaciones",
                            [
                                detail_section(
                                    "Roles / participaciones",
                                    [
                                        self._participaciones_table(
                                            data.get("participaciones", [])
                                        )
                                    ],
                                )
                            ],
                        ),
                        (
                            "Estado de cuenta",
                            self._estado_cuenta_tab(data, estado_cuenta_result),
                        ),
                        (
                            "Usos transversales",
                            [
                                detail_section(
                                    "Usos transversales",
                                    [self._usos_transversales(data)],
                                ),
                                detail_section(
                                    "Obligaciones del detalle integral",
                                    [self._obligaciones_table(data)],
                                ),
                            ],
                        ),
                    ]
                ),
            ],
            spacing=14,
            expand=True,
        )

    def _header_card(self, data: dict[str, Any]) -> ft.Control:
        secondary = self._join_secondary(
            data.get("tipo_persona"),
            self._documento_principal(data),
            data.get("cuit_cuil"),
            self._contacto_principal(data),
        )
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                self._display_name(data),
                                size=24,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Container(expand=True),
                            status_badge(data.get("estado_persona")),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(secondary or "Sin datos principales.", size=12, color=ft.Colors.BLUE_GREY_700),
                ],
                spacing=4,
            ),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
        )

    def _datos_base(self, data: dict[str, Any]) -> ft.Control:
        razon_social = data.get("razon_social")
        display_name = self._display_name(data)
        razon_social_complementaria = (
            razon_social if razon_social and str(razon_social) != display_name else None
        )
        return self._filtered_key_value_grid(
            [
                ("Razon social", razon_social_complementaria),
                ("Fecha nacimiento", data.get("fecha_nacimiento")),
                ("Fecha alta", data.get("fecha_alta")),
                ("Codigo", data.get("codigo_persona")),
                ("Observaciones", data.get("observaciones")),
            ]
        )

    def _estado_financiero(self, data: dict[str, Any]) -> ft.Control:
        raw_resumen = data.get("resumen_financiero") or {}
        resumen = raw_resumen if isinstance(raw_resumen, dict) else {}
        return ft.Row(
            controls=[
                self._summary_card(
                    "Cantidad de obligaciones",
                    self._format_count(resumen.get("cantidad_obligaciones")),
                ),
                self._summary_card(
                    "Saldo pendiente total",
                    self._format_money(resumen.get("saldo_pendiente_total")),
                    accent=True,
                ),
                self._summary_card(
                    "Saldo pendiente responsabilidad",
                    self._format_money(
                        resumen.get("saldo_pendiente_responsabilidad")
                    ),
                    accent=True,
                ),
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

    def _estado_cuenta_tab(self, data: dict[str, Any], result) -> list[ft.Control]:
        return [
            detail_tabs(
                [
                    (
                        "General",
                        [
                            detail_section(
                                "Estado de cuenta general",
                                self._estado_cuenta_controls(result),
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

    def _estado_cuenta_controls(self, result) -> list[ft.Control]:
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
            return [self._deudas_operativas_table(rows)]

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
                    self._deudas_operativas_table(obligaciones),
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
                controls.append(self._deudas_operativas_table(extra_rows))

        return controls

    def _deudas_operativas_table(
        self, obligaciones: list[dict[str, Any]]
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
                        ft.TextButton("Ver detalle", on_click=show_detail(row))
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
            "Simulacion de pago",
            [
                ft.Text(
                    "Simulacion global por persona: no registra pagos ni modifica saldos.",
                    size=12,
                ),
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
            label="Fecha corte",
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

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[monto, fecha_corte],
                    spacing=10,
                    wrap=True,
                ),
                ft.ElevatedButton("Simular", on_click=on_submit),
                ft.Text("Resultado de simulacion", weight=ft.FontWeight.W_600),
                result_area,
            ],
            spacing=10,
        )

    def _simulacion_result(self, payload: object) -> ft.Control:
        if isinstance(payload, list):
            rows = self._dict_rows(payload)
            if not rows:
                return ft.Text("La simulacion no devolvio obligaciones afectadas.")
            return self._friendly_generic_table(rows, empty_message="Sin deudas simuladas.")

        if not isinstance(payload, dict):
            return ft.Text("La simulacion devolvio una respuesta inesperada.")

        detalle = self._dict_rows(payload.get("detalle"))
        composiciones = self._flatten_composiciones(detalle, [])
        controls: list[ft.Control] = [
            key_value_grid(
                [
                    ("Fecha corte", payload.get("fecha_corte")),
                    (
                        "Total simulado",
                        self._format_money(payload.get("total_deuda_considerada")),
                    ),
                    ("Monto ingresado", self._format_money(payload.get("monto_ingresado"))),
                    ("Monto aplicado", self._format_money(payload.get("monto_aplicado"))),
                    ("Remanente", self._format_money(payload.get("remanente"))),
                    (
                        "Mora / punitorio",
                        self._format_money(self._sum_field(detalle, "mora_calculada")),
                    ),
                ]
            )
        ]

        if detalle:
            controls.extend(
                [
                    ft.Text("Deudas simuladas", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Concepto", "concepto"),
                            ("Origen", "origen"),
                            ("Saldo", "saldo_pendiente"),
                            ("Mora", "mora_calculada"),
                            ("Total a cubrir", "total_a_cubrir"),
                            ("Aplicado", "monto_aplicado"),
                            ("Saldo simulado", "saldo_restante_simulado"),
                        ],
                        rows=[
                            {
                                **item,
                                "concepto": self._deuda_label(item),
                                "origen": self._origen_label(item),
                                "saldo_pendiente": self._format_money(
                                    item.get("saldo_pendiente")
                                ),
                                "mora_calculada": self._format_money(
                                    item.get("mora_calculada")
                                ),
                                "total_a_cubrir": self._format_money(
                                    item.get("total_a_cubrir")
                                ),
                                "monto_aplicado": self._format_money(
                                    item.get("monto_aplicado")
                                ),
                                "saldo_restante_simulado": self._format_money(
                                    item.get("saldo_restante_simulado")
                                ),
                            }
                            for item in detalle
                        ],
                    ),
                ]
            )
        else:
            controls.append(ft.Text("Sin deudas afectadas."))

        if composiciones:
            controls.extend(
                [
                    ft.Text("Detalle de conceptos afectados", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Concepto", "concepto"),
                            ("Importe", "importe_componente"),
                            ("Saldo", "saldo_componente"),
                        ],
                        rows=[
                            {
                                **item,
                                "concepto": self._concepto_label(item),
                                "importe_componente": self._format_money(
                                    item.get("importe_componente")
                                ),
                                "saldo_componente": self._format_money(
                                    item.get("saldo_componente")
                                ),
                            }
                            for item in composiciones
                        ],
                    ),
                ]
            )

        if len(controls) == 1 and payload:
            rows = [payload]
            return self._friendly_generic_table(rows)

        return ft.Column(controls=controls, spacing=10)

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
    ) -> ft.Control:
        header_controls: list[ft.Control] = [
            ft.Text(str(title or "Sin tipo"), weight=ft.FontWeight.W_600)
        ]
        if principal:
            header_controls.append(self._principal_badge())

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
        if text.isupper() and "_" not in text:
            return text
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
        documentos = self._dict_rows(data.get("documentos"))
        if not documentos:
            return None
        principal = next(
            (
                item
                for item in documentos
                if item.get("es_principal") or item.get("principal")
            ),
            documentos[0],
        )
        return (
            principal.get("numero_documento")
            or principal.get("documento")
            or principal.get("valor")
        )

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
