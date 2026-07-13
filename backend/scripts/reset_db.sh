#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
DATABASE_DIR="${BACKEND_DIR}/database"
BAT_FILE="${SCRIPT_DIR}/reset_db.bat"

: "${PGHOST:=localhost}"
: "${PGPORT:=5432}"
: "${PGUSER:=postgres}"
: "${PGPASSWORD:=postgres}"
: "${DEV_DB:=inmobiliaria_dev}"
: "${TEST_DB:=inmobiliaria_test}"
export PGHOST PGPORT PGUSER PGPASSWORD

SQL_FILES=(
  "schema_inmobiliaria_20260418.sql"
  "seed_test_baseline.sql"
  "patch_plan_pago_venta_cronograma_v2_20260514.sql"
  "patch_plan_pago_venta_bloques_v2_20260515.sql"
  "patch_plan_pago_venta_metodo_plan_por_bloques_v2_20260515.sql"
  "patch_plan_pago_venta_bloque_metodo_liquidacion_20260527.sql"
  "patch_indices_financieros_20260527.sql"
  "patch_plan_pago_venta_bloque_indexacion_20260528.sql"
  "patch_relacion_persona_rol_porcentaje_responsabilidad_20260601.sql"
)
DEV_SEEDS=(
  "seed_minimo.sql"
  "seed_indices_financieros_demo.sql"
)

log() {
  printf '\n%s\n' "$*"
}

require_file() {
  local file="$1"
  if [[ ! -f "${file}" ]]; then
    printf 'ERROR: No existe el archivo requerido: %s\n' "${file}" >&2
    exit 1
  fi
}

audit_against_bat() {
  require_file "${BAT_FILE}"
  local bat_list sh_list missing extra
  bat_list="$(python - "${BAT_FILE}" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore')
seen = []
for match in re.finditer(r'database\\([^%\n\r"]+\.sql)', text, flags=re.IGNORECASE):
    name = match.group(1)
    if name not in seen:
        seen.append(name)
print('\n'.join(seen))
PY
)"
  sh_list="$(printf '%s\n' "${SQL_FILES[@]}" "${DEV_SEEDS[@]}" | awk '!seen[$0]++')"
  missing="$(comm -23 <(printf '%s\n' "${bat_list}" | sort) <(printf '%s\n' "${sh_list}" | sort) || true)"
  extra="$(comm -13 <(printf '%s\n' "${bat_list}" | sort) <(printf '%s\n' "${sh_list}" | sort) || true)"
  if [[ -n "${missing}" || -n "${extra}" ]]; then
    printf 'ERROR: Diferencias entre reset_db.bat y reset_db.sh.\n' >&2
    if [[ -n "${missing}" ]]; then
      printf 'Archivos invocados por reset_db.bat ausentes en reset_db.sh:\n%s\n' "${missing}" >&2
    fi
    if [[ -n "${extra}" ]]; then
      printf 'Archivos invocados por reset_db.sh ausentes en reset_db.bat:\n%s\n' "${extra}" >&2
    fi
    exit 1
  fi
  log "Auditoria reset_db.bat/reset_db.sh OK: $(printf '%s\n' "${bat_list}" | sed '/^$/d' | wc -l | tr -d ' ') archivos SQL coinciden."
}

run_sql() {
  local db="$1" label="$2" filename="$3" path
  path="${DATABASE_DIR}/${filename}"
  require_file "${path}"
  log "Aplicando ${label} en ${db}: ${filename}"
  local psql_file="${path}"
  local tmp_file=""
  if [[ "${filename}" == "schema_inmobiliaria_20260418.sql" ]]; then
    local server_version
    server_version="$(psql -v ON_ERROR_STOP=1 -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${db}" -Atc "SHOW server_version_num;")"
    if (( server_version < 170000 )) && grep -q '^SET transaction_timeout' "${path}"; then
      tmp_file="$(mktemp)"
      grep -v '^SET transaction_timeout' "${path}" > "${tmp_file}"
      psql_file="${tmp_file}"
      log "Compatibilidad PostgreSQL ${server_version}: se omite SET transaction_timeout del dump al aplicar el schema."
    fi
  fi
  if ! psql -v ON_ERROR_STOP=1 -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${db}" -f "${psql_file}"; then
    if [[ -n "${tmp_file}" ]]; then
      rm -f "${tmp_file}"
    fi
    printf 'ERROR aplicando %s en %s: %s\n' "${label}" "${db}" "${path}" >&2
    exit 1
  fi
  if [[ -n "${tmp_file}" ]]; then
    rm -f "${tmp_file}"
  fi
}

recreate_db() {
  local db="$1"
  log "============================"
  log "Reconstruyendo base ${db}"
  log "============================"
  psql -v ON_ERROR_STOP=1 -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${db}' AND pid <> pg_backend_pid();"
  psql -v ON_ERROR_STOP=1 -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres \
    -c "DROP DATABASE IF EXISTS \"${db}\";"
  psql -v ON_ERROR_STOP=1 -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres \
    -c "CREATE DATABASE \"${db}\";"
}

apply_common_files() {
  local db="$1"
  run_sql "${db}" "schema inicial" "schema_inmobiliaria_20260418.sql"
  run_sql "${db}" "baseline tecnico" "seed_test_baseline.sql"
  run_sql "${db}" "patch plan pago venta cronograma V2" "patch_plan_pago_venta_cronograma_v2_20260514.sql"
  run_sql "${db}" "patch plan pago venta bloques V2" "patch_plan_pago_venta_bloques_v2_20260515.sql"
  run_sql "${db}" "patch metodo PLAN_POR_BLOQUES V2" "patch_plan_pago_venta_metodo_plan_por_bloques_v2_20260515.sql"
  run_sql "${db}" "patch metodo_liquidacion por bloque" "patch_plan_pago_venta_bloque_metodo_liquidacion_20260527.sql"
  run_sql "${db}" "patch indices financieros" "patch_indices_financieros_20260527.sql"
  run_sql "${db}" "patch indexacion por bloque" "patch_plan_pago_venta_bloque_indexacion_20260528.sql"
  run_sql "${db}" "patch porcentaje responsabilidad comprador" "patch_relacion_persona_rol_porcentaje_responsabilidad_20260601.sql"
}

log "============================"
log "Reset DB - Sistema Inmobiliario (Linux/Codex Cloud)"
log "============================"
log "Backend dir: ${BACKEND_DIR}"
log "Host: ${PGHOST}:${PGPORT}"
log "Usuario PostgreSQL: ${PGUSER}"
log "DEV_DB: ${DEV_DB}"
log "TEST_DB: ${TEST_DB}"

audit_against_bat
for sql_file in "${SQL_FILES[@]}" "${DEV_SEEDS[@]}"; do
  require_file "${DATABASE_DIR}/${sql_file}"
done

recreate_db "${DEV_DB}"
apply_common_files "${DEV_DB}"
run_sql "${DEV_DB}" "seed minimo" "seed_minimo.sql"
run_sql "${DEV_DB}" "seed demo de indices financieros" "seed_indices_financieros_demo.sql"
log "Reset DEV finalizado correctamente: ${DEV_DB}"

recreate_db "${TEST_DB}"
apply_common_files "${TEST_DB}"
log "NOTA: no se aplica seed de negocio en ${TEST_DB}. Los tests deben crear sus propios datos de dominio."
log "Reset TEST finalizado correctamente: ${TEST_DB}"

log "============================"
log "Bases reseteadas correctamente"
log "- ${DEV_DB}  (baseline tecnico + seed + indices financieros demo)"
log "- ${TEST_DB} (solo baseline tecnico)"
log "============================"
