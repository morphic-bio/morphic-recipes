#!/usr/bin/env bash
# Agent smoke test for the compose-up output-composition contract.
# Part 1: deterministic --profile / --dry-run mechanism check (skips if fixtures absent).
# Part 2: spawns a fresh LLM agent and checks it composes to the target scope.
# See agent_protocol_composition_smoke.md for the full spec.
#
# AGENT_CMD must read a prompt on stdin and print the agent's answer on stdout,
# e.g.  AGENT_CMD='claude -p'  tests/run_agent_protocol_composition_smoke.sh
# With AGENT_CMD unset, Part 1 still runs and Part 2 prints prompt + criteria
# (documentation mode) so CI never fails on hosts without an agent runner.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECIPES_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RECIPE="${RECIPES_ROOT}/scripts/run_star_multiome_lane_smoke.sh"
MINIMAL="${RECIPES_ROOT}/scripts/run_multiome_minimal.sh"
rc=0

# ---- fixtures for the deterministic dry-run (CAT-ATAC on this host) ----
D=/mnt/pikachu/catatac_gse288996
STAR_BIN_DEF=/mnt/pikachu/STAR-suite-v1.3.0b/core/legacy/source/STAR
have_fixtures=1
for f in "$D/fastq/GEX/SRR32265752_1.fastq.gz" "$D/fastq/GEX/SRR32265752_2.fastq.gz" \
         "$D/fastq/ATAC/SRR32265760_1.fastq.gz" "$D/fastq/ATAC/SRR32265760_2.fastq.gz" \
         "$D/fastq/ATAC/SRR32265760_3.fastq.gz" /mnt/pikachu/autoindex_98_32/pe_index/SAindex \
         "$D/refs/GRCh38-arc.chromap.idx" "$STAR_BIN_DEF"; do
  [[ -e "$f" ]] || have_fixtures=0
done

dry() { # profile, out
  STAR_BIN="${STAR_BIN:-$STAR_BIN_DEF}" bash "$RECIPE" \
    --gex-r1 "$D/fastq/GEX/SRR32265752_1.fastq.gz" --gex-r2 "$D/fastq/GEX/SRR32265752_2.fastq.gz" \
    --atac-r1 "$D/fastq/ATAC/SRR32265760_1.fastq.gz" --atac-barcode "$D/fastq/ATAC/SRR32265760_2.fastq.gz" --atac-r2 "$D/fastq/ATAC/SRR32265760_3.fastq.gz" \
    --out-dir "$2" \
    --genome-dir /mnt/pikachu/autoindex_98_32/pe_index \
    --chromap-ref /mnt/pikachu/refdata-cellranger-arc-GRCh38-2020-A-2.0.0/fasta/genome.fa \
    --chromap-index "$D/refs/GRCh38-arc.chromap.idx" \
    --atac-whitelist /mnt/pikachu/atac-seq/benchmarks/pbmc_unsorted_3k_100k/chromap_index/737K-arc-v1_atac.txt \
    --atac-to-gex /mnt/pikachu/atac-seq/benchmarks/pbmc_unsorted_3k_100k/chromap_index/atac2gex.tsv \
    --gex-whitelist /mnt/pikachu/GEX_whitelist/737K-arc-v1.txt \
    --threads 8 --chromap-threads 8 --profile "$1" --dry-run 2>/dev/null
}

