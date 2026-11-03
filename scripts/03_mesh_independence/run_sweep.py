#!/usr/bin/env python3
"""
Mesh-independence sweep driver (fp64).  Faster Flow Simulations.

ONE convergence criterion, declared here, applied identically to every run:

    STEADY STATE  <=>  field-wide max|dU| between the two most recent 0.5 s
    write intervals  <  DU_TOL (= 1e-6 m/s).

This is implemented as an actual STEADY-STATE STOPPING CONDITION, not a fixed
end time: each mesh is advanced in chunks and keeps running until the
criterion is met, or until MAX_ENDTIME is reached (in which case it is recorded
as NOT converged and reported as such -- never loosened to make it pass).

The field-wide dU is the gate.  The per-step pressure/velocity initial residuals
and the outlet-output drift are recorded as DIAGNOSTICS only (reported alongside,
never gating).  There is exactly one definition of "converged" in this codebase;
analyse.py reads it from results.csv and does not recompute it.

Physics is fixed: L=1, H=0.1, nu=1e-3, uniform inlet U=(1 0 0),
Umean=1 -> Umax=1.5, Re_H=100.  Timestep set so dt = 0.2/nx (=> Co ~ 0.30, though
the realised Co_max drifts up mildly on finer meshes -- see the CSV / summary).

Usage:
  python3 run_sweep.py M0 M1 M2 M3 M4      # run these labels to steady state
  python3 run_sweep.py --max-endTime 15 M6 # raise the safety cap for a mesh
  python3 run_sweep.py --list
"""
import argparse, csv, os, re, shutil, subprocess, sys, time
import numpy as np

# ---- fixed geometry / physics (must match the template dictionaries) -------
L, H, W = 1.0, 0.1, 0.01
NU       = 1.0e-3
UMEAN    = 1.0
UMAX     = 1.5
CO_TARGET = 0.30                   # dt = Co*dx/Umax = 0.2/nx (nominal)

# ---- THE convergence criterion (declared once) -----------------------------
DU_TOL         = 1.0e-6            # field-wide max|dU| between successive writes
WRITE_INTERVAL = 0.5              # s; the window over which dU is measured
INIT_ENDTIME   = 2.5              # s; first chunk (past the 8k baseline's SS)
CHUNK          = 2.5              # s; extension per iteration if not yet steady
MAX_ENDTIME    = 10.0            # s; safety cap (overridable per run)
PURGE          = 2               # keep only the last 2 writes (disk)

HERE     = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template")
CASES    = os.path.join(HERE, "cases")
RESULTS  = os.path.join(HERE, "results.csv")
OF_LAUNCH = os.environ.get("FOAM_LAUNCH", "/Applications/OpenFOAM-v2512.app/Contents/Resources/etc/openfoam")
SP_BASHRC = os.environ.get("FOAM_SP_BASHRC", "/Volumes/OpenFOAM-SP/OpenFOAM-v2512-SP/etc/bashrc")   # single-precision build
# Precision is a whole-library compile-time setting, so fp32 means a different
# icoFoam binary. The MESH is precision-independent, so blockMesh/checkMesh always
# run under the DP build; only the SOLVER switches. Set in main().
PRECISION = "fp64"
PTOL = "1e-06"            # pressure-solver tolerance (fp32 floors ~2e-5; relax for it)

# ---- mesh series: aspect ratio 2 => nx = 5*ny ---------------------
MESHES = {
    "M0": dict(ny=40,  nx=200),    # baseline, 8k
    "M1": dict(ny=80,  nx=400),    # 32k
    "M2": dict(ny=160, nx=800),    # 128k
    "M3": dict(ny=240, nx=1200),   # 288k
    "M4": dict(ny=320, nx=1600),   # 512k
    "M5": dict(ny=448, nx=2240),   # ~1.00M
    "M6": dict(ny=632, nx=3160),   # ~2.00M
}

