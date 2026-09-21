#!/usr/bin/env bash
# backfill_range.sh — rellena extractores diarios en un rango de fechas.
#
# Uso:
#   ./scripts/backfill_range.sh START END [fuentes...]
#   ./scripts/backfill_range.sh 2026-06-01 2026-08-31
#   ./scripts/backfill_range.sh 2026-06-01 2026-08-31 siar embalses
#
# Fuentes por defecto: siar embalses ria
# - SiAR: extract_siar.py --ds DATE --no-station-meta + ~70s entre días (cuota API)
# - Embalses / RIA: extract respectivos + pausa corta (8s)
# - Si ya hay filas para esa fecha (psql + DATABASE_URL), se omite (SKIP)
# - Fallo de un día/fuente: log FAIL y continúa (no aborta el rango)
#
# En VPS / Airflow (ejemplo):
#   ssh data-flight 'docker exec -w /opt/airflow data-flight-pipeline-airflow-scheduler-1 \
#     bash /opt/airflow/scripts/backfill_range.sh 2026-06-01 2026-08-31'
# o día a día con:
#   docker exec ... /opt/airflow/.venv/bin/python scripts/extract_siar.py --ds YYYY-MM-DD --no-station-meta
#
set -u
set -o pipefail

START="${1:-}"
END="${2:-}"
shift 2 2>/dev/null || true
SOURCES=("$@")
if [[ ${#SOURCES[@]} -eq 0 ]]; then
  SOURCES=(siar embalses ria)
fi

if [[ -z "$START" || -z "$END" ]]; then
  echo "Uso: $0 START END [siar|embalses|ria ...]" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="${BACKFILL_LOG_DIR:-/tmp}"
mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="/tmp"
LOG_FILE="${BACKFILL_LOG_FILE:-$LOG_DIR/backfill_range_${START}_${END}.log}"

PYTHON="${BACKFILL_PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
  elif [[ -x "/opt/airflow/.venv/bin/python" ]]; then
    PYTHON="/opt/airflow/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

SIAR_SLEEP="${SIAR_SLEEP_SEC:-70}"
OTHER_SLEEP="${OTHER_SLEEP_SEC:-8}"

log() {
  local line="[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*"
  echo "$line" | tee -a "$LOG_FILE"
}

# Returns 0 if data already exists for source+date (SKIP).
has_data() {
  local source="$1" ds="$2"
  if [[ -z "${DATABASE_URL:-}" ]] && [[ -z "${PGHOST:-}" ]]; then
    return 1
  fi
  local sql=""
  case "$source" in
    siar)
      sql="SELECT 1 FROM raw.raw_siar_clima_diario WHERE ccaa_codigo='AND' AND fecha=DATE '$ds' LIMIT 1;"
      ;;
    ria)
      sql="SELECT 1 FROM raw.raw_ria_clima_diario WHERE fecha=DATE '$ds' LIMIT 1;"
      ;;
    embalses)
      # tabla sin schema fijo en extract; probar raw y public
      sql="SELECT 1 FROM raw.raw_embalses_diarios WHERE fecha=DATE '$ds' LIMIT 1;"
      ;;
    *)
      return 1
      ;;
  esac
  if command -v psql >/dev/null 2>&1; then
    if [[ -n "${DATABASE_URL:-}" ]]; then
      psql "$DATABASE_URL" -Atqc "$sql" 2>/dev/null | grep -q 1 && return 0
      # embalses fallback sin schema
      if [[ "$source" == "embalses" ]]; then
        psql "$DATABASE_URL" -Atqc "SELECT 1 FROM raw_embalses_diarios WHERE fecha=DATE '$ds' LIMIT 1;" 2>/dev/null | grep -q 1 && return 0
      fi
    else
      psql -Atqc "$sql" 2>/dev/null | grep -q 1 && return 0
    fi
  fi
  return 1
}

run_source() {
  local source="$1" ds="$2"
  local rc=0
  case "$source" in
    siar)
      "$PYTHON" extract_siar.py --ds "$ds" --no-station-meta || rc=$?
      ;;
    ria)
      "$PYTHON" extract_ria.py --ds "$ds" || rc=$?
      ;;
    embalses)
      "$PYTHON" extract_embalses.py --ds "$ds" || rc=$?
      ;;
    *)
      log "FAIL $ds $source — fuente desconocida"
      return 1
      ;;
  esac
  return $rc
}

log "START range=$START..$END sources=${SOURCES[*]} python=$PYTHON log=$LOG_FILE"

# Iterate calendar days inclusive
current="$START"
ok_n=0
fail_n=0
skip_n=0

while [[ "$current" < "$END" || "$current" == "$END" ]]; do
  for source in "${SOURCES[@]}"; do
    if has_data "$source" "$current"; then
      log "SKIP $current $source — ya hay datos"
      skip_n=$((skip_n + 1))
      continue
    fi
    log "RUN  $current $source"
    if run_source "$source" "$current"; then
      log "OK   $current $source"
      ok_n=$((ok_n + 1))
    else
      log "FAIL $current $source"
      fail_n=$((fail_n + 1))
    fi
    if [[ "$source" == "siar" ]]; then
      sleep "$SIAR_SLEEP"
    else
      sleep "$OTHER_SLEEP"
    fi
  done
  # next day (GNU date)
  if date -d "$current + 1 day" +%F >/dev/null 2>&1; then
    current="$(date -d "$current + 1 day" +%F)"
  else
    # BSD fallback
    current="$(date -j -v+1d -f %Y-%m-%d "$current" +%F)"
  fi
done

log "DONE ok=$ok_n fail=$fail_n skip=$skip_n log=$LOG_FILE"
exit 0