echo "== Part 1: deterministic --profile / --dry-run mechanism =="
if [[ "$have_fixtures" -eq 1 ]]; then
  LEAN="$(dry matrices-peaks /tmp/comp_smoke_lean)"
  FULL="$(dry full /tmp/comp_smoke_full)"
  p1=1
  grep -qE 'emit_velocyto=0[[:space:]]+emit_gex_bam=0' <<<"$LEAN" || { echo "  FAIL: matrices-peaks did not zero velocyto/gex_bam"; p1=0; }
  grep -qE '^\s*--soloFeatures GeneFull\s*\\?\s*$' <<<"$LEAN" || { echo "  FAIL: matrices-peaks did not yield GeneFull-only"; p1=0; }
  grep -qE '^\s*--outSAMtype None' <<<"$LEAN" || { echo "  FAIL: matrices-peaks did not set --outSAMtype None"; p1=0; }
  grep -qE '^\s*--soloFeatures GeneFull Velocyto' <<<"$FULL" || { echo "  FAIL: full lost Velocyto"; p1=0; }
  grep -qE '^\s*--outSAMtype BAM Unsorted' <<<"$FULL" || { echo "  FAIL: full lost BAM output"; p1=0; }
  # minimal wrapper == matrices-peaks
  MIN="$(STAR_BIN="${STAR_BIN:-$STAR_BIN_DEF}" bash "$MINIMAL" \
        --gex-r1 "$D/fastq/GEX/SRR32265752_1.fastq.gz" --gex-r2 "$D/fastq/GEX/SRR32265752_2.fastq.gz" \
        --atac-r1 "$D/fastq/ATAC/SRR32265760_1.fastq.gz" --atac-barcode "$D/fastq/ATAC/SRR32265760_2.fastq.gz" --atac-r2 "$D/fastq/ATAC/SRR32265760_3.fastq.gz" \
        --out-dir /tmp/comp_smoke_min --genome-dir /mnt/pikachu/autoindex_98_32/pe_index \
        --chromap-ref /mnt/pikachu/refdata-cellranger-arc-GRCh38-2020-A-2.0.0/fasta/genome.fa \
        --chromap-index "$D/refs/GRCh38-arc.chromap.idx" \
        --atac-whitelist /mnt/pikachu/atac-seq/benchmarks/pbmc_unsorted_3k_100k/chromap_index/737K-arc-v1_atac.txt \
        --atac-to-gex /mnt/pikachu/atac-seq/benchmarks/pbmc_unsorted_3k_100k/chromap_index/atac2gex.tsv \
        --gex-whitelist /mnt/pikachu/GEX_whitelist/737K-arc-v1.txt \
        --threads 8 --chromap-threads 8 --dry-run 2>/dev/null)"
  grep -qE '^\s*--soloFeatures GeneFull\s*\\?\s*$' <<<"$MIN" && grep -qE '^\s*--outSAMtype None' <<<"$MIN" \
    || { echo "  FAIL: run_multiome_minimal.sh did not match the matrices-peaks floor"; p1=0; }
  [[ $p1 -eq 1 ]] && echo "  PASS: profiles resolve correctly; minimal == matrices-peaks floor" || rc=1
else
  echo "  SKIP: CAT-ATAC dry-run fixtures not present on this host"
fi

# ---- Part 1b: end-to-end execution on the tiny fixture (catches RUNTIME errors a
#      dry-run cannot — e.g. the --outSAMtype None / GX-tag incompatibility) ----
FIX="${SCRIPT_DIR}/fixtures/multiome_tiny"
echo "== Part 1b: end-to-end smoke on tiny fixture (actually executes the composed command) =="
if [[ -f "${FIX}/gex_R1.fastq.gz" && -e /mnt/pikachu/autoindex_98_32/pe_index/SAindex \
      && -f "$D/refs/GRCh38-arc.chromap.idx" && -x "$STAR_BIN_DEF" ]]; then
  EOUT=/tmp/comp_smoke_e2e; rm -rf "$EOUT"; mkdir -p "$EOUT"
  if STAR_BIN="${STAR_BIN:-$STAR_BIN_DEF}" bash "$MINIMAL" \
       --gex-r1 "${FIX}/gex_R1.fastq.gz" --gex-r2 "${FIX}/gex_R2.fastq.gz" \
       --atac-r1 "${FIX}/atac_R1.fastq.gz" --atac-barcode "${FIX}/atac_barcode.fastq.gz" --atac-r2 "${FIX}/atac_R3.fastq.gz" \
       --out-dir "$EOUT" --genome-dir /mnt/pikachu/autoindex_98_32/pe_index \
       --chromap-ref /mnt/pikachu/refdata-cellranger-arc-GRCh38-2020-A-2.0.0/fasta/genome.fa \
       --chromap-index "$D/refs/GRCh38-arc.chromap.idx" \
       --atac-whitelist /mnt/pikachu/atac-seq/benchmarks/pbmc_unsorted_3k_100k/chromap_index/737K-arc-v1_atac.txt \
       --atac-to-gex /mnt/pikachu/atac-seq/benchmarks/pbmc_unsorted_3k_100k/chromap_index/atac2gex.tsv \
       --gex-whitelist /mnt/pikachu/GEX_whitelist/737K-arc-v1.txt \
       --threads 8 --chromap-threads 8 --chromap-low-mem --chromap-macs3-frag-low-mem \
       > "$EOUT/smoke.log" 2>&1; then
    p1b=1; RUNX="$EOUT/star_sample/run"
    [[ -f "$RUNX/outs/raw_feature_bc_matrix/matrix.mtx.gz" ]] || { echo "  FAIL: no GeneFull raw MEX"; p1b=0; }
    [[ -f "$RUNX/atac_peaks.narrowPeak" ]] || { echo "  FAIL: no ATAC peaks narrowPeak"; p1b=0; }
    [[ ! -d "$RUNX/outs/raw_velocyto_feature_bc_matrix" ]] || { echo "  FAIL: Velocyto emitted in lean profile"; p1b=0; }
    [[ ! -f "$RUNX/Aligned.out.bam" ]] || { echo "  FAIL: GEX BAM emitted in lean profile"; p1b=0; }
    [[ $p1b -eq 1 ]] && echo "  PASS: minimal profile ran end-to-end; CORE present, no Velocyto/BAM" || rc=1
  else
    echo "  FAIL: minimal profile did not run to completion on the fixture (see $EOUT/smoke.log)"; rc=1
  fi
