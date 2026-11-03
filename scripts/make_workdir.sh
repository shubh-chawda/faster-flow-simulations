#!/usr/bin/env bash
# Set up a working folder for one study under runs/<study>/.
#
# Each study's drivers were written to run from a single flat folder that holds
# the scripts, a case `template/` and the results CSV side by side. This copies
# exactly that layout out of the repo so the scripts run unchanged, and keeps
# solved output out of the tracked tree (runs/ is git-ignored).
#
#   scripts/make_workdir.sh 04_fp32_precision
#   cd runs/04_fp32_precision && ./run_all_final.sh
#
# Studies: 01_validation 02_scaling_study 03_mesh_independence
#          04_fp32_precision 05_inlet_profiles
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
STUDY="${1:?usage: scripts/make_workdir.sh <study>   (e.g. 04_fp32_precision)}"
WORK="$REPO/runs/$STUDY"
[ -d "$REPO/scripts/$STUDY" ] || { echo "unknown study: $STUDY" >&2; exit 1; }

mkdir -p "$WORK"
cp "$REPO/scripts/$STUDY/"* "$WORK/"

case "$STUDY" in
  01_validation)
    cp -r "$REPO/cases/channel_baseline_uniform_inlet" "$WORK/baseline" ;;
  02_scaling_study)
    mkdir -p "$WORK/scaling"
    cp -r "$REPO/scaling_study/template" "$WORK/scaling/template"
    cp "$REPO/scaling_study/psolve_isolation/isolate_psolve.sh" "$WORK/"
    cp "$REPO/results/02_scaling_study/results.csv" "$WORK/results.csv" ;;
  03_mesh_independence)
    cp -r "$REPO/cases/channel_mesh_study_template" "$WORK/template"
    cp -r "$REPO/scripts/_isambard" "$WORK/_isambard"
    cp "$REPO/results/03_mesh_independence/results.csv" "$WORK/results.csv" ;;
  04_fp32_precision)
    cp -r "$REPO/cases/channel_binary_exact_template" "$WORK/template"
    cp "$REPO/scripts/_orchestration/"*.sh "$WORK/"
    cp "$REPO/results/04_fp32_precision/results_final.csv" "$WORK/results_final.csv" ;;
  05_inlet_profiles)
    cp -r "$REPO/cases/channel_inlet_sine"   "$WORK/template"
    cp -r "$REPO/cases/channel_inlet_sine"   "$WORK/sine"
    cp -r "$REPO/cases/channel_inlet_skewed" "$WORK/skewed" ;;
esac

chmod +x "$WORK"/*.sh 2>/dev/null || true
echo "working folder ready: runs/$STUDY"
echo "the committed results CSV (if any) is copied in, so the analysis scripts run straight away"
