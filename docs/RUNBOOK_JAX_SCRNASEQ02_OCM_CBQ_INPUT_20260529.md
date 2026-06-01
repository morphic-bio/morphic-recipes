# JAX scRNAseq02 OCM CBQ Input Runbook

Date: 2026-05-29

## Purpose

Add CBQ as an optional STAR input surface for the JAX scRNAseq02 OCM composite
smoke recipe while leaving the existing FASTQ path unchanged.

Canonical recipe:

```text
/mnt/pikachu/morphic-recipes/scripts/run_jax_scrnaseq02_ocm_composite_smoke.sh
```

STAR-suite entrypoint:

```text
/mnt/pikachu/STAR-suite/scripts/run_jax_scrnaseq02_ocm_composite_smoke.sh
```

The STAR-suite script is a compatibility launcher that execs the Morphic recipe
copy.

## Current Status

Implemented:

- `--star-input-format fastq|cbq`
- `STAR_INPUT_FORMAT=fastq|cbq`
- ordered per-lane CBQ staging under `stage/star_composite_cbq/`
- one paired CBQ per lane in STARsolo mate order: R2 first, R1 second
- rendered STAR command uses `--readFilesType Binseq PE`
- CBQ mode can emit Y/noY read sidecars with
  `--emitYNoY yes --emitYNoYFormat cbq`
- MCP workflow schemas updated in STAR-suite and morphic-recipes

Passing smoke:

```text
/tmp/ocm_cbq_smoke_20260529T174218Z
```

Smoke summary:

- clean STAR-suite worktree: `/tmp/star_suite_ocm_cbq`
- STAR-suite version: `1.0.3`
- STAR compile path: `/tmp/star_suite_ocm_cbq/core/legacy/source`
- read pairs: `1000`
- threads: `8`
- input mode: `cbq`
- `--outSAMtype None`
- `STAR_COMPLETED.txt`: `completed_utc=2026-05-29T17:45:53Z`
- `Log.final.out`: `Number of input reads = 1000`, uniquely mapped reads = `964`

FASTQ-vs-CBQ parity smoke:

- CBQ run: `/tmp/ocm_cbq_impl_prepare_20260529T181158Z`
- FASTQ run: `/tmp/ocm_cbq_impl_fastq_parity_20260529T181518Z`
- shared settings: `--read-pairs 1000`, `--threads 8`,
  `--star-yremove no`, `--star-out-samtype None`
- both runs: `Number of input reads = 1000`, uniquely mapped reads = `964`
- `star_composite/run/Solo.out`: byte-identical
- `star_composite/outs`: byte-identical, including native per-sample OCM MEX

STAR-suite regression wrapper:

```bash
tests/run_cbq_ocm_composite_smoke.sh
```

The wrapper is registered in
`/mnt/pikachu/STAR-suite/tests/production_module_regression_manifest.tsv` as a
host-local production smoke because it requires the JAX scRNAseq02 OCM raw
files and genome index. A wrapper sanity run passed at:

```text
/tmp/star_suite_cbq_ocm_wrapper_check_20260529T182012Z
```

100K parity run:

```text
/mnt/pikachu/JAX_scRNAseq02_processed/ocm_cbq_100k_20260529T182838Z
```

- `READ_PAIRS=100000`
- `THREADS=16`
- `RUN_FASTQ_PARITY=1`
- CBQ and FASTQ both used `--star-yremove no` and `--star-out-samtype None`
- CBQ and FASTQ both reported `100000` input reads, `95687` uniquely mapped
  reads, and `95.69%` unique mapping
- `fastq/star_composite/run/Solo.out` vs `cbq/star_composite/run/Solo.out`:
  byte-identical by `diff -qr`
- `fastq/star_composite/outs` vs `cbq/star_composite/outs`:
  byte-identical by `diff -qr`
- Native OCM filtered cells per tag matched:
  `OB1=5325`, `OB2=4127`, `OB3=4277`, `OB4=3757`
- staged FASTQ.gz bytes: `15658160`
- staged CBQ bytes: `10461811`
- total wrapper wall time: `4:51.85`

## Input Contract

FASTQ mode is still the default:

```bash
--star-input-format fastq
```

CBQ mode:

```bash
--star-input-format cbq --star-yremove yes --star-yremove-format cbq
```

CBQ staging is derived from the STAR-specific staged FASTQs created by the OCM
adapter. For each lane, the recipe runs:

