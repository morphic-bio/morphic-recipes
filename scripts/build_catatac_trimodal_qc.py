#!/usr/bin/env python3
"""Build the CAT-ATAC trimodal MuData (GEX + ATAC-peak + CRISPR-guide) and render the
unified QC figure -- the worked example behind docs/trimodal-qc.md.

Dataset: CAT-ATAC (GSE288996, K562 DMSO rep1). All three modalities are the suite's OWN
single-pass output (one STAR process: GEX Solo + concurrent Chromap ATAC + guide
process_features). The guide modality carries BOTH callers on one cell definition:

  obs['gmm_*']      = the validated DEFAULT call (GMM, CR-compat root, crispr_analysis/
                      protospacer_calls_*; 100% Cell Ranger-concordant on A375) -- the
                      stricter baseline.
  X                 = the TUNABLE call at the shipped default cutoff (alpha = --default-fdr);
                      feeds the QC figure, which is the tunable instrument.
  layers['qvalue']  = the binary's BH q-value (READ from crispr_analysis/ambient_fdr/, not
                      recomputed; missing entries imply q = 1).
  layers['counts']  = deduped guide UMI counts (cr_assign matrix), if available.

This is NOT a new caller. GMM stays the default/validated path. The add is (1) a tunable QC
and (2) an automatic cutoff -- FDR-controlled against an empty-droplet noise floor: the
emptyDrops construction [Lun et al., Genome Biology 2019] with a Poisson guide-background
[Replogle et al. 2022; crispat, Braunger & Velten 2024; CLEANSER, Cell Genomics 2025] -- in
place of a static, arbitrary UMI threshold. The FDR alpha is principled (a controlled error
rate) but still a choice; the QC is PRIMARY -- the cutoff has to fit the biology, not the
statistical approximation of it. Re-call at any alpha downstream with one line:
    mdata['guide'].layers['qvalue'] <= alpha

Cell basis: the *finalized* EmptyDrops knee (is_simple_cell==1), NOT the permissive candidate
set STARsolo writes to outs/filtered_feature_bc_matrix (knee + a rescued low-UMI tail). The
knee (~12,220) matches CR-ARC's joint cells (12,466) within ~2%. The ambient cutoff *requires*
this finalized universe (a dependency of estimating the floor from data, not a correction);
see docs/trimodal-qc.md and docs/guide-fdr-qc.md.

Dataset-specific reproducer (like run_jax_multiome01_production.sh); paths default to the local
benchmark tree and are overridable. The reusable piece is generate_trimodal_qc.py (the figure).
"""
from __future__ import annotations

import argparse
import gzip
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io
import scipy.sparse as sp
import anndata as ad
import scanpy as sc
import mudata as md


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build CAT-ATAC trimodal MuData (in-binary guide calls) + render QC.")
    p.add_argument("--run-dir", default="/mnt/pikachu/catatac_gse288996/full_bench/"
                   "catatac_trimodal_full_ambientfdr_20260614T123323Z/star_run",
                   help="STAR single-pass run dir (contains outs/, Solo.out/, atac/, cr_assign/)")
    p.add_argument("--out-dir", default="/mnt/pikachu/catatac_gse288996/qc_endpoint",
                   help="Output dir for the .h5mu and figure")
    p.add_argument("--default-fdr", type=float, default=0.01, help="Shipped default FDR alpha for guide.X / called")
    p.add_argument("--guide-counts-mex", default=None,
                   help="cr_assign 'sample' MEX dir for the optional counts layer (auto-globbed if omitted)")
    p.add_argument("--skip-figure", action="store_true", help="Write the .h5mu only; do not render the figure")
    return p.parse_args()


def strip1(barcodes) -> list[str]:
    return [b[:-2] if str(b).endswith("-1") else str(b) for b in barcodes]


def canon(g) -> str:
    return str(g).replace("-", "_")


def gene(g) -> str:
    return canon(g).rsplit("_", 1)[0]


def load_mex(path: str, feat_col: int = 1, want_type: str | None = None) -> ad.AnnData:
    M = scipy.io.mmread(gzip.open(f"{path}/matrix.mtx.gz")).tocsr()           # features x cells
    bc = pd.read_csv(f"{path}/barcodes.tsv.gz", header=None, sep="\t")[0].astype(str).tolist()
    ft = pd.read_csv(f"{path}/features.tsv.gz", header=None, sep="\t")
    A = ad.AnnData(X=M.T.tocsr())
    A.obs_names = strip1(bc)
    col = feat_col if ft.shape[1] > feat_col else 0
    A.var_names = ft[col].astype(str).tolist()
    if want_type is not None and ft.shape[1] > 2:
        A = A[:, (ft[2].astype(str) == want_type).values].copy()
    A.var_names_make_unique()
    return A


