from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Validator = Callable[[Any], str | None]
Normalizer = Callable[[Any], Any]

STATUS_VALID = "VALID"
STATUS_WARNING = "WARNING"
STATUS_INVALID = "INVALID"


@dataclass(slots=True, frozen=True)
class ExcelColumn:
    index: int
    name: str
    normalized_name: str


@dataclass(slots=True, frozen=True)
class ImportTargetField:
    key: str
    label: str
    required: bool = False
    aliases: list[str] = field(default_factory=list)
    validator: Validator | None = None
    normalizer: Normalizer | None = None


@dataclass(slots=True, frozen=True)
class ImportMapping:
    target_field: str
    source_column: str | None = None


@dataclass(slots=True)
class ExcelSheetData:
    name: str
    columns: list[ExcelColumn]
    rows: list[dict[str, Any]]
    header_row_number: int


@dataclass(slots=True)
class ExcelWorkbookData:
    path: str
    sheet_names: list[str]
    active_sheet: str
    sheets: dict[str, ExcelSheetData]


@dataclass(slots=True)
class ImportRowPreview:
    row_number: int
    raw_values: dict[str, Any]
    mapped_values: dict[str, Any]
    errors: list[str]
    warnings: list[str]
    status: str
    preview_values: dict[str, Any] = field(default_factory=dict)

    def visible_preview_values(self) -> dict[str, Any]:
        if self.preview_values:
            return self.preview_values
        return {key: value for key, value in self.mapped_values.items() if not _is_empty(value)}


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


@dataclass(slots=True)
class ImportPreviewResult:
    columns: list[ExcelColumn]
    rows: list[ImportRowPreview]
    total_rows: int
    valid_rows: int
    invalid_rows: int


@dataclass(slots=True)
class ImportConfirmResult:
    total: int
    created: int
    skipped: int
    failed: int
    errors_by_row: dict[int, list[str]]
    created_ids: list[int] = field(default_factory=list)
    warnings_by_row: dict[int, list[str]] = field(default_factory=dict)
