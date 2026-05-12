from datetime import date
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
                        ft.Container(expand=True),
                        status_badge(data.get("estado_persona")),
                    ]
                ),
                ft.Text(self._display_name(data), size=30, weight=ft.FontWeight.W_700),
                self._header_card(data),
                detail_tabs(
                    [
                        (
                            "Resumen",
                            [
                                detail_section(
                                    "Datos base ampliados", [self._datos_base(data)]
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
                                    [self._simple_table(data.get("documentos", []))],
                                ),
                                detail_section(
                                    "Contactos",
                                    [self._simple_table(data.get("contactos", []))],
                                ),
                                detail_section(
                                    "Domicilios",
                                    [self._simple_table(data.get("domicilios", []))],
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
        return ft.Container(
            content=key_value_grid(
                [
                    ("Parte", self._display_name(data)),
                    ("Tipo de parte", data.get("tipo_persona")),
                    ("Estado", data.get("estado_persona")),
                    ("Documento principal", self._documento_principal(data)),
                    ("CUIT/CUIL", data.get("cuit_cuil")),
                    ("Contacto principal", self._contacto_principal(data)),
                ]
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=6,
        )

    def _datos_base(self, data: dict[str, Any]) -> ft.Control:
        return key_value_grid(
            [
                ("Tipo", data.get("tipo_persona")),
                ("Codigo", data.get("codigo_persona")),
                ("Nombre", data.get("nombre")),
                ("Apellido", data.get("apellido")),
                ("Razon social", data.get("razon_social")),
                ("CUIT/CUIL", data.get("cuit_cuil")),
                ("Estado", data.get("estado_persona")),
                ("Observaciones", data.get("observaciones")),
            ]
        )

    def _estado_financiero(self, data: dict[str, Any]) -> ft.Control:
        raw_resumen = data.get("resumen_financiero") or {}
        resumen = raw_resumen if isinstance(raw_resumen, dict) else {}
        return key_value_grid(
            [
                ("Cantidad obligaciones", resumen.get("cantidad_obligaciones")),
                ("Saldo pendiente total", resumen.get("saldo_pendiente_total")),
                (
                    "Saldo pendiente responsabilidad",
                    resumen.get("saldo_pendiente_responsabilidad"),
                ),
            ]
        )

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
                    or "No se pudo cargar el estado de cuenta formal."
                )
            ]

        payload = result.data
        if isinstance(payload, list):
            rows = self._dict_rows(payload)
            if not rows:
                return [ft.Text("Sin deuda registrada")]
            return [self._generic_table(rows)]

        if not isinstance(payload, dict):
            return [ft.Text("Sin deuda registrada")]

        resumen = self._as_dict(payload.get("resumen"))
        grupos = self._dict_rows(payload.get("grupos_deuda"))
        obligaciones = self._dict_rows(payload.get("obligaciones"))
        relaciones = self._flatten_relaciones(grupos)
        composiciones = self._flatten_composiciones(obligaciones, relaciones)

        controls: list[ft.Control] = [
            ft.Text("Resumen general", weight=ft.FontWeight.W_600),
            self._estado_cuenta_resumen(payload, resumen),
        ]

        if self._estado_cuenta_sin_deuda(resumen, grupos, obligaciones):
            controls.append(ft.Text("Sin deuda registrada"))
            return controls

        if grupos:
            controls.extend(
                [
                    ft.Text("Grupos de deuda", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Grupo", "grupo_origen_deuda"),
                            ("Saldo total", "saldo_total"),
                            ("Relaciones", "cantidad_relaciones"),
                        ],
                        rows=[self._grupo_row(grupo) for grupo in grupos],
                    ),
                ]
            )

        if relaciones:
            controls.extend(
                [
                    ft.Text("Relaciones generadoras", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Grupo", "grupo_origen_deuda"),
                            ("Tipo origen", "tipo_origen"),
                            ("Descripcion", "descripcion_origen"),
                            ("Saldo", "saldo_total"),
                            ("Obligaciones", "cantidad_obligaciones"),
                        ],
                        rows=relaciones,
                    ),
                ]
            )

        if obligaciones:
            controls.extend(
                [
                    ft.Text("Obligaciones", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Origen", "tipo_origen"),
                            ("Estado", "estado_obligacion"),
                            ("Vencimiento", "fecha_vencimiento"),
                            ("Saldo", "saldo_pendiente"),
                            ("Mora", "mora_calculada"),
                            ("Total con mora", "total_con_mora"),
                        ],
                        rows=obligaciones,
                    ),
                ]
            )

        if composiciones:
            controls.extend(
                [
                    ft.Text("Composiciones", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Concepto", "codigo_concepto_financiero"),
                            ("Importe", "importe_componente"),
                            ("Saldo", "saldo_componente"),
                            ("Estado", "estado_composicion_obligacion"),
                        ],
                        rows=composiciones,
                    ),
                ]
            )

        if len(controls) == 2:
            extra_rows = self._dict_rows(payload.get("items"))
            if extra_rows:
                controls.append(self._generic_table(extra_rows))

        return controls

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
            return self._generic_table(rows)

        if not isinstance(payload, dict):
            return ft.Text("La simulacion devolvio una respuesta inesperada.")

        detalle = self._dict_rows(payload.get("detalle"))
        composiciones = self._flatten_composiciones(detalle, [])
        controls: list[ft.Control] = [
            key_value_grid(
                [
                    ("Fecha corte", payload.get("fecha_corte")),
                    ("Total simulado", payload.get("total_deuda_considerada")),
                    ("Monto ingresado", payload.get("monto_ingresado")),
                    ("Monto aplicado", payload.get("monto_aplicado")),
                    ("Remanente", payload.get("remanente")),
                    ("Mora / punitorio", self._sum_field(detalle, "mora_calculada")),
                ]
            )
        ]

        if detalle:
            controls.extend(
                [
                    ft.Text("Obligaciones afectadas", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Saldo", "saldo_pendiente"),
                            ("Mora", "mora_calculada"),
                            ("Total a cubrir", "total_a_cubrir"),
                            ("Aplicado", "monto_aplicado"),
                            ("Saldo simulado", "saldo_restante_simulado"),
                        ],
                        rows=detalle,
                    ),
                ]
            )
        else:
            controls.append(ft.Text("Sin obligaciones afectadas."))

        if composiciones:
            controls.extend(
                [
                    ft.Text("Composiciones afectadas", weight=ft.FontWeight.W_600),
                    entity_table(
                        columns=[
                            ("Concepto", "codigo_concepto_financiero"),
                            ("Importe", "importe_componente"),
                            ("Saldo", "saldo_componente"),
                        ],
                        rows=composiciones,
                    ),
                ]
            )

        if len(controls) == 1 and payload:
            rows = [payload]
            return self._generic_table(rows)

        return ft.Column(controls=controls, spacing=10)

    def _estado_cuenta_resumen(
        self, payload: dict[str, Any], resumen: dict[str, Any]
    ) -> ft.Control:
        return key_value_grid(
            [
                ("Fecha corte", payload.get("fecha_corte")),
                (
                    "Saldo total",
                    self._first_present(
                        resumen, ["saldo_total", "saldo_pendiente_total"]
                    ),
                ),
                ("Saldo vencido", resumen.get("saldo_vencido")),
                ("Saldo futuro", resumen.get("saldo_futuro")),
                ("Mora calculada", resumen.get("mora_calculada")),
                ("Total con mora", resumen.get("total_con_mora")),
                ("Saldo locativo", resumen.get("saldo_locativo")),
                ("Saldo venta", resumen.get("saldo_venta")),
                ("Saldo trasladados", resumen.get("saldo_trasladados")),
                ("Saldo otros", resumen.get("saldo_otros")),
            ]
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

    def _grupo_row(self, grupo: dict[str, Any]) -> dict[str, Any]:
        row = dict(grupo)
        row["cantidad_relaciones"] = len(self._dict_rows(grupo.get("relaciones")))
        return row

    def _generic_table(self, rows: list[dict[str, Any]]) -> ft.Control:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys and not isinstance(row.get(key), (dict, list)):
                    keys.append(key)
                if len(keys) >= 6:
                    break
            if len(keys) >= 6:
                break
        if not keys:
            return ft.Text("Sin deuda registrada")
        return entity_table(columns=[(key, key) for key in keys], rows=rows)

    def _as_dict(self, value: object) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _first_present(self, data: dict[str, Any], keys: list[str]) -> object:
        for key in keys:
            if data.get(key) is not None:
                return data.get(key)
        return None

    def _to_number(self, value: object) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

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
