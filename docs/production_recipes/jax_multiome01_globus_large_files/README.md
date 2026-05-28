# JAX Multiome01 Globus Large-File Upload

## Purpose

This recipe uploads the large JAX Multiome01 files that are not part of the
compact h5mu handoff. It submits one checksum-synced Globus task per completed
sample and, after successful transfer, deletes generated local BAM and Y/noY
FASTQ artifacts while preserving raw input FASTQs locally.

## Executable Script

```text
scripts/upload_jax_multiome01_large_files_globus.sh
```

The exact script hash used for the May 2026 delivery is recorded in:

```text
morphic-provenance/runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/commands/script_hashes.tsv
```

## Inputs

- Production run root containing `metadata/sample_manifest.tsv`.
- Completed per-sample output directories.
- Local Globus endpoint:
  `07446cad-33b8-11f0-8c0c-0afffb017b7d`
- Destination Globus endpoint:
  `61fb8b9a-9b52-456e-928c-30c0fb0140bf`

## Destination

The May 2026 large-file destination root was:

```text
/JAX_Multiome01_processed/large_files/star_multiome_prod_globus_20260517T183219Z
```

Each sample task uploaded raw FASTQs plus selected generated BAM/Y-noY FASTQ
artifacts. Per-sample state is preserved in:

```text
morphic-provenance/runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/handoff/globus_large_files_upload_state.tsv
```

The dated release note summarizes the per-sample Globus tasks and total bytes.

## Deletion Policy

Generated local BAM/Y-noY FASTQ files were deleted only after the corresponding
Globus task succeeded. Raw FASTQ inputs remained on the local host.

## Provenance And Release Notes

Canonical run provenance:

```text
morphic-provenance/runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/
```

Dataset release notes keyed by Globus handoff date:

```text
morphic-provenance/dataset_releases/jax_multiome01/2026-05-18/
```
