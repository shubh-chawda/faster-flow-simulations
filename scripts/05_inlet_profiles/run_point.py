#!/usr/bin/env python3
"""Run ONE oscillating-inlet sweep point (amplitude A, frequency f) on the 32k
mesh and record: min Ux over the established cycles (backflow indicator) and the
outlet-centreline amplitude/mean/phase. Function objects supply both, so no heavy
field writes. Cases live in sweep/cases/<label>.  Usage:
    python3 run_point.py --label A050 --amp 0.5 --freq 1
"""
import argparse, csv, os, re, shutil, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template")
CASES = os.path.join(HERE, "cases")
RESULTS = os.path.join(HERE, "sweep_results.csv")
OF = "/Applications/OpenFOAM-v2512.app/Contents/Resources/etc/openfoam"
L, H, NU = 1.0, 0.1, 1.0e-3
ESTABLISH = 3.0                      # s of startup transient to discard
FIELDS = ["label", "nx", "amp", "freq", "alpha", "dt", "endTime",
          "min_Ux", "backflow", "out_mean", "out_amp", "out_phase_deg"]

def gen(label, amp, freq, nx):
    dx = L / nx
    dt = 0.3 * dx / (1.5 * (1 + amp))          # Co<=0.3 vs quasi-steady peak 1.5(1+A)
    endTime = round(ESTABLISH + 3.0 / freq, 4) # startup + 3 periods
    case = os.path.join(CASES, label)
    if os.path.exists(case): shutil.rmtree(case)
    shutil.copytree(TEMPLATE, case)
    ny = nx // 5                                # aspect ratio 2
    # replace ONLY the cell-count tuple (template is 400x80); leave simpleGrading (1 1 1)
    bm = os.path.join(case, "system/blockMeshDict"); s = open(bm).read()
    s = s.replace("(400 80 1)", f"({nx} {ny} 1)"); open(bm, "w").write(s)
    subs = {"__AMP__": repr(amp), "__FREQ__": repr(freq),
            "__DELTAT__": repr(dt), "__ENDTIME__": repr(endTime)}
    for rel in ("0/U", "system/controlDict"):
        p = os.path.join(case, rel); s = open(p).read()
        for k, v in subs.items(): s = s.replace(k, v)
        open(p, "w").write(s)
    return case, dt, endTime

def run(case):
    subprocess.run([OF, "bash", "-c",
                    f"cd '{case}' && blockMesh > log.blockMesh 2>&1 && "
                    f"icoFoam > log.icoFoam 2>&1"], capture_output=True, text=True)

def min_ux(case):
    """Minimum Ux over t >= ESTABLISH from fieldMinMax (min vector = 3rd column)."""
    f = None
    for root, _, files in os.walk(os.path.join(case, "postProcessing", "minMaxU")):
        for fn in files:
            if fn.endswith(".dat"): f = os.path.join(root, fn)
    if not f: return float("nan")
    m = 1e9
    for line in open(f):
        if line.startswith("#"): continue
        parts = line.split("\t")
        try: t = float(parts[0])
        except (ValueError, IndexError): continue
        if t < ESTABLISH: continue
        mvec = re.search(r"\(([-\deE.+]+)", parts[2])   # first component of min vector
        if mvec: m = min(m, float(mvec.group(1)))
    return m

def outlet_response(case, freq, endTime):
    """Fit outlet-centreline Ux over the last 2 periods -> amp, mean, phase."""
    f = None
    for root, _, files in os.walk(os.path.join(case, "postProcessing", "outletProbe")):
        if "U" in files: f = os.path.join(root, "U")
    if not f: return (float("nan"),) * 3
    t, u = [], []
    for line in open(f):
        if line.startswith("#"): continue
        mm = re.match(r"\s*([-\deE.+]+)\s+\(([-\deE.+]+)", line)
        if mm: t.append(float(mm.group(1))); u.append(float(mm.group(2)))
    t, u = np.array(t), np.array(u)
    mask = t >= endTime - 2.0 / freq
    if mask.sum() < 8: return (float("nan"),) * 3
    tt, uu = t[mask], u[mask]; w = 2 * np.pi * freq
    A, B, C = np.linalg.lstsq(np.column_stack([np.sin(w*tt), np.cos(w*tt),
                                               np.ones_like(tt)]), uu, rcond=None)[0]
    amp = float(np.hypot(A, B))
    phase = float((np.degrees(np.arctan2(B, A)) + 180) % 360 - 180)   # signed deg
    return float(C), amp, phase

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--amp", type=float, required=True)
    ap.add_argument("--freq", type=float, required=True)
    ap.add_argument("--nx", type=int, default=400)
    a = ap.parse_args()
    case, dt, endTime = gen(a.label, a.amp, a.freq, a.nx)
    run(case)
    mu = min_ux(case)
    mean, amp, phase = outlet_response(case, a.freq, endTime)
    alpha = (H/2) * np.sqrt(2*np.pi*a.freq / NU)
    row = dict(label=a.label, nx=a.nx, amp=a.amp, freq=a.freq, alpha=round(alpha, 3),
               dt=dt, endTime=endTime, min_Ux=round(mu, 5),
               backflow=("yes" if mu < -1e-3 else "no"),
               out_mean=round(mean, 4), out_amp=round(amp, 4),
               out_phase_deg=round(phase, 1))
    new = not os.path.exists(RESULTS)
    with open(RESULTS, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new: w.writeheader()
        w.writerow(row)
    print(f"{a.label}: A={a.amp} f={a.freq} alpha={alpha:.2f} min_Ux={mu:+.4f} "
          f"[{row['backflow']}] out_amp={amp:.3f} phase={phase:+.1f}deg")

if __name__ == "__main__":
    main()
