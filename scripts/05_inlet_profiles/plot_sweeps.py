#!/usr/bin/env python3
"""Plot the two oscillating-inlet sweeps from sweep_results.csv:
  (left)  amplitude sweep (f=1, α≈4): min Ux vs A -> backflow onset
  (right) frequency sweep (A=0.5): outlet-centreline attenuation & phase vs α."""
import csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "sweep_results.csv"))))
for r in rows:
    for k in ("nx", "amp", "freq", "alpha", "min_Ux", "out_amp", "out_phase_deg", "out_mean"):
        r[k] = float(r[k])

# amplitude sweep at 128k (near-wall backflow needs resolution); freq sweep at 32k (core flow)
amp_sweep = sorted([r for r in rows if r["nx"] == 800 and abs(r["freq"]-1.0) < 1e-9],
                   key=lambda r: r["amp"])
frq_sweep = sorted([r for r in rows if r["nx"] == 400 and abs(r["amp"]-0.5) < 1e-9],
                   key=lambda r: r["alpha"])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

# --- amplitude sweep: min Ux vs A ---
if amp_sweep:
    A = [r["amp"] for r in amp_sweep]; mn = [r["min_Ux"] for r in amp_sweep]
    ax1.plot(A, mn, "o-", color="#1f4e79", ms=7, lw=1.8)
    ax1.axhline(0, color="#c0392b", ls="--", lw=1.2, label="backflow onset (min $U_x$=0)")
    # linear-interpolate the crossing (first A where min Ux < 0)
    Acrit = None
    for i in range(1, len(A)):
        if mn[i-1] >= 0 > mn[i]:
            Acrit = A[i-1] + (0-mn[i-1])*(A[i]-A[i-1])/(mn[i]-mn[i-1]); break
    if Acrit:
        ax1.axvline(Acrit, color="gray", ls=":", lw=1)
        ax1.annotate(f"backflow begins\nat A ≈ {Acrit:.2f}", xy=(Acrit, 0),
                     xytext=(Acrit-0.35, max(mn)*0.4), fontsize=8,
                     arrowprops=dict(arrowstyle="->", color="gray"))
    ax1.set_xlabel("inlet oscillation amplitude A  (Uₓ = 1 + A·sin 2πt)")
    ax1.set_ylabel("min $U_x$ in domain over a cycle  [m/s]")
    ax1.set_title("Amplitude sweep (α≈4): onset of backflow")
    ax1.grid(alpha=.3); ax1.legend(fontsize=8)

# --- frequency sweep: attenuation & phase vs alpha ---
if frq_sweep:
    al = [r["alpha"] for r in frq_sweep]
    atten = [r["out_amp"]/0.75 for r in frq_sweep]     # 1.0 = quasi-steady
    ph = [abs(r["out_phase_deg"]) for r in frq_sweep]
    ax2.plot(al, atten, "s-", color="#1f4e79", ms=7, lw=1.8, label="amplitude ratio (÷0.75)")
    ax2.set_xlabel("Womersley number  α"); ax2.set_ylabel("outlet-centreline amplitude ratio")
    ax2.set_ylim(0, 1.05); ax2.grid(alpha=.3)
    ax2.axhline(1.0, color="gray", ls=":", lw=0.9)
    axb = ax2.twinx()
    axb.plot(al, ph, "^--", color="#c0392b", ms=6, lw=1.4, label="|phase shift|")
    axb.set_ylabel("|phase shift|  [deg]", color="#c0392b")
    axb.tick_params(axis="y", colors="#c0392b")
    ax2.set_title("Frequency sweep (A=0.5): unsteadiness vs α")
    l1, la1 = ax2.get_legend_handles_labels(); l2, la2 = axb.get_legend_handles_labels()
    ax2.legend(l1+l2, la1+la2, fontsize=8, loc="lower left")

fig.suptitle("Oscillating-inlet sweeps (32k mesh, fp64)", fontsize=10)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(os.path.join(HERE, "inlet_sweeps.png"), dpi=140)
print("wrote inlet_sweeps.png")
if amp_sweep: print("amplitude sweep:", [(r["amp"], r["min_Ux"], r["backflow"]) for r in amp_sweep])
if frq_sweep: print("frequency sweep:", [(r["alpha"], round(r["out_amp"],3), r["out_phase_deg"]) for r in frq_sweep])

if __name__ == "__main__":
    pass
