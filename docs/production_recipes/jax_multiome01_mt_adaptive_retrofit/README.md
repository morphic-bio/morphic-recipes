# JAX Multiome01 Adaptive MT Retrofit

## Purpose

This recipe records the one-time retrofit that converted the completed JAX
Multiome01 h5ad and h5mu outputs to the revised adaptive mitochondrial
percentage policy. The retrofit was applied after initial production completion
and before the revised h5mu Globus handoff.

## Executable Scripts

- `scripts/convert_jax_multiome01_mt_adaptive_once.sh`: one-time conversion
  wrapper. This script was still sourced from the STAR-suite compatibility copy
  for the May 2026 run.
- `scripts/apply_adaptive_mt_filter.py`: applies adaptive MT fields to h5ad.
- `scripts/scrna_mt_adaptive.py`: shared adaptive MT threshold logic.
- `scripts/generate_qc_histogram_mt_adaptive.py`: QC histogram helper.

The exact script hashes used for the May 2026 delivery are recorded in:

```text
morphic-provenance/runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/commands/script_hashes.tsv
```

## Command Shape

The May 2026 retrofit used:

```bash
scripts/convert_jax_multiome01_mt_adaptive_once.sh \
  --run-root /mnt/pikachu/JAX_Multiome01_processed/star_multiome_prod_globus_20260517T183219Z \
  --mt-floor 5 \
  --n-mad 3
```

## Outputs

The retrofit updates the h5ad and h5mu outputs in place and writes:

- `samples/<sample>/MT_ADAPTIVE_CONVERTED.txt`
- `logs/mt_adaptive_conversion/conversion_*.log`
- `adaptive_qc_threshold.json` and QC histograms in each downstream directory.

Pre-conversion local backups were preserved with the `.pre_mt_adaptive` suffix.

## Provenance And Release Notes

Canonical run provenance:

```text
morphic-provenance/runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/
```

Dataset release notes keyed by Globus handoff date:

```text
morphic-provenance/dataset_releases/jax_multiome01/2026-05-18/
```
