#!/usr/bin/env python3
"""Sine-inlet (oscillating) case: the bulk velocity is pinned to the inlet by
mass conservation, so the physics is in the CENTRELINE response — its amplitude
and phase lag relative to the inlet (unsteady/Womersley effect, alpha~4 here).
Plots inlet vs outlet-centreline Ux over time and reports amplitude ratio + lag."""
import os, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
CASE = os.path.join(HERE, "sine")
NX, NY, H, NU, F = 800, 160, 0.1, 1.0e-3, 1.0
alpha = (H/2)*np.sqrt(2*np.pi*F/NU)

def read_ux(path):
    body = open(path).read().split("internalField", 1)[1].split("boundaryField", 1)[0]
    return np.array([float(v) for v in re.findall(
        r"\(\s*([-\deE.+]+)\s+[-\deE.+]+\s+[-\deE.+]+\s*\)", body)][:NX*NY])

def centreline(ux, i):
    col = ux[np.arange(NY)*NX + i]
    return 0.5*(col[NY//2-1] + col[NY//2])

def main():
    times = sorted((float(d), d) for d in os.listdir(CASE)
                   if d.replace(".", "").isdigit() and os.path.isdir(os.path.join(CASE, d)))
    t, u_in, u_out = [], [], []
    gmin = 1e9                           # global min Ux over established cycles (backflow check)
    tmax = max(tf for tf, _ in times)
    for tf, td in times:
        if tf == 0:                      # initial uniform field: no solved data
            continue
        try: ux = read_ux(os.path.join(CASE, td, "U"))
        except (FileNotFoundError, IndexError): continue
        if ux.size != NX*NY:             # skip any non-solved/uniform field
            continue
        t.append(tf); u_in.append(centreline(ux, 0)); u_out.append(centreline(ux, NX-1))
        if tf >= tmax - 2.0:
            gmin = min(gmin, float(ux.min()))
    t, u_in, u_out = np.array(t), np.array(u_in), np.array(u_out)

    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.plot(t, 1+0.5*np.sin(2*np.pi*F*t), color="#c0392b", ls="--", lw=1.3,
            label="inlet bulk = 1+0.5 sin(2πt)")
    ax.plot(t, u_out, color="#1f4e79", lw=1.9, marker=".", ms=3,
            label="outlet centreline $U_x$")
    ax.axhline(1.5, color="gray", ls=":", lw=0.9, label="steady developed peak (1.5)")
    ax.set_xlabel("time  [s]"); ax.set_ylabel("$U_x$  [m/s]")
    ax.set_title(f"Oscillating inlet: outlet centreline response (Womersley α≈{alpha:.1f})")
    ax.grid(alpha=.3); ax.legend(fontsize=8, loc="upper right")

    # analyse the last 2 established cycles: amplitude + phase lag of outlet centreline
    mask = t >= t.max() - 2.0
    if mask.sum() > 10:
        tt, oo = t[mask], u_out[mask]
        omega = 2*np.pi*F
        # fit A*sin(omega t)+B*cos(omega t)+C
        M = np.column_stack([np.sin(omega*tt), np.cos(omega*tt), np.ones_like(tt)])
        A, B, C = np.linalg.lstsq(M, oo, rcond=None)[0]
        amp = np.hypot(A, B)
        shift = (np.degrees(np.arctan2(B, A)) + 180) % 360 - 180   # signed, in (-180,180]
        atten = (1 - amp/0.75) * 100     # vs quasi-steady centreline amplitude 0.75
        note = (f"outlet centreline: mean={C:.3f}, amplitude={amp:.3f}\n"
                f"→ {atten:.0f}% attenuated vs quasi-steady (0.75) — unsteadiness\n"
                f"phase shift ≈ {abs(shift):.0f}° (near in-phase)\n"
                f"min $U_x$ = {gmin:+.3f} m/s → no backflow")
        ax.text(0.015, 0.03, note, transform=ax.transAxes, fontsize=7.5, va="bottom",
                bbox=dict(boxstyle="round", fc="#eef", ec="#1f4e79", alpha=.85))
        print(f"outlet centreline: mean={C:.3f} amp={amp:.3f} ({atten:.0f}% atten) "
              f"shift={shift:.0f}deg minUx={gmin:+.4f} alpha={alpha:.2f}")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "sine_result.png"), dpi=140)
    print("wrote sine_result.png")

if __name__ == "__main__":
    main()
