#!/usr/bin/env bash
# Isolate the pressure-solve cost: run with nCorrectors=1 and =2.
# The difference in wall time is one extra pressure correction (solve + flux
# update), so (t2 - t1)/nsteps isolates the per-step pressure-solve time,
# independent of mesh assembly and the momentum (U) solve.
set -e
# source your OpenFOAM environment before running, e.g.
# . /usr/lib/openfoam/openfoam2312/etc/bashrc
TEMPLATE=${SCALING_ROOT:-$PWD/scaling}/template
WORK=${SCALING_ROOT:-$PWD/scaling}/psolve
NSTEPS=10
CSV=${SCALING_ROOT:-$PWD/scaling}/psolve.csv
mkdir -p "$WORK"
[ "${APPEND:-0}" = "1" ] || echo "solver,ncells,t1_per_step,t2_per_step,psolve_per_step,piters_per_step" > "$CSV"

for NY in "$@"; do
  NX=$(( NY*5 )); NCELLS=$(( NX*NY ))
  DT=$(python3 -c "print(0.2/$NX)"); ENDT=$(python3 -c "print($NSTEPS*0.2/$NX)")
  for SOLVER in ${SOLVERS:-pcg gamg}; do
    declare -A T
    for NC in 1 2; do
      C="$WORK/${SOLVER}_${NCELLS}_nc${NC}"
      rm -rf "$C"; cp -r "$TEMPLATE" "$C"
      sed -i "s/__NX__/$NX/; s/__NY__/$NY/" "$C/system/blockMeshDict"
      sed -i "s/__DT__/$DT/; s/__ENDTIME__/$ENDT/" "$C/system/controlDict"
      cp "$C/system/fvSolution.$SOLVER" "$C/system/fvSolution"
      sed -i "s/nCorrectors 2;/nCorrectors $NC;/" "$C/system/fvSolution"
      rm -f "$C"/system/fvSolution.pcg "$C"/system/fvSolution.gamg
      ( cd "$C"; blockMesh >log.bm 2>&1; icoFoam >log.ico 2>&1 )
      LOG="$C/log.ico"
      EXEC=$(grep "ExecutionTime" "$LOG" | tail -1 | awk '{print $3}')
      NST=$(grep -c "^Time = " "$LOG")
      T[$NC]=$(python3 -c "print($EXEC/$NST)")
      if [ "$NC" = "2" ]; then
        PIT=$(grep "Solving for p" "$LOG" | grep -oE "No Iterations [0-9]+" | awk '{s+=$3} END{print s+0}')
        PPS=$(python3 -c "print(f'{$PIT/$NST:.1f}')")
      fi
    done
    PS=$(python3 -c "print(f'{${T[2]}-${T[1]}:.6f}')")
    echo "$SOLVER,$NCELLS,${T[1]},${T[2]},$PS,$PPS" >> "$CSV"
    printf "  %-4s %8d  t1=%.3f t2=%.3f  p-solve/step=%.4fs  p-iters/step=%s\n" \
           "$SOLVER" "$NCELLS" "${T[1]}" "${T[2]}" "$PS" "$PPS"
  done
done
echo "-> $CSV"