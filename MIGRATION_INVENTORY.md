# Migration Inventory

Source STAR-suite commit:

```text
43a5853af0c627925f827ab576814b770d1874c1
```

Status: initial mirror. No STAR-suite files have been removed.

## Classification Rules

- `move-recipe`: this repo should become canonical.
- `duplicate-transition`: mirrored here and in STAR-suite until callers move.
- `keep-core`: STAR-suite remains canonical.
- `move-provenance`: executed run records belong in `morphic-provenance`.

## Initial Recipe Mirrors

These files were copied as `duplicate-transition` or `move-recipe` candidates.

| Path | Classification | Notes |
| --- | --- | --- |
| `scripts/run_msk_40ko_pipeline_from_manifest.py` | duplicate-transition | MSK 40KO production launcher. Needs explicit STAR-suite core path after split. |
| `scripts/run_msk_40ko_fastq_preflight.sh` | duplicate-transition | Dataset preflight wrapper. |
| `scripts/run_msk_30ko_fastq_preflight.sh` | duplicate-transition | Dataset preflight wrapper. |
| `scripts/preflight_whitelist_family.py` | duplicate-transition | Operational FASTQ chemistry preflight used by production recipes. |
| `scripts/preflight_library_pairing.py` | duplicate-transition | Operational FASTQ pairing preflight. |
| `scripts/run_jax_scrnaseq02_ocm_production_batch.sh` | duplicate-transition | JAX scRNAseq02 OCM production launcher. |
| `scripts/run_jax_scrnaseq02_ocm_composite_smoke.sh` | duplicate-transition | OCM recipe validation harness. |
| `scripts/run_jax_scrnaseq02_ocm_oracle_smoke.sh` | duplicate-transition | OCM oracle harness. |
| `scripts/backfill_jax_scrnaseq02_ocm_downstream.sh` | duplicate-transition | JAX downstream backfill helper. |
| `scripts/ocm_composite_adapter.py` | duplicate-transition | OCM helper retained for recipe validation and comparison flows. |
| `scripts/validate_jax_scrnaseq02_ocm_oracle.py` | duplicate-transition | External-oracle validator. |
| `scripts/run_jax_multiome01_production.sh` | duplicate-transition | JAX Multiome production launcher. |
| `scripts/upload_jax_multiome01_large_files_globus.sh` | duplicate-transition | Globus handoff helper. |
| `scripts/run_star_multiome_lane_smoke.sh` | duplicate-transition | Multiome lane recipe/smoke. |
| `scripts/run_multiome_mudata_smoke.sh` | duplicate-transition | Multiome h5mu recipe/smoke. |
| `scripts/run_remote_multiome_post_mex_rsync.sh` | duplicate-transition | Remote post-MEX helper. |
| `scripts/build_multiome_mudata.py` | duplicate-transition | Downstream MuData builder. |
| `scripts/build_atac_peak_matrix_from_fragments.py` | duplicate-transition | Downstream ATAC matrix helper. |
| `scripts/extract_cr_feature_type_mex.py` | duplicate-transition | Downstream MEX extraction helper. |
| `scripts/run_remote_scrna_downstream_rsync.sh` | duplicate-transition | Remote scRNA downstream launcher. |
| `scripts/run_remote_cellbender_*.sh` | duplicate-transition | Remote CellBender orchestration/scanning helpers. |
| `scripts/run_scrna_downstream_gene_full_velocyto.sh` | duplicate-transition | Main post-MEX h5ad/QC/CellBender workflow. |
| `scripts/build_gene_full_velocyto_h5ad.py` | duplicate-transition | h5ad builder. |
| `scripts/run_star_cell_doublets.R` | duplicate-transition | Doublet helper used by downstream workflow. |
| `scripts/integrate_feature_library.py` | duplicate-transition | Feature-library integration helper. |
| `scripts/postprocess_downstream_filters.py` | duplicate-transition | Filtered/default-singlet h5ad writer. |
| `scripts/compute_adaptive_qc_threshold.py` | duplicate-transition | Adaptive QC helper. |
| `scripts/scrna_mt_adaptive.py` | duplicate-transition | Shared MT adaptive helpers. |
| `scripts/apply_adaptive_mt_filter.py` | duplicate-transition | Adaptive MT rewrite helper. |
| `scripts/generate_qc_histogram_mt_adaptive.py` | duplicate-transition | QC plot helper. |
| `scripts/propagate_anndata_layer.py` | duplicate-transition | AnnData layer propagation helper. |
| `scripts/add_cellbender_layer_from_h5.py` | duplicate-transition | CellBender layer integration helper. |
| `scripts/repair_denoised_layer.py` | duplicate-transition | Downstream repair helper. |

## Initial Docs And Workflow Mirrors

| Path | Classification | Notes |
| --- | --- | --- |
| `docs/RUNBOOK_MSK_40KO_PRODUCTION.md` | duplicate-transition | Dataset production runbook. |
| `docs/RUNBOOK_MSK_30KO_GEMX_PRODUCTION_DRAFT.md` | duplicate-transition | Dataset production draft. |
| `docs/MSK_40KO_FASTQ_MANIFEST.tsv` | duplicate-transition | Dataset manifest. |
| `docs/MSK_30KO_FASTQ_MANIFEST.tsv` | duplicate-transition | Dataset manifest. |
| `docs/RUNBOOK_JAX_SCRNASEQ02_OCM_20260518.md` | duplicate-transition | Dataset production runbook. |
| `docs/RUNBOOK_SCRNA_OCM_*.md` | duplicate-transition | OCM recipe and implementation context. |
| `docs/RUNBOOK_MULTIOME_MEX_MUDATA_20260516.md` | duplicate-transition | Multiome downstream runbook. |
| `docs/RUNBOOK_SCRNA_MT_ADAPTIVE_FILTER_20260518.md` | duplicate-transition | Downstream filtering policy. |
| `mcp_server/workflows/*.yaml` | duplicate-transition | Workflow schemas mirrored until STAR-suite can load external workflow dirs. |

## Known Follow-Ups

1. Adapt production launchers to support `STAR_SUITE_ROOT` explicitly.
2. Add canonical-owner headers to STAR-suite mirrors or replace them with thin
   compatibility wrappers.
3. Move packet builders from `plans/artifacts/` into stable recipe scripts.
4. Add CI/lightweight linting for recipe command rendering.
5. Create GitHub remotes once names and visibility are confirmed.
