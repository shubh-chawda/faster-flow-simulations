#!/usr/bin/env bash
# MASTER PROTOCOL — stated up front, applied identically to both precisions.
#   mesh 512x128 = 65,536 cells, binary-exact (dx=2^-9, dt=2^-11, Co_nominal=0.375)
#   ptol 1e-4  : the tightest tolerance BOTH precisions meet at this size
#                (fp32 floors ~5e-5 here; at 262k its floor is 1.7e-4 and it cannot)
#   strictly SEQUENTIAL, never concurrent.
cd "$(dirname "$0")"   # run from the study working folder (see scripts/README.md)
echo "=== [1/3] TIMING+MEMORY: GAMG, 512 steps, 3 repeats, alternating ==="
for r in 1 2 3; do
  python3 run_case.py --label "t_fp64_r$r" --precision fp64 --steps 512 --ptol 1e-4
  python3 run_case.py --label "t_fp32_r$r" --precision fp32 --steps 512 --ptol 1e-4
done
echo "=== [2/3] ACCURACY: run to steady state (t=2.5) ==="
python3 run_case.py --label acc_fp64 --precision fp64 --endTime 2.5 --ptol 1e-4 --keep
python3 run_case.py --label acc_fp32 --precision fp32 --endTime 2.5 --ptol 1e-4 --keep
echo "=== [3/3] PCG at reduced precision, 512 steps, 2 repeats ==="
for r in 1 2; do
  python3 run_case.py --label "pcg_fp64_r$r" --precision fp64 --psolver PCG --steps 512 --ptol 1e-4
  python3 run_case.py --label "pcg_fp32_r$r" --precision fp32 --psolver PCG --steps 512 --ptol 1e-4
done
echo "ALL FINAL RUNS COMPLETE $(date)"
