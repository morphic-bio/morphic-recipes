# JAX Multiome01 Reproduction Entrypoint

Use `run_all.sh` when the goal is to reproduce the JAX Multiome01 production
analysis from a single working root.

The script is intentionally a thin orchestrator. It prepares a root directory,
downloads the Globus release inputs, generates a relocated
`sample_manifest.tsv`, then calls the canonical production recipes under
`scripts/`.

## Example

```bash
docs/production_recipes/jax_multiome01/run_all.sh \
  --root-directory /mnt/pikachu/reproduce/jax_multiome01_2026-05-18 \
  --local-globus-endpoint 07446cad-33b8-11f0-8c0c-0afffb017b7d \
  --star-suite-root /mnt/pikachu/STAR-suite \
  --remote-host 10.159.4.53 \
  --remote-root /home/lhhung/jax_multiome_remote_downstream_production
```

The default run downloads the released raw FASTQs and compact h5mu handoff,
then runs STAR/Chromap locally and post-MEX CellBender/MuData work on the
remote GPU host. Pass `--download-large-files-release` if you also want a local
archive copy of the full large-file Globus tree; that is not needed for
reprocessing because generated BAM/Y-noY FASTQs are rebuilt.

By default the script does not re-upload generated large files to Globus. Pass
`--globus-upload-large-files` only when intentionally creating a new delivery.

## Main Outputs

Under the selected root directory:

- `raw/`: downloaded raw FASTQs from the Globus large-file release tree.
- `downloads/large_files/`: optional full large-file release tree when
  `--download-large-files-release` is used.
- `downloads/h5mu/`: downloaded compact h5mu packet for comparison/reference.
- `metadata/sample_manifest.tsv`: relocated production manifest consumed by
  `scripts/run_jax_multiome01_production.sh`.
- `outputs/<run>/`: reproduced STAR/Chromap, downstream, and MuData outputs.
- `logs/run_all.log`: orchestrator log.

CBQ-native reruns are supported by supplying a manifest with appended
`gex_cbq`, `atac_read_pair_cbq`, and `atac_barcode_cbq` columns and passing
`--input-format cbq` through `run_all.sh`.

The exact run provenance for the May 2026 production delivery remains in
`morphic-provenance`:

```text
runs/jax_multiome01/20260517T183219Z_star_multiome_prod_globus/
```
