#!/usr/bin/env python3
"""Ambient-FDR guide-call cutoff — a per-cell-guide cutoff anchored to the noise floor.

SUPERSEDED FOR THE PRODUCTION PATH (2026-06): the suite now computes this cutoff IN-BINARY
(merged STAR-suite 464f394; outputs under outs/crispr_analysis/ambient_fdr/), and the recipe
build_catatac_trimodal_qc.py reads those q-values directly. This pure-Python implementation is
kept as a readable reference and for ad-hoc re-calling outside a STAR run. It is a CUTOFF
ESTIMATOR (emptyDrops construction [Lun 2019] + Poisson guide-background [Replogle 2022; crispat
2024; CLEANSER 2025]) layered on top of the validated GMM default -- NOT a new caller. The FDR is
principled but still a choice; the QC is primary. See docs/guide-fdr-qc.md.


The cutoff is *not* an arbitrary mixture-model valley. The per-guide ambient (noise) profile is
the guide's UMI distribution across EMPTY droplets (non-cell barcodes); for each cell-guide the
null is Poisson(f[guide] * cell_guide_depth) (depth-scaled ambient), and the BH q-value of that
test is the calling statistic. A call at FDR alpha is simply `qvalue <= alpha`.

Store the q-value, not a fixed call set: any FDR is then a one-line filter on the object
(`guide.layers['qvalue'] <= alpha`), and the figure slider, the MuData filter, and the binary
all share the same number. The FDR is the practitioner's interpretable knob
("<= X% of calls expected to be ambient").

Library:  ambient_fdr_qvalues(), guide_qvalue_anndata()
CLI:      guide count MEX + a called-cell barcode list -> calls.csv.gz + qvalues.npy
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io
import scipy.sparse as sp
from scipy.stats import poisson
from statsmodels.stats.multitest import multipletests

strip1 = lambda s: [b[:-2] if str(b).endswith("-1") else str(b) for b in s]
canon = lambda g: str(g).replace("-", "_")          # ADNP-1 / ADNP.1 -> ADNP_1
gene = lambda g: canon(g).rsplit("_", 1)[0]


def load_guide_mex(mex_dir: str):
    """Load a guides x ALL-barcodes count MEX (handles .gz or plain). Returns (M, guide_names, barcodes)."""
    p = Path(mex_dir)
    mtx = p / "matrix.mtx" if (p / "matrix.mtx").exists() else p / "matrix.mtx.gz"
    M = scipy.io.mmread(str(mtx)).tocsr()
    def rd(name):
        f = p / name if (p / name).exists() else p / (name + ".gz")
        return pd.read_csv(f, header=None, sep="\t")
    gn = [canon(x) for x in rd("features.tsv")[0].astype(str)]
    bc = strip1(rd("barcodes.tsv")[0])
    return M, gn, bc


def ambient_fdr_qvalues(M, gn, bc, cells):
    """Depth-scaled ambient-FDR test. M = guides x ALL barcodes (incl. empties); cells = called-cell
    barcodes (e.g. the GEX EmptyDrops knee). Returns (qmat, counts, ambient_profile), cell x guide."""
    cset = set(cells)
    is_cell = np.array([b in cset for b in bc])
    f = np.asarray(M[:, ~is_cell].sum(1)).ravel()          # ambient (empty-droplet) soup
    f = f / max(f.sum(), 1)
    ci = {b: i for i, b in enumerate(bc)}
    Mc = np.zeros((len(gn), len(cells)))                   # 0 where a cell has no guide barcode
    pres = [j for j, b in enumerate(cells) if b in ci]
    if pres:
        Mc[:, pres] = M[:, [ci[cells[j]] for j in pres]].toarray()
    T = Mc.sum(0)
    p = poisson.sf(Mc - 1, np.outer(f, T))                 # P(X >= obs) under ambient null
    q = multipletests(p.ravel(), method="fdr_bh")[1].reshape(p.shape)
    return q.T.astype("float32"), Mc.T.astype("float32"), f


def guide_qvalue_anndata(M, gn, bc, cells, default_fdr=0.01):
    """Build the guide modality AnnData carrying the q-value layer (the filterable QC)."""
    import anndata as ad
    q, counts, f = ambient_fdr_qvalues(M, gn, bc, cells)
    A = ad.AnnData(X=sp.csr_matrix(counts))
    A.obs_names = list(cells)
    A.var_names = gn
    A.layers["qvalue"] = q
    A.layers["called"] = (q <= default_fdr).astype("float32")
    A.var["ambient_rate"] = f
    called = q <= default_fdr
    gpc = [sorted({gene(gn[i]) for i in np.where(called[j])[0]}) for j in range(len(cells))]
    A.obs["min_qvalue"] = q.min(1)
    A.obs["n_guides_at_default"] = called.sum(1)
    A.obs["assigned_gene"] = [s[0] if len(s) == 1 else ("multiplet" if len(s) > 1 else "none") for s in gpc]
    A.uns["guide_qc"] = {
        "method": "ambient-FDR (depth-scaled Poisson vs empty-droplet soup, BH)",
        "default_fdr": default_fdr,
        "filter_recipe": "calls at FDR alpha = layers['qvalue'] <= alpha",
    }
    return A


def per_cell_genes(q, gn, fdr):
    """{cell_index: sorted set of called target genes} at a given FDR (a threshold on the q-matrix)."""
    called = q <= fdr
    return [sorted({gene(gn[i]) for i in np.where(called[j])[0]}) for j in range(q.shape[0])]


def main():
    ap = argparse.ArgumentParser(description="Ambient-FDR guide calls + q-values from a guide count MEX.")
    ap.add_argument("--guide-mex", required=True, help="guides x ALL barcodes MEX dir (incl. empties)")
    ap.add_argument("--cells", required=True, help="file of called-cell barcodes (GEX knee), one per line")
    ap.add_argument("--fdr", type=float, default=0.01)
    ap.add_argument("--out-prefix", required=True)
    a = ap.parse_args()
    M, gn, bc = load_guide_mex(a.guide_mex)
    cells = strip1([l.strip() for l in open(a.cells) if l.strip()])
    q, counts, f = ambient_fdr_qvalues(M, gn, bc, cells)
    gpc = per_cell_genes(q, gn, a.fdr)
    df = pd.DataFrame(
        [(b, len(gpc[j]), "|".join(gpc[j]) or "None", float(q[j].min())) for j, b in enumerate(cells)],
        columns=["barcode", "num_genes", "gene_call", "min_qvalue"])
    df.to_csv(f"{a.out_prefix}.calls_fdr{a.fdr:g}.csv.gz", index=False)
    np.save(f"{a.out_prefix}.qvalues.npy", q)              # cell x guide; threshold at any FDR later
    n = int((q <= a.fdr).any(1).sum())
    print(f"cells assigned @ FDR {a.fdr}: {n} / {len(cells)}  ->  {a.out_prefix}.calls_fdr{a.fdr:g}.csv.gz + .qvalues.npy")


if __name__ == "__main__":
    main()
