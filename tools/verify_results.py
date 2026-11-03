#!/usr/bin/env python3
"""Recompute every headline number in the README from the committed data.

Each check recomputes one number from a CSV in results/ or a field in
data/fields/ and compares it with the value quoted in the README. If any check
fails, the script exits non-zero, so CI goes red whenever the data and the text
disagree.

    python3 tools/verify_results.py            # table to stdout
    python3 tools/verify_results.py --markdown # same table as Markdown (used in CI)
"""
import argparse, csv, math, os, sys
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = lambda *a: os.path.join(REPO, *a)
CHECKS = []


def check(study, claim, value, expected, tol, fmt="{:.3g}"):
    ok = abs(value - expected) <= tol
    CHECKS.append((study, claim, fmt.format(value), fmt.format(expected), ok))


def rows(path):
    return list(csv.DictReader(open(P(path))))


def med(xs):
    return float(np.median(np.asarray(xs, dtype=float)))


def slope(x, y):
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


# --------------------------------------------------------------------- scaling
sc = rows("results/02_scaling_study/results.csv")
ser = lambda s, k: np.array([float(r[k]) for r in sc if r["solver"] == s])
pn, pt, pi = ser("pcg", "ncells"), ser("pcg", "time_per_step_s"), ser("pcg", "piters_per_step")
gn, gt, gi = ser("gamg", "ncells"), ser("gamg", "time_per_step_s"), ser("gamg", "piters_per_step")
check("Scaling", "PCG wall time grows as n^p, p =", slope(pn, pt), 1.51, 0.005, "{:.2f}")
check("Scaling", "GAMG wall time grows as n^p, p =", slope(gn, gt), 1.22, 0.005, "{:.2f}")
check("Scaling", "PCG pressure iterations/step at 8k", pi[0], 265, 0.5, "{:.0f}")
check("Scaling", "PCG pressure iterations/step at 512k", pi[-1], 1905, 0.5, "{:.0f}")
check("Scaling", "GAMG pressure iterations/step at 8k", gi[0], 10, 0.5, "{:.0f}")
check("Scaling", "GAMG pressure iterations/step at 2M", gi[-1], 33, 0.5, "{:.0f}")
check("Scaling", "GAMG seconds per timestep at 2M", gt[-1], 10.6, 0.05, "{:.1f}")
fit = np.polyfit(np.log(pn), np.log(pt), 1)
pcg2m = math.exp(np.polyval(fit, math.log(gn[-1])))
check("Scaling", "PCG projected s/step at 2M (from fit)", pcg2m, 138, 1.0, "{:.0f}")
check("Scaling", "PCG / GAMG at 2M (projected)", pcg2m / gt[-1], 13, 0.5, "{:.0f}")
check("Scaling", "GAMG speed-up over PCG at 512k", pt[-1] / gt[gn == pn[-1]][0], 12.8, 0.05, "{:.1f}")

# ----------------------------------------------------------- mesh independence
mi = {r["label"]: r for r in rows("results/03_mesh_independence/results.csv")}
uc = [float(mi[k]["U_centre_outlet"]) for k in ("M0", "M1", "M2", "M3", "M4")]
chg = [abs(b - a) / b * 100 for a, b in zip(uc, uc[1:])]
for (a, b), c, e, t in zip([("8k", "32k"), ("32k", "128k"), ("128k", "288k"), ("288k", "512k")],
                           chg, [0.094, 0.024, 0.004, 0.0015], [5e-4, 5e-4, 5e-4, 5e-5]):
    check("Mesh", f"centreline change {a} -> {b} (%)", c, e, t, "{:.4f}")
e0, e1, e2 = (float(mi[k]["err_max_pct_Umax"]) for k in ("M0", "M1", "M2"))
p_err = math.log2((e0 - e1) / (e1 - e2))
floor = e2 - (e1 - e2) / (2 ** p_err - 1)
check("Mesh", "error floor from Richardson (% of U_max)", floor, 0.0181, 5e-5, "{:.4f}")
check("Mesh", "order of accuracy, floor removed", p_err, 1.99, 0.005, "{:.2f}")
u0, u1, u2 = (float(mi[k]["U_peak_outlet"]) for k in ("M0", "M1", "M2"))
check("Mesh", "self-convergence order of peak velocity", math.log2((u1 - u0) / (u2 - u1)), 2.0, 0.01, "{:.2f}")
check("Validation", "baseline error vs analytical (% of U_max)", e0, 0.08, 0.0015, "{:.3f}")

# --------------------------------------------------------------------- fp32
fr = rows("results/04_fp32_precision/results_final.csv")
pick = lambda pre, key: [float(r[key]) for r in fr if r["label"].startswith(pre)]
valid = sum(1 for r in fr if r["valid"] == "yes"
            and int(r["ux_lines"]) == int(r["steps_done"]) == int(r["uy_lines"]))
check("fp32", "runs with Ux and Uy solved every step", valid, len(fr), 0, "{:.0f}")


def speed(f64, f32):
    """fp32 time relative to fp64: >0 means fp32 is slower."""
    return (med(pick(f32, "exec_s")) / med(pick(f64, "exec_s")) - 1) * 100


