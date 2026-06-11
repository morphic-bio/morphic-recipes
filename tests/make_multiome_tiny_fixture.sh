#!/usr/bin/env bash
# Generate a tiny downsampled 10x multiome fixture for a fast end-to-end smoke
# of the multiome recipe (STAR Solo + Chromap ATAC + MACS peak MEX) in ~1-2 min,
# instead of a ~35-min full run. Downsamples the first N read-pairs from a source
# multiome dataset into generic fixture filenames the composition smoke looks for.
#
# This is the "tiny fixture" half of the compose-up authoring contract: a recipe
# that emits optional layers should ship (or be able to generate) a small fixture
# so an agent can verify the composed command actually RUNS — a dry-run text check
# is not sufficient (it missed the --outSAMtype None / GX-tag incompatibility).
#
# Usage (defaults target the CAT-ATAC GSE288996 subset on host pikachu):
#   make_multiome_tiny_fixture.sh [--reads N] [--out-dir DIR] \
#     [--gex-r1 P --gex-r2 P --atac-r1 P --atac-barcode P --atac-r2 P]
# The fixture is generated data — keep it out of git (tests/fixtures/ is gitignored).
set -eu  # NOTE: no pipefail — `zcat | head` intentionally SIGPIPEs zcat early.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
N_READS="${MULTIOME_FIXTURE_READS:-300000}"
OUT_DIR="${SCRIPT_DIR}/fixtures/multiome_tiny"
SRC="/mnt/pikachu/catatac_gse288996/fastq"
GEX_R1="${SRC}/GEX/SRR32265752_1.fastq.gz"
GEX_R2="${SRC}/GEX/SRR32265752_2.fastq.gz"
ATAC_R1="${SRC}/ATAC/SRR32265760_1.fastq.gz"
ATAC_BARCODE="${SRC}/ATAC/SRR32265760_2.fastq.gz"
ATAC_R2="${SRC}/ATAC/SRR32265760_3.fastq.gz"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reads) N_READS="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --gex-r1) GEX_R1="$2"; shift 2 ;;
    --gex-r2) GEX_R2="$2"; shift 2 ;;
    --atac-r1) ATAC_R1="$2"; shift 2 ;;
    --atac-barcode) ATAC_BARCODE="$2"; shift 2 ;;
    --atac-r2) ATAC_R2="$2"; shift 2 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "ERROR: unknown arg $1" >&2; exit 1 ;;
  esac
done

for f in "$GEX_R1" "$GEX_R2" "$ATAC_R1" "$ATAC_BARCODE" "$ATAC_R2"; do
  [[ -f "$f" ]] || { echo "ERROR: source FASTQ missing: $f" >&2; exit 1; }
done

mkdir -p "$OUT_DIR"
lines=$(( N_READS * 4 ))
echo "Downsampling first ${N_READS} reads/file -> ${OUT_DIR}"
take() { zcat "$1" | head -n "$lines" | gzip > "$2"; echo "  wrote $(basename "$2")"; }
take "$GEX_R1"      "${OUT_DIR}/gex_R1.fastq.gz"
take "$GEX_R2"      "${OUT_DIR}/gex_R2.fastq.gz"
take "$ATAC_R1"     "${OUT_DIR}/atac_R1.fastq.gz"
take "$ATAC_BARCODE" "${OUT_DIR}/atac_barcode.fastq.gz"
take "$ATAC_R2"     "${OUT_DIR}/atac_R3.fastq.gz"

{
  echo "reads_per_file=${N_READS}"
  echo "source_gex_r1=${GEX_R1}"
  echo "source_atac_r1=${ATAC_R1}"
  echo "generated_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "purpose=fast end-to-end multiome recipe smoke (compose-up contract)"
} > "${OUT_DIR}/MANIFEST.txt"
echo "Fixture ready. Smoke it with run_agent_protocol_composition_smoke.sh"
echo "(it auto-detects this fixture), or run run_multiome_minimal.sh against ${OUT_DIR}/*."
