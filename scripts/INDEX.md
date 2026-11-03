# Scripts index

All scripts from the project, grouped by study in the order the work was done. The
numbering matches `results/`. Python 3 + numpy + matplotlib for the analysis scripts;
the run scripts need a sourced OpenFOAM environment (v2512).

## Running a study

Each study's drivers were written to run from one flat folder holding the scripts, a
case `template/` and the results CSV side by side. `make_workdir.sh` recreates that
layout under `runs/` (git-ignored), so the scripts run unchanged:

```bash
scripts/make_workdir.sh 04_fp32_precision
cd runs/04_fp32_precision
python3 analyse_final.py      # works straight away from the committed CSV
./run_all_final.sh            # re-runs the study (needs OpenFOAM and the SP build)
```

The single-precision build location defaults to `/Volumes/OpenFOAM-SP/...` (what
`build_sp.sh` creates on macOS); point `FOAM_SP_BASHRC`, `FOAM_DP_CTL_BASHRC` and
`FOAM_LAUNCH` elsewhere if yours differs.

## 01_validation — baseline vs analytical solution
- `analytical.py` — plots analytical plane-Poiseuille and planar-Womersley references
  and, given a solved case, overlays the simulated outlet profile and reports the
  error. Produced the 0.08 %-of-U_max validation figure.
  `python3 analytical.py <case_dir> <time_dir>`
  **Note:** it samples the **outlet cell column** (x ≈ 0.998 m). An earlier version of
  the plot legend said "x = 0.9 m", which was wrong; sampling at x = 0.9 m gives a
  larger error (0.103 % at 8k, 0.055 % at 32k) because the flow is still developing.

## 02_scaling_study — PCG vs GAMG cost scaling
- `run_scaling.sh` — refines the channel 8k → ~2M cells and runs 10 timesteps with each
  pressure solver, recording wall time and pressure iterations per step.
- `plot_scaling.py` — fits and plots the scaling laws (PCG ~ n^1.51, GAMG ~ n^1.22).
- Case template and a supplementary pressure-solve isolation experiment are in
  `../scaling_study/`.

## 03_mesh_independence — how fine a mesh is needed
- `run_sweep.py` — parameterised mesh sweep. Holds the Courant number fixed (dt ∝ dx)
  and runs each mesh to steady state with a **chunked stopping condition** (field-wide
  max|ΔU| between writes < 1e-6) rather than a fixed end time. Also takes
  `--precision fp32|fp64` and `--ptol`.
- `analyse.py` — %-change table, plateau detection, error-vs-analytical fit with a
  Richardson-extrapolated floor, and the convergence plots.
- `compare_precision.py` — an early precision plot, **superseded**. Use
  `04_fp32_precision/analyse_final.py` for the current precision results.

## 04_fp32_precision — single vs double precision (the final study)
- `build_sp.sh` — **builds single-precision OpenFOAM from source** (macOS). The two
  things that make it hard: it must be built on a **case-sensitive** filesystem, and
  `OSspecific` must use the `libo` target. Read this before attempting an fp32 build on
  any platform.
- `build_dp_control.sh` — builds a **double-precision control** from the identical
  source tree, compiler and flags, so the comparison measures precision and not build
  differences (measured build effect: 1.4 %).
- `run_case.py` — the comparison driver. Generates a binary-exact case, runs it under
  the chosen precision, **verifies `Solving for Ux`/`Uy` are present** (the mandatory
  check for the single-precision mesh bug), and records time, peak RSS, iterations and
  accuracy metrics.
- `timing_protocol.sh`, `run_all_final.sh` — the timing protocol: fixed step count,
  3 alternating repeats per precision, strictly sequential.
- `analyse_final.py` — validity check, timing/memory medians and spreads, accuracy
  table, residual-floor scaling, summary figure.
- `analyse_capped.py` — relative fp32 speed vs capped-solve fraction (the mechanism
  test), keeping the accuracy caveat and the asymmetric repeat counts explicit.

## 05_inlet_profiles — varying the inlet
- `analyse_sine.py` — oscillating-inlet response: outlet-centreline amplitude, phase,
  and a backflow check.
- `analyse_skewed.py` — skewed-inlet redevelopment to symmetric Poiseuille and the
  asymmetry-decay length.
- `run_point.py`, `run_all.sh`, `plot_sweeps.py` — an amplitude/frequency sweep driver.
  **This sweep was started and then stopped; its results are not used in any report.**
  Included for completeness only.

## _isambard — prepared but never run (no cluster access)
- `prep.py`, `submit.slurm`, `extract.py` — parallel 1M/2M-cell runs for Isambard, same
  numerics and same convergence gate as the local sweep. Blocked on access; read the
  notes in `prep.py` before using.

## _orchestration — session plumbing
Batch/wait/cleanup wrappers used to sequence the fp32 runs on one machine. Not needed to
reproduce any result; kept so the run sequence is documented. `make_workdir.sh
04_fp32_precision` copies them into the fp32 working folder, where they expect to run.
