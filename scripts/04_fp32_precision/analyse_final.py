#!/usr/bin/env python3
"""Summarise the final fp32/fp64 comparison from results_final.csv.

Reports median and spread (min-max) per precision, refuses to quote a speed-up
the timing spread cannot support, and flags any run that failed the mandatory
Ux/Uy validity check.
"""
import csv, os, statistics as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "results_final.csv"))))
f = lambda x, k: float(x[k]) if x.get(k) not in (None, "", "nan") else float("nan")

def group(pred):
    return [x for x in rows if pred(x)]

def stats(vals):
    vals = [v for v in vals if v == v]
    if not vals: return None
    return dict(median=st.median(vals), lo=min(vals), hi=max(vals), n=len(vals))

def fmt(s, unit=""):
    if not s: return "n/a"
    spread = (s["hi"] - s["lo"]) / s["median"] * 100 if s["median"] else 0
    return f"{s['median']:.2f}{unit} (range {s['lo']:.2f}–{s['hi']:.2f}, ±{spread/2:.1f}%, n={s['n']})"

print("=" * 78)
print("VALIDITY CHECK — any 'NO' invalidates that run's results")
print("=" * 78)
bad = [x for x in rows if not x["valid"].startswith("yes")]
for x in rows:
    print(f"  {x['label']:14} {x['precision']:5} steps={x['steps_done']:>5} "
          f"Ux={x['ux_lines']:>5} Uy={x['uy_lines']:>5}  -> {x['valid']}")
print(f"\n  {len(rows)-len(bad)}/{len(rows)} runs valid" +
      ("" if not bad else f"  ** {len(bad)} INVALID — excluded from results **"))

valid = [x for x in rows if x["valid"].startswith("yes")]

GROUPS = [("GAMG  [BUILD-CONTROLLED: fp32 vs same-tree/compiler/flags fp64]", "c_",
           ("fp64ctl", "fp32")),
          ("GAMG  [fp32 vs shipped CI fp64 build]", "t_", ("fp64", "fp32")),
          ("PCG", "pcg_", ("fp64", "fp32"))]

for title, pref, precs in GROUPS:
    tim = [x for x in valid if x["label"].startswith(pref)]
    if not tim: continue
    print("\n" + "=" * 78)
    print(f"TIMING & MEMORY — {title}")
    print(f"  {tim[0]['cells']} cells, ptol {tim[0]['ptol']}, {tim[0]['steps_done']} steps")
    print("=" * 78)
    res = {}
    for p in precs:
        g = [x for x in tim if x["precision"] == p]
        if not g: continue
        res[p] = dict(exec=stats([f(x, "exec_s") for x in g]),
                      wall=stats([f(x, "wall_s") for x in g]),
                      rss=stats([f(x, "peak_rss_MiB") for x in g]),
                      it=stats([f(x, "p_iters_median") for x in g]),
                      rp=stats([f(x, "p_finalres_median") for x in g]))
        print(f"  {p}: exec {fmt(res[p]['exec'],'s')}")
        print(f"        peak RSS {fmt(res[p]['rss'],' MiB')}")
        print(f"        p-iters median {res[p]['it']['median']:.0f}, "
              f"p final-residual median {res[p]['rp']['median']:.2e}")
    base = precs[0]
    if base in res and "fp32" in res:
        a, b = res[base]["exec"], res["fp32"]["exec"]
        speed = (a["median"] - b["median"]) / a["median"] * 100
        # spread test: is the effect larger than the observed noise?
        noise = max((a["hi"]-a["lo"])/a["median"], (b["hi"]-b["lo"])/b["median"]) * 100
        verdict = (f"fp32 {abs(speed):.1f}% {'FASTER' if speed>0 else 'SLOWER'}"
                   if abs(speed) > noise else
                   f"NO MEASURABLE DIFFERENCE (effect {speed:+.1f}% < noise {noise:.1f}%)")
        m64, m32 = res[base]["rss"], res["fp32"]["rss"]
        mem = (m64["median"] - m32["median"]) / m64["median"] * 100
        print(f"\n  SPEED : {verdict}   [effect {speed:+.1f}%, timing spread {noise:.1f}%]")
        memnoise = max((m64["hi"]-m64["lo"])/m64["median"], (m32["hi"]-m32["lo"])/m32["median"]) * 100
        memverdict = (f"fp32 uses {abs(mem):.1f}% {'LESS' if mem>0 else 'MORE'} memory"
                      if abs(mem) > memnoise else
                      f"NO MEASURABLE DIFFERENCE (effect {mem:+.1f}% < spread {memnoise:.1f}%)")
        print(f"  MEMORY: {memverdict} "
              f"({m32['median']:.1f} vs {m64['median']:.1f} MiB, spread {memnoise:.1f}%)")

