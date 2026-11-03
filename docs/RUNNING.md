# Running the cases

Everything needed to run the cases on another machine. Solved output is not included;
each case generates its own mesh with `blockMesh`.

## Environment

- **OpenFOAM v2512.** The standard build is double precision. Single precision needs a
  separate build, because precision is set when OpenFOAM is compiled
  (`WM_PRECISION_OPTION=SP`), not in `fvSolution`.
- The single-precision build script is `scripts/04_fp32_precision/build_sp.sh` (macOS,
  Apple Silicon). Two things it handles: the build has to be on a case-sensitive
  filesystem (otherwise `#include <time.h>` picks up OpenFOAM's `Time.H` and compiling
  fails), and `OSspecific` has to be built with the `libo` target.
- Windows was not tried. An fp32 run there would also need its own single-precision
  build; the cases themselves are platform-independent.

## Physics (the same in every case)

| quantity | value |
|---|---|
| domain | L = 1.0 m, H = 0.1 m, W = 0.01 m (2D: one cell in z, `empty` front and back) |
| ν | 1e-3 m²/s |
| inlet | uniform (1 0 0) m/s, except in the inlet-profile cases |
| walls | `noSlip`; outlet p = 0, U `zeroGradient` |
| Re_H | 100 (laminar); U_mean = 1.0, so the exact U_max = 1.5 |
| solver | `icoFoam`, GAMG for pressure (PCG version also provided) |

## Running a case

```bash
source <OpenFOAM>/etc/bashrc          # or the single-precision bashrc
cd cases/<case>
blockMesh && checkMesh && icoFoam > log.icoFoam 2>&1
```

## Cases

- `channel_baseline_uniform_inlet`: the baseline, which matches the exact Poiseuille
  profile to 0.08% of U_max.
- `channel_mesh_study_template`: the mesh-independence case (filled in by
  `scripts/03_mesh_independence/run_sweep.py`).
- `channel_binary_exact_template`: the fp32/fp64 case. `system/blockMeshDict`,
  `system/controlDict` and `system/fvSolution` contain placeholders that
  `scripts/04_fp32_precision/run_case.py` fills in. To run it by hand, use one of these:

  | cells | `__NX__` | `__NY__` | `__DELTAT__` |
  |---|---|---|---|
  | 16,384 | 256 | 64 | 0.0009765625 |
  | 65,536 | 512 | 128 | 0.00048828125 |
  | 262,144 | 1024 | 256 | 0.000244140625 |

  and set `__ENDTIME__`, `__WRITEINTERVAL__`, `__PTOL__` (1e-4) and `__PSOLVERBLOCK__`
  (the GAMG or PCG block from `run_case.py`).
- `channel_inlet_sine`, `channel_inlet_skewed`: the oscillating and skewed inlets.
- `channel_inlet_parabolic_codedBC`, `channel_inlet_pulsatile`: earlier inlet tests
  using coded boundary conditions.

## Timestep and Courant number

`dt` is chosen so that the nominal Courant number U_max·dt/dx is 0.375, and has to be
scaled with the mesh (`dt ∝ dx`). The measured Co_max is a bit higher because the
velocity overshoots near the inlet: 0.4311 on 512 × 128 (dt = 2⁻¹¹) and 0.4524 on
1024 × 256 (dt = 2⁻¹²).

## Single precision

In single precision, round-off in the face areas of the `empty` patches can exceed the
`1e-6` threshold in `polyMesh.C`. x and y are then marked as empty directions
(through `fvMeshTemplates.C` and `validComponents`), and `fvMatrixSolve.C` skips
solving for those velocity components. The run still finishes. Check every fp32 log:

```bash
grep -c "Solving for Ux" log.icoFoam   # should equal the number of timesteps
grep -c "Solving for Uy" log.icoFoam
```

Compare with the number of `Time = ` lines. On macOS, if `grep` is aliased to `ugrep`,
the count can be wrong, so check it another way (for example in Python).

Power-of-two cell counts avoid the problem, because dividing by 2^k keeps the spacing
exact in binary (nx = 1024 gives dx = 2⁻¹⁰; nx = 800 gives 0.00125, which is not exact).
In this domain H = 0.1 and W = 0.01 are not exact in binary either, but power-of-two
cell counts were enough: every run passed the check. If the problem does appear, W can
be changed to 0.015625 (2⁻⁶) without affecting a 2D result. H should not be changed,
because it sets Re_H.

The fp32 speed result depends on the mesh, so it is worth running more than one size:

| cells | nx × ny | fp32 vs fp64 time | fp32 solves hitting the iteration limit |
|---|---|---|---|
| 16,384 | 256 × 64 | 6.7% faster | 0% |
| 65,536 | 512 × 128 | 31% slower | 0.2% |
| 262,144 | 1024 × 256 | 116× slower | 95% |

At 262,144 cells fp32 does not reach the 1e-4 tolerance (its residual stops at about
1.4e-4), so that row compares work done rather than converged solves. Where both
precisions converge, the answers agree to about 3e-7 m/s.
