# Morphic Recipes

Operational recipes for running STAR-suite on Morphic/JAX/MSK/UCSF datasets.

This repo is the transition target for dataset-specific launchers, downstream
h5ad/QC/CellBender/celltyping helpers, workflow schemas, manifests, and handoff
packet builders. STAR-suite remains the canonical home for core STAR/Flex/Solo
source, compiled tools, core tests, release packaging, and generic MCP server
code.

## Status

Phase: Phase 1 cutover.

The first import was copied from STAR-suite commit:

```text
43a5853af0c627925f827ab576814b770d1874c1
```

During the transition, files may exist in both repos. Treat this repo as the
canonical home for production recipe work. STAR-suite compatibility launchers
should delegate here while the duplicated scripts age out.

## Layout

```text
docs/                  Dataset runbooks and recipe-specific handoffs
docs/production_recipes/
                       Human-facing summaries for production recipe chains
scripts/               Production launchers and downstream helpers
mcp_server/workflows/  Mirrored workflow YAMLs during transition
config/                Local environment templates
```

## Using Recipes

Production launchers that need STAR core tools default to the local core
checkout at `/mnt/pikachu/STAR-suite`. Override that checkout with
`STAR_SUITE_ROOT` when running from another host or clone:

```bash
export STAR_SUITE_ROOT=/mnt/pikachu/STAR-suite
--star-bin /mnt/pikachu/STAR-suite/core/legacy/source/STAR
--genome-dir /storage/autoindex_110_44/bulk_index
```

For CellBender production or handoff workflows, GPU mode is mandatory. The
rendered command must include the recipe-level GPU flag, Docker GPU access, and
CellBender `--cuda`.

## STAR CLI MCP Recipes

The mirrored MCP workflow schemas under `mcp_server/workflows/` expose
operator-facing STAR commands during the repo split. The paired CBQ/BINSEQ
batch recipe is `star_binseq_pe_batch`; STAR-Flex CBQ is
`star_flex_fixed_rna_cbq`. Both render `--readFilesType Binseq PE` with no
`--readFilesCommand`. See `docs/RUNBOOK_STAR_BINSEQ_CBQ_BATCH.md`.

The multiome lane recipe also accepts native CBQ on both sides:
`scripts/run_star_multiome_lane_smoke.sh --input-format cbq --gex-cbq ...`
plus `--atac-read-pair-cbq ... --atac-barcode-cbq ...`. That path renders
STAR GEX CBQ input and libchromap ATAC CBQ input without `--readFilesCommand`.

## Canonical Boundary

- Core behavior, source changes, and core regression tests: STAR-suite.
- Dataset launch, remote staging, downstream analysis, and handoff packaging:
  this repo.
- Executed run records, exact commands, checksums, and environment pins:
  `morphic-provenance`.

See `MIGRATION_INVENTORY.md` for the initial file ownership classification.
