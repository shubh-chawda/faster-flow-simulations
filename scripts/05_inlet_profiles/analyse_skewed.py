#!/usr/bin/env python3
"""Skewed-inlet case: show the asymmetric inlet profile re-developing toward the
symmetric Poiseuille parabola downstream. Extracts Ux(y) at several x-stations at
steady state and quantifies the asymmetry decay."""
import os, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
CASE = os.path.join(HERE, "skewed")
NX, NY, L, H = 800, 160, 1.0, 0.1
UMAX_POIS = 1.5

def latest_time(case):
    ts = []
    for d in os.listdir(case):
        try: ts.append((float(d), d))
        except ValueError: pass
    return sorted(ts)[-1][1]

def read_ux(path):
    body = open(path).read().split("internalField", 1)[1].split("boundaryField", 1)[0]
    return np.array([float(v) for v in re.findall(
        r"\(\s*([-\deE.+]+)\s+[-\deE.+]+\s+[-\deE.+]+\s*\)", body)][:NX*NY])

def profile_at_x(ux, x):
    i = min(int(round(x / (L/NX) - 0.5)), NX-1)
    return ux[np.arange(NY)*NX + i]

def main():
    t = latest_time(CASE)
    ux = read_ux(os.path.join(CASE, t, "U"))
    dy = H/NY; yj = (np.arange(NY)+0.5)*dy
    pois = UMAX_POIS*4*yj*(H-yj)/H**2
    stations = [0.0, 0.05, 0.15, 0.3, 0.6, 1.0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))
    cmap = plt.cm.viridis(np.linspace(0, 0.9, len(stations)))
    ymid = []
    for x, c in zip(stations, cmap):
        p = profile_at_x(ux, x)
        ax1.plot(p, yj*1e3, color=c, lw=1.8, label=f"x={x:.2f} m")
        # centroid of momentum (measure of skew): sum(y*U)/sum(U)
        ymid.append((np.sum(yj*p)/np.sum(p))/H)
    ax1.plot(pois, yj*1e3, "k--", lw=1.5, label="symmetric Poiseuille")
    ax1.axhline(H/2*1e3, color="gray", ls=":", lw=0.8)
    ax1.set_xlabel("$U_x$  [m/s]"); ax1.set_ylabel("y  [mm]")
    ax1.set_title("Skewed inlet re-developing to Poiseuille")
    ax1.legend(fontsize=7.5); ax1.grid(alpha=.3)

    # asymmetry decay: velocity centroid y/H (0.5 = symmetric) vs x, denser sampling
    xs = np.linspace(0, 1.0, 60)
    cen = []
    for x in xs:
        p = profile_at_x(ux, x); cen.append((np.sum(yj*p)/np.sum(p))/H)
    cen = np.array(cen)
    ax2.plot(xs, cen, "-", color="#1f4e79", lw=2)
    ax2.axhline(0.5, color="k", ls="--", lw=1, label="symmetric (0.5)")
    ax2.set_xlabel("x  [m]"); ax2.set_ylabel("velocity centroid  $y_c/H$")
    ax2.set_title("Asymmetry decays along the channel")
    ax2.legend(fontsize=8); ax2.grid(alpha=.3)
    # development length: where centroid within 1% of 0.5
    dev = xs[np.where(np.abs(cen-0.5) < 0.005)[0][0]] if np.any(np.abs(cen-0.5)<0.005) else None
    outlet_umax = profile_at_x(ux, 1.0).max()
    txt = (f"inlet centroid y/H = {cen[0]:.3f}\noutlet centroid y/H = {cen[-1]:.3f}\n"
           f"outlet peak U = {outlet_umax:.4f} (Poiseuille 1.5)\n"
           + (f"symmetric to <0.5% by x≈{dev:.2f} m" if dev else ""))
    ax2.text(0.5, 0.42, txt, fontsize=7.5,
             bbox=dict(boxstyle="round", fc="#eef", ec="#1f4e79", alpha=.8))
    fig.suptitle(f"Skewed inlet (128k mesh, fp64, steady t={t}s)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(HERE, "skewed_result.png"), dpi=140)
    print(f"wrote skewed_result.png  (inlet y_c/H={cen[0]:.3f} -> outlet {cen[-1]:.3f}, "
          f"outlet peak U={outlet_umax:.4f})")

if __name__ == "__main__":
    main()
