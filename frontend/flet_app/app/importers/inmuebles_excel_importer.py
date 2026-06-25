from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import uuid5, NAMESPACE_URL

from app.api_client import ApiResult
from app.importers.excel_import_models import (
    STATUS_INVALID,
    STATUS_VALID,
    STATUS_WARNING,
    ImportConfirmResult,
    ImportMapping,
    ImportPreviewResult,
    ImportTargetField,
)
from app.importers.excel_preview import build_preview
from app.importers.excel_reader import normalize_column_name
from app.importers.excel_validators import normalize_decimal, normalize_text, positive_decimal_validator
from app.inmueble_alta_helpers import build_dato_catastral_payload, build_inmueble_payload

DEFAULT_ESTADO_ADMINISTRATIVO = "ACTIVO"
DEFAULT_ESTADO_JURIDICO = "REGULAR"
CATASTRAL_FIELDS = (
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
    "partida_inmobiliaria",
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
)

DATE_FORMAT_HELP = "Usá formato AAAA-MM-DD."


class InmueblesImportApi(Protocol):
    def get_inmuebles(self, **kwargs: Any) -> ApiResult: ...
    def get_desarrollos(self) -> ApiResult: ...
    def crear_inmueble(self, payload: dict[str, Any], op_id: str | None = None) -> ApiResult: ...
    def crear_dato_catastral_registral_inmueble(self, id_inmueble: int, payload: dict[str, Any], op_id: str | None = None) -> ApiResult: ...


@dataclass(slots=True, frozen=True)
class DesarrolloRef:
    id_desarrollo: int
    codigo_desarrollo: str
    nombre_desarrollo: str


def inmueble_import_target_fields() -> list[ImportTargetField]:
    return [
        ImportTargetField("codigo_inmueble", "Código inmueble", True, ["codigo", "código", "codigo_lote", "cod_lote", "lote_codigo"], normalizer=normalize_text),
        ImportTargetField("nombre_inmueble", "Nombre inmueble", False, ["nombre", "descripcion", "descripción", "nombre_lote"], normalizer=normalize_text),
        ImportTargetField("desarrollo", "Desarrollo", False, ["loteo", "emprendimiento", "barrio"], normalizer=normalize_text),
        ImportTargetField("estado_administrativo", "Estado administrativo", False, ["estado", "estado_admin"], normalizer=normalize_text),
        ImportTargetField("estado_juridico", "Estado jurídico", False, ["estado legal", "situacion juridica", "situación jurídica"], normalizer=normalize_text),
        ImportTargetField("superficie", "Superficie", False, ["superficie_m2", "m2", "metros"], validator=positive_decimal_validator, normalizer=normalize_decimal),
        ImportTargetField("observaciones", "Observaciones", False, ["obs", "comentarios"], normalizer=normalize_text),
        ImportTargetField("folio_real", "Folio real", False, [], normalizer=normalize_text),
        ImportTargetField("circunscripcion", "Circunscripción", False, ["circunscripción", "circ"], normalizer=normalize_text),
        ImportTargetField("seccion", "Sección", False, ["sección", "sec"], normalizer=normalize_text),
        ImportTargetField("chacra", "Chacra", False, [], normalizer=normalize_text),
        ImportTargetField("quinta", "Quinta", False, [], normalizer=normalize_text),
        ImportTargetField("fraccion", "Fracción", False, ["fracción"], normalizer=normalize_text),
        ImportTargetField("manzana", "Manzana", False, ["mz", "mza"], normalizer=normalize_text),
        ImportTargetField("lote", "Lote", False, ["nro_lote", "numero_lote", "número_lote"], normalizer=normalize_text),
        ImportTargetField("parcela", "Parcela", False, [], normalizer=normalize_text),
        ImportTargetField("subparcela", "Subparcela", False, ["sub_parcela"], normalizer=normalize_text),
        ImportTargetField("nomenclatura_catastral", "Nomenclatura catastral", False, ["nomenclatura", "nomenclatura catastro"], normalizer=normalize_text),
        ImportTargetField("partida_inmobiliaria", "Partida inmobiliaria", False, ["partida"], normalizer=normalize_text),
        ImportTargetField("matricula", "Matrícula", False, ["matrícula", "matricula_registral"], normalizer=normalize_text),
        ImportTargetField("superficie_titulo", "Superficie título", False, ["superficie título", "superficie_de_titulo"], validator=positive_decimal_validator, normalizer=normalize_decimal),
        ImportTargetField("superficie_mensura", "Superficie mensura", False, ["superficie_de_mensura"], validator=positive_decimal_validator, normalizer=normalize_decimal),
        ImportTargetField("medidas", "Medidas", False, [], normalizer=normalize_text),
        ImportTargetField("situacion_posesoria", "Situación posesoria", False, ["situación posesoria"], normalizer=normalize_text),
        ImportTargetField("situacion_dominial", "Situación dominial", False, ["situación dominial"], normalizer=normalize_text),
        ImportTargetField("organismo_origen", "Organismo origen", False, ["organismo"], normalizer=normalize_text),
        ImportTargetField("fecha_desde", "Fecha desde", False, ["vigencia_desde"], validator=date_validator, normalizer=normalize_date),
        ImportTargetField("fecha_hasta", "Fecha hasta", False, ["vigencia_hasta"], validator=date_validator, normalizer=normalize_date),
        ImportTargetField("estado_dato", "Estado dato catastral", False, ["estado_dato_catastral"], validator=estado_dato_validator, normalizer=normalize_upper_text),
        ImportTargetField("observaciones_catastrales", "Observaciones catastrales", False, ["observaciones_catastro", "observaciones_registrales"], normalizer=normalize_text),
    ]

