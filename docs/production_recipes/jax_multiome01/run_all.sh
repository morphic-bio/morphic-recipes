#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

ROOT_DIRECTORY="${JAX_MULTIOME01_ROOT:-}"
STAR_SUITE_ROOT="${STAR_SUITE_ROOT:-/mnt/pikachu/STAR-suite}"
CHROMAP_SUITE_ROOT="${CHROMAP_SUITE_ROOT:-}"
RELEASE_GLOBUS_ENDPOINT="${JAX_MULTIOME01_RELEASE_GLOBUS_ENDPOINT:-61fb8b9a-9b52-456e-928c-30c0fb0140bf}"
LOCAL_GLOBUS_ENDPOINT="${JAX_MULTIOME01_LOCAL_GLOBUS_ENDPOINT:-}"
RAW_GLOBUS_PATH="${JAX_MULTIOME01_RAW_GLOBUS_PATH:-/JAX_Multiome01_processed/large_files/star_multiome_prod_globus_20260517T183219Z/raw}"
LARGE_FILES_GLOBUS_PATH="${JAX_MULTIOME01_LARGE_FILES_GLOBUS_PATH:-/JAX_Multiome01_processed/large_files/star_multiome_prod_globus_20260517T183219Z}"
COMPACT_H5MU_GLOBUS_PATH="${JAX_MULTIOME01_COMPACT_H5MU_GLOBUS_PATH:-/JAX_Multiome01_processed/JAX-Multiome01-5-18-26-revised/h5mu}"
REMOTE_HOST="${MULTIOME_REMOTE_HOST:-10.159.4.53}"
REMOTE_ROOT="${MULTIOME_REMOTE_ROOT:-/home/lhhung/jax_multiome_remote_downstream_production}"
THREADS="${STAR_MULTIOME_THREADS:-16}"
CHROMAP_THREADS="${STAR_MULTIOME_CHROMAP_THREADS:-16}"
INPUT_FORMAT="${STAR_MULTIOME_INPUT_FORMAT:-fastq}"
CHROMAP_START_MODE="${STAR_MULTIOME_CHROMAP_START_MODE:-concurrent}"
CHROMAP_MACS3_FRAG_QVALUE="${STAR_MULTIOME_CHROMAP_MACS3_FRAG_QVALUE:-0}"
GENOME_DIR="${STAR_MULTIOME_GENOME_DIR:-/storage/autoindex_110_44/bulk_index}"
GEX_WHITELIST="${STAR_MULTIOME_GEX_WHITELIST:-/mnt/pikachu/atac-seq/10xMultiome/pbmc_unsorted_3k/open_source_full_20260424_015259/refs/737K-arc-v1_gex.txt}"
CHROMAP_REF="${STAR_MULTIOME_CHROMAP_REF:-/storage/autoindex_110_44/bulk_index/cellranger_ref/genome.fa}"
CHROMAP_INDEX="${STAR_MULTIOME_CHROMAP_INDEX:-/mnt/pikachu/atac-seq/benchmarks/pbmc_unsorted_3k_100k/chromap_index/genome.index}"
ATAC_WHITELIST="${STAR_MULTIOME_ATAC_WHITELIST:-/mnt/pikachu/atac-seq/benchmarks/pbmc_unsorted_3k_100k/chromap_index/737K-arc-v1_atac.txt}"
ATAC_TO_GEX="${STAR_MULTIOME_ATAC_TO_GEX:-/mnt/pikachu/atac-seq/benchmarks/pbmc_unsorted_3k_100k/chromap_index/atac2gex.tsv}"
GLOBUS_POLL_SECONDS="${JAX_MULTIOME01_GLOBUS_POLL_SECONDS:-60}"
RAW_DIR=""
LARGE_FILES_DIR=""
COMPACT_H5MU_DIR=""
OUTPUT_ROOT=""
SAMPLE_MANIFEST=""
START_AT=""
SAMPLES=""
DOWNLOAD_RAW="1"
DOWNLOAD_LARGE_FILES_RELEASE="0"
DOWNLOAD_COMPACT_H5MU="1"
RUN_PRODUCTION="1"
GLOBUS_UPLOAD_LARGE_FILES="0"
SYNC_IMAGES="0"
KEEP_REMOTE="0"
FORCE="0"
DRY_RUN="0"

