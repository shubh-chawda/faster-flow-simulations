#!/usr/bin/env bash
# 262,144-cell timing point. Same ptol (1e-4) as the other timing points,
# 128 timesteps, alternating sequential, local DP control build for fp64.
# NOTE: at this size fp32 CANNOT reach the tolerance fp64 reaches -- it caps.
# This is therefore a WORK comparison at a fixed tolerance target, not an
# accuracy-matched speed benchmark. n=2 per precision.
cd "$(dirname "$0")"   # run from the study working folder (see scripts/README.md)
sed -i '' "s/^NX, NY = .*/NX, NY = 1024, 256/" run_case.py
sed -i '' "s/^DT   = .*/DT   = 0.000244140625/" run_case.py
for r in 1 2; do
  python3 run_case.py --label "b262k_fp64_r$r" --precision fp64ctl --steps 128 --ptol 1e-4
  python3 run_case.py --label "b262k_fp32_r$r" --precision fp32    --steps 128 --ptol 1e-4
done
sed -i '' "s/^NX, NY = .*/NX, NY = 512, 128              # powers of two -> binary-exact spacings/" run_case.py
sed -i '' "s/^DT   = .*/DT   = 0.00048828125        # 2^-11 -> Co = 0.375 on nx=512/" run_case.py
echo "262k TIMING DONE $(date)"