```bash
cbq_ordered_encoder \
  --readFilesIn <R2.fastq.gz> <R1.fastq.gz> \
  --outFile <stage/star_composite_cbq>/<sample>_<lane>_R2_R1.cbq
```

The rendered STAR command uses:

```bash
--readFilesType Binseq PE
--readFilesIn lane1_R2_R1.cbq,lane2_R2_R1.cbq
```

No `--readFilesCommand` is rendered in CBQ mode.

CBQ manifest:

```text
stage/star_composite_cbq/cbq_manifest.tsv
```

Columns:

```text
lane    cbq_path    source_R2_fastq    source_R1_fastq
```

## Y Removal

For FASTQ input, `--star-yremove-format auto` emits gzipped FASTQ sidecars. For
CBQ input, `auto` emits CBQ sidecars. Use `--star-yremove-format fastq|cbq` to
force a specific sidecar format.

## Clean Build

Use a clean STAR-suite worktree for validation so dirty development artifacts do
not affect the binary.

```bash
git -C /mnt/pikachu/STAR-suite worktree add --detach /tmp/star_suite_ocm_cbq origin/master
make -C /tmp/star_suite_ocm_cbq/core/legacy/source clean
make -C /tmp/star_suite_ocm_cbq/core/legacy/source -j8 STAR cbq-ordered-encoder
```

## Prepare-Only Smoke

```bash
OUT_ROOT=/tmp/ocm_cbq_smoke_$(date -u +%Y%m%dT%H%M%SZ)

STAR_SUITE_ROOT=/tmp/star_suite_ocm_cbq \
/mnt/pikachu/morphic-recipes/scripts/run_jax_scrnaseq02_ocm_composite_smoke.sh \
  --read-pairs 1000 \
  --out-root "$OUT_ROOT" \
  --prepare \
  --force \
  --threads 8 \
  --star-input-format cbq \
  --star-yremove no \
  --star-out-samtype None
```

Check:

```bash
test -s "$OUT_ROOT/stage/star_composite_cbq/cbq_manifest.tsv"
grep -F -- '--readFilesType Binseq PE' "$OUT_ROOT/RUN_STAR_COMPOSITE.sh"
! grep -F -- '--readFilesCommand' "$OUT_ROOT/RUN_STAR_COMPOSITE.sh"
! grep -F -- '--emitYNoYFastq' "$OUT_ROOT/RUN_STAR_COMPOSITE.sh"
```

## STAR Smoke

```bash
STAR_SUITE_ROOT=/tmp/star_suite_ocm_cbq \
/mnt/pikachu/morphic-recipes/scripts/run_jax_scrnaseq02_ocm_composite_smoke.sh \
  --read-pairs 1000 \
  --out-root "$OUT_ROOT" \
  --run-star \
  --threads 8 \
  --star-input-format cbq \
  --star-yremove no \
  --star-out-samtype None
```

Completion checks:

```bash
test -f "$OUT_ROOT/STAR_COMPLETED.txt"
test -f "$OUT_ROOT/star_composite/run/Log.final.out"
grep -F 'Number of input reads' "$OUT_ROOT/star_composite/run/Log.final.out"
```

## Release-Level Validation

Before treating this as a release gate, run at least one larger comparison:

1. Prepare and run FASTQ mode with `--star-yremove no` or
   `--star-yremove-format fastq`.
2. Prepare and run CBQ mode with the same `--read-pairs`, threads, and STAR
   output mode.
3. Compare raw `Solo.out/GeneFull` and `Solo.out/Velocyto` outputs after any
   needed canonicalization.
4. Verify native OCM materialization summaries are present under
   `star_composite/outs/multi/multiplexing_analysis/`.
5. Record wall time and output paths in the relevant handoff or benchmark log.

Suggested 100K command shape:

```bash
STAR_SUITE_ROOT=/tmp/star_suite_ocm_cbq \
/mnt/pikachu/morphic-recipes/scripts/run_jax_scrnaseq02_ocm_composite_smoke.sh \
  --read-pairs 100000 \
  --out-root /mnt/pikachu/JAX_scRNAseq02_processed/ocm_cbq_100k_<timestamp> \
  --prepare \
  --run-star \
  --threads 16 \
  --star-input-format cbq \
  --star-yremove yes \
  --star-yremove-format cbq \
  --star-out-samtype "BAM Unsorted"
```

## Known Limitations

- CBQ mode currently encodes from staged FASTQs produced by the recipe. It does
  not yet consume an external CBQ packet directly.
- The passing smoke is a 1K functional smoke, not a performance benchmark.
- CR comparison was not run for the CBQ smoke above.
