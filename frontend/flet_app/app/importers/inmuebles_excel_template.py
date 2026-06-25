from __future__ import annotations

from pathlib import Path
from typing import Final

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

DATA_SHEET: Final = "Datos"
HELP_SHEET: Final = "Ayuda"

EXPECTED_HEADERS: Final[tuple[str, ...]] = (
    "codigo",
    "descripcion",
    "desarrollo",
    "manzana",
    "lote",
    "parcela",
    "m2",
    "nomenclatura_catastral",
    "partida",
    "matricula",
    "estado_administrativo",
    "estado_juridico",
    "observaciones",
)

EXAMPLE_ROWS: Final[tuple[tuple[str, ...], ...]] = (
    ("IMP-001", "Lote importado 1", "Loteo existente", "M1", "L1", "", "10.5", "", "P-001", "", "", "", ""),
    ("IMP-002", "Lote importado 2", "Loteo existente", "M1", "L2", "", "1234.56", "", "P-002", "", "", "", ""),
    ("IMP-003", "Ejemplo sin dato catastral", "", "", "", "", "500", "", "", "", "", "", ""),
)

COLUMN_HELP: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("codigo", "Obligatoria", "Identificador del inmueble a importar.", "codigo, código, codigo_lote, cod_lote, lote_codigo"),
    ("descripcion", "Opcional", "Nombre o descripción visible del inmueble/lote.", "descripcion, descripción, nombre, nombre_lote"),
    ("desarrollo", "Opcional", "Debe coincidir con código o nombre de un desarrollo existente si se informa.", "desarrollo, loteo, emprendimiento, barrio"),
    ("manzana", "Opcional", "Dato funcional/catastral usado para crear dato catastral/registral.", "manzana, mz, mza"),
    ("lote", "Opcional", "No es una entidad separada; se trata como dato funcional/catastral del inmueble.", "lote, parcela, nro_lote, numero_lote"),
    ("parcela", "Opcional", "Dato catastral/registral del inmueble.", "parcela"),
    ("m2", "Opcional", "Superficie; debe ser número positivo si se informa.", "superficie, superficie_m2, m2, metros"),
    ("nomenclatura_catastral", "Opcional", "Dato catastral/registral del inmueble.", "nomenclatura_catastral"),
    ("partida", "Opcional", "Partida inmobiliaria para crear dato catastral/registral.", "partida, partida_inmobiliaria"),
    ("matricula", "Opcional", "Matrícula registral para crear dato catastral/registral.", "matricula, matrícula, matricula_registral"),
    ("estado_administrativo", "Opcional", "Estado administrativo del inmueble; si falta, el importador aplica el default vigente.", "estado_administrativo"),
    ("estado_juridico", "Opcional", "Estado jurídico del inmueble; si falta, el importador aplica el default vigente.", "estado_juridico"),
    ("observaciones", "Opcional", "Notas internas del inmueble.", "observaciones"),
)

VALIDATION_RULES: Final[tuple[str, ...]] = (
    "codigo es obligatorio.",
    "codigo no debe repetirse en el archivo.",
    "codigo no debe existir previamente en el sistema.",
    "m2 debe ser número positivo si se informa.",
    "desarrollo debe coincidir con código o nombre de un desarrollo existente.",
    "lote no es una entidad separada; se trata como dato funcional/catastral del inmueble.",
    "Manzana, lote, parcela, nomenclatura, partida y matrícula se usan para crear dato catastral/registral.",
    "No se importan ventas.",
    "No se importan precios.",
    "No se importan servicios.",
    "No se importa geometría/plano.",
)


def create_inmuebles_excel_template(path: str) -> str:
    """Create the inmuebles/lotes import template and return its absolute path."""
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    data = workbook.active
    data.title = DATA_SHEET
    _build_data_sheet(data)
    help_sheet = workbook.create_sheet(HELP_SHEET)
    _build_help_sheet(help_sheet)
    workbook.save(output)
    return str(output)


def _build_data_sheet(sheet) -> None:
    sheet.append(EXPECTED_HEADERS)
    for row in EXAMPLE_ROWS:
        sheet.append(row)
    sheet.freeze_panes = "A2"
    header_fill = PatternFill("solid", fgColor="D9EAF7")
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    _auto_width(sheet)


def _build_help_sheet(sheet) -> None:
    sheet.append(("Plantilla de importación de inmuebles/lotes",))
    sheet["A1"].font = Font(size=14, bold=True)
    sheet.append(("",))
    sheet.append(("Reglas de validación",))
    sheet["A3"].font = Font(bold=True)
    for rule in VALIDATION_RULES:
        sheet.append((rule,))
    sheet.append(("",))
    sheet.append(("Columnas", "Obligatoriedad", "Descripción", "Aliases aceptados"))
    header_row = sheet.max_row
    for item in COLUMN_HELP:
        sheet.append(item)
    for cell in sheet[header_row]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="D9EAD3")
    sheet.freeze_panes = f"A{header_row + 1}"
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    _auto_width(sheet, max_width=72)


def _auto_width(sheet, *, max_width: int = 36) -> None:
    for column_cells in sheet.columns:
        letter = get_column_letter(column_cells[0].column)
        width = max(len(str(cell.value or "")) for cell in column_cells) + 2
        sheet.column_dimensions[letter].width = min(max(width, 12), max_width)