acc = [x for x in valid if x["label"].startswith("acc_")]
if acc:
    print("\n" + "=" * 78)
    print("ACCURACY at steady state (analytical: U_peak=1.5, tau_w=0.06)")
    print("=" * 78)
    print(f"  {'prec':6}{'U_peak':>11}{'U_centre':>11}{'errMax%':>10}{'errL2%':>10}"
          f"{'tau_w':>10}{'Co_max':>9}{'cont_cum':>11}")
    for x in sorted(acc, key=lambda r: r["precision"], reverse=True):
        print(f"  {x['precision']:6}{f(x,'U_peak_outlet'):>11.6f}{f(x,'U_centre_outlet'):>11.6f}"
              f"{f(x,'err_max_pct_Umax'):>10.4f}{f(x,'err_L2_pct_Umax'):>10.4f}"
              f"{f(x,'tau_w_over_rho'):>10.6f}{f(x,'Co_max'):>9.4f}"
              f"{f(x,'cont_err_cumulative'):>11.2e}")
    if len(acc) == 2:
        a = {x["precision"]: x for x in acc}
        d = abs(f(a["fp64"], "U_peak_outlet") - f(a["fp32"], "U_peak_outlet"))
        print(f"\n  |U_peak(fp32) - U_peak(fp64)| = {d:.2e} m/s")

# ---------------- plot ----------------
if valid:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    ST = {"fp64": "#1f4e79", "fp64ctl": "#1f4e79", "fp32": "#c0392b"}
    tim = [x for x in valid if x["psolver"] == "GAMG" and x["label"].startswith("c_")]
    # panels 1-2: BOTH meshes, since the speed result changes sign with mesh size
    groups = [("16,384", "m16k_"), ("65,536", "c_")]
    import numpy as _np
    for ax, key, lab, unit in [(axes[0], "exec_s", "solver time", "s"),
                               (axes[1], "peak_rss_MiB", "peak memory", "MiB")]:
        xs = _np.arange(len(groups)); w = 0.36
        for k, (prec, disp) in enumerate((("fp64ctl", "fp64"), ("fp32", "fp32"))):
            meds, errs = [], [[], []]
            for _, pref in groups:
                g = [f(x, key) for x in valid
                     if x["label"].startswith(pref) and x["precision"] == prec]
                m = st.median(g) if g else 0
                meds.append(m)
                errs[0].append(m - min(g) if g else 0); errs[1].append(max(g) - m if g else 0)
            b = ax.bar(xs + (k - 0.5) * w, meds, w, color=ST[prec], label=disp)
            ax.errorbar(xs + (k - 0.5) * w, meds, yerr=errs, fmt="none", ecolor="k",
                        capsize=4, lw=1.1)
            for xi, m in zip(xs + (k - 0.5) * w, meds):
                ax.text(xi, m, f"{m:.1f}", ha="center", va="bottom", fontsize=8)
        ax.set_xticks(xs); ax.set_xticklabels([g[0] + " cells" for g in groups], fontsize=9)
        ax.set_title(f"{lab} ({unit}) — lower is better", fontsize=10)
        ax.set_ylabel(unit); ax.grid(alpha=.3, axis="y"); ax.legend(fontsize=8)
    ax = axes[2]
    # floors measured identically: ptol 1e-8 probes on binary-exact meshes
    fl = sorted((int(x["cells"]), f(x, "p_finalres_median"))
                for x in valid if x["label"].startswith("floor_") and x["precision"] == "fp32")
    cells = [c for c, _ in fl]; floor = [v for _, v in fl]
    if len(cells) > 1:
        import numpy as _np
        p, logc = _np.polyfit(_np.log(cells), _np.log(floor), 1)
        ax.loglog(cells, floor, "s-", color="#c0392b", ms=7,
                  label=f"fp32 floor (fit N^{p:.2f})")
        xs = _np.array([min(cells), max(cells)])
        ax.loglog(xs, _np.exp(logc) * xs**p, ":", color="#c0392b", lw=1, alpha=.7)
    f64 = [(int(x["cells"]), f(x, "p_finalres_median")) for x in valid
           if x["label"].startswith("floor_") and x["precision"] == "fp64ctl"]
    if f64:
        ax.loglog([c for c, _ in f64], [v for _, v in f64], "o", color="#1f4e79",
                  ms=9, label="fp64 control (no floor)")
    ax.set_xlabel("cells"); ax.set_ylabel("pressure residual floor")
    ax.set_title("fp32 convergence floor rises with mesh", fontsize=10)
    ax.grid(alpha=.3, which="both"); ax.legend(fontsize=8)
    fig.suptitle("Single vs double precision, icoFoam/GAMG, binary-exact meshes "
                 "(fp32 is faster at 16k, slower at 65k)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(HERE, "fp32_vs_fp64_final.png"), dpi=140)
    print("\nwrote fp32_vs_fp64_final.png")
