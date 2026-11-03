#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/etc/bashrc"
cd "$WM_PROJECT_DIR/src"
export WM_NCOMPPROCS=$(sysctl -n hw.ncpu)
echo "=== building $WM_OPTIONS with $WM_NCOMPPROCS procs ==="
[ "$WM_PRECISION_OPTION" = SP ] || { echo "NOT SP -- abort"; exit 1; }
wmakeLnInclude -u OpenFOAM
wmakeLnInclude -u OSspecific/POSIX
echo ">>> [1/8] OSspecific/POSIX (libo)"; OSspecific/POSIX/Allwmake
echo ">>> [2/8] Pstream";                 Pstream/Allwmake
echo ">>> [3/8] OpenFOAM";                wmake -j OpenFOAM
echo ">>> [4/8] fileFormats";            wmake -j fileFormats
echo ">>> [5/8] surfMesh";               wmake -j surfMesh
echo ">>> [6/8] meshTools";              wmake -j meshTools
echo ">>> [7/8] finiteVolume";           wmake -j finiteVolume
echo ">>> [8/8] icoFoam";                wmake -j "$WM_PROJECT_DIR/applications/solvers/incompressible/icoFoam"
echo "=== BUILD COMPLETE ==="; ls -la "$FOAM_APPBIN/icoFoam"; file "$FOAM_APPBIN/icoFoam"
