#!/usr/bin/env bash
# TIMING PROTOCOL (stated up front, applied identically to both precisions):
#   - binary-exact mesh 1024x256 (262,144 cells), dt=2^-12, Co=0.375
#   - ptol 1e-3: chosen because fp32 floors at ~1.7e-4 at this mesh size, so 1e-3 is the tightest round tolerance BOTH precisions can actually meet
#   - exactly 512 timesteps per run, from identical initial conditions
#   - 3 repeats each, fp64/fp32 ALTERNATING, strictly SEQUENTIAL (never concurrent)
#   - report median and spread
cd "$(dirname "$0")"   # run from the study working folder (see scripts/README.md)
for r in 1 2 3; do
  python3 run_case.py --label "t_fp64_r$r" --precision fp64 --steps 512 --ptol 1e-3
  python3 run_case.py --label "t_fp32_r$r" --precision fp32 --steps 512 --ptol 1e-3
done
echo "TIMING PROTOCOL COMPLETE $(date)"
