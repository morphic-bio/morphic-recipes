#!/usr/bin/env python3
"""Build the CAT-ATAC trimodal MuData (GEX + ATAC-peak + CRISPR-guide) and render the
unified QC figure -- the worked example behind docs/trimodal-qc.md.

Dataset: CAT-ATAC (GSE288996, K562 DMSO rep1). GEX + ATAC are the suite's own single-pass
outputs (lean run); the guide calls are the study's deposited DMSO1 calls, a placeholder
until the suite's own guide arm lands (swap then -- the MuData/QC pipeline is unchanged).
All three modalities live in GEX-barcode space.

Cell basis: the *finalized* EmptyDrops call (the knee, is_simple_cell==1), NOT the
permissive candidate set STARsolo writes to outs/filtered_feature_bc_matrix (knee + a
rescued low-UMI tail). The knee (~12,220) matches CR-ARC's joint cells (12,466) within
~2%; the rescued tail is exactly the low-UMI/low-ATAC population ARC's joint call rejects.
See docs/trimodal-qc.md for the why.

This is a dataset-specific reproducer (like run_jax_multiome01_production.sh); paths default
to the local benchmark tree and are overridable. The reusable pieces are
build_multiome_mudata.py (object) and generate_trimodal_qc.py (figure).
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
    p = argparse.ArgumentParser(description="Build CAT-ATAC trimodal MuData + render the QC figure.")
    p.add_argument("--bench-dir", default="/mnt/pikachu/catatac_gse288996", help="CAT-ATAC benchmark root")
    p.add_argument("--lean-subdir", default="full_bench/suite_out_lean", help="Suite lean run dir, relative to bench-dir")
    p.add_argument("--guide-calls", default="guide_ref/DMSO1_guide_calls.tsv.gz", help="Deposited guide calls TSV, relative to bench-dir")
    p.add_argument("--out-subdir", default="qc_endpoint", help="Output dir, relative to bench-dir")
    p.add_argument("--skip-figure", action="store_true", help="Write the .h5mu only; do not call generate_trimodal_qc.py")
    return p.parse_args()


def strip1(barcodes) -> list[str]:
    return [b[:-2] if str(b).endswith("-1") else str(b) for b in barcodes]


def load_mex(path: str, feat_col: int = 1) -> ad.AnnData:
    M = scipy.io.mmread(gzip.open(f"{path}/matrix.mtx.gz")).tocsr()        # features x cells
    bc = pd.read_csv(f"{path}/barcodes.tsv.gz", header=None, sep="\t")[0].astype(str).tolist()
    ft = pd.read_csv(f"{path}/features.tsv.gz", header=None, sep="\t")
    col = feat_col if ft.shape[1] > feat_col else 0
    A = ad.AnnData(X=M.T.tocsr())
    A.obs_names = strip1(bc)
    A.var_names = ft[col].astype(str).tolist()
    A.var_names_make_unique()
    return A


def main() -> None:
    args = parse_args()
    D = Path(args.bench_dir)
    L = D / args.lean_subdir
    run = L / "star_sample/run"
    out = D / args.out_subdir
    out.mkdir(parents=True, exist_ok=True)

    print(">> loading suite GEX (GeneFull) ...")
    gex = load_mex(str(run / "outs/filtered_feature_bc_matrix"))  # PERMISSIVE EmptyDrops candidates
    # Restrict to the FINALIZED cell call: the EmptyDrops knee (is_simple_cell==1).
    ed = pd.read_csv(run / "Solo.out/GeneFull/filtered/EmptyDrops/EmptyDrops/emptydrops_results.tsv", sep="\t")
    n_perm = gex.n_obs
    final_bc = set(strip1(ed.loc[ed["is_simple_cell"] == 1, "barcode"].astype(str)))
    gex = gex[[b for b in gex.obs_names if b in final_bc]].copy()
    print(f"   GEX finalized: {gex.n_obs} cells x {gex.n_vars} genes  (EmptyDrops knee; {n_perm} permissive candidates)")

    print(">> loading suite ATAC peak MEX ...")
    atac = load_mex(str(L / "atac/peak_mex"), feat_col=0)
    atac = atac[[b for b in gex.obs_names if b in set(atac.obs_names)]].copy()
    print(f"   ATAC: {atac.n_obs} cells x {atac.n_vars} peaks (restricted to finalized GEX cells)")
    # FRiP into atac.obs so the QC figure is a self-describing view of the object.
    mp = L / "atac/atac_metrics.tsv"
    if mp.exists():
        m = pd.read_csv(mp, sep="\t")
        m["barcode"] = strip1(m["barcode"])
        m = m.set_index("barcode")
        if "atac_peak_fraction" in m.columns:
            atac.obs["atac_frip"] = m["atac_peak_fraction"].reindex(atac.obs_names).values

    print(">> loading guide calls (deposited placeholder) ...")
    g = pd.read_csv(D / args.guide_calls, sep="\t")
    g["barcode"] = strip1(g["barcode"])
    g = g.set_index("barcode")
    guide = ad.AnnData(X=sp.csr_matrix(g.values.astype("float32")))
    guide.obs_names = g.index.tolist()
    guide.var_names = list(g.columns)
    print(f"   guide: {guide.n_obs} cells x {guide.n_vars} guides")

    print(">> computing GEX UMAP (stored in rna.obsm['X_umap']) ...")
    gx = gex.copy()
    sc.pp.normalize_total(gx, target_sum=1e4)
    sc.pp.log1p(gx)
    sc.pp.highly_variable_genes(gx, n_top_genes=2000)
    gx = gx[:, gx.var.highly_variable].copy()
    sc.pp.scale(gx, max_value=10)
    sc.tl.pca(gx, n_comps=30)
    sc.pp.neighbors(gx, n_neighbors=15)
    sc.tl.umap(gx)
    gex.obsm["X_umap"] = gx.obsm["X_umap"]   # cells preserved through HVG subsetting

    h5mu = out / "catatac_dmso1_trimodal.h5mu"
    mdata = md.MuData({"rna": gex, "atac": atac, "guide": guide})
    mdata.uns["trimodal"] = {
        "dataset": "CAT-ATAC GSE288996 K562 DMSO rep1",
        "cell_basis": "EmptyDrops knee (is_simple_cell==1)",
        "guide_source": "deposited DMSO1 calls (placeholder for suite guide arm)",
    }
    mdata.write(str(h5mu))
    print(f">> wrote MuData: {h5mu}  ({mdata.n_obs} union cells)")

    if not args.skip_figure:
        gen = Path(__file__).resolve().parent / "generate_trimodal_qc.py"
        cmd = [sys.executable, str(gen), "--mudata", str(h5mu),
               "--output-prefix", str(out / "trimodal_qc"),
               "--title", "CAT-ATAC K562 DMSO rep1 — single-pass trimodal QC (finalized cells; cf. ARC 12,466)"]
        print(f">> rendering figure: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
