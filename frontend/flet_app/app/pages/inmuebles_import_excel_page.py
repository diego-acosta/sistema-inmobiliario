from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import flet as ft

from app.api_client import ApiClient
from app.components.excel_import_wizard import ExcelImportWizard
from app.importers.excel_import_models import ImportConfirmResult, ImportPreviewResult
from app.importers.inmuebles_excel_template import create_inmuebles_excel_template
from app.importers.inmuebles_excel_importer import (
    collect_existing_codes,
    build_inmuebles_preview,
    confirm_inmuebles_import,
    inmueble_import_target_fields,
)


class InmueblesImportExcelPage:
    """Importador Excel específico de inmuebles/lotes sobre la base reusable #205."""

    def __init__(self, api: ApiClient, on_navigate) -> None:
        self.api = api
        self.on_navigate = on_navigate
        self.template_picker = ft.FilePicker(on_result=self._on_template_path_selected)

    def build(self) -> ft.Control:
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Importar inmuebles", size=28, weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        ft.TextButton("Volver a inmuebles", on_click=lambda _: self.on_navigate("inmuebles")),
                    ]
                ),
                ft.Text(
                    "Especialización técnica del importador Excel reusable: valida preview y confirma creando inmuebles y datos catastrales/registrales mediante endpoints del Dominio Inmobiliario.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                self._help_section(),
                ExcelImportWizard(
                    target_fields=inmueble_import_target_fields(),
                    title="Importador Excel — inmuebles/lotes",
                    description="Lectura local QUERY_READLIKE y preview PREVIEW_READLIKE (CORE-EF no aplica). La confirmación real es COMMAND_WRITE_NEGOCIO y usa headers CORE-EF en los writes inmobiliarios existentes.",
                    confirm_callback=self._confirm,
                    preview_callback=self._preview,
                    confirm_label="Confirmar importación real",
                    report_pending_label="Pendiente de confirmación real.",
                ),
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )


    def _help_section(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Ayuda rápida", size=18, weight=ft.FontWeight.W_600),
                    ft.Text("La plantilla es completa: incluye columnas básicas del inmueble y datos catastrales/registrales avanzados soportados."),
                    ft.Text("Solo el código es obligatorio; las columnas avanzadas pueden quedar vacías y se omiten del payload si no se informan."),
                    ft.Text("Si informás desarrollo, debe coincidir con el código o nombre de un desarrollo existente antes de importar."),
                    ft.Text("Lote se guarda como dato funcional/catastral del inmueble; no se crea una entidad lote separada."),
                    ft.Text("El preview valida códigos, superficies, fechas y desarrollo antes de confirmar. No se importan ventas, precios, servicios ni geometría/plano."),
                    ft.ElevatedButton(
                        "Descargar plantilla Excel",
                        icon=ft.Icons.DOWNLOAD,
                        on_click=self._download_template,
                    ),
                ],
                spacing=8,
            ),
            padding=16,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
        )

    def _download_template(self, event: ft.ControlEvent) -> None:
        page = event.page
        if page and self.template_picker not in page.overlay:
            page.overlay.append(self.template_picker)
            page.update()
        self.template_picker.save_file(
            dialog_title="Guardar plantilla Excel de inmuebles",
            file_name="plantilla_importacion_inmuebles.xlsx",
            allowed_extensions=["xlsx"],
        )

    def _on_template_path_selected(self, event: ft.FilePickerResultEvent) -> None:
        if not event.path:
            return
        path = create_inmuebles_excel_template(event.path)
        if event.page:
            event.page.snack_bar = ft.SnackBar(ft.Text(f"Plantilla Excel generada: {Path(path).name}"))
            event.page.snack_bar.open = True
            event.page.update()

    def _preview(self, sheet, mappings) -> ImportPreviewResult:
        codes = {
            str(row.get(mapping.source_column) or "").strip()
            for mapping in mappings
            if mapping.target_field == "codigo_inmueble" and mapping.source_column
            for row in sheet.rows
            if row.get(mapping.source_column)
        }
        existing, lookup_errors = collect_existing_codes(self.api, codes)
        desarrollos_result = self.api.get_desarrollos()
        desarrollos = desarrollos_result.data if desarrollos_result.success and isinstance(desarrollos_result.data, list) else []
        preview = build_inmuebles_preview(sheet, mappings, existing_codes=existing, desarrollos=desarrollos)
        if lookup_errors:
            for row in preview.rows:
                row.warnings.extend(lookup_errors)
                if row.status == "VALID":
                    row.status = "WARNING"
        return preview

    def _confirm(self, preview: ImportPreviewResult) -> ImportConfirmResult:
        codes = {
            str(row.mapped_values.get("codigo_inmueble") or "").strip()
            for row in preview.rows
            if row.mapped_values.get("codigo_inmueble")
        }
        existing, lookup_errors = collect_existing_codes(self.api, codes)
        if existing or lookup_errors:
            for row in preview.rows:
                code = str(row.mapped_values.get("codigo_inmueble") or "").strip().casefold()
                if code in existing and "Código de inmueble ya existe en el sistema." not in row.errors:
                    row.errors.append("Código de inmueble ya existe en el sistema.")
                for error in lookup_errors:
                    if error not in row.warnings:
                        row.warnings.append(error)
                row.status = "INVALID" if row.errors else ("WARNING" if row.warnings else "VALID")
            preview.valid_rows = sum(1 for row in preview.rows if row.status != "INVALID")
            preview.invalid_rows = preview.total_rows - preview.valid_rows
        return confirm_inmuebles_import(self.api, preview, import_run_id=str(uuid4()))
