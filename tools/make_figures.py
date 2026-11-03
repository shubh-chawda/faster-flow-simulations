#!/usr/bin/env python3
"""Build every figure in the README (light and dark versions) from committed data.

    python3 tools/make_figures.py          # writes into assets/

Inputs are only the CSVs in results/ and the packed fields in data/fields/, so the
pictures can be rebuilt without OpenFOAM. The numbers drawn here are the same ones
tools/verify_results.py checks.
"""
import csv, glob, math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = lambda *a: os.path.join(REPO, *a)
OUT = P("assets")
os.makedirs(OUT, exist_ok=True)

for f in glob.glob(P("tools", "fonts", "*.ttf")):
    font_manager.fontManager.addfont(f)
FONT = "Archivo" if glob.glob(P("tools", "fonts", "*.ttf")) else "DejaVu Sans"

# One palette, two modes. Series colours were checked with a colour-vision validator
# (light surface #f5f8f9, dark surface #0e1a24).
THEMES = {
    "light": dict(bg="#f5f8f9", ink="#13233a", ink2="#4a5b6e", grid="#dce4e8",
                  teal="#008aa0", orange="#e0602a", ref="#8a99a6"),
    "dark":  dict(bg="#0e1a24", ink="#e6eef2", ink2="#9fb2c1", grid="#22313d",
                  teal="#0f8fa0", orange="#dd6630", ref="#6c7f8e"),
}
FLOW = LinearSegmentedColormap.from_list(
    "flow", ["#081a2b", "#0d3557", "#0a6680", "#1fa39c", "#8fd8bf", "#f4f8d6"])


def rows(path):
    return list(csv.DictReader(open(P(path))))


def style(t):
    plt.rcParams.update({
        "font.family": FONT, "font.size": 11, "axes.titlesize": 13,
        "axes.titleweight": "semibold", "axes.titlelocation": "left", "axes.titlepad": 12,
        "axes.labelsize": 10.5, "axes.labelcolor": t["ink2"], "text.color": t["ink"],
        "axes.edgecolor": t["grid"], "axes.facecolor": t["bg"], "figure.facecolor": t["bg"],
        "xtick.color": t["ink2"], "ytick.color": t["ink2"], "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5, "axes.grid": True, "grid.color": t["grid"],
        "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "legend.fontsize": 9.5, "lines.linewidth": 2,
        "lines.markersize": 7, "savefig.facecolor": t["bg"], "axes.axisbelow": True,
    })


def k(n):
    return f"{n / 1e6:g}M" if n >= 1e6 else f"{int(n / 1e3)}k"


def plain_log(ax, fmt):
    """Label a log axis with ordinary numbers (0.01, 0.1, 1 ...) instead of 10^n."""
    from matplotlib.ticker import FuncFormatter, NullFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: fmt(v)))
    ax.yaxis.set_minor_formatter(NullFormatter())


num = lambda v: f"{v:,.0f}" if v >= 1 else f"{v:g}"


def cells_axis(ax, ticks):
    ax.set_xscale("log")
    ax.set_xticks(ticks)
    ax.set_xticklabels([k(x) for x in ticks])
    ax.minorticks_off()
    ax.set_xlabel("cells in the mesh")


