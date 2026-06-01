# STAR Paired CBQ/BINSEQ Batch Runbook

This recipe is the operator-facing wrapper for STAR-suite's experimental native
CBQ reader. STAR-suite remains the source of truth for the core implementation
and tests; this repo owns dataset launch recipes and handoff policy.

For Fixed RNA Profiling/Flex, use the dedicated MCP recipe
`star_flex_fixed_rna_cbq`, which adds `--flex yes` and the Fixed RNA whitelist
surface while preserving the same paired-CBQ input rules.

## MCP Workflow

- Workflow id: `star_binseq_pe_batch`
- Schema: `mcp_server/workflows/star_binseq_pe_batch.yaml`
- STAR binary: `${STAR_SUITE_ROOT:-/mnt/pikachu/STAR-suite}/core/legacy/source/STAR`

Paired CBQ stores both mates in one external file, so the STAR command takes one
input list instead of separate R1/R2 lists.

## Direct CBQ List

```bash
STAR_SUITE_ROOT="${STAR_SUITE_ROOT:-/mnt/pikachu/STAR-suite}"
"$STAR_SUITE_ROOT/core/legacy/source/STAR" \
  --runMode alignReads \
  --genomeDir /path/to/star_index \
  --readFilesType Binseq PE \
  --readFilesIn sampleA.cbq,sampleB.cbq \
  --batchMode 1 \
  --outFileNamePrefixAuto 1 \
  --outFileNamePrefix /path/to/out_root/
```

## CBQ Manifest

Manifest rows use one CBQ path, a literal `-` in the mate-2 column, and an
optional STAR read-group token:

```text
sampleA.cbq	-	ID:sampleA
sampleB.cbq	-	ID:sampleB
```

```bash
STAR_SUITE_ROOT="${STAR_SUITE_ROOT:-/mnt/pikachu/STAR-suite}"
"$STAR_SUITE_ROOT/core/legacy/source/STAR" \
  --runMode alignReads \
  --genomeDir /path/to/star_index \
  --readFilesType Binseq PE \
  --readFilesManifest /path/to/cbq_manifest.tsv \
  --batchMode 1 \
  --outFileNamePrefixAuto 1 \
  --outFileNamePrefix /path/to/out_root/
```

## Boundaries

- Y/noY FASTQ emission is not part of this recipe. For CBQ sidecars, use
  `--emitYNoY yes --emitYNoYFormat cbq`; do not use `--emitYNoYFastq` with
  CBQ/BINSEQ input.
- For `--batchMode 1`, each comma-separated CBQ entry or manifest row is one
  sample/library.
- For multi-lane alignment as a single sample, set `--batchMode 0` and pass the
  CBQ files as one comma-separated list.

## Verification

The core smoke test lives in STAR-suite:

```bash
cd "${STAR_SUITE_ROOT:-/mnt/pikachu/STAR-suite}"
BQTOOLS=/path/to/bqtools tests/run_cbq_star_input_smoke.sh
```

That test covers direct CBQ, manifest CBQ, comma-separated multisample CBQ, and
paired-CBQ batch output routing against FASTQ parity.
