# Trimodal QC — the single-pass multiome GO/NO-GO figure

A single unified QC figure that **requires all three modalities** (GEX + ATAC + CRISPR
guide) resolved on the **same cells**, with one purpose: *did GEX, ATAC, and guide capture
all work, on the same cells, well enough to proceed?* It is the endpoint instrument for the
single-pass multiome path — the rapid GO/NO-GO verdict that the fast unified binary makes
cheap. No vendor tool's output hands you this view (CR-ARC = RNA+ATAC, `cellranger multi` =
RNA+guide; neither spans all three).

This is QC, not biology — stop at the MuData + this figure (+ example downstream handoffs).

## Scripts

- **`scripts/generate_trimodal_qc.py`** — *reusable.* Reads a multiome MuData with `rna` +
  `atac` (+ optional `guide`) modalities and renders the figure → `<prefix>.{html,json,png}`.
  A view over the object, decoupled from how it was built. Reuses `rna.obsm['X_umap']` if
  present, else computes a quick GEX UMAP.
- **`scripts/build_catatac_trimodal_qc.py`** — *dataset reproducer* (like
  `run_jax_multiome01_production.sh`). Assembles the CAT-ATAC trimodal MuData on the
  finalized cell basis and calls the generator.

## Use it in the multiome path

```bash
# 1. Build the multiome MuData on the FINALIZED cell set (see "Cell basis" below).
python3 scripts/build_multiome_mudata.py \
    --rna-mex-dir   <GEX filtered MEX> \
    --atac-mex-dir  <ATAC peak MEX> \
    --filtered-barcodes <finalized knee barcodes> \    # NOT the permissive candidate set
    --strip-barcode-suffix \
    --output-h5mu   sample.h5mu
# ... then add a `guide` modality (guide x cell calls) to sample.h5mu ...

# 2. Render the unified trimodal QC figure.
python3 scripts/generate_trimodal_qc.py \
    --mudata sample.h5mu \
    --output-prefix qc/sample_trimodal_qc \
    --title "<sample> — single-pass trimodal QC"
```

The guide modality is an AnnData of `cell × guide` calls (boolean/float); guide names are
split on `--guide-gene-sep` (default `-`, e.g. `GENE-1`/`GENE-2`) to collapse dual guides to
a target gene. Cells absent from the guide modality are reported `not_in_guide_set`.

## Cell basis — use the finalized call, not the permissive candidate set

**This is the one trap.** For STARsolo `--soloCellFilter EmptyDrops_CR`, the matrix written
to `outs/filtered_feature_bc_matrix` is the **permissive EmptyDrops *candidate* set** — the
knee (`is_simple_cell==1`) **plus** a rescued low-UMI tail. From the CAT-ATAC lean run
(`Solo.out/GeneFull/filtered/EmptyDrops/EmptyDrops/summary.json`):

```
n_simple_cells  : 12,220   ← knee / finalized basis (≥ retain_threshold 1,612 UMIs)
n_ed_passers    :  6,295   ← permissive rescued tail (low UMI, low ATAC)
n_cells_passing : 18,515   = 12,220 + 6,295   ← the deceptive "filtered" count
```

The multiome path finalizes *after* ATAC by dropping the rescued empties; a profile that
stops at matrices leaves the candidate set in place. Build QC on the **knee** — restrict to
`is_simple_cell==1` from `emptydrops_results.tsv`, or pass those barcodes to
`build_multiome_mudata.py --filtered-barcodes`. The knee (12,220) matches CR-ARC's joint
cells (12,466) within ~2%; the rescued tail is exactly the low-UMI/low-ATAC population ARC's
joint call also rejects. Using the candidate set inflates the cell count and *deflates* the
guide-assignment rate (wrong denominator).

## Panels (2×3)

1. **GEX** — UMIs vs genes, coloured by % mito.
2. **ATAC** — in-peak depth vs # peaks, coloured by FRiP (`atac.obs['atac_frip']` or
   `--atac-metrics`).
3. **Guide** — assignment status (`not_in_guide_set` / `unassigned` / `singlet` / `multiplet`).
4. **Cells per modality** — GEX / ATAC / guide-assigned / triple overlap.
5. **Joint UMAP — guide** — GEX manifold coloured by perturbation (the money shot).
6. **Joint UMAP — ATAC** — same cells, coloured by ATAC depth/FRiP.

## CAT-ATAC worked example (GSE288996, K562 DMSO rep1)

`python3 scripts/build_catatac_trimodal_qc.py` → `catatac_dmso1_trimodal.h5mu` +
`trimodal_qc.{html,json,png}`. On the finalized cells:

| modality | count | note |
|---|---|---|
| GEX | 12,220 | EmptyDrops knee; cf. CR-ARC joint 12,466 (~2%) |
| ATAC | 12,220 | every finalized GEX cell has ATAC |
| guide-assigned | 4,775 | 39.1% of cells; ~72% of guide-considered (cf. paper ~77%) |
| triple | 4,775 | the trimodal-cell count |

Guide calls here are the study's deposited DMSO1 calls (placeholder); swap for the suite's
own guide-arm output when it lands — the MuData/QC pipeline is unchanged. Example output:
`docs/figures/trimodal_qc_catatac_dmso1.png`.

## Dependencies

`mudata`, `muon`, `scanpy`, `anndata`, `plotly`, and `kaleido` (static PNG export). The PNG
path re-introduces a static-image dependency the suite had otherwise dropped (HTML+JSON only)
— it is for the paper figure / headless reports.
