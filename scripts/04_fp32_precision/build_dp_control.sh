#!/usr/bin/env bash
# CONTROL BUILD: compile icoFoam in DOUBLE precision from the SAME source tree,
# same compiler, same flags, same recipe as the SP build. Without this, an
# SP-vs-DP speed comparison partly measures gerlero-CI-build vs my-local-build
# rather than precision. wmake keeps DP and SP artefacts in separate dirs.
set -e
TREE=/Volumes/OpenFOAM-SP/OpenFOAM-v2512-SP
cp "$TREE/etc/bashrc" "$TREE/etc/bashrc.dp"
sed -i '' 's/^export WM_PRECISION_OPTION=SP/export WM_PRECISION_OPTION=DP/' "$TREE/etc/bashrc.dp"
source "$TREE/etc/bashrc.dp"
[ "$WM_PRECISION_OPTION" = DP ] || { echo "not DP -- abort"; exit 1; }
echo "=== control build: $WM_OPTIONS ==="
cd "$WM_PROJECT_DIR/src"
export WM_NCOMPPROCS=$(sysctl -n hw.ncpu)
wmakeLnInclude -u OpenFOAM; wmakeLnInclude -u OSspecific/POSIX
OSspecific/POSIX/Allwmake
Pstream/Allwmake
wmake -j OpenFOAM
wmake -j fileFormats
wmake -j surfMesh
wmake -j meshTools
wmake -j finiteVolume
wmake -j "$WM_PROJECT_DIR/applications/solvers/incompressible/icoFoam"
echo "=== CONTROL BUILD COMPLETE ==="; ls -la "$FOAM_APPBIN/icoFoam"
