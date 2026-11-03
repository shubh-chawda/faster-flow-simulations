#!/usr/bin/env python3
"""
Analysis and plots for the mesh-independence sweep. Reads results.csv
(written by run_sweep.py) and writes the convergence table and plots.

Convergence has exactly ONE definition, set in run_sweep.py (field-wide
max|dU| between successive writes < 1e-6 m/s, enforced as a steady-state
stopping condition). This script READS that verdict from results.csv and never
recomputes it. The field-wide dU and the outlet-output drift are shown as
reported evidence, not as an alternative gate.

Outputs:
  convergence.png        outlet centreline velocity vs cells (log x), 1.5 ref.
  error_convergence.png  raw error (flattens onto a physical floor) AND the
                         floor-subtracted error (falls at ~2nd order); one
                         order figure (~2.0) is reported everywhere.
  wall_shear.png         outlet wall shear vs cells (log x), 0.06 ref.
  convergence_table.md   steady-state evidence, %-change table, and a conclusion
                         that leads with the numbers (the 1% threshold is shown
                         to be uninformative here) + a tighter 0.01% criterion.
"""
import csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE    = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results.csv")
UMAX, H, NU = 1.5, 0.1, 1.0e-3
TAU_ANALYTIC = 0.06
LOOSE_PCT, TIGHT_PCT = 1.0, 0.01     # thresholds: usual 1% and a tighter 0.01%

PHYSICAL = {   # physically-dimensioned outputs (plateau to a finite value)
    "outlet centreline velocity U_c [m/s]": ("U_centre_outlet", 1.5),
    "outlet peak velocity U_max [m/s]":     ("U_peak_outlet", 1.5),
    "wall shear tau_w/rho [m2/s2]":         ("tau_w_over_rho", 0.06),
    "mean outlet velocity [m/s]":           ("U_mean_outlet", 1.0),
}
ERRORS = {     # converge toward zero (a floor here is physical, see below)
    "max profile error [% Umax]": "err_max_pct_Umax",
    "L2 profile error [% Umax]":  "err_L2_pct_Umax",
}
STYLE = {"fp64": dict(color="#1f4e79", marker="o", ls="-"),
         "fp32": dict(color="#c0392b", marker="s", ls="--")}
NUMERIC_SKIP = {"label", "precision", "converged", "checkMesh_ok", "final_time"}


def load():
    rows = list(csv.DictReader(open(RESULTS)))
    for r in rows:
        for k, v in list(r.items()):
            if k not in NUMERIC_SKIP:
                try: r[k] = float(v)
                except (ValueError, TypeError): r[k] = float("nan")
    return rows

def by_precision(rows):
    out = {}
    for r in rows:
        out.setdefault(r["precision"], []).append(r)
    for p in out:
        out[p].sort(key=lambda r: r["cells"])
    return out

def fit_order(cells, err):
    c, e = np.asarray(cells, float), np.asarray(err, float)
    good = (e > 0) & np.isfinite(e) & np.isfinite(c)
    if good.sum() < 2: return float("nan")
    return -2.0 * np.polyfit(np.log(c[good]), np.log(e[good]), 1)[0]

def selfconv_order(rows, key):
    """Observed order from successive-difference ratios on the coarsest triple
    with a CONSTANT refinement ratio (|d2|/|d1| = r^-p). Not floor-contaminated."""
    for i in range(len(rows) - 2):
        c0, c1, c2 = rows[i]["cells"], rows[i+1]["cells"], rows[i+2]["cells"]
        r1, r2 = (c1/c0) ** 0.5, (c2/c1) ** 0.5
        if abs(r1 - r2) < 1e-6 * r1:
            d1 = rows[i+1][key] - rows[i][key]
            d2 = rows[i+2][key] - rows[i+1][key]
            if d1 * d2 > 0 and 0 < abs(d2) < abs(d1):
                return np.log(abs(d1/d2)) / np.log(r1), (int(c0), int(c1), int(c2)), r1
    return None

def richardson_floor(rows, key="err_max_pct_Umax"):
    """Fit a physical error floor F on the coarsest constant-2x triple:
    e = F + C h^p, so (e0-e1)/(e1-e2) = 2^p and F = e2 - (e1-e2)/(2^p - 1)."""
    for i in range(len(rows) - 2):
        c0, c1, c2 = rows[i]["cells"], rows[i+1]["cells"], rows[i+2]["cells"]
        if abs((c1/c0) - 4) < 1e-6 and abs((c2/c1) - 4) < 1e-6:   # 2x linear = 4x cells
            e0, e1, e2 = rows[i][key], rows[i+1][key], rows[i+2][key]
            a, b = e0 - e1, e1 - e2
            if a > b > 0:
                p = np.log2(a / b)
                return e2 - b / (2 ** p - 1), p
    return None


