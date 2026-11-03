#!/usr/bin/env bash
# Two remaining runs:
#  (a) PCG under the FULL timing protocol (3 alternating sequential repeats)
#  (b) one coarser mesh point for the GAMG fp32/fp64 comparison
cd "$(dirname "$0")"   # run from the study working folder (see scripts/README.md)
echo "=== (a) PCG, 3 repeats each, alternating, sequential ==="
for r in 1 2 3; do
  python3 run_case.py --label "p2_fp64_r$r" --precision fp64ctl --psolver PCG --steps 512 --ptol 1e-4
  python3 run_case.py --label "p2_fp32_r$r" --precision fp32    --psolver PCG --steps 512 --ptol 1e-4
done
echo "=== (b) coarser mesh: 256x64 = 16,384 cells, GAMG, 3 repeats each ==="
sed -i '' 's/^NX, NY = 512, 128.*/NX, NY = 256, 64               # coarser binary-exact point/' run_case.py
sed -i '' 's/^DT   = 0.00048828125.*/DT   = 0.0009765625         # 2^-10 -> Co = 0.375 on nx=256/' run_case.py
for r in 1 2 3; do
  python3 run_case.py --label "m16k_fp64_r$r" --precision fp64ctl --steps 512 --ptol 1e-4
  python3 run_case.py --label "m16k_fp32_r$r" --precision fp32    --steps 512 --ptol 1e-4
done
# restore the working mesh constants
sed -i '' 's/^NX, NY = 256, 64.*/NX, NY = 512, 128              # powers of two -> binary-exact spacings/' run_case.py
sed -i '' 's/^DT   = 0.0009765625.*/DT   = 0.00048828125        # 2^-11 -> Co = 0.375 on nx=512/' run_case.py
echo "GAPS CLOSED $(date)"
