# Scaling study: PCG vs GAMG

How does the cost of the pressure solve grow as the mesh is refined, and does multigrid
(GAMG) change that compared with conjugate gradient (PCG)?

## Set-up

The validated 2D channel case (uniform inlet), with the same mesh family (cell aspect
ratio 2) refined from 8k to about 2 million cells. For each mesh and each solver, 10
timesteps were run from rest, recording the wall time per timestep and the number of
pressure iterations per timestep. Only the pressure solver setting in `fvSolution`
changes between the two.

## Results

| cells | PCG s/step | GAMG s/step | speed-up | PCG iters/step | GAMG iters/step |
|------:|-----------:|------------:|--------:|---------------:|----------------:|
| 8,000 | 0.033 | 0.011 | 3.0× | 265 | 10 |
| 32,000 | 0.255 | 0.052 | 4.9× | 508 | 10 |
| 128,000 | 2.302 | 0.271 | 8.5× | 1028 | 13 |
| 512,000 | 17.126 | 1.334 | 12.8× | 1905 | 15 |
| 1,003,520 | – | 3.435 | – | – | 19 |
| 1,997,120 | – | 10.634 | – | – | 33 |

Fitted against the number of cells, the wall time grows as n<sup>1.51</sup> for PCG and
n<sup>1.22</sup> for GAMG. PCG's iteration count rises with the mesh (265 to 1,905,
roughly as √n), while GAMG's stays nearly constant (10 to 33 over a 250× range).
PCG was not run at 1M or 2M cells. Its fitted trend gives about 138 s per step at 2M
cells, compared with 10.6 s measured for GAMG.

## Caveats

- These are 10-step runs from rest, so they measure solver cost rather than developed
  flow. Accuracy was checked separately (the 8k case matches the exact solution to
  0.08%).
- GAMG builds its coarse-level hierarchy once, and over only 10 steps that set-up is a
  noticeable share of the time. Over a long run its scaling would be closer to linear.
- All runs are serial (one core).
- GAMG uses near-default settings.

## Running it

From the repository root:

```bash
scripts/make_workdir.sh 02_scaling_study && cd runs/02_scaling_study
# mesh sizes are given as ny values (nx = 5*ny); both solvers by default
bash run_scaling.sh 40 80 160 320
# one solver only, appending to an existing CSV
SOLVERS="gamg" APPEND=1 bash run_scaling.sh 448 632
python3 plot_scaling.py      # scaling.png and a summary table
```

`psolve_isolation/isolate_psolve.sh` runs each case with one and two pressure
correctors, so the difference isolates the time of one pressure solve.