def save(fig, name, mode):
    fig.savefig(os.path.join(OUT, f"{name}-{mode}.png"), dpi=160, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


# ------------------------------------------------------------------ scaling
def fig_scaling(t, mode):
    sc = rows("results/02_scaling_study/results.csv")
    s = lambda solver, key: np.array([float(r[key]) for r in sc if r["solver"] == solver])
    pn, pt, pi = s("pcg", "ncells"), s("pcg", "time_per_step_s"), s("pcg", "piters_per_step")
    gn, gt, gi = s("gamg", "ncells"), s("gamg", "time_per_step_s"), s("gamg", "piters_per_step")
    fp = np.polyfit(np.log(pn), np.log(pt), 1)
    fg = np.polyfit(np.log(gn), np.log(gt), 1)

    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"wspace": 0.28})
    a.plot(pn, pt, "o-", color=t["orange"], label="PCG (conjugate gradient)")
    a.plot(gn, gt, "s-", color=t["teal"], label="GAMG (multigrid)")
    xe = np.array([pn[-1], gn[-1]])
    a.plot(xe, np.exp(np.polyval(fp, np.log(xe))), "--", color=t["orange"], lw=1.4, alpha=0.7)
    a.plot([gn[-1]], [np.exp(np.polyval(fp, np.log(gn[-1])))], "o", mfc=t["bg"], mec=t["orange"], mew=1.6)
    a.annotate(f"PCG $\\propto$ n$^{{{fp[0]:.2f}}}$\n~{np.exp(np.polyval(fp, np.log(gn[-1]))):.0f} s at 2M (projected)",
               (gn[-1], np.exp(np.polyval(fp, np.log(gn[-1])))), xytext=(-12, 0),
               textcoords="offset points", ha="right", va="center", fontsize=9.5, color=t["ink"])
    a.text(5.5e5, 0.3, f"GAMG $\\propto$ n$^{{{fg[0]:.2f}}}$\n{gt[-1]:.1f} s at 2M (measured)",
           ha="left", va="center", fontsize=9.5, color=t["ink"])
    a.set_yscale("log"); cells_axis(a, [8e3, 3.2e4, 1.28e5, 5.12e5, 1e6, 2e6])
    plain_log(a, lambda v: num(v) + " s"); a.set_ylabel("time per timestep")
    a.set_title("Time per timestep")
    a.legend(loc="upper left")

    b.plot(pn, pi, "o-", color=t["orange"], label="PCG")
    b.plot(gn, gi, "s-", color=t["teal"], label="GAMG")
    b.annotate(f"{pi[0]:.0f} → {pi[-1]:,.0f}", (pn[-1], pi[-1]), xytext=(8, 0), textcoords="offset points",
               va="center", fontsize=9.5, color=t["ink"])
    b.annotate(f"{gi[0]:.0f} → {gi[-1]:.0f}", (gn[-1], gi[-1]), xytext=(-4, 10), textcoords="offset points",
               ha="right", fontsize=9.5, color=t["ink"])
    b.set_yscale("log"); cells_axis(b, [8e3, 3.2e4, 1.28e5, 5.12e5, 1e6, 2e6])
    plain_log(b, num); b.set_ylabel("pressure-solver iterations per step")
    b.set_title("Pressure iterations per timestep")
    b.legend(loc="upper left")
    save(fig, "scaling", mode)


# ---------------------------------------------------------------- precision
def fig_precision(t, mode):
    fr = rows("results/04_fp32_precision/results_final.csv")
    pick = lambda pre, key: np.median([float(r[key]) for r in fr if r["label"].startswith(pre)])
    pts = [("16k", "m16k_fp64", "m16k_fp32"), ("65k", "c_fp64ctl", "c_fp32"), ("262k", "b262k_fp64", "b262k_fp32")]
    ratio = [pick(f32, "exec_s") / pick(f64, "exec_s") for _, f64, f32 in pts]
    capped = [pick(f32, "p_iters_capped") / (2 * pick(f32, "steps_done")) * 100 for _, _, f32 in pts]

    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"wspace": 0.28})
    x = np.arange(3)
    a.axhline(1, color=t["ref"], lw=1.2, ls="--")
    a.text(2.85, 0.97, "same speed", color=t["ink2"], fontsize=9, va="top", ha="right")
    a.plot(x[:2], ratio[:2], "-", color=t["orange"], lw=1.4, alpha=0.5)
    a.plot(x[1:], ratio[1:], ":", color=t["orange"], lw=1.4, alpha=0.5)
    for i in range(3):
        hollow = i == 2
        a.plot(x[i], ratio[i], "o", ms=10, color=t["orange"], mfc=t["bg"] if hollow else t["orange"], mew=2)
        lab = (f"{(1 - ratio[i]) * 100:.1f}% faster" if ratio[i] < 1 else
               f"{(ratio[i] - 1) * 100:.0f}% slower" if ratio[i] < 2 else f"{ratio[i]:.0f}× slower*")
        a.annotate(f"{lab}\n{capped[i]:.2g}% of solves hit the iteration limit", (x[i], ratio[i]),
                   xytext=(12, [-8, 8, 0][i]), textcoords="offset points",
                   va=["top", "bottom", "center"][i], fontsize=9.3, color=t["ink"])
    a.set_yscale("log"); a.set_ylim(0.3, 300); a.set_xlim(-0.3, 2.9)
    a.set_xticks(x); a.set_xticklabels([f"{p[0]} cells" for p in pts]); a.grid(axis="x", visible=False)
    a.set_yticks([1, 10, 100]); a.set_yticklabels(["1×", "10×", "100×"])
    a.set_ylabel("fp32 time ÷ fp64 time")
    a.set_title("fp32 time relative to fp64 (GAMG)")
    a.text(0, -0.2, "* At 262k cells fp32 does not reach the tolerance, so this compares work done rather than converged solves.",
           transform=a.transAxes, fontsize=8.5, color=t["ink2"])

    fl = sorted((int(r["cells"]), float(r["p_finalres_median"])) for r in fr
                if r["label"].startswith("floor_") and r["precision"] == "fp32")
    n = np.array([c for c, _ in fl]); res = np.array([v for _, v in fl])
    f = np.polyfit(np.log(n), np.log(res), 1)
    f64 = float(next(r for r in fr if r["label"] == "floor_262k_fp64")["p_finalres_median"])
    xx = np.geomspace(3e3, 3.5e5, 50)
    b.plot(xx, np.exp(np.polyval(f, np.log(xx))), "-", color=t["orange"], lw=1.2, alpha=0.45)
    b.plot(n, res, "o", color=t["orange"], label="fp32: lowest residual it can reach")
    b.plot([262144], [f64], "s", color=t["teal"], label="fp64 at 262k")
    b.axhline(1e-4, color=t["ref"], lw=1.2, ls="--")
    b.text(3.3e3, 1.07e-4, "requested tolerance $10^{-4}$", color=t["ink2"], fontsize=9, va="bottom")
    b.annotate(f"$\\propto$ N$^{{{f[0]:.2f}}}$  (≈ √N)", (n[1], res[1]), xytext=(0, 14), textcoords="offset points",
               ha="center", fontsize=9.5, color=t["ink"])
    b.annotate(f"~{res[-1] / f64:.0f}× lower", (262144, f64), xytext=(-10, 0), textcoords="offset points",
               ha="right", va="center", fontsize=9.5, color=t["ink"])
    b.set_yscale("log"); cells_axis(b, [4096, 16384, 65536, 262144]); b.set_xlim(3e3, 3.6e5)
    b.set_ylabel("pressure residual floor")
    b.set_title("Lowest pressure residual reached in fp32")
    plain_log(b, lambda v: f"{v:.0e}".replace("e-0", "e-"))
    b.legend(loc="lower left")
    save(fig, "precision", mode)


