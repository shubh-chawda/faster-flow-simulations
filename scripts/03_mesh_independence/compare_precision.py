#!/usr/bin/env python3
"""fp64 vs fp32 comparison plot from results_precision.csv (pressure tol 1e-4).
Both precisions share an identical case/mesh/settings; only the icoFoam binary's
precision differs. fp32 stops at 128k because at 288k its pressure-solve floor
(~1.1e-4) exceeds the 1e-4 target and GAMG thrashes."""
import csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "results_precision.csv"))))
def series(prec, key):
    d = [(float(r["cells"]), float(r[key])) for r in rows if r["precision"] == prec]
    d.sort(); return [c for c, _ in d], [v for _, v in d]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))
ST = {"fp64": dict(color="#1f4e79", marker="o", ls="-"),
      "fp32": dict(color="#c0392b", marker="s", ls="--")}

# --- outlet centreline velocity ---
for p in ("fp64", "fp32"):
    c, u = series(p, "U_peak_outlet")
    ax1.plot(c, u, label=p, **ST[p], ms=7, lw=1.8)
ax1.axhline(1.5, ls=":", color="k", lw=1.2, label="analytical (1.5)")
ax1.set_xscale("log"); ax1.set_xlabel("number of cells")
ax1.set_ylabel("outlet centreline $U$  [m/s]")
ax1.set_title("Accuracy: fp32 tracks fp64, then diverges")
ax1.grid(alpha=.3, which="both"); ax1.legend(fontsize=8)
ax1.annotate("fp32 diverges here\n(ΔU≈3e-6, precision floor)", xy=(128000, 1.499607),
             xytext=(20000, 1.4991), fontsize=7.5,
             arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1))

# --- L2 error ---
for p in ("fp64", "fp32"):
    c, e = series(p, "err_L2_pct_Umax")
    ax2.plot(c, e, label=p, **ST[p], ms=7, lw=1.8)
ax2.set_xscale("log"); ax2.set_yscale("log")
ax2.set_xlabel("number of cells"); ax2.set_ylabel("L2 error  [% of $U_{max}$]")
ax2.set_title("fp32 error stops falling as mesh refines")
ax2.grid(alpha=.3, which="both"); ax2.legend(fontsize=8)
ax2.text(0.5, 0.06, "fp32 cannot run past 128k at this tol:\npressure-solve floor "
         "(~1.1e-4 at 288k) > target,\nGAMG thrashes (1000 iters/step)",
         transform=ax2.transAxes, fontsize=7, ha="center",
         bbox=dict(boxstyle="round", fc="#fdecea", ec="#c0392b", alpha=.8))

fig.suptitle("Single- vs double-precision icoFoam — 2D channel, identical mesh & settings (ptol 1e-4)",
             fontsize=10)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(os.path.join(HERE, "fp32_vs_fp64.png"), dpi=140)
print("wrote fp32_vs_fp64.png")
