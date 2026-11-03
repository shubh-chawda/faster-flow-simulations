#!/usr/bin/env python3
"""Scaling study plots: PCG (naive) vs GAMG (multigrid).
Reads results.csv, fits power laws, plots solve-time/step and iterations/step
versus number of cells, and extrapolates PCG to the 2M-cell target."""
import csv, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = {"pcg": {"n": [], "t": [], "it": []}, "gamg": {"n": [], "t": [], "it": []}}
with open("results.csv") as f:
    for r in csv.DictReader(f):
        s = r["solver"]
        d[s]["n"].append(float(r["ncells"]))
        d[s]["t"].append(float(r["time_per_step_s"]))
        d[s]["it"].append(float(r["piters_per_step"]))
for s in d:
    for k in d[s]:
        d[s][k] = np.array(d[s][k])

def slope(n, y):                      # power-law exponent (log-log LS fit)
    a, _ = np.polyfit(np.log(n), np.log(y), 1)
    return a

sp = slope(d["pcg"]["n"], d["pcg"]["t"])
sg = slope(d["gamg"]["n"], d["gamg"]["t"])
print(f"PCG  time ~ n^{sp:.2f}   GAMG time ~ n^{sg:.2f}")

RED, BLUE, GREY = "#c0392b", "#2e6da4", "#888888"
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))

# ---- panel 1: solve time per step ----
ax1.loglog(d["pcg"]["n"], d["pcg"]["t"], "o-", color=RED, lw=2, ms=6,
           label=f"PCG (naive)   ~ n$^{{{sp:.2f}}}$")
ax1.loglog(d["gamg"]["n"], d["gamg"]["t"], "s-", color=BLUE, lw=2, ms=6,
           label=f"GAMG (multigrid) ~ n$^{{{sg:.2f}}}$")
# extrapolate PCG power-law to 2M
c = d["pcg"]["t"][0] / d["pcg"]["n"][0]**sp
xext = np.array([d["pcg"]["n"][-1], 2.0e6])
ax1.loglog(xext, c*xext**sp, "--", color=RED, lw=1.5, alpha=.7)
ax1.loglog([2.0e6], [c*(2.0e6)**sp], "*", color=RED, ms=15,
           label=f"PCG @ 2M (projected \u2248 {c*(2.0e6)**sp:.0f} s/step)")
ax1.axvline(2.0e6, color=GREY, ls=":", lw=1)
ax1.text(2.0e6, ax1.get_ylim()[0]*1.5, " 2M target", color=GREY, fontsize=8, rotation=90, va="bottom")
ax1.set_xlabel("number of cells"); ax1.set_ylabel("wall time per timestep  [s]")
ax1.set_title("Solve time scaling"); ax1.grid(True, which="both", alpha=.25)
ax1.legend(fontsize=8, loc="upper left")

# ---- panel 2: pressure iterations per step ----
ax2.semilogx(d["pcg"]["n"], d["pcg"]["it"], "o-", color=RED, lw=2, ms=6, label="PCG (naive)")
ax2.semilogx(d["gamg"]["n"], d["gamg"]["it"], "s-", color=BLUE, lw=2, ms=6, label="GAMG (multigrid)")
ax2.axvline(2.0e6, color=GREY, ls=":", lw=1)
ax2.set_xlabel("number of cells"); ax2.set_ylabel("pressure solver iterations per timestep")
ax2.set_title("Iterations to converge"); ax2.grid(True, which="both", alpha=.25)
ax2.legend(fontsize=9, loc="upper left")
ax2.annotate("PCG iterations grow with mesh\n(work per solve \u2191)",
             xy=(d["pcg"]["n"][-1], d["pcg"]["it"][-1]), xytext=(2e4, 1500),
             fontsize=8, color=RED, arrowprops=dict(arrowstyle="->", color=RED))
ax2.annotate("GAMG ~ mesh-independent",
             xy=(d["gamg"]["n"][-1], d["gamg"]["it"][-1]), xytext=(3e4, 300),
             fontsize=8, color=BLUE, arrowprops=dict(arrowstyle="->", color=BLUE))

fig.suptitle("Pressure-solve scaling: naive CG vs multigrid (2D channel, icoFoam)",
             fontsize=12, y=1.02)
fig.tight_layout()
fig.savefig("scaling.png", dpi=130, bbox_inches="tight")
print("wrote scaling.png")

# ---- console summary table ----
print("\n cells      PCG t/step   GAMG t/step   speedup   PCG iters  GAMG iters")
alln = sorted(set(d["pcg"]["n"]).union(d["gamg"]["n"]))
for n in alln:
    def get(s, key):
        m = d[s]["n"] == n
        return d[s][key][m][0] if m.any() else None
    pt, gt = get("pcg","t"), get("gamg","t")
    pi, gi = get("pcg","it"), get("gamg","it")
    sp_ = f"{pt/gt:5.1f}x" if (pt and gt) else "   -  "
    print(f"{int(n):>8}   {('%.3f'%pt) if pt else '   -':>9}   {('%.3f'%gt) if gt else '   -':>9}   "
          f"{sp_:>7}   {('%.0f'%pi) if pi else '  -':>8}   {('%.0f'%gi) if gi else '  -':>8}")