# --------------------------------------------------------- mesh independence
def fig_mesh(t, mode):
    mi = {r["label"]: r for r in rows("results/03_mesh_independence/results.csv")}
    lab = ["M0", "M1", "M2", "M3", "M4"]
    n = np.array([float(mi[l]["cells"]) for l in lab])
    uc = np.array([float(mi[l]["U_centre_outlet"]) for l in lab])
    err = np.array([float(mi[l]["err_max_pct_Umax"]) for l in lab])
    chg = np.abs(np.diff(uc)) / uc[1:] * 100
    e0, e1, e2 = err[:3]
    p = math.log2((e0 - e1) / (e1 - e2)); F = e2 - (e1 - e2) / (2 ** p - 1)

    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"wspace": 0.28})
    a.plot(n[1:], chg, "o-", color=t["teal"])
    for v, txt in [(1, "1% criterion"), (0.01, "0.01% criterion")]:
        a.axhline(v, color=t["ref"], lw=1.2, ls="--")
        a.text(2.4e4, v * 1.12, txt, color=t["ink2"], fontsize=9, va="bottom")
    for xi, c in zip(n[1:], chg):
        a.annotate(f"{c:.3g}%", (xi, c), xytext=(7, 4), textcoords="offset points", fontsize=9.3, color=t["ink"])
    a.set_yscale("log"); a.set_ylim(8e-4, 3); cells_axis(a, [3.2e4, 1.28e5, 2.88e5, 5.12e5])
    plain_log(a, lambda v: f"{v:g}%")
    a.set_ylabel("change in outlet velocity vs previous mesh (%)")
    a.set_title("Change between successive meshes")

    a2 = b
    a2.plot(n, err, "o-", color=t["orange"], label="max error")
    a2.plot(n[:3], err[:3] - F, "s-", color=t["teal"], label="max error minus floor")
    a2.axhline(F, color=t["ref"], lw=1.2, ls="--")
    a2.text(5.4e5, F * 0.93, f"floor {F:.4f}% (flow not fully\ndeveloped at the outlet)",
            color=t["ink2"], fontsize=9, va="top", ha="right")
    xm = math.sqrt(n[1] * n[2]); ym = math.sqrt((err[1] - F) * (err[2] - F))
    a2.annotate(f"order {p:.2f}", (xm, ym), xytext=(10, 0), textcoords="offset points",
                va="center", fontsize=9.5, color=t["ink"])
    a2.set_yscale("log"); cells_axis(a2, [8e3, 3.2e4, 1.28e5, 2.88e5, 5.12e5])
    a2.set_yticks([0.005, 0.01, 0.02, 0.05]); plain_log(a2, lambda v: f"{v:g}%")
    a2.set_ylabel("max error, % of peak velocity")
    a2.set_title("Error against the exact solution")
    a2.legend(loc="upper right")
    save(fig, "mesh", mode)


