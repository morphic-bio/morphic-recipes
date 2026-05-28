# JAX Multiome01 STAR/Chromap Production

## Purpose

This recipe runs the local STAR-suite RNA plus Chromap ATAC phase for the
nine-sample JAX Multiome01 production set. It builds the production sample
manifest from the JAX metadata workbook, processes each sample through STAR
GeneFull/Velocyto and native Chromap ATAC integration, and stops at the
local MEX/ATAC sidecar boundary so remote post-MEX work can run on the GPU
host while the next sample starts locally.

For full reproduction from a working root, start with:

```text
../jax_multiome01/run_all.sh
```

## Executable Scripts

- `scripts/run_jax_multiome01_production.sh`: top-level production launcher.
- `scripts/run_star_multiome_lane_smoke.sh`: per-sample local STAR/Chromap
  boundary runner used by the production launcher.
- `scripts/build_multiome_mudata.py`: MuData builder staged later by the
  remote post-MEX recipe.

For the May 2026 delivery, the exact executed production script hashes are
recorded in:

```text
morphic-provenance/runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/commands/script_hashes.tsv
```

The executed top-level recipe content matches `morphic-recipes` commit:

```text
682f55493e9342aaed425dd89fb87b0148e8c258
```

## Inputs

- Raw FASTQs: `/mnt/pikachu/JAX_Multiome01/raw`
- Metadata workbook: `/mnt/pikachu/DPC_metadata_template_Multiome1-complete.xlsx`
- STAR-suite checkout: `/mnt/pikachu/STAR-suite`
- GEX reference: `/storage/autoindex_110_44/bulk_index`
- ATAC reference/index assets recorded in the rendered per-sample commands.

The production launcher writes:

```text
metadata/sample_manifest.tsv
```

inside the run root before any sample is processed.

## Production Command Shape

The May 2026 production launch used this shape:

```bash
scripts/run_jax_multiome01_production.sh \
  --output-root /mnt/pikachu/JAX_Multiome01_processed/star_multiome_prod_globus_20260517T183219Z \
  --threads 16 \
  --chromap-threads 16 \
  --chromap-low-mem \
  --chromap-macs3-frag-low-mem \
  --chromap-start-mode concurrent \
  --globus-upload-large-files \
  --no-sync-images
```

The run was resumed from the same output root with `--skip-build` and
`--start-at` after completed samples.

## Outputs

Per-sample local outputs include:

- `RUN_STAR_MULTIOME.sh`: exact rendered per-sample command script.
- `star_sample/run/Log.out` and `Log.final.out`: STAR command, git commit,
  dirty-file list, and final mapping metrics.
- `star_sample/run/outs/`: STAR GeneFull and Velocyto MEX outputs.
- `star_sample/run/atac_*`: Chromap ATAC sidecars, peaks, and metrics.
- `atac/peak_mex/`: materialized ATAC peak matrix.

The remote post-MEX recipe consumes these outputs.

## Provenance And Release Notes

Canonical run provenance:

```text
morphic-provenance/runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/
```

Dataset release notes keyed by Globus handoff date:

```text
morphic-provenance/dataset_releases/jax_multiome01/2026-05-18/
```
