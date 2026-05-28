# Production Recipe READMEs

This directory contains human-facing summaries for production recipes that have
been used for collaborator deliveries.

The scripts under `scripts/` remain the executable source. These READMEs explain
which scripts form a recipe chain, what each step is responsible for, what
inputs and outputs the operator should expect, and where the canonical
provenance record lives.

## JAX Multiome01

The JAX Multiome01 production delivery used these recipe summaries:

- `jax_multiome01/`: one-command reproduction entrypoint, including
  `run_all.sh`.
- `jax_multiome01_star_multiome/`: local STAR RNA plus Chromap ATAC production
  launcher and per-sample boundary runner.
- `jax_multiome01_remote_post_mex/`: remote GPU post-MEX RNA downstream,
  CellBender, adaptive filtering, and MuData construction.
- `jax_multiome01_mt_adaptive_retrofit/`: one-time adaptive mitochondrial QC
  retrofit for h5ad and h5mu outputs.
- `jax_multiome01_globus_large_files/`: per-sample large-file Globus uploader.

The canonical executed-run record is in `morphic-provenance`:

```text
runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/
```

The dated dataset release notes for the May 18, 2026 Globus handoff are:

```text
dataset_releases/jax_multiome01/2026-05-18/
```