def pct_change(vals):
    out = []
    for i in range(1, len(vals)):
        qc = vals[i-1]
        out.append(abs(vals[i] - qc) / abs(qc) * 100 if qc else float("nan"))
    return out

def crossing_mesh(cells, changes, thr):
    """Coarsest cell count beyond which every successive change stays < thr."""
    plateau = cells[0]
    for i, pc in enumerate(changes, start=1):
        if not (pc < thr):
            plateau = cells[i]
    return plateau


def write_table(prec_rows):
    L = ["# Mesh-independence: convergence table\n",
         "Convergence criterion (the same for every run): "
         "field-wide max|dU| between successive 0.5 s writes < 1e-6 m/s, enforced "
         "as a steady-state stopping condition.\n"]
    for prec, rows in prec_rows.items():
        cells = [int(r["cells"]) for r in rows]
        L.append(f"\n## {prec}\n")
        L.append("_Steady-state evidence:_\n")
        L.append("| mesh | cells | final t (s) | chunks | field max\\|dU\\| (m/s) | "
                 "U_peak drift % | Co_max | steady |")
        L.append("|---|---|---|---|---|---|---|---|")
        for r in rows:
            L.append(f"| {r['label']} | {int(r['cells']):,} | {r.get('final_time','?')} "
                     f"| {int(r.get('n_chunks',1))} | {r['dU_field_last_writes']:.2e} "
                     f"| {r['out_drift_pct']:.5f} | {r['Co_max']:.4f} | {r['converged']} |")
        bad = [r['label'] for r in rows if r['converged'] != 'yes']
        if bad:
            L.append(f"\n> Not converged: {', '.join(bad)}.\n")

        # per-metric %-change tables
        for name, (key, ana) in PHYSICAL.items():
            vals = [r[key] for r in rows]; ch = pct_change(vals)
            L.append(f"\n**{name}**  (analytical = {ana:g})")
            L.append("| pair | cells | Q(coarser) | Q(finer) | % change |")
            L.append("|---|---|---|---|---|")
            for i, pc in enumerate(ch, start=1):
                f1 = " ✓₁" if pc < LOOSE_PCT else ""
                f2 = " ✓₀.₀₁" if pc < TIGHT_PCT else ""
                L.append(f"| M{i-1}→M{i} | {cells[i-1]:,}→{cells[i]:,} | {vals[i-1]:.6g} "
                         f"| {vals[i]:.6g} | {pc:.4f}%{f2 or f1} |")
        for name, key in ERRORS.items():
            vals = [r[key] for r in rows]; ch = pct_change(vals)
            L.append(f"\n**{name}**  (→ 0; %-change stays large near the floor)")
            L.append("| pair | cells | Q(coarser) | Q(finer) | % change |")
            L.append("|---|---|---|---|---|")
            for i, pc in enumerate(ch, start=1):
                L.append(f"| M{i-1}→M{i} | {cells[i-1]:,}→{cells[i]:,} | {vals[i-1]:.6g} "
                         f"| {vals[i]:.6g} | {pc:.4f}% |")

        # ---- interpretation ----
        L.append("\n### Interpretation\n")
        # 1% is uninformative
        first_uc = pct_change([r["U_centre_outlet"] for r in rows])
        if first_uc and max(first_uc) < LOOSE_PCT:
            L.append(f"- Every mesh, including the {cells[0]:,}-cell one, passes the 1% "
                     f"criterion ({first_uc[0]:.3f}% change at the first refinement), so "
                     f"1% does not distinguish between meshes for this case.\n")
        # tighter criterion, governing metric
        govs = {}
        for name, (key, ana) in PHYSICAL.items():
            ch = pct_change([r[key] for r in rows])
            govs[name] = crossing_mesh(cells, ch, TIGHT_PCT)
        gov_name = max(govs, key=govs.get); gov = govs[gov_name]
        # distance of each mesh from the finest-mesh (asymptotic) value
        L.append(f"- With a {TIGHT_PCT}% criterion, every output settles by {gov:,} cells "
                 f"(the slowest is {gov_name.split(' [')[0]}).")
        finest = rows[-1]
        dist_lines = []
        for name, (key, ana) in PHYSICAL.items():
            for r in rows:
                d = abs(r[key] - finest[key]) / abs(finest[key]) * 100 if finest[key] else 0
                if d < 0.01:
                    dist_lines.append(f"{name.split(' [')[0]} within 0.01% of the "
                                      f"{int(finest['cells']):,}-cell value by "
                                      f"{int(r['cells']):,}")
                    break
        if dist_lines:
            L.append("  - " + "; ".join(dist_lines) + ".")
        sc = selfconv_order(rows, "U_peak_outlet")
        if sc:
            p, (c0, c1, c2), r = sc
            L.append(f"- Self-convergence order of U_peak: {p:.1f} ({r:.0f}× refinement, "
                     f"{c0:,}, {c1:,} and {c2:,} cells), as expected for second-order schemes.")
        rf = richardson_floor(rows)
        if rf:
            F, p = rf
            L.append(f"- The error against the exact solution levels off at {F:.4f}% of "
                     f"U_max (Richardson fit on {cells[0]:,}, {cells[1]:,} and {cells[2]:,} "
                     f"cells, order {p:.2f}). The outlet at x = 1.0 m is about two entrance "
                     f"lengths downstream, so the flow there is not fully developed. With this "
                     f"value subtracted the error converges at second order "
                     f"(error_convergence.png).")
        # Courant number
        cos = [r["Co_max"] for r in rows]
        L.append(f"- dt was set to 0.2/nx. The resulting Co_max goes from {min(cos):.3f} to "
                 f"{max(cos):.3f} across the series, because finer meshes resolve the "
                 f"velocity overshoot near the inlet.")
    open(os.path.join(HERE, "convergence_table.md"), "w").write("\n".join(L))
    print("wrote convergence_table.md")


