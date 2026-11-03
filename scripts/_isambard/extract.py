#!/usr/bin/env python3
"""
Post-run metric + convergence extraction for an Isambard M5/M6 case.

Run AFTER the parallel solve has been reconstructed to a serial case
(`reconstructPar -latestTime` plus the previous write). Reuses the EXACT
extraction functions from the local driver (run_sweep.py) so the numbers are
computed identically to the local sweep, then applies the SAME strict gate
(field-wide max|dU| between the last two writes < 1e-6) and appends a row to
isambard/results_isambard.csv.

Usage:
    python3 extract.py M5
"""
import argparse, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from run_sweep import (MESHES, L, H, UMAX, CO_TARGET, DU_TOL,
                       steady_metrics, outlet_metrics, numeric_time_dirs)

CASES   = os.path.join(HERE, "cases")
RESULTS = os.path.join(HERE, "results_isambard.csv")
FIELDS  = ["label", "precision", "cells", "nx", "ny", "dt", "final_time",
           "converged", "dU_field_last_writes", "out_drift_pct",
           "U_peak_outlet", "U_centre_outlet", "U_mean_outlet",
           "err_max_pct_Umax", "err_L2_pct_Umax", "tau_w_over_rho"]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("label"); a = ap.parse_args()
    ny, nx = MESHES[a.label]["ny"], MESHES[a.label]["nx"]
    case = os.path.join(CASES, a.label)
    times = numeric_time_dirs(case)
    if len(times) < 2:
        sys.exit(f"{case}: need >=2 reconstructed time dirs (got {times}); "
                 f"run reconstructPar on the last two writes first.")
    dU, drift = steady_metrics(case, nx, ny)
    met = outlet_metrics(case, nx, ny)
    converged = dU < DU_TOL
    row = dict(label=a.label, precision="fp64", cells=nx*ny, nx=nx, ny=ny,
               dt=CO_TARGET*(L/nx)/UMAX, final_time=met["final_time"],
               converged=("yes" if converged else "NO"),
               dU_field_last_writes=dU, out_drift_pct=drift,
               U_peak_outlet=met["U_peak_outlet"], U_centre_outlet=met["U_centre_outlet"],
               U_mean_outlet=met["U_mean_outlet"], err_max_pct_Umax=met["err_max_pct_Umax"],
               err_L2_pct_Umax=met["err_L2_pct_Umax"], tau_w_over_rho=met["tau_w_over_rho"])
    new = not os.path.exists(RESULTS)
    with open(RESULTS, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        w.writerow(row)
    print(f"{a.label}: converged={row['converged']} at t={met['final_time']}s "
          f"(field dU={dU:.2e}, gate {DU_TOL:.0e}, output drift={drift:.5f}%)")
    print(f"  U_peak={met['U_peak_outlet']:.6f} err_max={met['err_max_pct_Umax']:.4f}% "
          f"tau_w={met['tau_w_over_rho']:.6f}")
    if not converged:
        print("  ** gate NOT met -> resubmit with a larger endTime (edit controlDict, "
              "restart from latestTime). Report as not-converged if it persists.")

if __name__ == "__main__":
    main()
