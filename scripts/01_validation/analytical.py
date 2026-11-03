#!/usr/bin/env python3
"""
Validation / reference curves for the 2D channel cases.

  1. Plane Poiseuille (steady)      -> validates the parabolic/developing case
  2. Planar Womersley (oscillatory) -> reference shape for the pulsatile case
  3. If an OpenFOAM solved field is given, overlays the simulated outlet
     profile on the analytical Poiseuille curve and reports the error.

Geometry / flow parameters (match the OpenFOAM case):
  H    = 0.1   m   channel height (walls at y=0 and y=H)
  h    = H/2       half-height
  nu   = 1e-3  m^2/s
  Umean= 1.0   m/s -> Umax = 1.5 (Poiseuille)
  f    = 1.0   Hz  -> omega = 2*pi,  Womersley alpha = h*sqrt(omega/nu) ~ 3.96

Usage:
  python3 analytical.py                      # analytical curves only
  python3 analytical.py /path/to/case 3      # overlay solved field at time '3'
"""
import sys, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- parameters (keep in sync with the OpenFOAM dictionaries) --------------
H, nu, Umean, f = 0.1, 1.0e-3, 1.0, 1.0
NX, NY = 200, 40                      # blockMesh cell counts
h     = H/2.0
Umax  = 1.5*Umean
omega = 2*np.pi*f
alpha = h*np.sqrt(omega/nu)

# ------------------------- 1. Poiseuille ------------------------------------
def poiseuille(y):
    """Steady plane-Poiseuille x-velocity, walls at y=0,H."""
    return Umax*4.0*y*(H - y)/H**2

# ------------------------- 2. Planar Womersley ------------------------------
def womersley(yc, phase, K=None):
    """Oscillatory channel velocity, yc in [-h, h] (centreline 0).
    Driven by -1/rho dp/dx = Re(K e^{i w t}). K chosen so the steady
    limit centreline velocity equals Umax (comparable amplitude)."""
    if K is None:
        K = Umax*2.0*nu/h**2          # steady-limit centreline -> Umax
    beta = np.sqrt(1j*omega/nu)
    u = (K/(1j*omega))*(1.0 - np.cosh(beta*yc)/np.cosh(beta*h))*np.exp(1j*phase)
    return np.real(u)

# ------------------- 3. read solved OpenFOAM Ux profile ---------------------
def read_outlet_profile(case, time):
    """Return (y_centres, Ux) for the last x-column of cells.
    NOTE: this is the OUTLET cell centre (x = (nx-0.5)/nx ~ 0.998 m), NOT x=0.9 m.
    An earlier version of the plot label said "x=0.9 m"; that was wrong and the
    error propagated into the progress document.
    Cell ordering from blockMesh is x-fastest: idx = j*NX + i (k=0)."""
    txt = open(f"{case}/{time}/U").read()
    body = txt.split("internalField")[1]
    vecs = re.findall(r"\(([-\d.eE+ ]+)\)", body.split("(",1)[1])
    ux = np.array([float(v.split()[0]) for v in vecs[:NX*NY]])
    dy = H/NY
    yj = (np.arange(NY)+0.5)*dy
    col = ux[np.arange(NY)*NX + (NX-1)]   # i = NX-1 (outlet column)
    return yj, col

# ------------------------------ plots ---------------------------------------
print(f"Womersley number alpha = {alpha:.2f}")

# Figure 1: Poiseuille (+ optional simulated overlay)
y = np.linspace(0, H, 200)
fig, ax = plt.subplots(figsize=(5.2, 4.2))
ax.plot(poiseuille(y), y*1e3, 'k-', lw=2, label="Analytical Poiseuille")
sim_err = None
if len(sys.argv) >= 3:
    yj, col = read_outlet_profile(sys.argv[1], sys.argv[2])
    ax.plot(col, yj*1e3, 'o', ms=4, color="#c0392b",
            label="OpenFOAM (outlet cell column, x$\\approx$0.998 m)")
    sim_err = np.max(np.abs(col - poiseuille(yj)))/Umax*100
    np.savetxt("openfoam_outlet_profile.csv",
               np.column_stack([yj, col, poiseuille(yj)]),
               header="y[m],Ux_sim[m/s],Ux_analytical[m/s]", delimiter=",")
ax.set_xlabel("U$_x$  [m/s]"); ax.set_ylabel("y  [mm]")
ax.set_title("Steady channel: Poiseuille validation")
ax.legend(fontsize=8); ax.grid(alpha=.3); fig.tight_layout()
fig.savefig("poiseuille.png", dpi=130)

# Figure 2: Womersley profile evolution over a cycle
yc = np.linspace(-h, h, 200)
fig, ax = plt.subplots(figsize=(5.2, 4.2))
for deg in (0, 45, 90, 135, 180):
    ax.plot(womersley(yc, np.deg2rad(deg)), (yc+h)*1e3,
            label=f"$\\omega t$={deg}°")
ax.set_xlabel("U$_x$  [m/s]"); ax.set_ylabel("y  [mm]")
ax.set_title(f"Pulsatile reference: planar Womersley ($\\alpha$={alpha:.1f})")
ax.legend(fontsize=8); ax.grid(alpha=.3); fig.tight_layout()
fig.savefig("womersley.png", dpi=130)
np.savetxt("womersley_phases.csv",
           np.column_stack([(yc+h)] + [womersley(yc, np.deg2rad(d))
                                       for d in (0,45,90,135,180)]),
           header="y[m],wt0,wt45,wt90,wt135,wt180", delimiter=",")

print("Wrote poiseuille.png, womersley.png, womersley_phases.csv")
if sim_err is not None:
    print(f"Max outlet-profile error vs Poiseuille: {sim_err:.2f}% of Umax")
    print("Wrote openfoam_outlet_profile.csv")