def main() -> None:
    args = parse_args()
    R = Path(args.run_dir)
    OUT = Path(args.out_dir)
    OUT.mkdir(parents=True, exist_ok=True)
    AF = R / "outs/crispr_analysis/ambient_fdr"
    DEFAULT_FDR = args.default_fdr

    # ---- RNA (GEX) on the finalized EmptyDrops knee --------------------------------------
    print(">> GEX (Gene Expression rows of merged MEX), restricted to EmptyDrops knee ...")
    gex = load_mex(str(R / "outs/filtered_feature_bc_matrix"), feat_col=1, want_type="Gene Expression")
    ed = pd.read_csv(R / "Solo.out/GeneFull/filtered/EmptyDrops/EmptyDrops/emptydrops_results.tsv", sep="\t")
    knee = set(strip1(ed.loc[ed["is_simple_cell"] == 1, "barcode"].astype(str)))
    gex = gex[[b for b in gex.obs_names if b in knee]].copy()
    cells = list(gex.obs_names)
    print(f"   GEX: {gex.n_obs} cells x {gex.n_vars} genes (knee)")

    # ---- ATAC peaks ----------------------------------------------------------------------
    print(">> ATAC peak MEX ...")
    atac = load_mex(str(R / "atac/peak_mex"), feat_col=0)
    atac = atac[[b for b in cells if b in set(atac.obs_names)]].copy()
    mp = R / "atac/atac_metrics.tsv"
    if mp.exists():
        m = pd.read_csv(mp, sep="\t")
        m["barcode"] = strip1(m["barcode"])
        m = m.set_index("barcode")
        if "atac_peak_fraction" in m.columns:
            atac.obs["atac_frip"] = m["atac_peak_fraction"].reindex(atac.obs_names).values
    print(f"   ATAC: {atac.n_obs} cells x {atac.n_vars} peaks")

    # ---- guide: tunable cutoff (q-values READ from the binary) + GMM validated default ----
    print(">> guide q-values READ from crispr_analysis/ambient_fdr/guide_qvalues.mtx (not recomputed) ...")
    qco = scipy.io.mmread(str(AF / "guide_qvalues.mtx")).tocoo()    # rows=cells, cols=guides; missing => q=1
    qbc = strip1(pd.read_csv(AF / "guide_qvalues_barcodes.tsv", header=None, sep="\t")[0])
    qgn = [canon(x) for x in pd.read_csv(AF / "guide_qvalues_features.tsv", header=None, sep="\t")[0].astype(str)]
    qd = np.ones((len(qbc), len(qgn)), dtype="float32")
    qd[qco.row, qco.col] = qco.data.astype("float32")              # explicit observed entries; missing stay 1.0
    qidx = {b: i for i, b in enumerate(qbc)}
    qrow = np.array([qidx.get(b, -1) for b in cells])
    qlayer = np.ones((len(cells), len(qgn)), dtype="float32")
    vq = qrow >= 0
    qlayer[vq] = qd[qrow[vq]]
    called = (qlayer <= DEFAULT_FDR).astype("float32")

    guide = ad.AnnData(X=sp.csr_matrix(called))                    # X = default-FDR call set (feeds the QC figure)
    guide.obs_names = cells
    guide.var_names = qgn
    guide.layers["qvalue"] = qlayer
    guide.var["target_gene"] = [gene(g) for g in qgn]
    arp = AF / "guide_ambient_rates.tsv"
    if arp.exists():
        ar = pd.read_csv(arp, sep="\t")
        ar["fid"] = [canon(x) for x in ar["feature_id"].astype(str)]
        guide.var["ambient_rate"] = ar.set_index("fid")["ambient_rate"].reindex(qgn).values

    # optional deduped UMI counts (cr_assign)
    gd = args.guide_counts_mex
    if gd is None:
        hits = sorted((R / "cr_assign/CRISPR_Guide_Capture").glob("*/sample"))
        gd = str(hits[0]) if hits else None
    if gd and (Path(gd) / "matrix.mtx").exists():
        Mc = scipy.io.mmread(f"{gd}/matrix.mtx").tocsr()           # features x cells
        mbc = strip1(pd.read_csv(f"{gd}/barcodes.tsv", header=None, sep="\t")[0])
        mgn = [canon(x) for x in pd.read_csv(f"{gd}/features.tsv", header=None, sep="\t")[0].astype(str)]
        mci = {b: i for i, b in enumerate(mbc)}
        mgi = {g: i for i, g in enumerate(mgn)}
        Md = Mc.toarray()
        col_idx = np.array([mci.get(b, -1) for b in cells])
        row_idx = np.array([mgi.get(g, -1) for g in qgn])
        counts = np.zeros((len(cells), len(qgn)), dtype="float32")
        vc = col_idx >= 0
        rr = np.where(row_idx < 0, 0, row_idx)
        sub = Md[np.ix_(rr, col_idx[vc])]
        sub[row_idx < 0, :] = 0.0
        counts[vc, :] = sub.T
        guide.layers["counts"] = counts

    # ambient-FDR per-cell call (the tunable cutoff's per-cell summary)
    cc = pd.read_csv(AF / "guide_fdr_calls_per_cell.csv")
    cc["bc"] = strip1(cc["cell_barcode"])
    cc = cc.set_index("bc")
    for col in ["call_status", "feature_call", "num_features", "num_umis", "min_qvalue"]:
        if col in cc.columns:
            guide.obs[col] = cc[col].reindex(cells).values
    guide.obs["assigned_gene"] = [
        gene(fc) if (st == "singlet" and isinstance(fc, str)) else ("multiplet" if st == "multiplet" else "none")
        for st, fc in zip(guide.obs.get("call_status", pd.Series(["none"] * len(cells))),
                          guide.obs.get("feature_call", pd.Series([None] * len(cells))))
    ]
    # the validated DEFAULT caller (GMM, CR-compat root) on the SAME knee, for reference
    gmm = pd.read_csv(R / "outs/crispr_analysis/protospacer_calls_per_cell.csv")
    gmm["bc"] = strip1(gmm["cell_barcode"])
    gmm = gmm.set_index("bc")
    if "feature_call" in gmm.columns:
        guide.obs["gmm_feature_call"] = gmm["feature_call"].reindex(cells).values
    if "num_features" in gmm.columns:
        guide.obs["gmm_num_features"] = gmm["num_features"].reindex(cells).values
    n_gmm = int((guide.obs.get("gmm_num_features", pd.Series(0, index=cells)).fillna(0) > 0).sum())
    n_any = int((called.sum(1) > 0).sum())
    print(f"   guide: {guide.n_obs} cells x {guide.n_vars} guides")
    print(f"     GMM (validated default, CR-compat baseline): {n_gmm} cells called (the stricter default)")
    print(f"     tunable cutoff @ alpha={DEFAULT_FDR}: emits {n_any} cells -- what the default emits, NOT a result")

    # ---- GEX UMAP ------------------------------------------------------------------------
    print(">> GEX UMAP -> rna.obsm['X_umap'] ...")
    gx = gex.copy()
    sc.pp.normalize_total(gx, target_sum=1e4)
    sc.pp.log1p(gx)
    sc.pp.highly_variable_genes(gx, n_top_genes=2000)
    gx = gx[:, gx.var.highly_variable].copy()
    sc.pp.scale(gx, max_value=10)
    sc.tl.pca(gx, n_comps=30)
    sc.pp.neighbors(gx, n_neighbors=15)
    sc.tl.umap(gx)
    gex.obsm["X_umap"] = gx.obsm["X_umap"]

    # ---- assemble + write ----------------------------------------------------------------
    mdata = md.MuData({"rna": gex, "atac": atac, "guide": guide})
    mdata.uns["trimodal"] = {
        "dataset": "CAT-ATAC GSE288996 K562 DMSO rep1",
        "cell_basis": "EmptyDrops knee (is_simple_cell==1)",
        "guide_default_caller": "GMM (CR-compat root); carried in guide.obs['gmm_*']",
        "guide_tunable_cutoff": "FDR-controlled vs empty-droplet noise floor; guide.X + layers['qvalue']",
        "run": str(R),
    }
    mdata.uns["guide_qc"] = {
        "default_caller": "GMM (CR-compat root, crispr_analysis/protospacer_calls_*); validated 100% CR-concordant on A375; carried in guide.obs['gmm_*']",
        "tunable_cutoff": "an automatic, tunable cutoff -- NOT a new caller: FDR-controlled vs an empty-droplet noise floor (emptyDrops construction [Lun 2019] + Poisson guide-background [Replogle 2022; crispat 2024; CLEANSER 2025])",
        "default_fdr": DEFAULT_FDR,
        "fdr_is_a_choice": "alpha is principled (a controlled error rate) but still arbitrary; the QC is PRIMARY -- the cutoff must fit the biology, not the statistical approximation",
        "filter_recipe": "re-call at FDR alpha  =  mdata['guide'].layers['qvalue'] <= alpha (one line; reproduces the binary's sweep)",
        "universe_note": "the ambient method requires the finalized knee universe (a dependency of estimating the floor from data) -- not a correction of prior behavior",
        "qvalue_basis": "knee cells x guides; BH universe = n_knee_cells * n_guides",
    }
    mdata.obs["guide_gene"] = pd.Series(guide.obs["assigned_gene"].values,
                                        index=guide.obs_names).reindex(mdata.obs_names).values
    h5mu = OUT / "catatac_dmso1_trimodal.h5mu"
    mdata.write(str(h5mu))
    print(f">> wrote MuData: {h5mu}  ({mdata.n_obs} union cells)")

    if not args.skip_figure:
        gen = Path(__file__).resolve().parent / "generate_trimodal_qc.py"
        cmd = [sys.executable, str(gen), "--mudata", str(h5mu),
               "--output-prefix", str(OUT / "trimodal_qc"),
               "--guide-gene-sep", "_",
               "--title", "CAT-ATAC K562 DMSO rep1 - single-pass trimodal QC (tunable guide cutoff, alpha=1%; QC-primary)"]
        print(f">> rendering figure: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