usage() {
  cat <<'EOF'
Usage:
  run_all.sh --root-directory PATH --local-globus-endpoint UUID [options]

Downloads the JAX Multiome01 Globus release inputs into a working root,
generates a relocated production sample manifest, and runs the STAR/Chromap
plus remote post-MEX production recipe.

Required unless --skip-download is used:
  --local-globus-endpoint UUID
                           Local Globus endpoint used as the download target.

Required:
  --root-directory PATH     Working root for downloads, metadata, logs, outputs.

Installation assumptions:
  --star-suite-root PATH    STAR-suite checkout with core/ (default: /mnt/pikachu/STAR-suite)
  --chromap-suite-root PATH Optional Chromap-suite checkout marker for local provenance.
  docker, python3, make, ssh, rsync, and globus CLI are available as needed.

Download options:
  --release-globus-endpoint UUID
  --raw-globus-path PATH
  --large-files-globus-path PATH
  --compact-h5mu-globus-path PATH
  --raw-dir PATH
  --large-files-dir PATH
  --compact-h5mu-dir PATH
  --download-large-files-release
                           Also download the full large-file release tree.
                           This is not needed to rerun the analysis because
                           generated BAM/Y-noY FASTQs are rebuilt.
  --skip-download
  --skip-raw-download
  --skip-compact-h5mu-download
  --download-only

Run options:
  --output-root PATH
  --sample-manifest PATH    Use an existing relocated manifest instead of generating one.
  --remote-host HOST
  --remote-root PATH
  --threads N
  --chromap-threads N
  --input-format fastq|cbq
                           Use CBQ-native STAR/Chromap inputs from a supplied
                           manifest with gex_cbq, atac_read_pair_cbq, and
                           atac_barcode_cbq columns.
  --chromap-start-mode MODE
  --chromap-macs3-frag-qvalue Q
                           Use MACS3 FRAG q-value/FDR peak selection in local
                           ATAC peak-MEX materialization; 0 preserves default
                           p-value mode (default: 0)
  --genome-dir PATH
  --gex-whitelist PATH
  --chromap-ref PATH
  --chromap-index PATH
  --atac-whitelist PATH
  --atac-to-gex PATH
  --samples CSV
  --start-at SAMPLE
  --sync-images             Sync Docker images to the remote host before downstream.
  --keep-remote
  --force
  --skip-run

Delivery options:
  --globus-upload-large-files
                           Re-upload generated large files after successful samples.
                           Off by default to avoid accidental new deliveries.

Other:
  --dry-run                 Print actions without running transfers or production.
  --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root-directory|--root) ROOT_DIRECTORY="$2"; shift 2 ;;
    --star-suite-root) STAR_SUITE_ROOT="$2"; shift 2 ;;
    --chromap-suite-root) CHROMAP_SUITE_ROOT="$2"; shift 2 ;;
    --release-globus-endpoint) RELEASE_GLOBUS_ENDPOINT="$2"; shift 2 ;;
    --local-globus-endpoint) LOCAL_GLOBUS_ENDPOINT="$2"; shift 2 ;;
    --raw-globus-path) RAW_GLOBUS_PATH="$2"; shift 2 ;;
    --large-files-globus-path) LARGE_FILES_GLOBUS_PATH="$2"; shift 2 ;;
    --compact-h5mu-globus-path) COMPACT_H5MU_GLOBUS_PATH="$2"; shift 2 ;;
    --raw-dir) RAW_DIR="$2"; shift 2 ;;
    --large-files-dir) LARGE_FILES_DIR="$2"; shift 2 ;;
    --compact-h5mu-dir) COMPACT_H5MU_DIR="$2"; shift 2 ;;
    --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
    --sample-manifest) SAMPLE_MANIFEST="$2"; shift 2 ;;
    --remote-host) REMOTE_HOST="$2"; shift 2 ;;
    --remote-root) REMOTE_ROOT="$2"; shift 2 ;;
    --threads) THREADS="$2"; shift 2 ;;
    --chromap-threads) CHROMAP_THREADS="$2"; shift 2 ;;
    --input-format) INPUT_FORMAT="$2"; shift 2 ;;
    --chromap-start-mode) CHROMAP_START_MODE="$2"; shift 2 ;;
    --chromap-macs3-frag-qvalue) CHROMAP_MACS3_FRAG_QVALUE="$2"; shift 2 ;;
    --genome-dir) GENOME_DIR="$2"; shift 2 ;;
    --gex-whitelist) GEX_WHITELIST="$2"; shift 2 ;;
    --chromap-ref) CHROMAP_REF="$2"; shift 2 ;;
    --chromap-index) CHROMAP_INDEX="$2"; shift 2 ;;
    --atac-whitelist) ATAC_WHITELIST="$2"; shift 2 ;;
    --atac-to-gex) ATAC_TO_GEX="$2"; shift 2 ;;
    --samples) SAMPLES="$2"; shift 2 ;;
    --start-at) START_AT="$2"; shift 2 ;;
    --download-large-files-release) DOWNLOAD_LARGE_FILES_RELEASE="1"; shift ;;
    --skip-download) DOWNLOAD_RAW="0"; DOWNLOAD_LARGE_FILES_RELEASE="0"; DOWNLOAD_COMPACT_H5MU="0"; shift ;;
    --skip-raw-download) DOWNLOAD_RAW="0"; shift ;;
    --skip-compact-h5mu-download) DOWNLOAD_COMPACT_H5MU="0"; shift ;;
    --download-only) RUN_PRODUCTION="0"; shift ;;
    --skip-run) RUN_PRODUCTION="0"; shift ;;
    --globus-upload-large-files) GLOBUS_UPLOAD_LARGE_FILES="1"; shift ;;
    --sync-images) SYNC_IMAGES="1"; shift ;;
    --keep-remote) KEEP_REMOTE="1"; shift ;;
    --force) FORCE="1"; shift ;;
    --dry-run) DRY_RUN="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      if [[ -z "${ROOT_DIRECTORY}" && "$1" != -* ]]; then
        ROOT_DIRECTORY="$1"
        shift
      else
        echo "ERROR: unknown argument $1" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

