# Mesh-independence: convergence table

Convergence criterion (the same for every run): field-wide max|dU| between successive 0.5 s writes < 1e-6 m/s, enforced as a steady-state stopping condition.


## fp64

_Steady-state evidence:_

| mesh | cells | final t (s) | chunks | field max\|dU\| (m/s) | U_peak drift % | Co_max | steady |
|---|---|---|---|---|---|---|---|
| M0 | 8,000 | 2.5 | 1 | 1.00e-07 | 0.00000 | 0.2996 | yes |
| M1 | 32,000 | 2.5 | 1 | 1.00e-07 | 0.00000 | 0.3151 | yes |
| M2 | 128,000 | 2.5 | 1 | 2.02e-07 | 0.00000 | 0.3293 | yes |
| M3 | 288,000 | 2.5 | 1 | 7.03e-07 | 0.00000 | 0.3370 | yes |
| M4 | 512,000 | 5 | 2 | 1.00e-07 | 0.00000 | 0.3415 | yes |

**outlet centreline velocity U_c [m/s]**  (analytical = 1.5)
| pair | cells | Q(coarser) | Q(finer) | % change |
|---|---|---|---|---|
| M0→M1 | 8,000→32,000 | 1.49785 | 1.49926 | 0.0941% ✓₁ |
| M1→M2 | 32,000→128,000 | 1.49926 | 1.49961 | 0.0236% ✓₁ |
| M2→M3 | 128,000→288,000 | 1.49961 | 1.49968 | 0.0044% ✓₀.₀₁ |
| M3→M4 | 288,000→512,000 | 1.49968 | 1.4997 | 0.0015% ✓₀.₀₁ |

**outlet peak velocity U_max [m/s]**  (analytical = 1.5)
| pair | cells | Q(coarser) | Q(finer) | % change |
|---|---|---|---|---|
| M0→M1 | 8,000→32,000 | 1.49785 | 1.49926 | 0.0941% ✓₁ |
| M1→M2 | 32,000→128,000 | 1.49926 | 1.49961 | 0.0236% ✓₁ |
| M2→M3 | 128,000→288,000 | 1.49961 | 1.49968 | 0.0044% ✓₀.₀₁ |
| M3→M4 | 288,000→512,000 | 1.49968 | 1.4997 | 0.0015% ✓₀.₀₁ |

**wall shear tau_w/rho [m2/s2]**  (analytical = 0.06)
| pair | cells | Q(coarser) | Q(finer) | % change |
|---|---|---|---|---|
| M0→M1 | 8,000→32,000 | 0.059945 | 0.0600004 | 0.0925% ✓₁ |
| M1→M2 | 32,000→128,000 | 0.0600004 | 0.060014 | 0.0226% ✓₁ |
| M2→M3 | 128,000→288,000 | 0.060014 | 0.0600164 | 0.0040% ✓₀.₀₁ |
| M3→M4 | 288,000→512,000 | 0.0600164 | 0.0600171 | 0.0013% ✓₀.₀₁ |

**mean outlet velocity [m/s]**  (analytical = 1)
| pair | cells | Q(coarser) | Q(finer) | % change |
|---|---|---|---|---|
| M0→M1 | 8,000→32,000 | 1 | 1 | 0.0000% ✓₀.₀₁ |
| M1→M2 | 32,000→128,000 | 1 | 1 | 0.0000% ✓₀.₀₁ |
| M2→M3 | 128,000→288,000 | 1 | 1 | 0.0000% ✓₀.₀₁ |
| M3→M4 | 288,000→512,000 | 1 | 1 | 0.0000% ✓₀.₀₁ |

**max profile error [% Umax]**  (→ 0; %-change stays large near the floor)
| pair | cells | Q(coarser) | Q(finer) | % change |
|---|---|---|---|---|
| M0→M1 | 8,000→32,000 | 0.0810267 | 0.033955 | 58.0940% |
| M1→M2 | 32,000→128,000 | 0.033955 | 0.0221204 | 34.8537% |
| M2→M3 | 128,000→288,000 | 0.0221204 | 0.0199306 | 9.8997% |
| M3→M4 | 288,000→512,000 | 0.0199306 | 0.0191634 | 3.8490% |

**L2 profile error [% Umax]**  (→ 0; %-change stays large near the floor)
| pair | cells | Q(coarser) | Q(finer) | % change |
|---|---|---|---|---|
| M0→M1 | 8,000→32,000 | 0.0495785 | 0.0186254 | 62.4325% |
| M1→M2 | 32,000→128,000 | 0.0186254 | 0.0118476 | 36.3900% |
| M2→M3 | 128,000→288,000 | 0.0118476 | 0.0107861 | 8.9599% |
| M3→M4 | 288,000→512,000 | 0.0107861 | 0.01044 | 3.2087% |

### Interpretation

- Every mesh, including the 8,000-cell one, passes the 1% criterion (0.094% change at the first refinement), so 1% does not distinguish between meshes for this case.

- With a 0.01% criterion, every output settles by 128,000 cells (the slowest is outlet centreline velocity U_c).
  - outlet centreline velocity U_c within 0.01% of the 512,000-cell value by 128,000; outlet peak velocity U_max within 0.01% of the 512,000-cell value by 128,000; wall shear tau_w/rho within 0.01% of the 512,000-cell value by 128,000; mean outlet velocity within 0.01% of the 512,000-cell value by 8,000.
- Self-convergence order of U_peak: 2.0 (2× refinement, 8,000, 32,000 and 128,000 cells), as expected for second-order schemes.
- The error against the exact solution levels off at 0.0181% of U_max (Richardson fit on 8,000, 32,000 and 128,000 cells, order 1.99). The outlet at x = 1.0 m is about two entrance lengths downstream, so the flow there is not fully developed. With this value subtracted the error converges at second order (error_convergence.png).
- dt was set to 0.2/nx. The resulting Co_max goes from 0.300 to 0.341 across the series, because finer meshes resolve the velocity overshoot near the inlet.