#!/bin/bash

./config.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_01_Allclean
./config.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_02_data_setup
./config.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_03_blockMesh
./config.py --disable-ssl --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_04_decomposePar
./config.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_05_parallel_snappyHexMesh
./config.py --disable-ssl --mpi-processes 1 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_06_rmexec
./config.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_07_parallel_renumberMesh
./config.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_08_parallel_potentialFoam
./config.py --disable-ssl --mpi-processes 8 --mpi-image blik6126287/amazonlinux2023_openfoam12:motorBike_09_parallel_foamRun
