#!/usr/bin/env bash
# Scaling study: solve-time vs mesh size for PCG (naive) vs GAMG (multigrid).
# Runs a fixed number of timesteps at each mesh size and records wall time
# and pressure-solve iterations.
set -e
# source your OpenFOAM environment before running, e.g.
# . /usr/lib/openfoam/openfoam2312/etc/bashrc

TEMPLATE=${SCALING_ROOT:-$PWD/scaling}/template
WORK=${SCALING_ROOT:-$PWD/scaling}/runs
NSTEPS=10
CSV=${SCALING_ROOT:-$PWD/scaling}/results.csv
mkdir -p "$WORK"
: "${SOLVERS:=pcg gamg}"
if [ "${APPEND:-0}" != "1" ]; then
  echo "solver,ncells,nx,ny,exec_time_s,nsteps,total_p_iters,time_per_step_s,piters_per_step" > "$CSV"
fi

# ny values; nx = 5*ny keeps cell aspect ratio = 2
NYS="$@"
[ -z "$NYS" ] && NYS="40 80 160 320"

for NY in $NYS; do
  NX=$(( NY * 5 ))
  NCELLS=$(( NX * NY ))
  DT=$(python3 -c "print(0.2/$NX)")
  ENDT=$(python3 -c "print($NSTEPS*0.2/$NX)")
  for SOLVER in $SOLVERS; do
    C="$WORK/${SOLVER}_${NCELLS}"
    rm -rf "$C"; cp -r "$TEMPLATE" "$C"
    sed -i "s/__NX__/$NX/; s/__NY__/$NY/" "$C/system/blockMeshDict"
    sed -i "s/__DT__/$DT/; s/__ENDTIME__/$ENDT/" "$C/system/controlDict"
    cp "$C/system/fvSolution.$SOLVER" "$C/system/fvSolution"
    rm -f "$C"/system/fvSolution.pcg "$C"/system/fvSolution.gamg

    ( cd "$C"
      blockMesh > log.blockMesh 2>&1
      icoFoam   > log.icoFoam   2>&1 )

    LOG="$C/log.icoFoam"
    EXEC=$(grep "ExecutionTime" "$LOG" | tail -1 | awk '{print $3}')
    NST=$(grep -c "^Time = " "$LOG" || echo 0)
    PIT=$(grep "Solving for p" "$LOG" | grep -oE "No Iterations [0-9]+" | awk '{s+=$3} END{print s+0}')
    TPS=$(python3 -c "print(f'{$EXEC/$NST:.6f}')" 2>/dev/null || echo 0)
    PPS=$(python3 -c "print(f'{$PIT/$NST:.2f}')" 2>/dev/null || echo 0)
    echo "$SOLVER,$NCELLS,$NX,$NY,$EXEC,$NST,$PIT,$TPS,$PPS" >> "$CSV"
    printf "  %-4s  %8d cells  exec=%7ss  steps=%s  p-iters/step=%s\n" "$SOLVER" "$NCELLS" "$EXEC" "$NST" "$PPS"
  done
done
echo "=== done -> $CSV ==="
cat "$CSV"
