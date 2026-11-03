#!/usr/bin/env python3
"""Relative fp32 speed vs CAPPED-SOLVE FRACTION (not cell count).

The proposed mechanism is that the fp32/fp64 speed ratio is governed by how often the fp32
pressure solve fails to converge and burns the 1000-iteration cap, not by mesh size
as such. This tests that across a 16x range of mesh size.

TWO THINGS ARE KEPT EXPLICIT EVERYWHERE (table, figure, and printed output), not in
footnotes:
  1. The 262,144-cell point is NOT the same kind of measurement as the other two.
     There, fp32 never reaches the tolerance fp64 reaches -- it caps on ~85% of
     solves -- so it is a WORK comparison at a fixed tolerance target, not an
     accuracy-matched speed benchmark. It is reported in its own section.
  2. The repeat counts are asymmetric at 262k: fp64 n=2, fp32 n=1 (a second fp32
     repeat costs ~49 min and the effect is ~50x, far beyond any plausible noise).
"""
import csv, os, re, statistics as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [x for x in csv.DictReader(open(os.path.join(HERE, "results_final.csv")))
        if x["valid"].startswith("yes")]
f = lambda x, k: float(x[k])

MATCHED = [("16,384", "m16k_"), ("65,536", "c_")]      # both precisions reach ptol
WORKONLY = [("262,144", "b262k_")]                      # fp32 never reaches ptol

def stats_for(pref):
    out = {}
    for prec in ("fp64ctl", "fp32"):
        g = [x for x in rows if x["label"].startswith(pref) and x["precision"] == prec]
        if not g: continue
        sps, caps, tots = [], [], []
        for x in g:
            sps.append(f(x, "exec_s") / f(x, "steps_done"))
            log = os.path.join(HERE, "cases", x["label"], "log.icoFoam")
            if os.path.exists(log):
                it = [int(m.group(1)) for m in re.finditer(
                    r"Solving for p.*?No Iterations (\d+)",
                    open(log, errors="replace").read())]
                if it:
                    caps.append(sum(1 for i in it if i >= 1000)); tots.append(len(it))
        out[prec] = dict(n=len(g), sps=st.median(sps),
                         cap=(sum(caps)/sum(tots) if tots else float("nan")))
    return out

def line(label, s):
    a, b = s.get("fp64ctl"), s.get("fp32")
    if not a or not b: return None
    return dict(label=label, ratio=b["sps"]/a["sps"], cap=b["cap"],
                n64=a["n"], n32=b["n"], sp64=a["sps"], sp32=b["sps"])

print("=" * 92)
print("fp32 slowdown vs capped-solve fraction (icoFoam/GAMG, ptol 1e-4)")
print("=" * 92)
print("\n--- A. ACCURACY-MATCHED points (both precisions reach ptol 1e-4) ---")
print(f"{'mesh':>9}{'n fp64':>8}{'n fp32':>8}{'fp64 s/step':>13}{'fp32 s/step':>13}"
      f"{'fp32/fp64':>11}{'fp32 capped':>13}")
pts = []
for label, pref in MATCHED:
    r = line(label, stats_for(pref))
    if r:
        pts.append((r, True))
        print(f"{r['label']:>9}{r['n64']:>8}{r['n32']:>8}{r['sp64']:>13.4f}"
              f"{r['sp32']:>13.4f}{r['ratio']:>10.2f}x{r['cap']*100:>12.2f}%")

print("\n--- B. WORK COMPARISON ONLY — NOT accuracy-matched, NOT comparable to A ---")
print("    At this size fp32 NEVER reaches ptol 1e-4: it caps on most solves and")
print("    returns a residual ~1.4e-4. fp64 reaches the tolerance normally.")
print("    This measures work done at a fixed tolerance TARGET, not equal-accuracy speed.")
print(f"{'mesh':>9}{'n fp64':>8}{'n fp32':>8}{'fp64 s/step':>13}{'fp32 s/step':>13}"
      f"{'fp32/fp64':>11}{'fp32 capped':>13}")
for label, pref in WORKONLY:
    r = line(label, stats_for(pref))
    if r:
        pts.append((r, False))
        print(f"{r['label']:>9}{r['n64']:>8}{r['n32']:>8}{r['sp64']:>13.4f}"
              f"{r['sp32']:>13.4f}{r['ratio']:>10.2f}x{r['cap']*100:>12.2f}%")
        if r['n64'] != r['n32']:
            print(f"    ** ASYMMETRIC REPEATS: fp64 n={r['n64']}, fp32 n={r['n32']} "
                  f"(a 2nd fp32 repeat costs ~49 min; effect is ~{r['ratio']:.0f}x) **")

# ---------------- figure ----------------
if len(pts) >= 2:
    fig, ax = plt.subplots(figsize=(8.0, 5.4))
    for r, matched in pts:
        x = max(r["cap"], 3e-4)
        col = "#1f4e79" if matched else "#c0392b"
        ax.plot(x, r["ratio"], "o" if matched else "s", color=col, ms=13,
                markerfacecolor=col if matched else "none", markeredgewidth=2.5, zorder=3)
        tag = f"{r['label']} cells\nfp64 n={r['n64']}, fp32 n={r['n32']}"
        if not matched:
            tag += "\nWORK COMPARISON ONLY\n(fp32 never reaches ptol)"
        ax.annotate(tag, (x, r["ratio"]), textcoords="offset points",
                    xytext=(12, 6 if matched else -40), fontsize=8.5,
                    color=col, fontweight="bold" if not matched else "normal")
    ax.axhline(1.0, color="k", ls="--", lw=1.3)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("fraction of fp32 pressure solves hitting the 1000-iteration cap")
    ax.set_ylabel("fp32 time / fp64 time  (per timestep)")
    ax.set_title("fp32 slowdown tracks capped-solve fraction, not mesh size", fontsize=12)
    ax.grid(alpha=.3, which="both")
    ax.plot([], [], "o", color="#1f4e79", ms=10,
            label="accuracy-matched: both precisions reach ptol 1e-4")
    ax.plot([], [], "s", color="#c0392b", ms=10, markerfacecolor="none", markeredgewidth=2.5,
            label="WORK comparison only: fp32 never reaches ptol")
    ax.legend(fontsize=8.5, loc="upper left")
    ax.set_ylim(0.7, 400)
    fig.tight_layout(rect=[0, 0.11, 1, 1])
    fig.text(0.5, 0.045,
             "Repeat counts differ and are shown per point. Leftmost point plotted at 3e-4 "
             "for the log axis; its true capped fraction is 0.\n"
             "The red point is a WORK comparison at a fixed tolerance target, NOT a "
             "like-for-like speed benchmark — fp32 never reaches ptol there.",
             fontsize=7.6, ha="center", va="bottom", style="italic")
    fig.savefig(os.path.join(HERE, "capped_fraction.png"), dpi=140)
    print("\nwrote capped_fraction.png")
