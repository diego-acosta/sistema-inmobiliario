from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import flet as ft

from app.importers.excel_import_models import (
    ExcelWorkbookData,
    ImportConfirmResult,
    ImportMapping,
    ImportPreviewResult,
    ImportTargetField,
)
from app.importers.excel_mapping import suggest_mapping
from app.importers.excel_preview import build_preview, simulate_confirm
from app.importers.excel_reader import ExcelImportError, read_excel_workbook

ConfirmCallback = Callable[[ImportPreviewResult], ImportConfirmResult]


class ExcelImportWizard(ft.Column):
    """Reusable local Excel import wizard for technical/read-like previews."""

    def __init__(
        self,
        *,
        target_fields: list[ImportTargetField],
        title: str = "Importador Excel",
        confirm_callback: ConfirmCallback | None = None,
    ) -> None:
        super().__init__(spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)
        self.target_fields = target_fields
        self.title = title
        self.confirm_callback = confirm_callback or simulate_confirm
        self.file_path: str | None = None
        self.workbook: ExcelWorkbookData | None = None
        self.selected_sheet: str | None = None
        self.mappings: list[ImportMapping] = []
        self.preview: ImportPreviewResult | None = None
        self.confirm_result: ImportConfirmResult | None = None
        self.error_message: str | None = None
        self.loading = False
        self.file_picker = ft.FilePicker(on_result=self._on_file_selected)
        self.controls = []
        self._render()

    def did_mount(self) -> None:
        if self.page and self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)
            self.page.update()

    def _on_file_selected(self, event: ft.FilePickerResultEvent) -> None:
        if not event.files:
            self.error_message = "Archivo no seleccionado."
            self._render_update()
            return
        self.file_path = event.files[0].path
        self.workbook = None
        self.preview = None
        self.confirm_result = None
        self.error_message = None
        self._read_workbook()

    def _pick_file(self, _: ft.ControlEvent) -> None:
        self.file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["xlsx"],
            dialog_title="Seleccionar Excel .xlsx",
        )

    def _read_workbook(self) -> None:
        if not self.file_path:
            self.error_message = "Archivo no seleccionado."
            self._render_update()
            return
        self.loading = True
        self._render_update()
        try:
            self.workbook = read_excel_workbook(self.file_path, self.selected_sheet)
            self.selected_sheet = self.workbook.active_sheet
            sheet = self.workbook.sheets[self.selected_sheet]
            self.mappings = suggest_mapping(sheet.columns, self.target_fields)
            self.preview = None
            self.confirm_result = None
            self.error_message = None
        except ExcelImportError as exc:
            self.error_message = str(exc)
        finally:
            self.loading = False
            self._render_update()

    def _on_sheet_change(self, event: ft.ControlEvent) -> None:
        self.selected_sheet = event.control.value
        self._read_workbook()

    def _on_mapping_change(self, field_key: str, event: ft.ControlEvent) -> None:
        updated = [m for m in self.mappings if m.target_field != field_key]
        source = event.control.value or None
        updated.append(ImportMapping(target_field=field_key, source_column=source))
        self.mappings = updated
        self.preview = None
        self.confirm_result = None
        self._render_update()

    def _build_preview(self, _: ft.ControlEvent) -> None:
        if not self.workbook or not self.selected_sheet:
            self.error_message = "Primero seleccioná un archivo Excel válido."
            self._render_update()
            return
        sheet = self.workbook.sheets[self.selected_sheet]
        self.preview = build_preview(sheet, self.target_fields, self.mappings)
        self.confirm_result = None
        self.error_message = None
        self._render_update()

    def _confirm(self, _: ft.ControlEvent) -> None:
        if self.preview is None:
            self.error_message = "Generá el preview antes de confirmar."
            self._render_update()
            return
        self.confirm_result = self.confirm_callback(self.preview)
        self.error_message = None
        self._render_update()

    def _render_update(self) -> None:
        self._render()
        if self.page:
            self.update()

    def _render(self) -> None:
        controls: list[ft.Control] = [
            ft.Text(self.title, size=24, weight=ft.FontWeight.W_700),
            ft.Text(
                "Flujo local reutilizable: lectura .xlsx, detección de columnas, mapping, preview y confirmación simulada.",
                color=ft.Colors.BLUE_GREY_700,
            ),
        ]
        if self.loading:
            controls.append(ft.Row([ft.ProgressRing(width=18, height=18), ft.Text("Leyendo Excel...")], spacing=12))
        if self.error_message:
            controls.append(_message_box(self.error_message, ft.Colors.RED_50, ft.Colors.RED_700))
        controls.extend([self._file_step(), self._sheet_step(), self._mapping_step(), self._preview_step(), self._report_step()])
        self.controls = controls

    def _file_step(self) -> ft.Control:
        filename = Path(self.file_path).name if self.file_path else "Sin archivo seleccionado"
        return _section(
            "1. Seleccionar archivo",
            [
                ft.Row(
                    [
                        ft.ElevatedButton("Elegir .xlsx", icon=ft.Icons.UPLOAD_FILE, on_click=self._pick_file),
                        ft.Text(filename, selectable=True),
                    ],
                    spacing=12,
                )
            ],
        )

    def _sheet_step(self) -> ft.Control:
        if not self.workbook:
            return _section("2. Seleccionar hoja", [ft.Text("Pendiente de archivo válido.")])
        options = [ft.dropdown.Option(name) for name in self.workbook.sheet_names]
        selected = self.selected_sheet or self.workbook.active_sheet
        sheet = self.workbook.sheets.get(selected)
        controls: list[ft.Control] = [
            ft.Dropdown(label="Hoja", value=selected, options=options, on_change=self._on_sheet_change),
        ]
        if sheet is None:
            controls.append(ft.Text("La hoja seleccionada no pudo leerse. Elegí otra hoja para reintentar."))
        else:
            controls.extend(
                [
                    ft.Text(f"Columnas detectadas: {', '.join(c.name for c in sheet.columns)}"),
                    ft.Text(f"Filas leídas: {len(sheet.rows)}"),
                ]
            )
        return _section("2. Seleccionar hoja y detectar columnas", controls)

    def _mapping_step(self) -> ft.Control:
        if (
            not self.workbook
            or not self.selected_sheet
            or self.selected_sheet not in self.workbook.sheets
        ):
            return _section("3. Mapear columnas", [ft.Text("Pendiente de detección de columnas.")])
        sheet = self.workbook.sheets[self.selected_sheet]
        current = {mapping.target_field: mapping.source_column for mapping in self.mappings}
        options = [ft.dropdown.Option("")] + [
            ft.dropdown.Option(column.normalized_name, text=column.name) for column in sheet.columns
        ]
        rows: list[ft.Control] = []
        for field in self.target_fields:
            rows.append(
                ft.Row(
                    [
                        ft.Text(f"{field.label}{' *' if field.required else ''}", width=220),
                        ft.Dropdown(
                            value=current.get(field.key) or "",
                            options=options,
                            width=320,
                            on_change=lambda e, key=field.key: self._on_mapping_change(key, e),
                        ),
                    ],
                    spacing=12,
                )
            )
        rows.append(ft.ElevatedButton("Generar preview", icon=ft.Icons.PREVIEW, on_click=self._build_preview))
        return _section("3. Mapear columnas", rows)

    def _preview_step(self) -> ft.Control:
        if self.preview is None:
            return _section("4. Preview", [ft.Text("Pendiente de generación.")])
        preview = self.preview
        rows = []
        for row in preview.rows[:50]:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(row.row_number))),
                        ft.DataCell(ft.Text(row.status)),
                        ft.DataCell(ft.Text(str(row.mapped_values))),
                        ft.DataCell(ft.Text("; ".join(row.errors + row.warnings) or "-")),
                    ]
                )
            )
        return _section(
            "4. Preview",
            [
                ft.Text(f"Filas: {preview.total_rows} | Válidas: {preview.valid_rows} | Inválidas: {preview.invalid_rows}"),
                ft.Row(
                    [
                        ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("Fila")),
                                ft.DataColumn(ft.Text("Estado")),
                                ft.DataColumn(ft.Text("Valores mapeados")),
                                ft.DataColumn(ft.Text("Errores / advertencias")),
                            ],
                            rows=rows,
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                ),
                ft.ElevatedButton("Confirmación simulada", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=self._confirm),
            ],
        )

    def _report_step(self) -> ft.Control:
        if self.confirm_result is None:
            return _section("5. Reporte final", [ft.Text("Pendiente de confirmación simulada.")])
        result = self.confirm_result
        return _section(
            "5. Reporte final",
            [
                ft.Text(f"Total: {result.total} | Simulados creados: {result.created} | Omitidos: {result.skipped} | Fallidos: {result.failed}"),
                ft.Text(f"Errores por fila: {result.errors_by_row or '-'}", selectable=True),
            ],
        )


def _section(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        content=ft.Column([ft.Text(title, size=18, weight=ft.FontWeight.W_600), *controls], spacing=10),
        padding=16,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=8,
    )


def _message_box(message: str, bgcolor: str, color: str) -> ft.Control:
    return ft.Container(content=ft.Text(message, color=color), bgcolor=bgcolor, padding=12, border_radius=6)
