from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.importers.excel_import_models import ImportTargetField
from app.importers.excel_mapping import suggest_mapping
from app.importers.excel_preview import build_preview, simulate_confirm
from app.importers.excel_reader import ExcelImportError, normalize_column_name, read_excel_workbook
from app.importers.excel_validators import normalize_decimal, normalize_text, positive_decimal_validator


def _target_fields() -> list[ImportTargetField]:
    return [
        ImportTargetField("codigo", "Código", True, ["cod"], normalizer=normalize_text),
        ImportTargetField("nombre", "Nombre", True, ["descripcion"], normalizer=normalize_text),
        ImportTargetField(
            "superficie",
            "Superficie",
            False,
            ["m2"],
            validator=positive_decimal_validator,
            normalizer=normalize_decimal,
        ),
    ]


def _workbook(path: Path) -> Path:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.append([None, None, None])
    ws.append(["Cód.", "Descripción", "M2"])
    ws.append(["A-1", "Lote A", "10,5"])
    ws.append(["", "Sin código", "-3"])
    wb.save(path)
    return path


def _workbook_with_empty_sheet(path: Path) -> Path:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.append(["Cód.", "Descripción", "M2"])
    ws.append(["A-1", "Lote A", 10.5])
    wb.create_sheet("Plantilla")
    wb.save(path)
    return path


def _workbook_with_invalid_optional_decimal(path: Path) -> Path:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.append(["Cód.", "Descripción", "M2"])
    ws.append(["A-1", "Lote A", "abc"])
    wb.save(path)
    return path


def test_normalizacion_de_columnas() -> None:
    assert normalize_column_name("  Supérficie m² / Total  ") == "superficie_m2_total"


def test_deteccion_de_columnas(tmp_path: Path) -> None:
    workbook = read_excel_workbook(_workbook(tmp_path / "demo.xlsx"))
    sheet = workbook.sheets["Datos"]
    assert [column.normalized_name for column in sheet.columns] == ["cod", "descripcion", "m2"]
    assert len(sheet.rows) == 2
    assert sheet.header_row_number == 2


def test_workbook_con_hoja_valida_y_hoja_vacia_no_falla(tmp_path: Path) -> None:
    workbook = read_excel_workbook(
        _workbook_with_empty_sheet(tmp_path / "demo.xlsx"),
        sheet_name="Datos",
    )
    assert workbook.sheet_names == ["Datos", "Plantilla"]
    assert workbook.active_sheet == "Datos"
    assert list(workbook.sheets) == ["Datos"]
    assert len(workbook.sheets["Datos"].rows) == 1


def test_hoja_vacia_seleccionada_lanza_error_claro(tmp_path: Path) -> None:
    with pytest.raises(ExcelImportError, match="Plantilla.*no tiene encabezados"):
        read_excel_workbook(
            _workbook_with_empty_sheet(tmp_path / "demo.xlsx"),
            sheet_name="Plantilla",
        )


def test_mapping_automatico_por_alias(tmp_path: Path) -> None:
    sheet = read_excel_workbook(_workbook(tmp_path / "demo.xlsx")).sheets["Datos"]
    mapping = suggest_mapping(sheet.columns, _target_fields())
    assert {item.target_field: item.source_column for item in mapping} == {
        "codigo": "cod",
        "nombre": "descripcion",
        "superficie": "m2",
    }


def test_validacion_de_requerido(tmp_path: Path) -> None:
    sheet = read_excel_workbook(_workbook(tmp_path / "demo.xlsx")).sheets["Datos"]
    preview = build_preview(sheet, _target_fields(), suggest_mapping(sheet.columns, _target_fields()))
    assert preview.rows[1].status == "INVALID"
    assert "Código: campo requerido." in preview.rows[1].errors


def test_campo_opcional_decimal_invalido_queda_invalid(tmp_path: Path) -> None:
    sheet = read_excel_workbook(_workbook_with_invalid_optional_decimal(tmp_path / "demo.xlsx")).sheets["Datos"]
    preview = build_preview(sheet, _target_fields(), suggest_mapping(sheet.columns, _target_fields()))
    assert preview.invalid_rows == 1
    assert preview.rows[0].status == "INVALID"
    assert "Superficie: valor inválido o no convertible." in preview.rows[0].errors


def test_validacion_decimal_positivo() -> None:
    assert positive_decimal_validator(normalize_decimal("12,50")) is None
    assert positive_decimal_validator(normalize_decimal("0")) == "Debe ser un decimal positivo."
    assert positive_decimal_validator("abc") == "Debe ser un número decimal válido."


def test_normalizacion_decimal_preserva_numeros_y_separadores() -> None:
    assert normalize_decimal(10.5) == Decimal("10.5")
    assert normalize_decimal("10.5") == Decimal("10.5")
    assert normalize_decimal("10,5") == Decimal("10.5")
    assert normalize_decimal("1.234,56") == Decimal("1234.56")
    assert normalize_decimal("1,234.56") == Decimal("1234.56")


def test_preview_con_filas_validas_e_invalidas(tmp_path: Path) -> None:
    sheet = read_excel_workbook(_workbook(tmp_path / "demo.xlsx")).sheets["Datos"]
    preview = build_preview(sheet, _target_fields(), suggest_mapping(sheet.columns, _target_fields()))
    assert preview.total_rows == 2
    assert preview.valid_rows == 1
    assert preview.invalid_rows == 1
    assert preview.rows[0].status == "VALID"


def test_confirmacion_simulada_con_reporte(tmp_path: Path) -> None:
    sheet = read_excel_workbook(_workbook(tmp_path / "demo.xlsx")).sheets["Datos"]
    preview = build_preview(sheet, _target_fields(), suggest_mapping(sheet.columns, _target_fields()))
    result = simulate_confirm(preview)
    assert result.total == 2
    assert result.created == 1
    assert result.failed == 1
    assert result.errors_by_row == {4: ["Código: campo requerido.", "Superficie: Debe ser un decimal positivo."]}


def test_preview_values_son_legibles_y_no_dependen_del_diccionario_completo(tmp_path: Path) -> None:
    sheet = read_excel_workbook(_workbook(tmp_path / "demo.xlsx")).sheets["Datos"]
    preview = build_preview(sheet, _target_fields(), suggest_mapping(sheet.columns, _target_fields()))

    assert preview.rows[0].visible_preview_values() == {
        "Código": "A-1",
        "Nombre": "Lote A",
        "Superficie": Decimal("10.5"),
    }
    assert preview.rows[0].mapped_values["codigo"] == "A-1"
    result = simulate_confirm(preview)
    assert result.created == 1
