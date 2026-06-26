from __future__ import annotations

from app.api_client import ApiResult
from app.components.excel_import_wizard import ExcelImportWizard
from app.importers.excel_import_models import ExcelColumn, ExcelSheetData
from app.importers.excel_mapping import suggest_mapping
from app.importers.inmuebles_excel_importer import (
    build_catastral_import_payload,
    build_inmueble_import_payload,
    build_inmuebles_preview,
    confirm_inmuebles_import,
    inmueble_import_target_fields,
)


class FakeApi:
    def __init__(self, *, fail_catastral: bool = False) -> None:
        self.created_payloads = []
        self.catastral_payloads = []
        self.fail_catastral = fail_catastral

    def crear_inmueble(self, payload, op_id=None):
        self.created_payloads.append((payload, op_id))
        if payload["codigo_inmueble"] == "FALLA":
            return ApiResult(False, error_message="falló alta")
        return ApiResult(True, data={"id_inmueble": len(self.created_payloads)})

    def crear_dato_catastral_registral_inmueble(self, id_inmueble, payload, op_id=None):
        self.catastral_payloads.append((id_inmueble, payload, op_id))
        if self.fail_catastral:
            return ApiResult(False, error_message="falló catastro")
        return ApiResult(True, data={"id_dato_catastral_registral": 10})


def _sheet(rows):
    headers = ["codigo", "descripcion", "desarrollo", "manzana", "lote", "m2", "partida"]
    return ExcelSheetData(
        name="Datos",
        columns=[ExcelColumn(i, h, h.replace("ú", "u")) for i, h in enumerate(headers)],
        rows=[dict(zip(headers, values), __row_number__=idx + 2) for idx, values in enumerate(rows)],
        header_row_number=1,
    )


def test_mapping_automatico_de_columnas_inmobiliarias() -> None:
    mapping = suggest_mapping(_sheet([]).columns, inmueble_import_target_fields())
    assert {m.target_field: m.source_column for m in mapping}["codigo_inmueble"] == "codigo"
    assert {m.target_field: m.source_column for m in mapping}["nombre_inmueble"] == "descripcion"
    assert {m.target_field: m.source_column for m in mapping}["superficie"] == "m2"


def test_validacion_codigo_requerido_y_superficie_positiva() -> None:
    sheet = _sheet([["", "Sin código", "", "", "", "-1", ""]])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))
    assert preview.invalid_rows == 1
    assert "Código inmueble: campo requerido." in preview.rows[0].errors
    assert "Superficie: Debe ser un decimal positivo." in preview.rows[0].errors


def test_detecta_duplicados_internos_y_contra_sistema() -> None:
    sheet = _sheet([["A1", "Uno", "", "", "", "10", ""], ["A1", "Dos", "", "", "", "11", ""], ["B2", "Tres", "", "", "", "12", ""]])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()), existing_codes={"b2"})
    assert preview.invalid_rows == 2
    assert "Código de inmueble duplicado dentro del archivo." in preview.rows[1].errors
    assert "Código de inmueble ya existe en el sistema." in preview.rows[2].errors


def test_preview_valida_desarrollo_y_genera_warnings() -> None:
    sheet = _sheet([["A1", "", "Barrio Norte", "", "", "10", ""]])
    preview = build_inmuebles_preview(
        sheet,
        suggest_mapping(sheet.columns, inmueble_import_target_fields()),
        desarrollos=[{"id_desarrollo": 7, "codigo_desarrollo": "BN", "nombre_desarrollo": "Barrio Norte"}],
    )
    assert preview.valid_rows == 1
    assert preview.rows[0].mapped_values["id_desarrollo"] == "7"
    assert preview.rows[0].status == "WARNING"
    assert any("Falta nombre" in warning for warning in preview.rows[0].warnings)