[[ -n "${ROOT_DIRECTORY}" ]] || { echo "ERROR: --root-directory is required" >&2; usage >&2; exit 1; }

ROOT_DIRECTORY="$(realpath -m "${ROOT_DIRECTORY}")"
RAW_DIR="$(realpath -m "${RAW_DIR:-${ROOT_DIRECTORY}/raw}")"
LARGE_FILES_DIR="$(realpath -m "${LARGE_FILES_DIR:-${ROOT_DIRECTORY}/downloads/large_files}")"
COMPACT_H5MU_DIR="$(realpath -m "${COMPACT_H5MU_DIR:-${ROOT_DIRECTORY}/downloads/h5mu}")"
OUTPUT_ROOT="$(realpath -m "${OUTPUT_ROOT:-${ROOT_DIRECTORY}/outputs/star_multiome_prod_globus_reproduction_$(date -u +%Y%m%dT%H%M%SZ)}")"
METADATA_DIR="${ROOT_DIRECTORY}/metadata"
LOG_DIR="${ROOT_DIRECTORY}/logs"
GENERATED_MANIFEST="${METADATA_DIR}/sample_manifest.tsv"
LOG_FILE="${LOG_DIR}/run_all.log"

log() {
  mkdir -p "${LOG_DIR}"
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${LOG_FILE}"
}

