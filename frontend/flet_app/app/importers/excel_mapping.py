from __future__ import annotations

from .excel_import_models import ExcelColumn, ImportMapping, ImportTargetField
from .excel_reader import normalize_column_name


def suggest_mapping(
    columns: list[ExcelColumn], target_fields: list[ImportTargetField]
) -> list[ImportMapping]:
    available = {column.normalized_name for column in columns}
    mappings: list[ImportMapping] = []
    for field in target_fields:
        candidates = [field.key, field.label, *field.aliases]
        source = next(
            (normalized for normalized in (normalize_column_name(c) for c in candidates) if normalized in available),
            None,
        )
        mappings.append(ImportMapping(target_field=field.key, source_column=source))
    return mappings


def mapping_by_target(mappings: list[ImportMapping]) -> dict[str, str | None]:
    return {mapping.target_field: mapping.source_column for mapping in mappings}
