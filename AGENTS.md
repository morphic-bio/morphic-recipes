# Morphic Recipes Agent Guide

This repo contains operational recipes, not STAR-suite core code.

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