quote_cmd() {
  printf '%q ' "$@"
  printf '\n'
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 1
  }
}

require_path() {
  [[ -e "$1" ]] || {
    echo "ERROR: required path missing: $1" >&2
    exit 1
  }
}

submit_globus_transfer() {
  local source_path="$1"
  local dest_path="$2"
  local label="$3"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[dry-run] globus transfer ${RELEASE_GLOBUS_ENDPOINT}:${source_path} -> ${LOCAL_GLOBUS_ENDPOINT}:${dest_path}"
    return 0
  fi

  local submit_json task_id
  log "Submitting Globus transfer: ${label}"
  submit_json="$(globus transfer \
    "${RELEASE_GLOBUS_ENDPOINT}" \
    "${LOCAL_GLOBUS_ENDPOINT}" \
    "${source_path%/}/" \
    "${dest_path%/}/" \
    --recursive \
    --sync-level checksum \
    --label "${label}" \
    --format json)"
  printf '%s\n' "${submit_json}" > "${LOG_DIR}/${label//[^A-Za-z0-9_.-]/_}.submit.json"
  task_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("task_id",""))' <<< "${submit_json}")"
  [[ -n "${task_id}" ]] || { echo "ERROR: Globus transfer did not return a task_id" >&2; exit 1; }
  log "Waiting for Globus task ${task_id}"
  globus task wait --polling-interval "${GLOBUS_POLL_SECONDS}" "${task_id}" | tee -a "${LOG_FILE}"
}

write_manifest_from_raw() {
  mkdir -p "${METADATA_DIR}"
  if [[ -n "${SAMPLE_MANIFEST}" ]]; then
    SAMPLE_MANIFEST="$(realpath "${SAMPLE_MANIFEST}")"
    log "Using supplied sample manifest: ${SAMPLE_MANIFEST}"
    if [[ "${SAMPLE_MANIFEST}" != "${GENERATED_MANIFEST}" ]]; then
      cp "${SAMPLE_MANIFEST}" "${GENERATED_MANIFEST}"
    fi
    return 0
  fi

  log "Generating relocated sample manifest from raw FASTQs under ${RAW_DIR}"
  python3 - "${RAW_DIR}" "${GENERATED_MANIFEST}" <<'PY'
from pathlib import Path
import sys

raw = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])

samples = [
    ("Und-KOLF2.2J", "Und-KOLF2.2J", "25E113-L1", "25E113-L10", "20251015_GT25-CourtoisE-265", "20251009_GT25-CourtoisE-263"),
    ("TE-KOLF2.2J-Nor", "TE-KOLF2.2J-Nor", "25E113-L2", "25E113-L11", "20251015_GT25-CourtoisE-265", "20251009_GT25-CourtoisE-263"),
    ("TE-KOLF2.2J-Hyp", "TE-KOLF2.2J-Hyp", "25E113-L3", "25E113-L12", "20251015_GT25-CourtoisE-265", "20251009_GT25-CourtoisE-263"),
    ("PrS-KOLF2.2J-Nor-Day4", "PrS-KOLF2.2J-Nor-Day4", "25E113-L4", "25E113-L13", "20251015_GT25-CourtoisE-265,20251028_GT25-CourtoisE-265-run2", "20251009_GT25-CourtoisE-263"),
    ("ExM-KOLF2.2J-Day4", "ExM-KOLF2.2J-Day4", "25E113-L5", "25E113-L14", "20251028_GT25-CourtoisE-268", "20251009_GT25-CourtoisE-263"),
    ("PrS-KOLF2.2J-Hyp-Day4", "PrS-KOLF2.2J-Hyp-Day4", "25E113-L6", "25E113-L15", "20251028_GT25-CourtoisE-268", "20251009_GT25-CourtoisE-263"),
    ("PrS-KOLF2.2J-Nor-Day6", "PrS-KOLF2.2J-Nor-Day6", "25E113-L7", "25E113-L16", "20251028_GT25-CourtoisE-268", "20251009_GT25-CourtoisE-263"),
    ("ExM-KOLF2.2J-Day6", "ExM-KOLF2.2J-Day6", "25E113-L8", "25E113-L17", "20251028_GT25-CourtoisE-268", "20251009_GT25-CourtoisE-263,20251029_GT25-CourtoisE-263-run2"),
    ("PrS-KOLF2.2J-Hyp-Day6", "PrS-KOLF2.2J-Hyp-Day6", "25E113-L9", "25E113-L18", "20251028_GT25-CourtoisE-268", "20251009_GT25-CourtoisE-263"),
]