CSV_FIELDS = [
    "label", "precision", "p_tol", "cells", "nx", "ny", "dx", "dy", "aspect_ratio",
    "dt", "final_time", "n_steps", "n_chunks", "Co_max",
    "U_peak_outlet", "U_centre_outlet", "U_mean_outlet",
    "err_max_pct_Umax", "err_L2_pct_Umax", "tau_w_over_rho",
    "converged", "dU_field_last_writes", "out_drift_pct",
    "p_init_res_final", "U_init_res_final",
    "gamg_iters_p", "exec_time_s", "s_per_step", "wall_time_s",
    "checkMesh_ok",
]

# ---------------------------------------------------------------------------
def poiseuille(y):
    return UMAX * 4.0 * y * (H - y) / H**2

def _parse_field(path, ncomp):
    """Parse an OpenFOAM ascii internal field; returns (N, ncomp) or (N,)."""
    txt = open(path).read()
    body = txt.split("internalField", 1)[1].split("boundaryField", 1)[0]
    if ncomp == 3:
        tup = re.findall(r"\(\s*([-\deE.+]+)\s+([-\deE.+]+)\s+([-\deE.+]+)\s*\)", body)
        return np.array(tup, dtype=float)
    tup = re.findall(r"\(\s*([-\deE.+]+)\s+[-\deE.+]+\s+[-\deE.+]+\s*\)", body)
    return np.array(tup, dtype=float)

def read_U(path, ncells):
    arr = _parse_field(path, 3)[:ncells]
    if arr.shape != (ncells, 3):
        raise RuntimeError(f"parsed {arr.shape} vs ({ncells},3) from {path}")
    return arr

def read_ux(path, ncells):
    ux = _parse_field(path, 1)[:ncells]
    if ux.size != ncells:
        raise RuntimeError(f"parsed {ux.size} vs {ncells} from {path}")
    return ux

def numeric_time_dirs(case):
    ts = []
    for d in os.listdir(case):
        try: ts.append((float(d), d))
        except ValueError: pass
    return [name for _, name in sorted(ts)]

def steady_metrics(case, nx, ny):
    """From the last two writes: (field-wide max|dU|, %drift of outlet U_peak)."""
    times = numeric_time_dirs(case)
    if len(times) < 2:
        return float("nan"), float("nan")
    nc = nx * ny
    u0 = read_U(os.path.join(case, times[-2], "U"), nc)
    u1 = read_U(os.path.join(case, times[-1], "U"), nc)
    dU = float(np.linalg.norm(u1 - u0, axis=1).max())
    col0 = u0[np.arange(ny) * nx + (nx - 1), 0]
    col1 = u1[np.arange(ny) * nx + (nx - 1), 0]
    drift = abs(col1.max() - col0.max()) / abs(col1.max()) * 100.0
    return dU, drift