def build_inmuebles_preview(
    sheet: Any,
    mappings: list[ImportMapping],
    *,
    existing_codes: set[str] | None = None,
    desarrollos: list[dict[str, Any]] | None = None,
    context_desarrollo: dict[str, Any] | None = None,
    require_context_match: bool = False,
) -> ImportPreviewResult:
    preview = build_preview(sheet, inmueble_import_target_fields(), mappings)
    existing = {_code(c) for c in (existing_codes or set()) if _code(c)}
    seen: set[str] = set()
    desarrollo_index = _build_desarrollo_index(desarrollos or [])
    context_ref = _desarrollo_ref(context_desarrollo) if context_desarrollo else None

    for row in preview.rows:
        values = row.mapped_values
        code = _code(values.get("codigo_inmueble"))
        if code:
            if code in seen:
                row.errors.append("Código de inmueble duplicado dentro del archivo.")
            seen.add(code)
            if code in existing:
                row.errors.append("Código de inmueble ya existe en el sistema.")

        desarrollo_text = normalize_text(values.get("desarrollo"))
        resolved = desarrollo_index.get(normalize_column_name(desarrollo_text)) if desarrollo_text else context_ref
        if desarrollo_text and resolved is None:
            row.errors.append("Desarrollo/loteo informado no existe.")
        if desarrollo_text and context_ref and require_context_match and resolved != context_ref:
            row.errors.append("Desarrollo/loteo informado no coincide con el contexto obligatorio.")
        values["id_desarrollo"] = str(resolved.id_desarrollo) if resolved else None

        if not normalize_text(values.get("nombre_inmueble")) and code:
            values["nombre_inmueble"] = values.get("codigo_inmueble")
            row.warnings.append("Falta nombre: se usará el código como nombre por defecto.")
        if not normalize_text(values.get("estado_administrativo")):
            values["estado_administrativo"] = DEFAULT_ESTADO_ADMINISTRATIVO
            row.warnings.append(f"Falta estado administrativo: se usará {DEFAULT_ESTADO_ADMINISTRATIVO}.")
        if not normalize_text(values.get("estado_juridico")):
            values["estado_juridico"] = DEFAULT_ESTADO_JURIDICO
            row.warnings.append(f"Falta estado jurídico: se usará {DEFAULT_ESTADO_JURIDICO}.")
        fecha_desde = values.get("fecha_desde")
        fecha_hasta = values.get("fecha_hasta")
        if fecha_desde and fecha_hasta and str(fecha_hasta) < str(fecha_desde):
            row.errors.append("Fecha hasta no puede ser anterior a fecha desde.")
        if not has_catastral_data(values):
            row.warnings.append("No hay datos catastrales/registrales para crear.")
        row.status = STATUS_INVALID if row.errors else (STATUS_WARNING if row.warnings else STATUS_VALID)

    preview.valid_rows = sum(1 for row in preview.rows if row.status != STATUS_INVALID)
    preview.invalid_rows = preview.total_rows - preview.valid_rows
    return preview


def build_inmueble_import_payload(values: dict[str, Any]) -> dict[str, Any]:
    form_values = _string_form_values(values)
    return build_inmueble_payload(form_values)


def has_catastral_data(values: dict[str, Any]) -> bool:
    return any(normalize_text(values.get(field)) for field in CATASTRAL_FIELDS)