def csv_for(lib: str, read: str) -> str:
    paths = sorted(raw.rglob(f"{lib}_*_R{read}_*.fastq.gz"))
    if not paths:
        raise SystemExit(f"missing FASTQs for {lib} R{read} under {raw}")
    return ",".join(str(p.resolve()) for p in paths)

headers = [
    "sample",
    "sample_slug",
    "atac_library",
    "gex_library",
    "gex_r1",
    "gex_r2",
    "atac_r1",
    "atac_barcode",
    "atac_r2",
    "gex_run_ids",
    "atac_run_ids",
]
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", encoding="utf-8") as handle:
    print("\t".join(headers), file=handle)
    for sample, slug, atac_lib, gex_lib, gex_run_ids, atac_run_ids in samples:
        row = [
            sample,
            slug,
            atac_lib,
            gex_lib,
            csv_for(gex_lib, "1"),
            csv_for(gex_lib, "2"),
            csv_for(atac_lib, "1"),
            csv_for(atac_lib, "2"),
            csv_for(atac_lib, "3"),
            gex_run_ids,
            atac_run_ids,
        ]
        print("\t".join(row), file=handle)
PY
}

mkdir -p "${ROOT_DIRECTORY}" "${RAW_DIR}" "${LARGE_FILES_DIR}" "${COMPACT_H5MU_DIR}" "${METADATA_DIR}" "${LOG_DIR}" "$(dirname "${OUTPUT_ROOT}")"

if [[ "${DOWNLOAD_RAW}" == "1" || "${DOWNLOAD_LARGE_FILES_RELEASE}" == "1" || "${DOWNLOAD_COMPACT_H5MU}" == "1" ]]; then
  [[ -n "${LOCAL_GLOBUS_ENDPOINT}" ]] || {
    echo "ERROR: --local-globus-endpoint is required for downloads" >&2
    exit 1
  }
  require_command globus
fi

require_command python3
if [[ "${RUN_PRODUCTION}" == "1" ]]; then
  require_command docker
  require_command make
  require_command ssh
  require_command rsync
  require_path "${STAR_SUITE_ROOT}/core/legacy/source"
  [[ -z "${CHROMAP_SUITE_ROOT}" ]] || require_path "${CHROMAP_SUITE_ROOT}"
  for path in "${GENOME_DIR}" "${GEX_WHITELIST}" "${CHROMAP_REF}" "${CHROMAP_INDEX}" "${ATAC_WHITELIST}" "${ATAC_TO_GEX}"; do
    require_path "${path}"
  done
fi

log "JAX Multiome01 run_all root: ${ROOT_DIRECTORY}"
log "morphic-recipes repo: ${REPO_ROOT}"
log "STAR-suite root: ${STAR_SUITE_ROOT}"
[[ -z "${CHROMAP_SUITE_ROOT}" ]] || log "Chromap-suite root: ${CHROMAP_SUITE_ROOT}"

if [[ "${DOWNLOAD_RAW}" == "1" ]]; then
  submit_globus_transfer "${RAW_GLOBUS_PATH}" "${RAW_DIR}" "JAX Multiome01 raw FASTQs"
else
  log "Skipping raw FASTQ download"
