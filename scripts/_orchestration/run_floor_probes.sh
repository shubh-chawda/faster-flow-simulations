#!/usr/bin/env bash
# Measure the fp32 pressure-residual FLOOR identically on three binary-exact meshes.
# ptol 1e-8 is deliberately unreachable, so GAMG runs to its iteration cap and the
# final residual it settles at IS the floor. Same solver, same protocol, fp32 only.
cd "$(dirname "$0")"   # run from the study working folder (see scripts/README.md)
while pgrep -f run_gaps >/dev/null 2>&1; do sleep 20; done
echo "=== floor probes (ptol 1e-8, binary-exact, fp32) ==="
probe () {  # $1=label $2=nx $3=ny $4=dt
  sed -i '' "s/^NX, NY = .*/NX, NY = $2, $3/" run_case.py
  sed -i '' "s/^DT   = .*/DT   = $4/" run_case.py
  python3 run_case.py --label "$1" --precision fp32 --steps 40 --ptol 1e-8
}
probe floor_16k  256  64  0.0009765625
probe floor_65k  512 128  0.00048828125
probe floor_262k 1024 256 0.000244140625
# also a DP reference at the largest mesh, same probe, to show fp64 has no such floor
sed -i '' "s/^NX, NY = .*/NX, NY = 1024, 256/" run_case.py
sed -i '' "s/^DT   = .*/DT   = 0.000244140625/" run_case.py
python3 run_case.py --label floor_262k_fp64 --precision fp64ctl --steps 40 --ptol 1e-8
# restore working-mesh constants
sed -i '' "s/^NX, NY = .*/NX, NY = 512, 128              # powers of two -> binary-exact spacings/" run_case.py
sed -i '' "s/^DT   = .*/DT   = 0.00048828125        # 2^-11 -> Co = 0.375 on nx=512/" run_case.py
echo "FLOOR PROBES DONE $(date)"
