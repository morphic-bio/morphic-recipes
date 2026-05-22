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
