# Morphic Recipes

Operational recipes for running STAR-suite on Morphic/JAX/MSK/UCSF datasets.

This repo is the transition target for dataset-specific launchers, downstream
h5ad/QC/CellBender/celltyping helpers, workflow schemas, manifests, and handoff
packet builders. STAR-suite remains the canonical home for core STAR/Flex/Solo
source, compiled tools, core tests, release packaging, and generic MCP server
code.

## Status

Phase: initial mirror.

The first import was copied from STAR-suite commit:

```text
43a5853af0c627925f827ab576814b770d1874c1
```

During the transition, files may exist in both repos. Treat this repo as the
preferred home for new production recipe work, but expect some scripts to keep
STAR-suite compatibility defaults until they are adapted.

## Layout

```text
docs/                  Dataset runbooks and recipe-specific handoffs
scripts/               Production launchers and downstream helpers
mcp_server/workflows/  Mirrored workflow YAMLs during transition
config/                Local environment templates
```

## Using Mirrored Recipes

Most copied scripts preserve their STAR-suite-relative layout. Until wrappers
are fully adapted, pass explicit core paths when needed:

```bash
--star-bin /mnt/pikachu/STAR-suite/core/legacy/source/STAR
--genome-dir /storage/autoindex_110_44/bulk_index
```

For CellBender production or handoff workflows, GPU mode is mandatory. The
rendered command must include the recipe-level GPU flag, Docker GPU access, and
CellBender `--cuda`.

## Canonical Boundary

- Core behavior, source changes, and core regression tests: STAR-suite.
- Dataset launch, remote staging, downstream analysis, and handoff packaging:
  this repo.
- Executed run records, exact commands, checksums, and environment pins:
  `morphic-provenance`.

See `MIGRATION_INVENTORY.md` for the initial file ownership classification.
