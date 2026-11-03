#!/usr/bin/env bash
cd "$(dirname "$0")"   # run from the study working folder (see scripts/README.md)
probe () {
  sed -i '' "s/^NX, NY = .*/NX, NY = $2, $3/" run_case.py
  sed -i '' "s/^DT   = .*/DT   = $4/" run_case.py
  python3 run_case.py --label "$1" --precision "$5" --steps 30 --ptol 1e-8
}
probe floor_4k    128  32  0.001953125    fp32
probe floor_65k   512 128  0.00048828125  fp32
probe floor_262k 1024 256  0.000244140625 fp32
probe floor_262k_fp64 1024 256 0.000244140625 fp64ctl
sed -i '' "s/^NX, NY = .*/NX, NY = 512, 128              # powers of two -> binary-exact spacings/" run_case.py
sed -i '' "s/^DT   = .*/DT   = 0.00048828125        # 2^-11 -> Co = 0.375 on nx=512/" run_case.py
echo "PROBES DONE $(date)"
