#!/usr/bin/env python3
"""One-stop guide QC: an interactive GEX UMAP whose perturbation calls are driven by a single
FDR slider (the ambient-noise-floor cutoff). The embedding is the GEX manifold (cutoff-independent
— computed once); only the colouring changes with the FDR, so the q-values are computed once and
each slider step is a threshold. The live readout shows the chosen q-value and the cells retained.

This is the practitioner-facing answer to "where do I set the cutoff": drag the slider, watch the
calls and retention update, and the same q-value is what `guide.layers['qvalue'] <= alpha` filters
on in the MuData. (The published CAT-ATAC calls use an undocumented, unshared Stan cutoff; this is
the transparent, reproducible alternative.)

Usage:
  guide_fdr_umap.py --h5mu sample.h5mu --guide-mex <count_mex_dir> \
     --emptydrops <emptydrops_results.tsv> --output-prefix out/guide_fdr_umap
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import mudata as md
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_ambient_fdr import load_guide_mex, ambient_fdr_qvalues, per_cell_genes, strip1


def parse_args():
    p = argparse.ArgumentParser(description="Interactive FDR-slider guide-call UMAP (ambient noise-floor cutoff).")
    p.add_argument("--h5mu", required=True, help="MuData with rna.obsm['X_umap'] on the cell set")
    p.add_argument("--guide-mex", required=True, help="guide UMI count MEX dir (guides x ALL barcodes)")
    p.add_argument("--emptydrops", required=True, help="EmptyDrops results.tsv (is_simple_cell = cell knee)")
    p.add_argument("--fdrs", default="0.0001,0.0005,0.001,0.005,0.01,0.02,0.05", help="slider FDR steps")
    p.add_argument("--rna-mod", default="rna")
    p.add_argument("--top-genes", type=int, default=10)
    p.add_argument("--output-prefix", required=True)
    p.add_argument("--no-png", action="store_true")
    return p.parse_args()


def assigned(genes_list, cells):
    return {b: (g[0] if len(g) == 1 else ("multiplet" if len(g) > 1 else "none"))
            for b, g in zip(cells, genes_list)}


def main():
    a = parse_args()
    fdrs = [float(x) for x in a.fdrs.split(",")]
    m = md.read(a.h5mu)
    rna = m.mod[a.rna_mod]
    cells = list(rna.obs_names)
    um = pd.DataFrame(rna.obsm["X_umap"][:, :2], index=rna.obs_names, columns=["u1", "u2"])
    M, gn, bc = load_guide_mex(a.guide_mex)
    q, _, _ = ambient_fdr_qvalues(M, gn, bc, cells)            # cell x guide, ONCE

    asg, summ = {}, {}
    for fdr in fdrs:
        gl = per_cell_genes(q, gn, fdr)
        asg[fdr] = assigned(gl, cells)
        n = int((q <= fdr).any(1).sum()); ncalls = sum(len(g) for g in gl); cut = "—"
        summ[fdr] = (n, ncalls)
        print(f">> FDR={fdr:<7} cells retained={n:<6} guide calls={ncalls}")

    loosest = max(fdrs)
    top = pd.Series([g for g in asg[loosest].values() if g not in ("none", "multiplet")]).value_counts().head(a.top_genes).index.tolist()
    cats = top + ["multiplet"]
    pal = dict(zip(cats, ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#17becf","#bcbd22","#7f7f7f","#111111"]))

    fig = go.Figure(); default = len(fdrs) // 2
    for g in ["unassigned"] + cats:                            # stable legend = dummy traces
        fig.add_trace(go.Scattergl(x=[None], y=[None], mode="markers", name=g, legendgroup=g,
            marker=dict(size=7, color=("#cccccc" if g == "unassigned" else pal[g])), visible=True, showlegend=True))
    n_dummy = len(cats) + 1; per_step = len(cats) + 1
    for i, fdr in enumerate(fdrs):
        sub = um.copy(); sub["g"] = [asg[fdr][b] for b in sub.index]; vis = (i == default)
        bg = sub[~sub.g.isin(cats)]
        fig.add_trace(go.Scattergl(x=bg.u1, y=bg.u2, mode="markers", marker=dict(size=2, color="#e8e8e8"),
            visible=vis, showlegend=False, legendgroup="unassigned"))
        for g in cats:
            s = sub[sub.g == g]
            fig.add_trace(go.Scattergl(x=s.u1, y=s.u2, mode="markers", marker=dict(size=3, color=pal[g]),
                visible=vis, showlegend=False, legendgroup=g))

    ncells_total = um.shape[0]
    def readout(fdr):
        n, nc = summ[fdr]
        return (f"<b>q ≤ {fdr:g}</b>  (ambient-FDR)<br>"
                f"<b>{n:,}</b> / {ncells_total:,} cells retained ({100*n/ncells_total:.0f}%)<br>"
                f"{nc:,} guide calls")
    steps = []
    for i, fdr in enumerate(fdrs):
        v = [True]*n_dummy + [False]*(len(fdrs)*per_step)
        for k in range(per_step): v[n_dummy + i*per_step + k] = True
        steps.append(dict(method="update", label=f"{fdr:g}", args=[{"visible": v}, {"annotations[0].text": readout(fdr)}]))
    fig.update_layout(height=700, width=860, template="plotly_white", legend=dict(itemsizing="constant"),
        xaxis_title="UMAP-1", yaxis_title="UMAP-2",
        title="Guide perturbation calls on the GEX UMAP — drag the FDR slider",
        annotations=[dict(x=0.015, y=0.985, xref="paper", yref="paper", xanchor="left", yanchor="top",
            align="left", showarrow=False, bordercolor="#888", borderwidth=1, borderpad=8,
            bgcolor="rgba(255,255,255,0.88)", font=dict(size=13), text=readout(fdrs[default]))],
        sliders=[dict(active=default, currentvalue={"prefix": "q ≤ ", "font": {"size": 15}}, pad={"t": 55}, steps=steps)])

    out = Path(a.output_prefix); out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(f"{out}.html", include_plotlyjs="cdn")
    Path(f"{out}.json").write_text(fig.to_json())
    if not a.no_png:
        fig.write_image(f"{out}.png", scale=2)
    print(f">> wrote {out}.{{html,json,png}}")


if __name__ == "__main__":
    main()
