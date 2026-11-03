#!/usr/bin/env bash
# Let b262k_fp32_r1 and b262k_fp64_r2 finish, then stop before the second
# (49-minute) fp32 repeat. Yields fp64 n=2, fp32 n=1 -- stated explicitly.
cd "$(dirname "$0")"   # run from the study working folder (see scripts/README.md)
while :; do
  if grep -q "b262k_fp64_r2" results_final.csv 2>/dev/null; then
    sleep 3
    pkill -f run_262k.sh; pkill -x icoFoam; pkill -f "run_case.py --label b262k_fp32_r2"
    # restore working-mesh constants that run_262k.sh would have restored
    sed -i '' "s/^NX, NY = .*/NX, NY = 512, 128              # powers of two -> binary-exact spacings/" run_case.py
    sed -i '' "s/^DT   = .*/DT   = 0.00048828125        # 2^-11 -> Co = 0.375 on nx=512/" run_case.py
    rm -rf cases/b262k_fp32_r2
    echo "STOPPED after fp64_r2 (fp32 n=1, fp64 n=2) at $(date)"
    break
  fi
  sleep 20
done
