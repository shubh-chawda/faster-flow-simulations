#!/usr/bin/env python3
"""Pack solved OpenFOAM velocity fields into small .npz files under data/fields/.

The solved cases are far too big to commit (each U file is 2-4 MB of ASCII and the
oscillating-inlet run wrote 120 of them), so this keeps only what the figures and
the checks in tools/verify_results.py need:

  steady_512x128.npz   uniform inlet, t = 2.5 s, 65,536 cells (fp64 accuracy run)
  skewed_800x160.npz   skewed inlet,  t = 2.5 s, 128,000 cells
  sine_800x160.npz     oscillating inlet, one full cycle t = 5.00 ... 5.95 s

Usage:
  python3 tools/extract_fields.py --steady <case>/2.5/U \
      --skewed <case>/2.5/U --sine-dir <sine_case> [--out data/fields]

Cell ordering: blockMesh numbers cells x-fastest, so the internalField list
reshapes directly to (ny, nx) with row 0 at the bottom wall.
"""
import argparse, os, re
import numpy as np


def read_U(path):
    """Return (ux, uy) as float64 arrays from an ASCII volVectorField."""
    txt = open(path).read()
    body = txt.split("internalField", 1)[1].split("boundaryField", 1)[0]
    n = int(re.search(r"\n(\d+)\s*\n\(", body).group(1))
    nums = re.findall(r"\(([-\d.eE+]+)\s+([-\d.eE+]+)\s+[-\d.eE+]+\)", body)
    assert len(nums) == n, f"{path}: expected {n} vectors, got {len(nums)}"
    a = np.array(nums, dtype=float)
    return a[:, 0], a[:, 1]


def grid(path, nx, ny):
    ux, uy = read_U(path)
    return ux.reshape(ny, nx), uy.reshape(ny, nx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steady"); ap.add_argument("--skewed"); ap.add_argument("--sine-dir")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "fields"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    if a.steady:
        ux, uy = grid(a.steady, 512, 128)
        np.savez_compressed(os.path.join(a.out, "steady_512x128.npz"),
                            ux=ux.astype(np.float32), uy=uy.astype(np.float32),
                            L=1.0, H=0.1, t=2.5)
    if a.skewed:
        ux, uy = grid(a.skewed, 800, 160)
        np.savez_compressed(os.path.join(a.out, "skewed_800x160.npz"),
                            ux=ux.astype(np.float32), uy=uy.astype(np.float32),
                            L=1.0, H=0.1, t=2.5)
    if a.sine_dir:
        times = [f"{5 + 0.05 * k:.2f}".rstrip("0").rstrip(".") for k in range(20)]
        frames = [grid(os.path.join(a.sine_dir, t, "U"), 800, 160)[0] for t in times]
        np.savez_compressed(os.path.join(a.out, "sine_800x160.npz"),
                            ux=np.stack(frames).astype(np.float16),
                            t=np.array([float(t) for t in times]), L=1.0, H=0.1)
    print("wrote", sorted(os.listdir(a.out)))


if __name__ == "__main__":
    main()
