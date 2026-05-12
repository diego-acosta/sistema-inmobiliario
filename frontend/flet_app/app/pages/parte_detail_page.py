from datetime import date
from typing import Any

import flet as ft

from app.api_client import ApiClient
from app.components.detail_section import detail_section, key_value_grid
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
                detail_section("Datos base", [self._datos_base(data)]),
                detail_section(
                    "Documentos", [self._simple_table(data.get("documentos", []))]
                ),
                detail_section(
                    "Contactos", [self._simple_table(data.get("contactos", []))]
                ),
                detail_section(
                    "Domicilios", [self._simple_table(data.get("domicilios", []))]
                ),
                detail_section(
                    "Roles / participaciones",
                    [self._participaciones_table(data.get("participaciones", []))],
                ),
                detail_section(
                    "Resumen financiero de parte", [self._estado_financiero(data)]
                ),
                detail_section(
                    "Estado de cuenta",
                    self._estado_cuenta_controls(estado_cuenta_result),
                ),
                detail_section("Simular pago", [self._simular_pago_section()]),
                detail_section("Obligaciones", [self._obligaciones_table(data)]),
                detail_section("Usos transversales", [self._usos_transversales(data)]),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _datos_base(self, data: dict[str, Any]) -> ft.Control:
        return key_value_grid(
            [
                ("ID", data.get("id_persona")),
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
                ("ID origen", "id_origen"),
                ("Rol", "rol_obligado"),
                ("Estado", "estado_obligacion"),
                ("Vencimiento", "fecha_vencimiento"),
                ("Saldo", "saldo_pendiente"),
            ],
            rows=obligaciones,
        )

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
                            ("ID relacion", "id_relacion_generadora"),
                            ("Tipo origen", "tipo_origen"),
                            ("ID origen", "id_origen"),
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
                            ("ID", "id_obligacion_financiera"),
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
                            ("Obligacion", "id_obligacion_financiera"),
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

    def _simular_pago_section(self) -> ft.Control:
        monto = ft.TextField(
            label="Monto",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180,
        )
        fecha_pago = ft.TextField(
            label="Fecha pago",
            value=date.today().isoformat(),
            width=180,
        )
        alcance_pago = ft.Dropdown(
            label="Alcance",
            value="GLOBAL_PERSONA",
            width=220,
            options=[
                ft.dropdown.Option("GLOBAL_PERSONA"),
                ft.dropdown.Option("OBLIGACION"),
                ft.dropdown.Option("RELACION_GENERADORA"),
                ft.dropdown.Option(""),
            ],
        )
        id_obligacion = ft.TextField(
            label="ID obligacion",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180,
        )
        id_relacion = ft.TextField(
            label="ID relacion generadora",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=220,
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

            alcance = alcance_pago.value or None
            id_ob_value = self._parse_optional_int(id_obligacion.value)
            id_rel_value = self._parse_optional_int(id_relacion.value)

            if alcance == "OBLIGACION" and id_ob_value is None:
                show_error("Para alcance OBLIGACION indique id_obligacion_financiera.")
                return
            if alcance == "RELACION_GENERADORA" and id_rel_value is None:
                show_error("Para alcance RELACION_GENERADORA indique id_relacion_generadora.")
                return

            result = self.api.simular_pago_persona(
                self.id_persona,
                monto=monto_value,
                fecha_pago=fecha_pago.value or None,
                alcance_pago=alcance,
                id_obligacion_financiera=id_ob_value,
                id_relacion_generadora=id_rel_value,
            )
            if not result.success:
                show_error(result.error_message or "No se pudo simular el pago.")
                return

            result_area.content = self._simulacion_result(result.data)
            result_area.update()

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[monto, fecha_pago, alcance_pago],
                    spacing=10,
                    wrap=True,
                ),
                ft.Row(
                    controls=[id_obligacion, id_relacion],
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
                            ("Obligacion", "id_obligacion_financiera"),
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
                            ("Obligacion", "id_obligacion_financiera"),
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
                ("ID relacion", "id_relacion"),
                ("Rol", "codigo_rol"),
                ("Desde", "fecha_desde"),
                ("Hasta", "fecha_hasta"),
            ],
            rows=rows,
        )

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
        keys = list(rows[0].keys())[:6]
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
        return value or f"Ficha de parte #{self.id_persona}"
