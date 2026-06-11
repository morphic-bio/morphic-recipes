# Recipe catalog — starting points

> GENERATED from catalog.yaml by scripts/render_recipe_catalog.py — do not hand-edit.
>
> The curated single source of truth is [`catalog.yaml`](catalog.yaml).
> This list is deliberately **small**: it holds canonical *starting points*,
> not a record of every run (that is `morphic-provenance`). Provenance is the
> oracle for parameter *values*; a recipe's `--profile`/compose-up governs which
> output *layers* it emits. See AGENTS.md "Compose to the target".

| id | recipe | modality | engine | minimal wrapper | profiles | compose-up | provenance oracle | status |
|---|---|---|---|---|---|---|---|---|
| multiome | 10x Multiome (GEX + ATAC) — STAR GeneFull + Chromap ATAC + MACS peaks | multiome | `scripts/run_star_multiome_lane_smoke.sh` | `scripts/run_multiome_minimal.sh` | full, matrices-peaks | ✓ | runs/jax_multiome01 | current |
| jax-multiome01-production | MorPhiC jax_multiome01 production wrapper (pins the verified multiome config) | multiome | `scripts/run_jax_multiome01_production.sh` | — | — | inherits | runs/jax_multiome01 | project-wrapper |
| scrnaseq-ocm | 10x scRNA-seq (OCM) production batch — STARsolo GeneFull (+ Velocyto) | scRNA-seq | `scripts/run_jax_scrnaseq02_ocm_production_batch.sh` | — | — | — | runs/jax_scrnaseq02 | current |
| scrna-downstream | scRNA downstream — GeneFull+Velocyto h5ad + CellBender (remote, CUDA) | scRNA-seq | `scripts/run_scrna_downstream_gene_full_velocyto.sh` | — | — | — | runs/msk_30ko_revised | current |

## Notes

- **multiome** — Compose-up reference recipe. matrices-peaks = apples-to-apples with Cell Ranger ARC --no-bam + a Signac/MACS peak re-call; full = MorPhiC production superset (adds Velocyto + GEX BAM + Y/noY + remote downstream).
- **jax-multiome01-production** — Thin project wrapper of the multiome engine with the verified jax_multiome01 production parameters. Use the generic engine for new work.
- **scrnaseq-ocm** — Compose-up RETROFIT candidate: Velocyto / BAM / remote downstream are optional layers that should become --profile/flags.
- **scrna-downstream** — Compose-up RETROFIT candidate: CellBender / remote execution are optional layers. Needs CUDA for CellBender (see AGENTS.md CUDA policy).

## Not catalogued as starting points

Deliberately excluded to keep the list small (internal steps, smokes, remote executors, preflight, ops):

- *preflight*: `run_msk_30ko_fastq_preflight.sh`, `run_msk_40ko_fastq_preflight.sh`
- *remote_executors*: `run_remote_cellbender_batch.sh`, `run_remote_cellbender_rsync.sh`, `run_remote_cellbender_scan.sh`, `run_remote_multiome_post_mex_rsync.sh`, `run_remote_scrna_downstream_rsync.sh`
- *smokes*: `run_jax_scrnaseq02_ocm_composite_smoke.sh`, `run_jax_scrnaseq02_ocm_oracle_smoke.sh`, `run_multiome_mudata_smoke.sh`
- *ops*: `backfill_jax_scrnaseq02_ocm_downstream.sh`, `upload_jax_multiome01_large_files_globus.sh`

## Elsewhere (suite-repo recipes / workflows)

Catalogued by each MCP server's `list_workflows`; cross-reference, do not duplicate:

- STAR-suite/scripts/run_jax_scrnaseq01_flex_2024.sh  (Flex; oracle runs/jax_scrnaseq01)
- STAR-suite slam_seq_pe recipes  (oracle runs/slam_seq_pe)
- STAR-suite & Chromap-suite mcp_server/workflows/*.yaml  (lower-level workflow schemas)

