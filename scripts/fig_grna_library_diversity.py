#!/usr/bin/env python3
"""Supplementary figure: gRNA-capture library diversity is a common problem, and a per-guide
noise-floor FDR overcomes it. Built from a suite single-pass run's own outputs (GMM root +
crispr_analysis/ambient_fdr/).

Four panels:
  A. per-guide ambient contamination spans orders of magnitude (the library is uneven)
  B. one FDR adapts the per-guide UMI threshold to each guide's floor (a fixed cutoff cannot)
  C. the library is shallow; the cells the FDR recovers are the low-UMI cells a fixed cutoff drops
  D. outcome: real low-UMI cells recovered without re-sequencing

Frames the approach as a reaction to a common condition (shallow / uneven gRNA capture), not a
better caller. The ideal fix is a deeper, better-targeted gRNA library; this is the salvage when
that isn't an option. No claim about any published analysis is made or needed.
"""
import argparse

import numpy as np
import pandas as pd
import scipy.io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="gRNA library-diversity supplementary figure.")
    p.add_argument("--run-dir", default="/mnt/pikachu/catatac_gse288996/full_bench/"
                   "catatac_trimodal_full_ambientfdr_20260614T123323Z/star_run",
                   help="STAR single-pass run dir (outs/, Solo.out/, cr_assign/)")
    p.add_argument("--out-prefix", default="/mnt/pikachu/chromap_suite_paper/figures/supp_grna_library_diversity",
                   help="Output prefix; writes <prefix>.png and <prefix>.pdf")
    p.add_argument("--alpha", type=float, default=0.01, help="FDR alpha for the effective-threshold panel")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    R = args.run_dir
    AF = f"{R}/outs/crispr_analysis/ambient_fdr"
    gd_hits = sorted(__import__("glob").glob(f"{R}/cr_assign/CRISPR_Guide_Capture/*/sample"))
    GD = gd_hits[0]
    OUT = args.out_prefix
    ALPHA = args.alpha
    s1 = lambda s: [b[:-2] if str(b).endswith("-1") else str(b) for b in s]
    canon = lambda g: str(g).replace("-", "_")

    # per-guide ambient rates
    ar = pd.read_csv(f"{AF}/guide_ambient_rates.tsv", sep="\t")
    ar["g"] = [canon(x) for x in ar["feature_id"].astype(str)]
    rate = dict(zip(ar["g"], ar["ambient_rate"].astype(float)))

    # knee + cells x guides q-values and counts
    ed = pd.read_csv(f"{R}/Solo.out/GeneFull/filtered/EmptyDrops/EmptyDrops/emptydrops_results.tsv", sep="\t")
    cells = s1(ed.loc[ed.is_simple_cell == 1, "barcode"].astype(str))
    qco = scipy.io.mmread(f"{AF}/guide_qvalues.mtx").tocoo()
    qbc = s1(pd.read_csv(f"{AF}/guide_qvalues_barcodes.tsv", header=None, sep="\t")[0])
    qgn = [canon(x) for x in pd.read_csv(f"{AF}/guide_qvalues_features.tsv", header=None, sep="\t")[0].astype(str)]
    qd = np.ones((len(qbc), len(qgn)), "float32"); qd[qco.row, qco.col] = qco.data
    qidx = {b: i for i, b in enumerate(qbc)}
    Mc = scipy.io.mmread(f"{GD}/matrix.mtx").tocsr(); Md = Mc.toarray()
    mbc = s1(pd.read_csv(f"{GD}/barcodes.tsv", header=None, sep="\t")[0])
    mgn = [canon(x) for x in pd.read_csv(f"{GD}/features.tsv", header=None, sep="\t")[0].astype(str)]
    mci = {b: i for i, b in enumerate(mbc)}; mgi = {g: i for i, g in enumerate(mgn)}
    col = np.array([mci.get(b, -1) for b in cells]); rowm = np.array([mgi.get(g, -1) for g in qgn])
    qr = np.array([qidx.get(b, -1) for b in cells])
    Q = np.ones((len(cells), len(qgn)), "float32"); vq = qr >= 0; Q[vq] = qd[qr[vq]]
    C = np.zeros((len(cells), len(qgn)), "float32"); vc = col >= 0
    rr = np.where(rowm < 0, 0, rowm); sub = Md[np.ix_(rr, col[vc])]; sub[rowm < 0, :] = 0; C[vc, :] = sub.T

    rows = []
    for j, g in enumerate(qgn):
        m = Q[:, j] <= ALPHA
        if m.sum():
            rows.append((g, rate.get(g, np.nan), int(C[m, j].min()), int(m.sum())))
    pg = pd.DataFrame(rows, columns=["guide", "ambient_rate", "eff_thr", "n_cells"])

    af = pd.read_csv(f"{AF}/guide_fdr_calls_per_cell.csv"); af["bc"] = s1(af.cell_barcode.astype(str)); af = af.set_index("bc")
    af_called = set(af.index[af.call_status.isin(["singlet", "multiplet"])])
    g = pd.read_csv(f"{R}/outs/crispr_analysis/protospacer_calls_per_cell.csv"); g["bc"] = s1(g.cell_barcode.astype(str)); g = g.set_index("bc")
    gmm_called = set(g.index[g.feature_call.notna() & (g.feature_call.astype(str) != "None")])
    knee = set(cells)
    umis = af["num_umis"].reindex(cells).fillna(0).astype(float)
    grp = pd.Series("no-call", index=cells)
    grp[[c for c in cells if c in (af_called & gmm_called)]] = "both"
    grp[[c for c in cells if c in (af_called - gmm_called)]] = "rescued"
    n_gmm, n_af, n_knee = len(gmm_called & knee), len(af_called), len(knee)
    n_resc = len(af_called - gmm_called)

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5, "axes.titleweight": "bold"})
    fig, ax = plt.subplots(2, 2, figsize=(11, 8.2))
    C_BOTH, C_RESC = "#2c7fb8", "#d95f0e"

    a = ax[0, 0]
    r = pg.sort_values("ambient_rate")["ambient_rate"].values.copy()
    floor = r[r > 0].min() / 3.0
    r[r <= 0] = floor
    a.bar(np.arange(len(r)), r, color="#41719c", width=0.9)
    a.set_yscale("log"); a.set_xlabel("guides, ranked by ambient rate (n=%d)" % len(r)); a.set_ylabel("ambient rate (UMI fraction in empties)")
    a.set_title("A  gRNA libraries are uneven:\nper-guide ambient contamination spans ~%.0f×" % (pg.ambient_rate[pg.ambient_rate > 0].max() / pg.ambient_rate[pg.ambient_rate > 0].min()))
    hi = pg.nlargest(1, "ambient_rate").iloc[0]
    a.annotate(f"dirtiest {hi.guide}", (len(r) - 1, hi.ambient_rate), xytext=(len(r) * 0.42, hi.ambient_rate * 0.7), fontsize=7.5, color="#b30000")

    b = ax[0, 1]
    x = pg.ambient_rate.values.copy(); x[x <= 0] = floor
    sc = b.scatter(x, pg.eff_thr, s=8 + pg.n_cells / 8, c=pg.eff_thr, cmap="viridis", edgecolor="k", linewidth=0.3, zorder=3)
    b.set_xscale("log"); b.set_xlabel("per-guide ambient rate"); b.set_ylabel("UMIs needed to be called @ %g%% FDR" % (ALPHA * 100))
    b.axhline(3, ls="--", c="#888", lw=1); b.text(b.get_xlim()[0], 3.12, " fixed UMI≥3 (CR default)", fontsize=7, color="#555")
    b.axhline(10, ls="--", c="#888", lw=1); b.text(b.get_xlim()[0], 10.15, " fixed UMI≥10 (CR A375 parity)", fontsize=7, color="#555")
    b.set_ylim(0, 12)
    b.set_title("B  One FDR adapts the per-guide threshold (%d→%d UMIs)\nto each guide's floor — a fixed cutoff cannot" % (pg.eff_thr.min(), pg.eff_thr.max()))
    plt.colorbar(sc, ax=b, label="eff. UMI threshold", fraction=0.046, pad=0.04)

    c = ax[1, 0]
    bins = np.logspace(0, np.log10(max(umis.max(), 10)), 40)
    for col_, color, lbl in [("both", C_BOTH, "called by both"), ("rescued", C_RESC, "rescued by FDR cutoff")]:
        v = umis[grp == col_]; v = v[v > 0]
        c.hist(v, bins=bins, alpha=0.75, label=lbl, color=color)
    c.set_xscale("log"); c.set_xlabel("guide UMIs per cell (cells with >0 shown)"); c.set_ylabel("cells")
    med_all = umis.median(); zero_pct = (umis == 0).mean() * 100
    c.axvline(max(med_all, 1), ls=":", c="k"); c.text(max(med_all, 1) * 1.06, c.get_ylim()[1] * 0.85, f"overall median {med_all:.0f} UMIs", fontsize=7.5)
    c.set_title("C  Shallow library (median %.0f UMIs/cell overall; %.0f%% have 0).\nRescued cells are the low-UMI cells a fixed cutoff drops" % (med_all, zero_pct))
    c.legend(fontsize=8, loc="upper right")

    d = ax[1, 1]
    labels = ["knee cells\n(finalized)", "GMM default\n(validated)", "FDR cutoff\n@ %g%%" % (ALPHA * 100)]
    d.bar(0, n_knee, color="#cccccc")
    d.bar(1, n_gmm, color=C_BOTH)
    d.bar(2, n_gmm, color=C_BOTH, label="also called by GMM")
    d.bar(2, n_resc, bottom=n_gmm, color=C_RESC, label="rescued (low-UMI)")
    d.set_xticks([0, 1, 2]); d.set_xticklabels(labels)
    for i, v in [(0, n_knee), (1, n_gmm), (2, n_af)]:
        d.text(i, v + 180, f"{v:,}", ha="center", fontsize=8.5, fontweight="bold")
    d.text(2, n_gmm + n_resc / 2, f"+{n_resc:,}", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    d.set_ylabel("cells"); d.legend(fontsize=7.5, loc="upper right")
    d.set_title("D  Outcome: +%d real low-UMI cells recovered\nfrom the same data (no re-sequencing)" % n_resc)
    d.set_ylim(0, n_knee * 1.12)

    fig.suptitle("Shallow / uneven gRNA capture is a common problem — a per-guide noise-floor FDR overcomes it",
                 fontsize=11.5, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(f"{OUT}.png", dpi=200)
    fig.savefig(f"{OUT}.pdf")
    print(f">> wrote {OUT}.png and {OUT}.pdf")
    print(f"   per-guide ambient {pg.ambient_rate[pg.ambient_rate>0].min():.5f}..{pg.ambient_rate.max():.5f}; "
          f"eff thr {pg.eff_thr.min()}..{pg.eff_thr.max()} UMIs; cells/guide {pg.n_cells.min()}..{pg.n_cells.max()}")
    print(f"   knee {n_knee}  GMM {n_gmm}  FDR {n_af}  rescued {n_resc}  median {med_all:.0f}  zero {zero_pct:.0f}%")


if __name__ == "__main__":
    main()
