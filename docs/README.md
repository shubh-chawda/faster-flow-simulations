# Docs

| | |
|---|---|
| [`report/Faster_Flow_Simulations_report.pdf`](report/Faster_Flow_Simulations_report.pdf) | The 5-page project report. LaTeX source and figures in [`report/latex/`](report/latex/). |
| [`slides/Faster_Flow_Simulations_slides.pdf`](slides/Faster_Flow_Simulations_slides.pdf) | The slides from the end-of-project presentation (30 July 2026). |
| [`RUNNING.md`](RUNNING.md) | How to run the cases: Courant settings, the binary-exact template, the fp32 check, platform notes. |


## Correction to the report

The version of the report first circulated in July 2026 said PCG at 2 million cells
"would need ~20 minutes" per timestep. That figure was the total for the 10-step timing
run. The fitted trend gives about 2.3 minutes (138 s) per timestep, roughly 13× slower
than GAMG's measured 10.6 s. The PDF here has the corrected sentence.
