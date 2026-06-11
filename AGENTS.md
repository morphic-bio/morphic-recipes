# Morphic Recipes Agent Guide

This repo contains operational recipes, not STAR-suite core code.

## Recipe catalog (start here)

The curated list of canonical **starting points** is the single source of truth in
[`catalog.yaml`](catalog.yaml) (agent-friendly) with generated human views
[`RECIPES.md`](RECIPES.md) (table) and `RECIPES.xlsx`. It is deliberately **small** —
it holds starting points, not a record of every run (that is `morphic-provenance`).
Pick a recipe there, then read its script header (`COMPOSITION` block) and the
"Compose to the target" + "Consult provenance" guidance below.

Regenerate the human views after editing `catalog.yaml` (never hand-edit them):
`python3 scripts/render_recipe_catalog.py`.

## Local Core Dependency

- Use STAR-suite for core source and binaries.
- Default local STAR-suite checkout on pikachu:
  `/mnt/pikachu/STAR-suite`
- When a recipe runs STAR, prefer explicit `--star-bin` and `--genome-dir`
  arguments rather than relying on repo-relative defaults.

## CUDA Policy

- NEVER run CellBender without CUDA for production or handoff workflows.
- Recipe commands that enable CellBender must expose a GPU flag and propagate
  to Docker `--gpus all` and CellBender `--cuda`.
- Before launching remote downstream/CellBender jobs, verify the rendered
  command contains GPU mode. If it does not, stop and fix the recipe.
- After launch, confirm `nvidia-smi` shows the CellBender process using GPU
  memory/utilization.

## Transition Policy

- During the transition, some files are mirrored from STAR-suite.
- Change canonical recipe files here first, then sync compatibility mirrors in
  STAR-suite when needed.
- Do not move STAR core source, release packaging, or core regression tests
  into this repo.
- Do not commit large data outputs, h5ad/BAM/FASTQ files, or generated packet
  payloads. Record them in provenance by path and checksum.

## Provenance

Every production or handoff run should create or update a corresponding record
in `morphic-provenance` before delivery.

### Consult provenance BEFORE you run (not only after)

Recipes are **starting points, not turnkey commands.** Resource and scale
parameters — thread counts, memory, `--*-low-mem` flags, `--*-start-mode` — must
come from a known-good run, not be invented.

Before executing a recipe at non-trivial scale:

1. Look in `morphic-provenance/runs/<project>/` for a completed run of this
   workflow. Read `run.json` and `commands/` for the rendered command and the
   exact parameters that actually worked.
2. Reproduce those parameters. Adapt only what the new input or machine requires,
   and note the deviation.
3. If no provenance exists at your scale, start from the closest run, scale
   conservatively, and record a new run.

Inventing thread/memory parameters and running blind is a known failure mode.
Example: a multiome run was OOM-killed at `--threads 32 --chromap-threads 32`
with no low-mem flags, while the verified `jax_multiome01` production config was
`--threads 16 --chromap-threads 16 --chromap-low-mem --chromap-macs3-frag-low-mem`
and completed the full BAM + Velocyto + noY output set on the same 125 GB machine.

## Compose to the target (start minimal, add only what is needed)

Recipes often emit a **superset** of outputs sized for the heaviest downstream
(e.g. the MorPhiC production set: GeneFull + Velocyto + GEX BAM + Y/noY +
fragments + peaks + remote CellBender/MuData). **Do not run the maximal set
blindly.** Match the outputs to *your* target workflow:

1. **Start from the minimal functional core** — the tested floor that produces
   the analysis-ready deliverable and nothing else (for multiome:
   `scripts/run_multiome_minimal.sh`, i.e. GeneFull MEX + ATAC fragments + MACS
   peaks; apples-to-apples with Cell Ranger ARC `--no-bam` + a Signac/MACS peak
   re-call).
2. **Add only the layers your target consumes.** Read the recipe's `COMPOSITION:`
   header block: it lists each optional add-on with *add when*, *how* (the
   `--profile`/flag), and the **provenance oracle** for that layer's parameter
   values.
3. **Preview with `--dry-run`** — it prints the resolved command and the exact
   output layers it will emit, then exits without running. Inspect it (or hand it
   to a human) before the real run or smoke.

Emitting layers the target never uses wastes compute and, in a benchmark, unfairly
inflates the suite's own time against a comparator that emitted less. Example
(CAT-ATAC, 2026-06): running the full multiome recipe materialized Velocyto + a
GEX BAM that the matrices+peaks target (and CR-ARC `--no-bam`) never used; the
right call was `run_multiome_minimal.sh` / `--profile matrices-peaks`. This is the
output-composition complement to PROVENANCE-FIRST above: provenance is the oracle
for *parameter values*; compose-up governs *which output layers* you include.

### Compose-up retrofit backlog (TODO)

Only the **multiome** recipe (`run_star_multiome_lane_smoke.sh` +
`run_multiome_minimal.sh`) currently implements the full compose-up contract
(COMPOSITION block, `--profile`, `--dry-run`, minimal wrapper, tiny-fixture smoke).
Other recipes that have provenance runs emit similar optional supersets
(Velocyto, CellBender/remote downstream, extra BAMs) and should be reviewed and
retrofitted the same way. Candidates (from `morphic-provenance/runs/`):

| Recipe / wrapper | Provenance run | Likely optional layers to declare |
| --- | --- | --- |
| `run_jax_scrnaseq01_flex_2024.sh` | `jax_scrnaseq01` | BAM, downstream |
| `run_jax_scrnaseq02_ocm_production_batch.sh` | `jax_scrnaseq02` | Velocyto, BAM, downstream |
| `run_scrna_downstream_gene_full_velocyto.sh` | `msk_30ko_revised` | Velocyto, CellBender (remote) |
| `run_msk_40ko_*` | `msk_40ko` | downstream, remote rsync |
| `run_all_libmacs3_*.sh` | `nw_atac_seq_libmacs3` | BAM vs fragments-only |
| `run_full_deseq2_modes.sh` | `slam_seq_pe` | DESeq2 modes, remote target |

For each: declare the minimal CORE vs optional ADD-ONs, add `--profile`/`--dry-run`
and a minimal wrapper, and a tiny-fixture smoke per
`mcp_server/workflows/AUTHORING.md` "Compose-up recipes". Provenance stays the
oracle for the parameter values of whatever layers are included.