def outlet_metrics(case, nx, ny):
    """Outlet metrics from the outlet cell column at the latest time."""
    final = numeric_time_dirs(case)[-1]
    ux = read_ux(os.path.join(case, final, "U"), nx * ny)
    dy = H / ny
    yj = (np.arange(ny) + 0.5) * dy
    col = ux[np.arange(ny) * nx + (nx - 1)]
    uana = poiseuille(yj)
    dudy_wall = 0.5 * (col[0] + col[-1]) / (0.5 * dy)
    return dict(
        U_peak_outlet=float(col.max()),
        U_centre_outlet=float(0.5 * (col[ny // 2 - 1] + col[ny // 2])),
        U_mean_outlet=float(col.mean()),
        err_max_pct_Umax=float(np.abs(col - uana).max() / UMAX * 100.0),
        err_L2_pct_Umax=float(np.sqrt(np.mean((col - uana) ** 2)) / UMAX * 100.0),
        tau_w_over_rho=float(NU * dudy_wall),
        final_time=final)

def parse_log(logfile):
    txt = open(logfile).read()
    chunks = txt.split("\nTime = ")
    n_steps = len(chunks) - 1
    last = chunks[-1] if n_steps else ""
    def first(pat, s):
        m = re.search(pat, s); return float(m.group(1)) if m else float("nan")
    p_res = first(r"Solving for p,\s*Initial residual = ([-\deE.+]+)", last)
    U_res = first(r"Solving for Ux,\s*Initial residual = ([-\deE.+]+)", last)
    m = re.search(r"Solving for p,.*?No Iterations (\d+)", last)
    gamg = int(m.group(1)) if m else -1
    co = first(r"Courant Number mean: [-\deE.+]+ max: ([-\deE.+]+)",
               txt[txt.rfind("Courant Number"):])
    et = first(r"ExecutionTime = ([-\deE.+]+) s", txt[txt.rfind("ExecutionTime"):])
    return dict(n_steps=n_steps, Co_max=co, p_init_res_final=p_res,
                U_init_res_final=U_res, gamg_iters_p=gamg, exec_time_s=et)

# ---------------------------------------------------------------------------
def gen_case(label):
    ny, nx = MESHES[label]["ny"], MESHES[label]["nx"]
    dx, dy = L / nx, H / ny
    dt = CO_TARGET * dx / UMAX
    case = os.path.join(CASES, label if PRECISION == "fp64" else f"{label}_{PRECISION}")
    if os.path.exists(case):
        shutil.rmtree(case)
    shutil.copytree(TEMPLATE, case)
    subs = {"__NX__": str(nx), "__NY__": str(ny), "__DELTAT__": repr(dt),
            "__ENDTIME__": repr(INIT_ENDTIME), "__PTOL__": str(PTOL),
            "__WRITEINTERVAL__": repr(WRITE_INTERVAL), "__PURGE__": str(PURGE)}
    for rel in ("system/blockMeshDict", "system/controlDict", "system/fvSolution"):
        p = os.path.join(case, rel); s = open(p).read()
        for k, v in subs.items():
            s = s.replace(k, v)
        open(p, "w").write(s)
    return case, nx, ny, dx, dy, dt

def set_control(case, start_from, end_time):
    p = os.path.join(case, "system/controlDict"); s = open(p).read()
    s = re.sub(r"startFrom\s+\w+;", f"startFrom       {start_from};", s)
    s = re.sub(r"endTime\s+[-\deE.+]+;", f"endTime         {end_time!r};", s)
    open(p, "w").write(s)

def of(case, script, engine="dp"):
    """Run an OpenFOAM command. engine 'dp' = the app's double-precision build;
    'sp' = the single-precision build (sourced from its own bashrc)."""
    if engine == "sp":
        full = ["bash", "-c", f"source '{SP_BASHRC}' && cd '{case}' && {script}"]
    else:
        full = [OF_LAUNCH, "bash", "-c", f"cd '{case}' && {script}"]
    return subprocess.run(full, capture_output=True, text=True).returncode

def check_mesh_ok(case):
    try: return "Mesh OK." in open(os.path.join(case, "log.checkMesh")).read()
    except FileNotFoundError: return False

def prune_times(case):
    """Keep only '0' and the latest time dir (the restart point) between chunks,
    so long multi-chunk runs on fine meshes don't accumulate field sets."""
    times = numeric_time_dirs(case)
    for t in times[:-1]:
        if t != "0":
            shutil.rmtree(os.path.join(case, t), ignore_errors=True)

def append_row(row):
    new = not os.path.exists(RESULTS)
    with open(RESULTS, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new: w.writeheader()
        w.writerow(row)

# ---------------------------------------------------------------------------
def run_label(label, max_endTime):
    ny, nx = MESHES[label]["ny"], MESHES[label]["nx"]
    print(f"\n=== {label}: {nx}x{ny} = {nx*ny:,} cells [{PRECISION}] ===", flush=True)
    case, nx, ny, dx, dy, dt = gen_case(label)
    print(f"    dx={dx:.3e} dy={dy:.3e} AR={dx/dy:.2f} dt={dt:.3e}", flush=True)
    # mesh is precision-independent -> always generate with the DP build
    of(case, "blockMesh > log.blockMesh 2>&1 && checkMesh > log.checkMesh 2>&1", "dp")
    mok = check_mesh_ok(case)
    solver_engine = "sp" if PRECISION == "fp32" else "dp"

    # --- steady-state stopping loop -------------------------------------
    t0 = time.time()
    endT, n_chunks, tot_exec, tot_steps = INIT_ENDTIME, 0, 0.0, 0
    logm = {}
    while True:
        if n_chunks > 0:
            prune_times(case)
            set_control(case, "latestTime", endT)
        log = f"log.icoFoam.{endT:g}"
        of(case, f"icoFoam > {log} 2>&1", solver_engine)
        logm = parse_log(os.path.join(case, log))
        tot_exec += logm["exec_time_s"] if logm["exec_time_s"] == logm["exec_time_s"] else 0
        tot_steps += logm["n_steps"]; n_chunks += 1
        dU, drift = steady_metrics(case, nx, ny)
        print(f"    t={endT:g}s: field dU={dU:.2e}, U_peak drift={drift:.5f}% "
              f"(chunk {n_chunks}, +{logm['n_steps']} steps)", flush=True)
        if dU < DU_TOL or endT >= max_endTime:
            converged = dU < DU_TOL
            break
        endT = round(min(endT + CHUNK, max_endTime), 6)
    wall = time.time() - t0

    met = outlet_metrics(case, nx, ny)
    s_per_step = tot_exec / tot_steps if tot_steps else float("nan")
    row = dict(
        label=label, precision=PRECISION, p_tol=PTOL, cells=nx * ny, nx=nx, ny=ny,
        dx=dx, dy=dy, aspect_ratio=dx / dy, dt=dt,
        final_time=met["final_time"], n_steps=tot_steps, n_chunks=n_chunks,
        Co_max=logm["Co_max"], U_peak_outlet=met["U_peak_outlet"],
        U_centre_outlet=met["U_centre_outlet"], U_mean_outlet=met["U_mean_outlet"],
        err_max_pct_Umax=met["err_max_pct_Umax"], err_L2_pct_Umax=met["err_L2_pct_Umax"],
        tau_w_over_rho=met["tau_w_over_rho"],
        converged=("yes" if converged else "NO"),
        dU_field_last_writes=dU, out_drift_pct=drift,
        p_init_res_final=logm["p_init_res_final"], U_init_res_final=logm["U_init_res_final"],
        gamg_iters_p=logm["gamg_iters_p"], exec_time_s=round(tot_exec, 1),
        s_per_step=s_per_step, wall_time_s=round(wall, 1),
        checkMesh_ok=("yes" if mok else "NO"))
    append_row(row)
    print(f"    -> converged={row['converged']} at t={met['final_time']}s "
          f"(field dU={dU:.2e}, gate {DU_TOL:.0e}); U_peak={met['U_peak_outlet']:.6f} "
          f"err_max={met['err_max_pct_Umax']:.4f}% tau_w={met['tau_w_over_rho']:.6f} "
          f"Co_max={logm['Co_max']:.3f}", flush=True)
    print(f"    exec={tot_exec:.0f}s ({s_per_step:.3f}s/step, {n_chunks} chunks) "
          f"meshOK={row['checkMesh_ok']}", flush=True)
    return row

def main():
    global PRECISION, PTOL, RESULTS
    ap = argparse.ArgumentParser()
    ap.add_argument("labels", nargs="*")
    ap.add_argument("--max-endTime", type=float, default=MAX_ENDTIME)
    ap.add_argument("--precision", choices=["fp64", "fp32"], default="fp64")
    ap.add_argument("--ptol", default="1e-06", help="pressure-solver tolerance")
    ap.add_argument("--results-file", default="results.csv")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    PRECISION = a.precision
    PTOL = a.ptol
    RESULTS = os.path.join(HERE, a.results_file)
    if a.list or not a.labels:
        print(f"{'label':6}{'nx':>6}{'ny':>6}{'cells':>12}{'dt=0.2/nx':>14}")
        for k, v in MESHES.items():
            print(f"{k:6}{v['nx']:>6}{v['ny']:>6}{v['nx']*v['ny']:>12,}{0.2/v['nx']:>14.3e}")
        return
    os.makedirs(CASES, exist_ok=True)
    for label in a.labels:
        if label not in MESHES:
            print(f"unknown label {label}"); continue
        run_label(label, a.max_endTime)

if __name__ == "__main__":
    main()