def plot_convergence(prec_rows):
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for prec, rows in prec_rows.items():
        st = STYLE.get(prec, dict(color="gray", marker="^", ls="-"))
        ax.plot([r["cells"] for r in rows], [r["U_centre_outlet"] for r in rows],
                label=f"{prec} (centreline)", **st, ms=6, lw=1.8)
    ax.axhline(1.5, ls=":", color="k", lw=1.3, label="analytical (1.5 m/s)")
    ax.set_xscale("log")
    ax.set_xlabel("number of cells"); ax.set_ylabel("outlet centreline $U$  [m/s]")
    ax.set_title("Mesh independence: outlet centreline velocity")
    ax.grid(alpha=.3, which="both"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "convergence.png"), dpi=140)
    print("wrote convergence.png")

def plot_error(prec_rows):
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    for prec, rows in prec_rows.items():
        st = STYLE.get(prec, dict(color="gray", marker="^", ls="-"))
        cells = [r["cells"] for r in rows]
        emax = [r["err_max_pct_Umax"] for r in rows]
        ax.plot(cells, emax, **st, ms=6, lw=1.8, label=f"{prec} max err (raw)")
        rf = richardson_floor(rows)
        if rf:
            F, _ = rf
            es = [e - F for e in emax]
            cc = [c for c, e in zip(cells, es) if e > 0]
            ee = [e for e in es if e > 0]
            order = fit_order(cc, ee)
            st2 = dict(st); st2["ls"] = "--"; st2["marker"] = "D"
            ax.plot(cc, ee, **st2, ms=5, lw=1.6,
                    label=f"{prec} max err − floor (order≈{order:.1f})")
            ax.axhline(F, color=st["color"], ls=(0, (1, 3)), lw=1.0, alpha=.7)
            ax.text(cells[-1], F * 1.05,
                    f"floor F≈{F:.4f}%  (incomplete flow\ndevelopment, mesh-independent)",
                    fontsize=7, ha="right", va="bottom", color=st["color"])
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("number of cells"); ax.set_ylabel("max profile error  [% of $U_{max}$]")
    ax.set_title("Error vs analytical Poiseuille: raw vs floor-subtracted")
    ax.grid(alpha=.3, which="both"); ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "error_convergence.png"), dpi=140)
    print("wrote error_convergence.png")

def plot_wallshear(prec_rows):
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for prec, rows in prec_rows.items():
        st = STYLE.get(prec, dict(color="gray", marker="^", ls="-"))
        ax.plot([r["cells"] for r in rows], [r["tau_w_over_rho"] for r in rows],
                label=f"{prec}", **st, ms=6, lw=1.8)
    ax.axhline(TAU_ANALYTIC, ls=":", color="k", lw=1.3, label="analytical (0.06 m²/s²)")
    ax.set_xscale("log")
    ax.set_xlabel("number of cells"); ax.set_ylabel(r"wall shear $\tau_w/\rho$  [m²/s²]")
    ax.set_title("Mesh independence: outlet wall shear stress")
    ax.grid(alpha=.3, which="both"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "wall_shear.png"), dpi=140)
    print("wrote wall_shear.png")


def main():
    rows = load(); prec_rows = by_precision(rows)
    print("loaded " + ", ".join(f"{p}={len(r)}" for p, r in prec_rows.items()))
    write_table(prec_rows)
    plot_convergence(prec_rows); plot_error(prec_rows); plot_wallshear(prec_rows)

if __name__ == "__main__":
    main()