# --------------------------------------------------------------- validation
def fig_validation(t, mode):
    d = np.loadtxt(P("results/01_validation/openfoam_outlet_profile.csv"), delimiter=",", comments="#")
    y, sim = d[:, 0] * 1e3, d[:, 1]
    yy = np.linspace(0, 100, 200); exact = 1.5 * 4 * (yy / 100) * (1 - yy / 100)
    err = np.abs(sim - d[:, 2]).max() / 1.5 * 100
    fig, a = plt.subplots(figsize=(5.6, 4.4))
    a.plot(exact, yy, "-", color=t["ref"], lw=2, label="exact (Poiseuille)")
    a.plot(sim, y, "o", color=t["teal"], ms=5.5, label="OpenFOAM, 8k cells")
    a.text(0.04, 0.40, f"max difference\n{err:.2f}% of peak", transform=a.transAxes, fontsize=10, color=t["ink"], va="center")
    a.set_xlabel("velocity at the outlet (m/s)"); a.set_ylabel("height across the channel (mm)")
    a.set_ylim(0, 100); a.set_xlim(0, 1.65)
    a.set_title("Outlet velocity profile")
    a.legend(loc="center left", bbox_to_anchor=(0.0, 0.62))
    save(fig, "validation", mode)


# -------------------------------------------------------------- flow fields
def strip(ax, field, vmax):
    ax.imshow(field, origin="lower", cmap=FLOW, vmin=0, vmax=vmax, extent=[0, 1, 0, 0.1],
              aspect="auto", interpolation="bicubic")
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def fig_fields(t, mode):
    st = np.load(P("data/fields/steady_512x128.npz"))["ux"]
    sk = np.load(P("data/fields/skewed_800x160.npz"))["ux"]
    fig = plt.figure(figsize=(12, 3.9))
    a = fig.add_axes([0.0, 0.56, 0.9, 0.24]); b = fig.add_axes([0.0, 0.08, 0.9, 0.24])
    strip(a, st, 1.55); strip(b, sk, 1.55)
    fig.text(0, 0.86, "Uniform inlet",
             fontsize=12, fontweight="semibold", color=t["ink"])
    fig.text(0, 0.38, "Skewed inlet",
             fontsize=12, fontweight="semibold", color=t["ink"])
    cax = fig.add_axes([0.925, 0.08, 0.012, 0.72])
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=FLOW, norm=plt.Normalize(0, 1.55)), cax=cax)
    cb.outline.set_visible(False); cb.set_label("velocity (m/s)", color=t["ink2"], fontsize=9.5)
    cb.ax.tick_params(labelsize=9, colors=t["ink2"])
    fig.text(0, 0.0, "Channel 1.0 m × 0.1 m, drawn to scale. Flow is from left to right.",
             fontsize=9, color=t["ink2"])
    save(fig, "fields", mode)


# ------------------------------------------------------------------- banner
def banner():
    """Animated banner: one real cycle of the oscillating-inlet run (20 saved frames)."""
    from PIL import Image
    sn = np.load(P("data/fields/sine_800x160.npz"))
    u, tt = sn["ux"].astype(float), sn["t"]
    bg = "#0e1a24"
    style(THEMES["dark"])
    frames = []
    for i in range(len(u)):
        fig = plt.figure(figsize=(16, 4.0), dpi=100)
        fig.patch.set_facecolor(bg)
        fig.text(0.04, 0.80, "Faster Flow Simulations", fontsize=40, fontweight="bold", color="#e6eef2")
        fig.text(0.04, 0.66, "Multigrid and single precision for the pressure solve in OpenFOAM",
                 fontsize=17, color="#9fb2c1")
        ax = fig.add_axes([0.04, 0.17, 0.92, 0.37]); strip(ax, u[i], 2.2)
        phase = (tt[i] - 5.0) % 1.0
        fig.text(0.04, 0.06, "OpenFOAM output, 128,000 cells. Inlet velocity 1 + 0.5 sin(2πt) m/s, one 1 s cycle.",
                 fontsize=11.5, color="#9fb2c1")
        fig.text(0.96, 0.06, f"t = {phase:.2f} s", fontsize=11.5, color="#9fb2c1", ha="right")
        fig.canvas.draw()
        im = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert("RGB")
        frames.append(im); plt.close(fig)
    frames[0].save(os.path.join(OUT, "banner.png"))
    # one palette built from every frame, so colours that only appear late in the cycle survive
    sheet = Image.new("RGB", (frames[0].width, frames[0].height * len(frames)))
    for i, f in enumerate(frames):
        sheet.paste(f, (0, i * f.height))
    pal = sheet.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(os.path.join(OUT, "banner.gif"), save_all=True, append_images=q[1:],
              duration=60, loop=0, optimize=True, disposal=1)


if __name__ == "__main__":
    for mode, th in THEMES.items():
        style(th)
        fig_scaling(th, mode); fig_precision(th, mode); fig_mesh(th, mode)
        fig_validation(th, mode); fig_fields(th, mode)
    banner()
    print("wrote", ", ".join(sorted(os.listdir(OUT))))