def mem(f64, f32):
    return (1 - med(pick(f32, "peak_rss_MiB")) / med(pick(f64, "peak_rss_MiB"))) * 100


check("fp32", "16k cells: fp32 faster by (%)", -speed("m16k_fp64", "m16k_fp32"), 6.7, 0.05, "{:.1f}")
check("fp32", "65k cells: fp32 slower by (%)", speed("c_fp64ctl", "c_fp32"), 31.1, 0.05, "{:.1f}")
ratio = med(pick("b262k_fp32", "exec_s")) / med(pick("b262k_fp64", "exec_s"))
check("fp32", "262k cells: fp32 slower by (x)", ratio, 115.6, 0.05, "{:.1f}")
check("fp32", "PCG 65k: fp32 slower by (%)", speed("p2_fp64", "p2_fp32"), 7.7, 0.05, "{:.1f}")
check("fp32", "memory saved, 16k GAMG (%)", mem("m16k_fp64", "m16k_fp32"), 13.6, 0.05, "{:.1f}")
check("fp32", "memory saved, 65k GAMG (%)", mem("c_fp64ctl", "c_fp32"), 28.3, 0.05, "{:.1f}")
check("fp32", "memory saved, 65k PCG (%)", mem("p2_fp64", "p2_fp32"), 27.0, 0.05, "{:.1f}")
# two pressure correctors per step -> 2 solves per step
capfrac = lambda pre: med(pick(pre, "p_iters_capped")) / (2 * med(pick(pre, "steps_done"))) * 100
check("fp32", "capped pressure solves, 16k (%)", capfrac("m16k_fp32"), 0.0, 0.0, "{:.2f}")
check("fp32", "capped pressure solves, 65k (%)", capfrac("c_fp32"), 0.20, 0.005, "{:.2f}")
check("fp32", "capped pressure solves, 262k (%)", capfrac("b262k_fp32"), 95.31, 0.005, "{:.2f}")
acc = {r["label"]: float(r["U_peak_outlet"]) for r in fr if r["label"].startswith("acc_")}
check("fp32", "fp32 vs fp64 peak velocity gap (m/s)", abs(acc["acc_fp32"] - acc["acc_fp64"]), 3e-7, 5e-8, "{:.1e}")
fl = {int(r["cells"]): float(r["p_finalres_median"]) for r in fr
      if r["label"].startswith("floor_") and r["precision"] == "fp32"}
n_ = sorted(fl)
check("fp32", "fp32 residual floor grows as N^p, p =", slope(n_, [fl[k] for k in n_]), 0.50, 0.005, "{:.2f}")
f64floor = float(next(r for r in fr if r["label"] == "floor_262k_fp64")["p_finalres_median"])
check("fp32", "fp64 sits below the fp32 floor at 262k by (x)", fl[262144] / f64floor, 150, 5, "{:.0f}")

# ------------------------------------------------------------- inlet profiles
sk = np.load(P("data/fields/skewed_800x160.npz"))["ux"].astype(float)
ny, nx = sk.shape
yj = (np.arange(ny) + 0.5) / ny
col = lambda x: sk[:, min(int(round(x / (1.0 / nx) - 0.5)), nx - 1)]
cen = lambda p: float((yj * p).sum() / p.sum())
check("Inlets", "skewed: velocity centroid at inlet (y/H)", cen(col(0.0)), 0.40, 0.0015, "{:.2f}")
check("Inlets", "skewed: velocity centroid at outlet (y/H)", cen(col(1.0)), 0.50, 0.0015, "{:.2f}")
check("Inlets", "skewed: outlet peak velocity (m/s)", col(1.0).max(), 1.5002, 5e-5, "{:.4f}")
xs = np.linspace(0, 1, 60)
x_sym = next(x for x in xs if abs(cen(col(x)) - 0.5) < 0.005)
check("Inlets", "skewed: centroid within 0.5% of centre by x (m)", x_sym, 0.44, 0.005, "{:.2f}")
sn = np.load(P("data/fields/sine_800x160.npz"))["ux"].astype(float)
check("Inlets", "oscillating: lowest velocity anywhere in a cycle (m/s)", sn.min(), 0.004, 0.0005, "{:.3f}")

# ------------------------------------------------------------------ report
ap = argparse.ArgumentParser(); ap.add_argument("--markdown", action="store_true")
md = ap.parse_args().markdown
bad = [c for c in CHECKS if not c[4]]
if md:
    print("| Study | Claim | Recomputed | README | |\n|---|---|---:|---:|:-:|")
    for s, c, v, e, ok in CHECKS:
        print(f"| {s} | {c} | {v} | {e} | {'✅' if ok else '❌'} |")
    print(f"\n**{len(CHECKS) - len(bad)}/{len(CHECKS)} checks pass.**")
else:
    w = max(len(c[1]) for c in CHECKS)
    for s, c, v, e, ok in CHECKS:
        print(f"{'ok  ' if ok else 'FAIL'}  {s:<10} {c:<{w}}  {v:>9}  (README {e})")
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks pass")
sys.exit(1 if bad else 0)