def test_armado_de_payloads_inmueble_y_dato_catastral() -> None:
    values = {
        "codigo_inmueble": "A1",
        "nombre_inmueble": "Lote A1",
        "superficie": "12.5",
        "estado_administrativo": "ACTIVO",
        "estado_juridico": "REGULAR",
        "id_desarrollo": "3",
        "manzana": "M1",
        "lote": "L1",
        "partida_inmobiliaria": "P123",
    }
    assert build_inmueble_import_payload(values) == {
        "codigo_inmueble": "A1",
        "nombre_inmueble": "Lote A1",
        "superficie": "12.5",
        "estado_administrativo": "ACTIVO",
        "estado_juridico": "REGULAR",
        "id_desarrollo": 3,
    }
    assert build_catastral_import_payload(values) == {
        "estado_dato": "ACTIVO",
        "manzana": "M1",
        "lote": "L1",
        "partida_inmobiliaria": "P123",
    }


def test_confirmacion_con_fallo_de_inmueble_reporta_failed() -> None:
    sheet = _sheet([["FALLA", "Dos", "", "", "", "11", ""]])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))
    result = confirm_inmuebles_import(FakeApi(), preview, import_run_id="run-1")
    assert result.created == 0
    assert result.failed == 1
    assert result.created_ids == []
    assert result.errors_by_row == {2: ["falló alta"]}
    assert result.warnings_by_row == {}


def test_confirmacion_con_fallo_catastral_reporta_created_con_warning() -> None:
    sheet = _sheet([["A1", "Uno", "", "M", "L", "10", "P"]])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))
    api = FakeApi(fail_catastral=True)
    result = confirm_inmuebles_import(api, preview, import_run_id="run-1")
    assert result.created == 1
    assert result.failed == 0
    assert result.created_ids == [1]
    assert result.errors_by_row == {}
    assert result.warnings_by_row == {
        2: ["Inmueble creado, pero falló el dato catastral/registral: falló catastro"]
    }


def test_confirmacion_mockeada_reporta_creadas_y_fallidas() -> None:
    sheet = _sheet([["A1", "Uno", "", "M", "L", "10", "P"], ["FALLA", "Dos", "", "", "", "11", ""]])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))
    api = FakeApi()
    result = confirm_inmuebles_import(api, preview, import_run_id="run-1")
    assert result.created == 1
    assert result.failed == 1
    assert result.created_ids == [1]
    assert result.warnings_by_row == {}
    assert api.catastral_payloads[0][0] == 1


def _advanced_sheet(rows):
    headers = [
        "codigo",
        "descripcion",
        "m2",
        "folio_real",
        "circunscripcion",
        "seccion",
        "chacra",
        "quinta",
        "fraccion",
        "manzana",
        "lote",
        "parcela",
        "subparcela",
        "nomenclatura_catastral",
        "nomenclatura_madre",
        "partida",
        "matricula",
        "superficie_titulo",
        "superficie_mensura",
        "medidas",
        "situacion_posesoria",
        "situacion_dominial",
        "organismo_origen",
        "fecha_desde",
        "fecha_hasta",
        "estado_dato",
        "observaciones_catastrales",
    ]
    return ExcelSheetData(
        name="Datos",
        columns=[ExcelColumn(i, h, h.replace("ú", "u")) for i, h in enumerate(headers)],
        rows=[dict(zip(headers, values), __row_number__=idx + 2) for idx, values in enumerate(rows)],
        header_row_number=1,
    )


def test_mapping_automatico_de_campos_catastrales_avanzados() -> None:
    mapping = suggest_mapping(_advanced_sheet([]).columns, inmueble_import_target_fields())
    by_target = {m.target_field: m.source_column for m in mapping}
    assert by_target["folio_real"] == "folio_real"
    assert by_target["subparcela"] == "subparcela"
    assert by_target["superficie_titulo"] == "superficie_titulo"
    assert by_target["fecha_desde"] == "fecha_desde"
    assert by_target["observaciones_catastrales"] == "observaciones_catastrales"
    assert by_target["nomenclatura_madre"] == "nomenclatura_madre"


