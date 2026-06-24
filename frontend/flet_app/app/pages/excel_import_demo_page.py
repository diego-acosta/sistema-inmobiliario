from __future__ import annotations

import flet as ft

from app.components.excel_import_wizard import ExcelImportWizard
from app.importers.excel_import_models import ImportTargetField
from app.importers.excel_validators import normalize_decimal, normalize_text, positive_decimal_validator


class ExcelImportDemoPage:
    """Technical demo for the reusable Excel importer; it creates no real data."""

    def build(self) -> ft.Control:
        fields = [
            ImportTargetField(
                key="codigo",
                label="Código",
                required=True,
                aliases=["código", "cod", "codigo_lote"],
                normalizer=normalize_text,
            ),
            ImportTargetField(
                key="nombre",
                label="Nombre",
                required=True,
                aliases=["descripcion", "descripción", "detalle"],
                normalizer=normalize_text,
            ),
            ImportTargetField(
                key="superficie",
                label="Superficie",
                required=False,
                aliases=["superficie_m2", "m2", "metros"],
                normalizer=normalize_decimal,
                validator=positive_decimal_validator,
            ),
            ImportTargetField(
                key="observaciones",
                label="Observaciones",
                required=False,
                aliases=["obs", "comentarios"],
                normalizer=normalize_text,
            ),
        ]
        return ExcelImportWizard(target_fields=fields, title="Demo técnica — Importador Excel reutilizable")
