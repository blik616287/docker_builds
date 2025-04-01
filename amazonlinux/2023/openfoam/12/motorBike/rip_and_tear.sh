#!/bin/bash

./submit2.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_01_Allclean
./submit2.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_02_data_setup
./submit2.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_03_blockMesh
./submit2.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_04_decomposePar
./submit2.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_05_parallel_snappyHexMesh
./submit2.py --disable-ssl --mpi-processes 1 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_06_rmexec
./submit2.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_07_parallel_renumberMesh
./submit2.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_08_parallel_potentialFoam
./submit2.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_09_parallel_foamRun
