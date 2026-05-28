# JAX Multiome01 Remote Post-MEX

## Purpose

This recipe runs the post-MEX phase for each JAX Multiome01 sample on a GPU
host. The local STAR/Chromap runner stages only the files needed after the
MEX boundary, then the remote host runs RNA downstream analysis, CellBender,
adaptive filtering, and MuData construction. STAR, Chromap, and libchromap are
not required on the remote host.

For full reproduction from a working root, start with:

```text
../jax_multiome01/run_all.sh
```

## Executable Scripts

- `scripts/run_remote_multiome_post_mex_rsync.sh`: stages MEX/ATAC inputs,
  launches the remote downstream job, and syncs outputs back.
- `scripts/run_scrna_downstream_gene_full_velocyto.sh`: remote RNA downstream
  recipe.
- `scripts/build_gene_full_velocyto_h5ad.py`: h5ad construction helper.
- `scripts/build_multiome_mudata.py`: combines RNA h5ad plus ATAC peak MEX into
  filtered and unfiltered h5mu files.
- `scripts/apply_adaptive_mt_filter.py`,
  `scripts/generate_qc_histogram_mt_adaptive.py`, and
  `scripts/scrna_mt_adaptive.py`: adaptive filtering helpers.

The executed remote post-MEX script hash is recorded in:

```text
morphic-provenance/runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/commands/script_hashes.tsv
```

## Inputs

For each sample, the recipe stages:

- STAR filtered, raw, and raw Velocyto MEX directories.
- ATAC peak MEX directory.
- ATAC metrics table.
- ATAC peaks and sidecars when present.
- The downstream and MuData scripts listed above.

## Remote Host

The May 2026 production run used:

```text
10.159.4.53
```

with remote staging under:

```text
/home/lhhung/jax_multiome_remote_downstream_production
```

The production command included `--run-cellbender`, `--adaptive-filter`,
`--cellbender-cpu-cores 24`, and GPU CellBender mode. GPU mode is required for
production and handoff workflows.

## Outputs

Outputs are synced back into each sample directory under the local production
root:

- `star_sample/downstream_genefull_velocyto_cellbender/`: RNA h5ad files,
  CellBender outputs, adaptive QC thresholds, and QC plots.
- `mudata/star_chromap_filtered_multiome.h5mu`
- `mudata/star_chromap_unfiltered_multiome.h5mu`

## Provenance And Release Notes

Canonical run provenance:

```text
morphic-provenance/runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/
```

Dataset release notes keyed by Globus handoff date:

```text
morphic-provenance/dataset_releases/jax_multiome01/2026-05-18/
```
