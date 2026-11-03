#!/usr/bin/env bash
cd "$(dirname "$0")"   # run from the study working folder (see scripts/README.md)
while pgrep -f run_all_final >/dev/null 2>&1; do sleep 15; done
echo "=== protocol finished; starting DP control build $(date) ==="
./build_dp_control.sh > build_dp.log 2>&1 || { echo "CONTROL BUILD FAILED"; tail -20 build_dp.log; exit 1; }
echo "=== control build ok; re-timing fp32 vs locally-built fp64 ==="
for r in 1 2 3; do
  python3 run_case.py --label "c_fp64ctl_r$r" --precision fp64ctl --steps 512 --ptol 1e-4
  python3 run_case.py --label "c_fp32_r$r"    --precision fp32    --steps 512 --ptol 1e-4
done
echo "CONTROL COMPARISON DONE $(date)"