fi

if [[ "${DOWNLOAD_LARGE_FILES_RELEASE}" == "1" ]]; then
  submit_globus_transfer "${LARGE_FILES_GLOBUS_PATH}" "${LARGE_FILES_DIR}" "JAX Multiome01 full large-file release"
else
  log "Skipping full large-file release download"
fi

if [[ "${DOWNLOAD_COMPACT_H5MU}" == "1" ]]; then
  submit_globus_transfer "${COMPACT_H5MU_GLOBUS_PATH}" "${COMPACT_H5MU_DIR}" "JAX Multiome01 compact h5mu packet"
else
  log "Skipping compact h5mu packet download"
fi

write_manifest_from_raw

if [[ "${RUN_PRODUCTION}" != "1" ]]; then
  log "Download/manifest stage complete; --skip-run or --download-only was set"
  exit 0
fi

production_args=(
  "${REPO_ROOT}/scripts/run_jax_multiome01_production.sh"
  --raw-dir "${RAW_DIR}"
  --sample-manifest "${GENERATED_MANIFEST}"
  --output-root "${OUTPUT_ROOT}"
  --threads "${THREADS}"
  --chromap-threads "${CHROMAP_THREADS}"
  --input-format "${INPUT_FORMAT}"
  --chromap-low-mem
  --chromap-macs3-frag-low-mem
  --chromap-start-mode "${CHROMAP_START_MODE}"
)
if python3 - "${CHROMAP_MACS3_FRAG_QVALUE}" <<'PY'
import math
import sys

try:
    q = float(sys.argv[1])
except ValueError:
    raise SystemExit(2)
if math.isnan(q) or q < 0.0 or q > 1.0:
    raise SystemExit(2)
raise SystemExit(0 if q > 0.0 else 1)
PY
then
  production_args+=(--chromap-macs3-frag-qvalue "${CHROMAP_MACS3_FRAG_QVALUE}")
elif [[ "$?" == "2" ]]; then
  echo "ERROR: --chromap-macs3-frag-qvalue must be 0 (disabled) or in (0, 1]" >&2
  exit 1
fi
[[ "${SYNC_IMAGES}" != "1" ]] && production_args+=(--no-sync-images)
[[ "${KEEP_REMOTE}" == "1" ]] && production_args+=(--keep-remote)
[[ "${FORCE}" == "1" ]] && production_args+=(--force)
[[ -n "${START_AT}" ]] && production_args+=(--start-at "${START_AT}")
[[ -n "${SAMPLES}" ]] && production_args+=(--samples "${SAMPLES}")
if [[ "${GLOBUS_UPLOAD_LARGE_FILES}" == "1" ]]; then
  production_args+=(--globus-upload-large-files)
fi

log "Production command:"
quote_cmd "${production_args[@]}" | tee -a "${LOG_FILE}"

if [[ "${DRY_RUN}" == "1" ]]; then
  log "[dry-run] production was not launched"
  exit 0
fi

export STAR_SUITE_ROOT
export MULTIOME_REMOTE_HOST="${REMOTE_HOST}"
export MULTIOME_REMOTE_ROOT="${REMOTE_ROOT}"
export STAR_MULTIOME_GENOME_DIR="${GENOME_DIR}"
export STAR_MULTIOME_GEX_WHITELIST="${GEX_WHITELIST}"
export STAR_MULTIOME_CHROMAP_REF="${CHROMAP_REF}"
export STAR_MULTIOME_CHROMAP_INDEX="${CHROMAP_INDEX}"
export STAR_MULTIOME_ATAC_WHITELIST="${ATAC_WHITELIST}"
export STAR_MULTIOME_ATAC_TO_GEX="${ATAC_TO_GEX}"

"${production_args[@]}" 2>&1 | tee "${LOG_DIR}/production.log"
log "PASS: JAX Multiome01 run_all complete"
log "Output root: ${OUTPUT_ROOT}"
