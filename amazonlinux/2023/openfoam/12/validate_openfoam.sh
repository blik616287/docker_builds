#!/bin/bash

echo "--------------------------------------"
echo "Validating OpenFOAM installation..."
echo "--------------------------------------"

# Find OpenFOAM installation directories
FOAM_INST_DIR="/opt/openfoam"
WM_PROJECT_DIR="$FOAM_INST_DIR/OpenFOAM-12"
echo "Looking for OpenFOAM installation at: $WM_PROJECT_DIR"
if [ ! -d "$WM_PROJECT_DIR" ]; then
    echo "ERROR: OpenFOAM installation directory not found!"
    exit 1
fi
# Source OpenFOAM environment
echo "Sourcing OpenFOAM environment..."
if [ -f "$WM_PROJECT_DIR/etc/bashrc" ]; then
    source "$WM_PROJECT_DIR/etc/bashrc"
    echo "Environment sourced successfully."
else
    echo "ERROR: OpenFOAM bashrc not found at $WM_PROJECT_DIR/etc/bashrc"
    exit 1
fi
# Find platform directory
echo "Searching for OpenFOAM platform directory..."
PLATFORM_DIR=$(find $WM_PROJECT_DIR/platforms -type d -name "linux64Gcc*" 2>/dev/null | head -1)
if [ -z "$PLATFORM_DIR" ]; then
    echo "Platform directory not found. Let's try to find binaries directly."
    FOAM_APPBIN=$(find $WM_PROJECT_DIR -name "simpleFoam" -o -name "blockMesh" 2>/dev/null | head -1 | xargs dirname 2>/dev/null)
    if [ -z "$FOAM_APPBIN" ]; then
        echo "Could not find any OpenFOAM binaries in the installation directory."
    else
        echo "Found binary directory: $FOAM_APPBIN"
    fi
else
    echo "Found platform directory: $PLATFORM_DIR"
    FOAM_APPBIN="$PLATFORM_DIR/bin"
    FOAM_LIBBIN="$PLATFORM_DIR/lib"
fi
# Find the tutorial directory
FOAM_TUTORIALS="$WM_PROJECT_DIR/tutorials"
if [ ! -d "$FOAM_TUTORIALS" ]; then
    echo "Tutorials directory not found at $FOAM_TUTORIALS"
fi
echo "OpenFOAM Environment Variables:"
echo " - WM_PROJECT_DIR = $WM_PROJECT_DIR"
echo " - FOAM_APPBIN = $FOAM_APPBIN"
echo " - FOAM_LIBBIN = $FOAM_LIBBIN"
echo " - FOAM_TUTORIALS = $FOAM_TUTORIALS"
echo " - WM_MPLIB = $WM_MPLIB"
echo " - MPI_ARCH_PATH = $MPI_ARCH_PATH"
echo "--------------------------------------"
echo "Checking OpenFOAM installation structure:"
echo "Directory listing of $WM_PROJECT_DIR:"
ls -la $WM_PROJECT_DIR
if [ -d "$PLATFORM_DIR" ]; then
    echo "Directory listing of $PLATFORM_DIR:"
    ls -la $PLATFORM_DIR
    echo "Directory listing of $FOAM_APPBIN:"
    ls -la $FOAM_APPBIN | head -10
    echo "Directory listing of $FOAM_LIBBIN:"
    ls -la $FOAM_LIBBIN | head -10
fi
echo "--------------------------------------"
echo "Looking for OpenFOAM binaries using find:"
find $WM_PROJECT_DIR -name "simpleFoam" -o -name "blockMesh" 2>/dev/null
find $WM_PROJECT_DIR -name "*.so" | head -5
echo "--------------------------------------"
echo "Checking for OpenFOAM binaries on PATH:"
which simpleFoam || echo "simpleFoam not found on PATH"
which blockMesh || echo "blockMesh not found on PATH"
which foamToVTK || echo "foamToVTK not found on PATH"
echo "--------------------------------------"
echo "Checking MPI installation:"
which mpirun || echo "mpirun not found on PATH"
mpirun --version || echo "Failed to get mpirun version"
echo "--------------------------------------"
echo "Searching for other OpenFOAM components:"
if [ -d "$FOAM_TUTORIALS" ]; then
    echo "Available tutorials:"
    find $FOAM_TUTORIALS -name "pitzDaily" -o -name "cavity" | head -5
fi
echo "--------------------------------------"
echo "Checking for OpenFOAM version:"
simpleFoam -help 2>&1 | grep -i version || echo "Could not determine OpenFOAM version"
echo "--------------------------------------"
echo "Checking for third-party software:"
echo "ThirdParty directory: $FOAM_INST_DIR/ThirdParty-12"
if [ -d "$FOAM_INST_DIR/ThirdParty-12" ]; then
    echo "ThirdParty contents:"
    ls -la $FOAM_INST_DIR/ThirdParty-12
    echo "ThirdParty platforms directory:"
    if [ -d "$FOAM_INST_DIR/ThirdParty-12/platforms" ]; then
        ls -la $FOAM_INST_DIR/ThirdParty-12/platforms
    else
        echo "ThirdParty platforms directory not found"
    fi
else
    echo "ThirdParty directory not found"
fi
echo "--------------------------------------"
echo "OpenFOAM inspection completed"
echo "--------------------------------------"
