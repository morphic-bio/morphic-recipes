# Guide QC — ambient-FDR cutoff, q-value MuData layer, FDR-slider UMAP

The one-stop answer to *"where do I set the guide-calling cutoff?"* — a principled cutoff anchored
to the measured noise floor, carried into the analysis object as a filter, and exposed to the
practitioner as an interactive slider. This replaces an arbitrary mixture-model valley (a bare
"UMI ≥ 10") with a transparent, FDR-controlled, reproducible decision.

## The cutoff: ambient-FDR (noise floor, not a magic number)

- The per-guide **ambient/noise floor** is the guide's UMI distribution across **empty droplets**
  (non-cell barcodes) — pure ambient contamination.
- For each cell-guide the null is **Poisson(f[guide] × cell_guide_depth)** (depth-scaled ambient),
  and the **BH q-value** of that test is the calling statistic.
- A call at FDR α is simply **`qvalue ≤ α`**. The FDR is the practitioner's interpretable knob
  ("≤ X% of calls expected to be ambient").

Why this matters: the published CAT-ATAC calls use an **undocumented, unshared Stan cutoff** — not
reproducible. This method is anchored to data the run already produces (the empties), needs no
fitting loop, and exposes the decision. Validation that it is the *same* underlying signal as the
published caller: per-guide **AUC 0.989** of the suite's UMI evidence vs the deposited calls
(rank-based, cutoff-independent).

## Store the q-value, not a fixed call set

The guide modality carries the q-value so **any FDR is a one-line filter** — no recompute:

```python
mdata['guide'].layers['qvalue'] <= alpha        # calls at FDR alpha
```

Schema (`guide_ambient_fdr.guide_qvalue_anndata`):

| where | field | meaning |
|---|---|---|
| `guide.X` | counts | deduped guide UMI counts (cell × guide) |
| `guide.layers['qvalue']` | **the filter** | BH q-value of the ambient-FDR test |
| `guide.layers['called']` | bool | convenience: `qvalue ≤ default_fdr` (shipped default 1%) |
| `guide.obs` | `assigned_gene`, `min_qvalue`, `n_guides_at_default` | per-cell summary at the default |
| `guide.var['ambient_rate']` | f[guide] | the empty-droplet soup fraction |
| `mdata.uns['guide_qc']` | method, default_fdr, filter_recipe | self-documenting |

The figure slider, the MuData filter, and (when vendored) the binary all use the **same** q-value.

## Scripts

- **`scripts/guide_ambient_fdr.py`** — the caller. Library (`ambient_fdr_qvalues`,
  `guide_qvalue_anndata`, `per_cell_genes`) + CLI (`--guide-mex --cells --fdr --out-prefix` →
  `calls.csv.gz` + `qvalues.npy`). This is the executable to re-call at any cutoff.
- **`scripts/guide_fdr_umap.py`** — the interactive QC: one GEX UMAP with an **FDR slider**.
  The embedding is computed once (cutoff-independent); only the colouring changes, with a live
  readout of the chosen **q-value** and the **cells retained**. One self-contained Plotly
  HTML+JSON+PNG.

```bash
python3 scripts/guide_fdr_umap.py \
  --h5mu sample.h5mu \
  --guide-mex <guide_count_mex_dir> \
  --emptydrops <Solo.out/.../EmptyDrops/.../emptydrops_results.tsv> \
  --output-prefix qc/sample_guide_fdr_umap
```

## Vendoring (the single-binary target)

The *calling* math is ~free (column sums + Poisson tail + BH; ~50 ms). The reason it belongs in
the C++ binary is the self-contained-output promise, not compute: the binary already emits
protospacer calls, so this is a threshold-method swap (GMM valley → ambient-FDR) plus emitting the
q-value. The expensive piece — the **UMAP embedding (~5 min in Python)** — is the genuine vendor
target (e.g. `umappp`), computed once; the FDR slider then explores all cutoffs client-side. See
the STAR-suite handoff for the C++ spec. This standalone is the exploration / further-analysis layer.
