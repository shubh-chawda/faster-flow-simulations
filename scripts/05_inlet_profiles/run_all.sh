#!/usr/bin/env bash
cd "$(dirname "$0")"   # run from the study working folder (see scripts/README.md)
# AMPLITUDE sweep at 128k (near-wall backflow needs resolution), f=1, alpha~4
for a in 0.5 0.6 0.7 0.8; do
  lab="AMP$(python3 -c "print(int($a*100))")"
  python3 run_point.py --label "$lab" --amp "$a" --freq 1 --nx 800 &
done
# FREQUENCY sweep at 32k (core centreline is mesh-independent), A=0.5
for f in 0.5 1 2 4; do
  lab="FRQ$(python3 -c "print(int($f*100))")"
  python3 run_point.py --label "$lab" --amp 0.5 --freq "$f" --nx 400 &
done
wait
echo "ALL SWEEP POINTS DONE $(date)"