def build_catastral_import_payload(values: dict[str, Any]) -> dict[str, Any] | None:
    if not has_catastral_data(values):
        return None
    form_values = _string_form_values(values)
    if not form_values.get("observaciones_catastrales"):
        form_values["observaciones"] = None
    return build_dato_catastral_payload(form_values, incluir_avanzados=True)


def collect_existing_codes(api: InmueblesImportApi, codes: set[str]) -> tuple[set[str], list[str]]:
    existing: set[str] = set()
    errors: list[str] = []
    for code in sorted(codes):
        result = api.get_inmuebles(q=code, limit=20, offset=0)
        if not result.success:
            errors.append(f"No se pudo validar código {code}: {result.error_message}")
            continue
        for item in _items(result.data):
            if _code(item.get("codigo_inmueble")) == _code(code):
                existing.add(_code(code))
    return existing, errors


def confirm_inmuebles_import(api: InmueblesImportApi, preview: ImportPreviewResult, import_run_id: str) -> ImportConfirmResult:
    created = skipped = failed = 0
    errors_by_row: dict[int, list[str]] = {}
    warnings_by_row: dict[int, list[str]] = {}
    created_ids: list[int] = []
    for row in preview.rows:
        if row.status == STATUS_INVALID:
            skipped += 1
            errors_by_row[row.row_number] = list(row.errors)
            continue
        code = normalize_text(row.mapped_values.get("codigo_inmueble"))
        op_seed = f"{import_run_id}:{row.row_number}:{code}"
        inmueble_result = api.crear_inmueble(build_inmueble_import_payload(row.mapped_values), op_id=str(uuid5(NAMESPACE_URL, op_seed + ":inmueble")))
        if not inmueble_result.success:
            failed += 1
            errors_by_row[row.row_number] = [inmueble_result.error_message or "No se pudo crear el inmueble."]
            continue

        created += 1
        id_inmueble = _extract_id(inmueble_result.data, "id_inmueble")
        if id_inmueble is not None:
            created_ids.append(id_inmueble)

        catastral_payload = build_catastral_import_payload(row.mapped_values)
        if catastral_payload and id_inmueble is not None:
            cat_result = api.crear_dato_catastral_registral_inmueble(id_inmueble, catastral_payload, op_id=str(uuid5(NAMESPACE_URL, op_seed + ":catastral")))
            if not cat_result.success:
                warnings_by_row[row.row_number] = [
                    "Inmueble creado, pero falló el dato catastral/registral: "
                    f"{cat_result.error_message or 'No se pudo crear el dato catastral/registral.'}"
                ]
    return ImportConfirmResult(
        total=preview.total_rows,
        created=created,
        skipped=skipped,
        failed=failed,
        errors_by_row=errors_by_row,
        created_ids=created_ids,
        warnings_by_row=warnings_by_row,
    )


def _string_form_values(values: dict[str, Any]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for key, value in values.items():
        if value is None:
            result[key] = None
        elif isinstance(value, Decimal):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = datetime.combine(value, datetime.min.time()).isoformat()
        else:
            result[key] = str(value)
    return result


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat()
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed_date = datetime.strptime(text, fmt).date()
            return datetime.combine(parsed_date, datetime.min.time()).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        return None


def date_validator(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return None if normalize_date(value) else f"Fecha inválida. {DATE_FORMAT_HELP}"


def estado_dato_validator(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return None if str(value).strip().upper() in {"ACTIVO", "INACTIVO", "HISTORICO"} else "Debe ser ACTIVO, INACTIVO o HISTORICO."


def normalize_upper_text(value: Any) -> str | None:
    text = normalize_text(value)
    return text.upper() if text else None


def _build_desarrollo_index(items: list[dict[str, Any]]) -> dict[str, DesarrolloRef]:
    index: dict[str, DesarrolloRef] = {}
    for item in items:
        ref = _desarrollo_ref(item)
        if ref is None:
            continue
        for value in (ref.codigo_desarrollo, ref.nombre_desarrollo):
            key = normalize_column_name(value)
            if key:
                index[key] = ref
    return index


def _desarrollo_ref(item: dict[str, Any] | None) -> DesarrolloRef | None:
    if not item or item.get("id_desarrollo") is None:
        return None
    return DesarrolloRef(int(item["id_desarrollo"]), str(item.get("codigo_desarrollo") or ""), str(item.get("nombre_desarrollo") or ""))


def _code(value: Any) -> str:
    return (normalize_text(value) or "").casefold()


def _items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        items = data.get("items") or data.get("data") or []
        return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    return []


def _extract_id(data: Any, key: str) -> int | None:
    if isinstance(data, dict) and data.get(key) is not None:
        return int(data[key])
    return None
