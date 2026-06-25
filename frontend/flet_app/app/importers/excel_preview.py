from __future__ import annotations

from typing import Any, Callable

from .excel_import_models import (
    STATUS_INVALID,
    STATUS_VALID,
    STATUS_WARNING,
    ExcelSheetData,
    ImportConfirmResult,
    ImportMapping,
    ImportPreviewResult,
    ImportRowPreview,
    ImportTargetField,
)
from .excel_mapping import mapping_by_target

ConfirmFunction = Callable[[ImportPreviewResult], ImportConfirmResult]


def build_preview(
    sheet: ExcelSheetData,
    target_fields: list[ImportTargetField],
    mappings: list[ImportMapping],
) -> ImportPreviewResult:
    source_by_target = mapping_by_target(mappings)
    fields_by_key = {field.key: field for field in target_fields}
    rows: list[ImportRowPreview] = []

    for raw_row in sheet.rows:
        row_number = int(raw_row.get("__row_number__") or 0)
        raw_values = {k: v for k, v in raw_row.items() if k != "__row_number__"}
        mapped_values: dict[str, Any] = {}
        errors: list[str] = []
        warnings: list[str] = []

        for field_key, field in fields_by_key.items():
            source_column = source_by_target.get(field_key)
            raw_value = raw_values.get(source_column) if source_column else None
            raw_is_empty = _is_empty(raw_value)
            value = field.normalizer(raw_value) if field.normalizer is not None else raw_value
            normalized_is_empty = _is_empty(value)
            mapped_values[field_key] = value

            if field.required and normalized_is_empty:
                errors.append(f"{field.label}: campo requerido.")
                continue
            if (
                not raw_is_empty
                and normalized_is_empty
                and field.normalizer is not None
            ):
                errors.append(f"{field.label}: valor inválido o no convertible.")
                continue
            if not normalized_is_empty and field.validator is not None:
                message = field.validator(value)
                if message:
                    errors.append(f"{field.label}: {message}")

        status = STATUS_INVALID if errors else (STATUS_WARNING if warnings else STATUS_VALID)
        preview_values = _default_preview_values(mapped_values, target_fields)
        rows.append(
            ImportRowPreview(
                row_number=row_number,
                raw_values=raw_values,
                mapped_values=mapped_values,
                errors=errors,
                warnings=warnings,
                status=status,
                preview_values=preview_values,
            )
        )

    valid_rows = sum(1 for row in rows if row.status != STATUS_INVALID)
    invalid_rows = len(rows) - valid_rows
    return ImportPreviewResult(
        columns=sheet.columns,
        rows=rows,
        total_rows=len(rows),
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
    )


def _default_preview_values(mapped_values: dict[str, Any], target_fields: list[ImportTargetField], limit: int = 6) -> dict[str, Any]:
    preview: dict[str, Any] = {}
    for field in target_fields:
        value = mapped_values.get(field.key)
        if _is_empty(value):
            continue
        preview[field.label] = value
        if len(preview) >= limit:
            break
    return preview


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def simulate_confirm(preview: ImportPreviewResult) -> ImportConfirmResult:
    errors_by_row = {row.row_number: row.errors for row in preview.rows if row.errors}
    return ImportConfirmResult(
        total=preview.total_rows,
        created=preview.valid_rows,
        skipped=0,
        failed=preview.invalid_rows,
        errors_by_row=errors_by_row,
    )
