#!/bin/bash
#SBATCH --job-name=meshindep
#SBATCH --nodes=1                    # <-- CONFIRM with the group: 1 node enough for 2M?
#SBATCH --ntasks-per-node=144       # <-- CONFIRM: cores/node (Isambard 3 Grace = 2x72)
#SBATCH --time=12:00:00             # <-- wall limit; raise if a mesh needs it
#SBATCH --account=__ACCOUNT__       # <-- your project/budget code (ask the supervisor)
#SBATCH --partition=__PARTITION__   # <-- e.g. the standard CPU partition
# ---------------------------------------------------------------------------
# Mesh-independence M5/M6 on Isambard (fp64). PLACEHOLDERS __LIKE_THIS__ MUST be
# filled in after confirming the environment with the supervisor.
#
#   sbatch submit.slurm M5 144
# ---------------------------------------------------------------------------
set -euo pipefail
LABEL=${1:?usage: sbatch submit.slurm <M5|M6> <ncores>}
NCORES=${2:?give ncores == ntasks-per-node above}

module purge
module load __OPENFOAM_MODULE__     # <-- CONFIRM exact module name (double precision!)

cd "$SLURM_SUBMIT_DIR"
python3 prep.py "$LABEL" --ncores "$NCORES"
CASE="cases/$LABEL"

cd "$CASE"
blockMesh                 > log.blockMesh   2>&1
checkMesh                 > log.checkMesh   2>&1
decomposePar              > log.decompose   2>&1
mpirun -np "$NCORES" icoFoam -parallel > log.icoFoam 2>&1
# reconstruct only the last two writes for the dU + metric check
reconstructPar -latestTime            > log.reconstruct 2>&1
reconstructPar -time "$(ls -d processor0/[0-9]* | sed 's#.*/##' | sort -g | tail -2 | head -1)" \
                                      >> log.reconstruct 2>&1

cd "$SLURM_SUBMIT_DIR"
python3 extract.py "$LABEL"           # appends results_isambard.csv, checks the gate
echo "done $LABEL -- see results_isambard.csv"
