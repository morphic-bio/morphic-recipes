#!/usr/bin/env python3
"""Build the HIV-DOGMA four-ome MuData (GEX + ATAC-peak + protein/ADT + HIV-state) and
render the unified four-factor QC figure.

Dataset: HIV DOGMA-seq (GSE239916, sample YW8). All four arms are the suite's own
single-pass STAR four-arm outputs; every modality lives in GEX-barcode space (the run
used atac2gex translation for the ATAC arm, like the CAT-ATAC trimodal builder, so the
ATAC peak barcodes already intersect the GEX cell calls -- no re-translation here).

Four omes:
  rna     -- GeneFull filtered MEX (gene expression)
  atac    -- peak MEX (chromatin accessibility); FRiP from atac/atac_metrics.tsv
  protein -- ADT MEX (171 antibodies, incl. 9 IgG isotype controls)
  state   -- HIV viral-reservoir state (HIV_DNA / HIV_RNA), the identity arm

Cell basis: the *finalized* EmptyDrops call materialized at
  Solo.out/GeneFull/filtered/EmptyDrops/filtered_barcodes.txt
(the run's finalized knee + rescued passers, n_cells_passing == 9034; identical set to
GeneFull/filtered/barcodes.tsv). Same principle as the CAT-ATAC builder -- restrict every
arm to the finalized GEX cell call, but keep per-modality presence masks so the renderer
computes overlap/inclusion itself (we do NOT drop cells that lack the protein or state arm).

The HIV `state` arm is a per-cell viral-reservoir state, NOT a CRISPR guide. Most cells are
zero (the reservoir is biologically rare); only a few hundred carry nonzero HIV state. That
is expected -- a single HIV UMI marks a reservoir-positive cell (--min-identity-umis 1).

This is a dataset-specific reproducer (like build_catatac_trimodal_qc.py); paths default to
the local tree and are overridable so it can be re-run against a baseline-benchmark run dir.
The reusable pieces are build_multiome_mudata.py (object) and generate_four_factor_qc.py
(figure).
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


# Isotype-control ADTs in the YW8 panel: every antibody whose name contains "IgG".
ISOTYPE_TOKEN = "igg"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build HIV-DOGMA four-ome MuData + render the four-factor QC figure.")
    p.add_argument(
        "--run-dir",
        default="/mnt/pikachu/hiv_dogma_gse239916/star_four_arm_full/star_run_20260615_001327",
        help="Completed STAR four-arm run dir",
    )
    p.add_argument(
        "--out-dir",
        default="/mnt/pikachu/hiv_dogma_gse239916/qc_endpoint",
        help="Output dir for the .h5mu and QC figure",
    )
    p.add_argument("--min-identity-umis", type=int, default=1, help="Min HIV-state count to mark a reservoir+ cell")
    p.add_argument("--skip-figure", action="store_true", help="Write the .h5mu only; do not call generate_four_factor_qc.py")
    return p.parse_args()


def strip1(barcodes) -> list[str]:
    """Strip a trailing -1 suffix (idempotent -- safe on barcodes that lack it)."""
    return [b[:-2] if str(b).endswith("-1") else str(b) for b in barcodes]


def _open(path: Path):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path, "r", encoding="utf-8")


def _resolve(base: Path, stem: str) -> Path:
    plain, gz = base / stem, base / f"{stem}.gz"
    if plain.exists():
        return plain
    if gz.exists():
        return gz
    raise FileNotFoundError(f"Missing required file: {plain}(.gz)")


def load_mex(path: str, feat_col: int = 1) -> ad.AnnData:
    """Load a 10x-style MEX dir (.mtx or .mtx.gz). Returns cells x features AnnData with a
    `counts` layer; var carries feature ids (index), feature_names, and feature_types."""
    base = Path(path)
    M = scipy.io.mmread(_resolve(base, "matrix.mtx")).tocsr()  # features x cells
    bc_rows = [ln.strip().split("\t")[0] for ln in _open(_resolve(base, "barcodes.tsv")) if ln.strip()]
    ft = pd.read_csv(_resolve(base, "features.tsv"), header=None, sep="\t")
    X = M.T.tocsr()
    A = ad.AnnData(X=X)
    A.obs_names = strip1(bc_rows)
    A.var_names = ft[0].astype(str).tolist()  # feature ids
    name_col = feat_col if ft.shape[1] > feat_col else 0
    A.var["feature_names"] = ft[name_col].astype(str).tolist()
    A.var["feature_types"] = (ft[2].astype(str).tolist() if ft.shape[1] > 2 else [""] * ft.shape[0])
    A.var_names_make_unique()
    A.layers["counts"] = A.X.copy()
    return A


def restrict_and_mark(adata: ad.AnnData, cell_basis: list[str], modality: str) -> ad.AnnData:
    """Reindex `adata` onto the full GEX cell basis. Cells absent from this modality get an
    all-zero row; `<modality>_barcode_present` records true presence. We never drop cells."""
    present_set = set(adata.obs_names)
    basis = list(cell_basis)
    idx = pd.Index(adata.obs_names)
    indexer = idx.get_indexer(pd.Index(basis))
    have = indexer >= 0
    src = adata.X.tocsr()
    rows = np.zeros((len(basis), adata.n_vars), dtype=src.dtype)
    if have.any():
        rows[np.flatnonzero(have), :] = src[indexer[have], :].toarray()
    out = ad.AnnData(X=sp.csr_matrix(rows), var=adata.var.copy())
    out.obs_names = basis
    out.layers["counts"] = out.X.copy()
    out.obs[f"{modality}_barcode_present"] = [b in present_set for b in basis]
    return out


def add_library_metrics(adata: ad.AnnData, modality: str) -> None:
    """Per-cell library metrics the renderer reads (umis, features_detected, module_call,
    top_feature_fraction). Mirrors build_multiome_mudata.add_feature_library_metrics."""
    counts = adata.layers["counts"]
    umis = np.asarray(counts.sum(axis=1)).ravel()
    nnz = np.asarray((counts > 0).sum(axis=1)).ravel()
    adata.obs[f"{modality}_umis"] = umis
    adata.obs[f"{modality}_features_detected"] = nnz
    adata.obs[f"{modality}_module_call"] = umis > 0
    if adata.n_vars > 0:
        max_counts = np.asarray(counts.max(axis=1).toarray()).ravel()
        adata.obs[f"{modality}_top_feature_fraction"] = max_counts / np.maximum(umis, 1.0)
    else:
        adata.obs[f"{modality}_top_feature_fraction"] = np.zeros(adata.n_obs)


def main() -> None:
    args = parse_args()
    run = Path(args.run_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ---- cell basis: finalized EmptyDrops call (knee + rescued passers) ----------------
    fb_path = run / "Solo.out/GeneFull/filtered/EmptyDrops/filtered_barcodes.txt"
    cell_basis = strip1([ln.strip() for ln in open(fb_path) if ln.strip()])
    # de-dup while preserving order
    seen: set[str] = set()
    cell_basis = [b for b in cell_basis if not (b in seen or seen.add(b))]
    print(f">> cell basis: {len(cell_basis)} finalized EmptyDrops cells  ({fb_path})")

    # ---- RNA (GeneFull filtered MEX) ----------------------------------------------------
    print(">> loading RNA (GeneFull filtered MEX) ...")
    rna_full = load_mex(str(run / "Solo.out/GeneFull/filtered"))
    rna = restrict_and_mark(rna_full, cell_basis, "rna")
    # gene_symbols alias so the renderer's marker lookup (CD3D) resolves on either field.
    rna.var["gene_symbols"] = rna.var["feature_names"].values
    print(f"   RNA: {rna.n_obs} cells x {rna.n_vars} genes")

    # ---- ATAC (peak MEX); barcodes already in GEX space via atac2gex --------------------
    print(">> loading ATAC peak MEX ...")
    atac_full = load_mex(str(run / "atac/peak_mex"), feat_col=0)
    n_atac_overlap = len(set(atac_full.obs_names) & set(cell_basis))
    print(f"   ATAC raw: {atac_full.n_obs} barcodes; {n_atac_overlap}/{len(cell_basis)} in GEX cell basis")
    atac = restrict_and_mark(atac_full, cell_basis, "atac")
    atac.var["peak_ids"] = atac.var["feature_names"].values
    # FRiP into atac.obs so the figure is a self-describing view of the object.
    mp = run / "atac/atac_metrics.tsv"
    if mp.exists():
        m = pd.read_csv(mp, sep="\t")
        m["barcode"] = strip1(m["barcode"])
        m = m.drop_duplicates(subset=["barcode"]).set_index("barcode")
        if "atac_peak_fraction" in m.columns:
            atac.obs["atac_frip"] = m["atac_peak_fraction"].reindex(atac.obs_names).values
    print(f"   ATAC: {atac.n_obs} cells x {atac.n_vars} peaks")

    # ---- Protein / ADT ------------------------------------------------------------------
    print(">> loading protein/ADT MEX ...")
    prot_full = load_mex(str(run / "cr_assign/Protein/adt_yw8/adt"))
    protein = restrict_and_mark(prot_full, cell_basis, "protein")
    add_library_metrics(protein, "protein")
    # Isotype controls: every ADT whose name contains "IgG" (case-insensitive).
    names = protein.var["feature_names"].astype(str)
    is_isotype = names.str.lower().str.contains(ISOTYPE_TOKEN).values
    protein.var["is_isotype"] = is_isotype
    pc = protein.layers["counts"].tocsc()
    iso_total = np.asarray(pc[:, np.flatnonzero(is_isotype)].sum(axis=1)).ravel() if is_isotype.any() else np.zeros(protein.n_obs)
    spec_total = np.asarray(pc[:, np.flatnonzero(~is_isotype)].sum(axis=1)).ravel()
    protein.obs["isotype_total"] = iso_total
    protein.obs["specific_total"] = spec_total
    print(f"   protein: {protein.n_obs} cells x {protein.n_vars} ADTs; {int(is_isotype.sum())} isotype controls "
          f"({', '.join(names[is_isotype].tolist())})")

    # ---- HIV state (identity arm) -------------------------------------------------------
    print(">> loading HIV-state MEX (identity arm) ...")
    state_full = load_mex(str(run / "cr_assign/Custom/hiv_state_yw8"))
    state = restrict_and_mark(state_full, cell_basis, "state")
    add_library_metrics(state, "state")
    sc_counts = state.layers["counts"].toarray()
    state_pos = (sc_counts >= args.min_identity_umis).any(axis=1)
    state.obs["hiv_state_positive"] = state_pos
    feat = state.var["feature_names"].astype(str).tolist()
    for j, fname in enumerate(feat):
        state.obs[f"{fname}_count"] = sc_counts[:, j]
    print(f"   state: {state.n_obs} cells x {state.n_vars} features ({', '.join(feat)}); "
          f"{int(state_pos.sum())} HIV-state positive (>= {args.min_identity_umis} UMI)")

    # ---- RNA UMAP cached into rna.obsm['X_umap'] for the renderer to reuse ---------------
    print(">> computing RNA UMAP (stored in rna.obsm['X_umap']) ...")
    gx = rna.copy()
    sc.pp.normalize_total(gx, target_sum=1e4)
    sc.pp.log1p(gx)
    sc.pp.highly_variable_genes(gx, n_top_genes=2000)
    gx = gx[:, gx.var.highly_variable].copy()
    sc.pp.scale(gx, max_value=10)
    sc.tl.pca(gx, n_comps=30)
    sc.pp.neighbors(gx, n_neighbors=15)
    sc.tl.umap(gx)
    rna.obsm["X_umap"] = gx.obsm["X_umap"]  # cells preserved through HVG subsetting

    # ---- assemble + write ---------------------------------------------------------------
    h5mu = out / "hiv_dogma_yw8_fourome.h5mu"
    mdata = md.MuData({"rna": rna, "atac": atac, "protein": protein, "state": state})
    mdata.uns["fourome"] = {
        "dataset": "HIV DOGMA-seq GSE239916 sample YW8",
        "cell_basis": "finalized EmptyDrops call (filtered_barcodes.txt; knee + rescued passers)",
        "n_cells": len(cell_basis),
        "identity_modality": "state",
        "state_meaning": "HIV viral-reservoir state (HIV_DNA / HIV_RNA), not a CRISPR guide",
        "min_identity_umis": int(args.min_identity_umis),
        "n_hiv_state_positive": int(state_pos.sum()),
        "run_dir": str(run),
    }
    mdata.write(str(h5mu))
    print(f">> wrote MuData: {h5mu}  ({mdata.n_obs} cells x 4 modalities)")

    # ---- render the four-factor QC figure -----------------------------------------------
    if not args.skip_figure:
        gen = Path(__file__).resolve().parent / "generate_four_factor_qc.py"
        cmd = [
            sys.executable, str(gen),
            "--mudata", str(h5mu),
            "--output-prefix", str(out / "hiv_dogma_yw8_fourome_qc"),
            "--identity-mod", "state",
            "--protein-marker", "CD3D",
            "--rna-marker", "CD3D",
            "--min-identity-umis", str(args.min_identity_umis),
            "--atac-metrics", str(run / "atac/atac_metrics.tsv"),
            "--atac-metrics-barcode-column", "barcode",
            "--atac-metrics-frip-column", "atac_peak_fraction",
            "--title", "HIV DOGMA YW8 — single-pass four-ome QC (RNA + ATAC + protein + HIV state)",
        ]
        print(f">> rendering figure: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
