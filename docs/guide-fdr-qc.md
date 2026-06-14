# Guide QC — a tunable, FDR-controlled cutoff + a q-value MuData layer

A practical answer to *"where do I set the guide-calling cutoff, and how do I move off the
default?"* — **not** a new caller. GMM (the suite's CR-compat path, 100% Cell Ranger–concordant
on A375) stays the **default and the only validated caller**. What this adds is:

1. a **tunable QC** — needed in practice because a vendor default can be too strict for a given
   assay (it under-calls), and
2. an **automatically chosen default cutoff** in place of a static, arbitrary UMI threshold,
   carried into the analysis object as a filter so any FDR is a one-line re-call.

The FDR α is principled (a controlled error rate) but still a *choice*; the **QC is primary** —
the cutoff ultimately has to fit the biology, not the statistical approximation of it.

## The situation it helps with: low, uneven guide-UMI depth

This helps with a *common* condition, not a better caller. Guide-UMI depth is often low and varies
across guides — guides differ by orders of magnitude in capture depth and in ambient contamination.
A single fixed UMI/mixture-valley threshold cannot serve a library that diverse: it is
simultaneously too strict for the clean, low-ambient guides and too loose for the contaminated
ones. Low guide-UMI depth is common — every dataset has a low-depth tail of cells, and
higher-diversity libraries spread reads thinner — so the adaptive cutoff helps wherever depth is
low, and is simply unnecessary where depth is high.

Worked numbers (CAT-ATAC K562 DMSO rep1, suite single-pass): per-guide ambient contamination spans
**~500×**, representation runs **5–672 cells/guide**, per-cell depth is modest (**median 16 guide
UMIs/cell; only 0.6% lack guide reads**). Assignment is **depth-limited** — it climbs from ~0% below
5 guide UMIs/cell to ~100% above 30; on the public A375 CRISPR screen (10x `1k_CRISPR_5p_gemx`) the
same default GMM caller assigns **91.5%** of cells (1,086/1,187), so a lower overall rate reflects
the library's depth, not the caller (GMM 41% here vs 91.5% on A375). The effective per-guide threshold
the FDR sets moves **2 → 7 UMIs**, beating the GMM default at every depth band and recovering **+2,807**
real cells (GMM 4,991 → 7,797 of 12,220) with no re-sequencing. Supplementary figure (4 panels;
panel C is a double histogram of assignment vs depth): `scripts/fig_grna_library_diversity.py`
(`--run-dir <star_run> --out-prefix <path>`) → `supp_grna_library_diversity.{png,pdf}`.

## The cutoff: an FDR-controlled noise floor (established methodology, cited — not ours)

- The per-guide **ambient/noise floor** is the guide's UMI profile across **empty droplets**
  (non-cell barcodes) — pure ambient contamination.
- For each cell-guide the null is **Poisson(f[guide] × cell_guide_depth)** (depth-scaled ambient),
  and the **Benjamini–Hochberg q-value** of that test is the statistic.
- A call at FDR α is simply **`qvalue ≤ α`** ("≤ X% of calls expected to be ambient").

This is the **emptyDrops** construction (ambient-from-empties + BH FDR; Lun et al., *Genome
Biology* 2019) with a Poisson guide-background (cf. Replogle et al. 2022; **crispat**, Braunger &
Velten, *Bioinformatics* 2024; **CLEANSER**, *Cell Genomics* 2025) — a **cutoff estimator**, not a
learned caller. A tuned ratio method could likely reach similar numbers; the merit is
*justifiability* (the floor is anchored in low-noise empirical signal), not unique capability.

Context that makes this useful here: the published CAT-ATAC calls use an **undocumented, unshared
Stan cutoff** — not reproducible. This cutoff is anchored to data the run already produces (the
empties), needs no fitting loop, and is transparent. Equivalence is shown only where we can show
it: per-guide **AUC 0.989** of the suite's UMI *evidence* vs the deposited calls (rank-based,
cutoff-independent) — that validates the *evidence ranking*, not the cutoff.

## Store the q-value, not a fixed call set

The guide modality carries the q-value so **any FDR is a one-line filter** — no recompute:

```python
mdata['guide'].layers['qvalue'] <= alpha        # re-call at FDR alpha
```

Schema produced by `build_catatac_trimodal_qc.py` (consuming the binary's `crispr_analysis/`):

| where | field | meaning |
|---|---|---|
| `guide.obs['gmm_*']` | **the validated default** | GMM (CR-compat) call: `gmm_feature_call`, `gmm_num_features` |
| `guide.X` | the tunable call set | boolean call at the shipped default α (feeds the QC figure) |
| `guide.layers['qvalue']` | **the filter** | the binary's BH q-value (READ, not recomputed; missing ⇒ 1) |
| `guide.layers['counts']` | counts | deduped guide UMI counts (cell × guide), if cr_assign present |
| `guide.obs` | `call_status`, `feature_call`, `min_qvalue`, `assigned_gene` | tunable-cutoff per-cell summary |
| `guide.var` | `ambient_rate`, `target_gene` | empty-droplet soup fraction; gene split |
| `mdata.uns['guide_qc']` | `default_caller`, `tunable_cutoff`, `fdr_is_a_choice`, `filter_recipe` | self-documenting framing |

## Where the cutoff is computed

**In the single binary (production path).** As of merged STAR-suite `464f394`, the cutoff,
the per-cell calls, the FDR×min-UMI sweep, and the sparse q-value matrix are emitted in-binary
under `outs/crispr_analysis/ambient_fdr/` (`--crGuideCaller auto --crGuideFdr 0.01
--crGuideFdrMinUmi 1 --crGuideFdrEmitQvalues sparse`), alongside the GMM CR-compat root. The
machinery is concurrent and adds no wall-clock. **This is the path the recipe consumes.**

> The cutoff **requires** the finalized EmptyDrops knee universe. This is a *dependency* of
> estimating the floor from data (cell vs ambient feeds the floor), not a correction of prior
> behavior — with a static floor the cell universe was irrelevant. Both callers (GMM and the
> ambient cutoff) share the knee (`is_simple_cell==1`); the rescued low-UMI tail is demoted to
> the ambient pool.

**Standalone reference (`scripts/guide_ambient_fdr.py`).** A pure-Python implementation of the
same math — **superseded by the in-binary caller for the production path**, kept as a readable
reference and for ad-hoc re-calling outside a STAR run. `scripts/guide_fdr_umap.py` (an
exploratory per-FDR UMAP) is likewise retained but not part of the shipped path.

## Dependencies

`mudata`, `scanpy`, `anndata`, `scipy`, `plotly`, `kaleido` (static PNG). See `trimodal-qc.md`
for the unified figure this feeds.
