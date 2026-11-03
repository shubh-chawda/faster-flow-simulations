#!/usr/bin/env python3
"""
Prepare an M5/M6 case for a PARALLEL run on Isambard.

Generates cases/<label>/ from ../template with the SAME numerics as the local
fp64 sweep (GAMG on p, dt = 0.2/nx so Co~0.30, identical schemes/tolerances),
sets a generous fixed endTime, and drops in a decomposeParDict for domain
decomposition. The strict convergence gate (field-wide max|dU| between successive
0.5 s writes < 1e-6 m/s) is verified POST-RUN by extract.py -- so the physics is
identical to the local runs; only the platform and the serial->parallel split
differ (which must not change the answer -- that is exactly what the
cross-platform consistency check confirms; see README).

endTime default = 10 s: informed by the local M4 (512k), which needed ~t=7.5 s to
reach the 1e-6 field-wide gate. 10 s gives margin; extract.py reports the dU
actually achieved, and if a mesh has not met the gate by 10 s you resubmit with a
larger endTime (the same steady-state stopping logic, batched).

Usage (on Isambard, after `module load <openfoam>`):
    python3 prep.py M5 --ncores 144
    python3 prep.py M6 --ncores 288 --endTime 12
"""
import argparse, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # import the local driver
from run_sweep import MESHES, L, H, UMAX, CO_TARGET

TEMPLATE = os.path.join(os.path.dirname(HERE), "template")
CASES    = os.path.join(HERE, "cases")

DECOMPOSE = """/*--------------------------------*- C++ -*----------------------------------*/
FoamFile {{ version 2.0; format ascii; class dictionary; object decomposeParDict; }}
numberOfSubdomains {ncores};
method          scotch;   // topology-based; no geometric hints needed
// ************************************************************************* //
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label", choices=[k for k in MESHES if k in ("M5", "M6")])
    ap.add_argument("--ncores", type=int, required=True,
                    help="numberOfSubdomains == MPI ranks (confirm node size with the group)")
    ap.add_argument("--endTime", type=float, default=10.0)
    ap.add_argument("--writeInterval", type=float, default=0.5)
    a = ap.parse_args()

    ny, nx = MESHES[a.label]["ny"], MESHES[a.label]["nx"]
    dx = L / nx
    dt = CO_TARGET * dx / UMAX                       # = 0.2/nx, identical to local
    os.makedirs(CASES, exist_ok=True)
    case = os.path.join(CASES, a.label)
    if os.path.exists(case): shutil.rmtree(case)
    shutil.copytree(TEMPLATE, case)

    subs = {"__NX__": str(nx), "__NY__": str(ny), "__DELTAT__": repr(dt),
            "__ENDTIME__": repr(a.endTime), "__WRITEINTERVAL__": repr(a.writeInterval),
            "__PURGE__": "4"}
    for rel in ("system/blockMeshDict", "system/controlDict"):
        p = os.path.join(case, rel); s = open(p).read()
        for k, v in subs.items(): s = s.replace(k, v)
        open(p, "w").write(s)
    open(os.path.join(case, "system/decomposeParDict"), "w").write(
        DECOMPOSE.format(ncores=a.ncores))

    print(f"prepared {case}: {nx}x{ny} = {nx*ny:,} cells, dt={dt:.3e}, "
          f"endTime={a.endTime}s, {a.ncores} subdomains")
    print("next: sbatch submit.slurm   (edit placeholders first)")

if __name__ == "__main__":
    main()
