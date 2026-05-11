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
                detail_section("Estado financiero", [self._estado_financiero(data)]),
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