def test_payload_catastral_con_campos_avanzados_y_fechas() -> None:
    values = {
        "codigo_inmueble": "ADV-1",
        "estado_administrativo": "ACTIVO",
        "estado_juridico": "REGULAR",
        "folio_real": "FR-1",
        "circunscripcion": "I",
        "seccion": "A",
        "chacra": "CH",
        "quinta": "Q",
        "fraccion": "F",
        "manzana": "M",
        "lote": "L",
        "parcela": "P",
        "subparcela": "SP",
        "nomenclatura_catastral": "NC",
        "nomenclatura_madre": "NC-MADRE",
        "partida_inmobiliaria": "PI",
        "matricula": "MAT",
        "superficie_titulo": "1200.50",
        "superficie_mensura": "1198.75",
        "medidas": "20x60",
        "situacion_posesoria": "REGULAR",
        "situacion_dominial": "DOMINIO",
        "organismo_origen": "Catastro",
        "fecha_desde": "2026-01-01T00:00:00",
        "fecha_hasta": "2026-12-31T00:00:00",
        "estado_dato": "HISTORICO",
        "observaciones_catastrales": "Obs cat",
    }
    assert build_catastral_import_payload(values) == {
        "estado_dato": "HISTORICO",
        "manzana": "M",
        "lote": "L",
        "nomenclatura_catastral": "NC",
        "nomenclatura_madre": "NC-MADRE",
        "partida_inmobiliaria": "PI",
        "matricula": "MAT",
        "folio_real": "FR-1",
        "circunscripcion": "I",
        "seccion": "A",
        "chacra": "CH",
        "quinta": "Q",
        "fraccion": "F",
        "parcela": "P",
        "subparcela": "SP",
        "medidas": "20x60",
        "situacion_posesoria": "REGULAR",
        "situacion_dominial": "DOMINIO",
        "organismo_origen": "Catastro",
        "fecha_desde": "2026-01-01T00:00:00",
        "fecha_hasta": "2026-12-31T00:00:00",
        "observaciones": "Obs cat",
        "superficie_titulo": "1200.50",
        "superficie_mensura": "1198.75",
    }



def test_fechas_vacias_no_generan_error_ni_se_envian_en_payload() -> None:
    sheet = _advanced_sheet([
        ["ADV-FECHA-VACIA", "Sin vigencia", "100", "FR-1", "", "", "", "", "", "M", "L", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
    ])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))
    assert preview.invalid_rows == 0
    payload = build_catastral_import_payload(preview.rows[0].mapped_values)
    assert payload is not None
    assert "fecha_desde" not in payload
    assert "fecha_hasta" not in payload


def test_fechas_se_normalizan_a_datetime_iso() -> None:
    sheet = _advanced_sheet([
        ["ADV-FECHA-ISO", "Con vigencia", "100", "FR-1", "", "", "", "", "", "M", "L", "", "", "", "", "", "", "", "", "", "", "", "", "2026-01-01", "2026-12-31", "", ""],
        ["ADV-FECHA-SLASH", "Con vigencia slash", "100", "FR-2", "", "", "", "", "", "M", "L", "", "", "", "", "", "", "", "", "", "", "", "", "01/01/2026", "", "", ""],
    ])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))
    assert preview.invalid_rows == 0
    assert preview.rows[0].mapped_values["fecha_desde"] == "2026-01-01T00:00:00"
    assert preview.rows[0].mapped_values["fecha_hasta"] == "2026-12-31T00:00:00"
    assert preview.rows[1].mapped_values["fecha_desde"] == "2026-01-01T00:00:00"
    payload = build_catastral_import_payload(preview.rows[0].mapped_values)
    assert payload is not None
    assert payload["fecha_desde"] == "2026-01-01T00:00:00"
    assert payload["fecha_hasta"] == "2026-12-31T00:00:00"

def test_preview_valida_fechas_y_superficies_avanzadas() -> None:
    sheet = _advanced_sheet([
        ["A1", "Avanzado", "10", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "-1", "2", "", "", "", "", "2026-01-01", "2025-12-31", "", ""],
        ["A2", "Fecha inválida", "10", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "1", "2", "", "", "", "", "31/12/2026", "mal", "", ""],
    ])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))
    assert preview.invalid_rows == 2
    assert "Superficie título: Debe ser un decimal positivo." in preview.rows[0].errors
    assert "Fecha hasta no puede ser anterior a fecha desde." in preview.rows[0].errors
    assert "Fecha hasta: valor inválido o no convertible." in preview.rows[1].errors