else
  echo "  SKIP: tiny fixture or references absent."
  echo "        Generate the fixture first: tests/make_multiome_tiny_fixture.sh"
fi

# ---- Part 2: agent-driven scoping ----
ENTRY='Entry points (read whatever you need; do NOT run anything):
- Recipe + its COMPOSITION header block: /mnt/pikachu/morphic-recipes/scripts/run_star_multiome_lane_smoke.sh
- Minimal wrapper: /mnt/pikachu/morphic-recipes/scripts/run_multiome_minimal.sh
- Agent guide: /mnt/pikachu/morphic-recipes/AGENTS.md
- MCP discovery guidance is the `agent_protocol` field in /mnt/pikachu/STAR-suite/mcp_server/config.yaml
Output (1) THE COMMAND you would run and (2) one-line RATIONALE naming your source.'
PROMPT="You are an automation agent on host pikachu. Task: produce the command to process CAT-ATAC (GSE288996, K562+iPSC 10x multiome) for a Cell Ranger ARC-style BENCHMARK. The deliverable is GEX matrices + ATAC fragments + re-called MACS peaks; the comparator (Cell Ranger ARC) ran --no-bam and computed no RNA velocity. ${ENTRY}"

echo "== Part 2: agent composes to the target scope =="
if [[ -z "${AGENT_CMD:-}" ]]; then
  echo "DOC MODE (AGENT_CMD unset). Prompt:"; echo "$PROMPT"
  echo "PASS: uses --profile matrices-peaks | run_multiome_minimal.sh | (--no-velocyto & --no-gex-bam);"
  echo "      NOT --profile full; rationale cites COMPOSITION / compose-up / comparator needs no velocyto+BAM."
else
  OUT="$(printf '%s' "$PROMPT" | ${AGENT_CMD} 2>/dev/null)"
  ok=1
  grep -qiE 'matrices-peaks|run_multiome_minimal|(--no-velocyto.*--no-gex-bam|--no-gex-bam.*--no-velocyto)' <<<"$OUT" \
    || { echo "  FAIL: did not take the minimal/lean composition path"; ok=0; }
  grep -qiE '\-\-profile[ =]*full' <<<"$OUT" && { echo "  FAIL: chose --profile full (maximal) for a matrices+peaks target"; ok=0; }
  grep -qiE 'compos|COMPOSITION|minimal|velocyto|no-bam' <<<"$OUT" || { echo "  FAIL: rationale does not reference composing to target"; ok=0; }
  [[ $ok -eq 1 ]] && echo "  PASS: composed to the target (minimal core, no Velocyto/BAM)" || rc=1
fi

echo; [[ $rc -eq 0 ]] && echo "ALL PASS" || echo "FAILURES (see above)"
exit $rc
