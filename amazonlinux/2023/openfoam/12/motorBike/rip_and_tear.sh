#!/bin/bash

./submit.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_01_Allclean
./submit.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_02_data_setup
./submit.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_03_blockMesh
./submit.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_04_decomposePar
./submit.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_05_parallel_snappyHexMesh
./submit.py --disable-ssl --mpi-processes 1 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_06_rmexec
./submit.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_07_parallel_renumberMesh
./submit.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_08_parallel_potentialFoam
./submit.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_09_parallel_foamRun