def test_confirmacion_mockeada_envia_dato_catastral_completo() -> None:
    sheet = _advanced_sheet([
        ["ADV-1", "Avanzado", "100", "FR-1", "I", "A", "CH", "Q", "F", "M", "L", "P", "SP", "NC", "NC-MADRE", "PI", "MAT", "1200.50", "1198.75", "20x60", "REGULAR", "DOMINIO", "Catastro", "2026-01-01", "", "ACTIVO", "Obs cat"],
    ])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))
    api = FakeApi()
    result = confirm_inmuebles_import(api, preview, import_run_id="run-adv")
    assert result.created == 1
    assert result.failed == 0
    _, payload, _ = api.catastral_payloads[0]
    assert payload["folio_real"] == "FR-1"
    assert payload["nomenclatura_madre"] == "NC-MADRE"
    assert payload["subparcela"] == "SP"
    assert payload["superficie_titulo"] == "1200.50"
    assert payload["fecha_desde"] == "2026-01-01T00:00:00"
    assert payload["observaciones"] == "Obs cat"


def test_preview_inmuebles_muestra_codigo_nombre_y_no_diccionario_como_principal() -> None:
    sheet = _sheet([["PR233-101", "Lote legible", "", "", "", "10", ""]])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))

    visible = preview.rows[0].visible_preview_values()
    assert visible["Código"] == "PR233-101"
    assert visible["Nombre/descripción"] == "Lote legible"
    assert "codigo_inmueble" not in visible
    assert preview.rows[0].mapped_values["codigo_inmueble"] == "PR233-101"


def test_preview_inmuebles_muestra_datos_catastrales_principales() -> None:
    sheet = _sheet([["PR233-102", "Lote con catastro", "", "MZ-7", "LT-9", "10", "PI-123"]])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))

    visible = preview.rows[0].visible_preview_values()
    assert visible["Manzana"] == "MZ-7"
    assert visible["Lote"] == "LT-9"
    assert visible["Partida"] == "PI-123"


def test_preview_inmuebles_invalido_y_warning_exponen_mensajes_legibles() -> None:
    sheet = _sheet([["", "Sin código", "", "", "", "-3", ""], ["PR233-103", "", "", "", "", "10", ""]])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))

    assert preview.rows[0].status == "INVALID"
    assert "Código inmueble: campo requerido." in preview.rows[0].errors
    assert "Superficie: Debe ser un decimal positivo." in preview.rows[0].errors
    assert preview.rows[1].status == "WARNING"
    assert any("Falta nombre" in warning for warning in preview.rows[1].warnings)
    assert preview.rows[1].visible_preview_values()["Código"] == "PR233-103"


def test_preview_inmuebles_preview_vacio_no_agrega_columnas_tecnicas_ni_desplaza_legibles() -> None:
    sheet = _sheet([["", "", "", "", "", "10", ""], ["PR233-104", "Lote visible", "", "MZ-8", "LT-10", "10", "PI-456"]])
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))

    assert preview.rows[0].visible_preview_values() == {}
    columns = ExcelImportWizard._preview_columns(object(), preview)

    assert "superficie" not in columns
    assert "estado_administrativo" not in columns
    assert columns[:5] == ["Código", "Nombre/descripción", "Manzana", "Lote", "Partida"]


def test_importador_mapea_aliases_direccion_basica() -> None:
    headers = ["codigo", "descripcion", "nombre_calle", "número"]
    sheet = ExcelSheetData(
        name="Datos",
        columns=[ExcelColumn(i, h, h.replace("ú", "u")) for i, h in enumerate(headers)],
        rows=[dict(zip(["codigo", "descripcion", "nombre_calle", "numero"], ["A1", "Lote A1", "San Martín", "123 bis"]), __row_number__=2)],
        header_row_number=1,
    )
    preview = build_inmuebles_preview(sheet, suggest_mapping(sheet.columns, inmueble_import_target_fields()))

    values = preview.rows[0].mapped_values
    assert values["calle"] == "San Martín"
    assert values["altura"] == "123 bis"
    assert build_inmueble_import_payload(values)["calle"] == "San Martín"
    assert build_inmueble_import_payload(values)["altura"] == "123 bis"
