# docker_builds

Just some general docker builds and a potential implementation of MPI on Armada.
Theres alot of cargo cult code in this repo, so its not intended for production use.
This is here just for interative development for the Armada MPI POC

## General build templates for preproduction OpenFoam containers:
- alpine
  - os version: 3.21
  - packages:
    - mpich
      - 4.3.0
        - base:latest
        - test:latest
    - openmpi
      - 5.0.7
        - base:latest
        - test:latest
    - openfoam
      - 11
        - base:mpich4.3.0
        - base:openmpi5.0.7

## Untested configuration and submission scripts using armada_client
- python - fatty debian image
  - os version: 3.9-slim
    - mpi_sample # apt resolved mpi
      - 0.0.1
        - base:latest
- debian
  - os version: bullseye-slim
    - mpi-c-app  # apt resolved mpi
      - 0.0.1
        - base:latest

## build
```bash
# openmpi c/fortran support
make OS=alpine OS_VERSION=3.21 PKG=openmpi PKG_VERSION=5.0.7
# REPOSITORY                     TAG       IMAGE ID       CREATED          SIZE
# alpine3.21_openmpi5.0.7_test   latest    cc06b03e8819   7 seconds ago    499MB
# alpine3.21_openmpi5.0.7_base   latest    0d961b9e2f34   10 seconds ago   499MB

# openfoam openmpi variant
make OS=alpine OS_VERSION=3.21 PKG=openfoam PKG_VERSION=11 MPI_TYPE=openmpi MPI_VERSION=5.0.7
# REPOSITORY                     TAG       IMAGE ID       CREATED          SIZE
# alpine3.21_openfoam11_openmpi5.0.7_base   latest    9bacddb6d12a   7 seconds ago        960MB

# mpich c/fortran support
make OS=alpine OS_VERSION=3.21 PKG=mpich PKG_VERSION=4.3.0
# REPOSITORY                     TAG       IMAGE ID       CREATED          SIZE
# alpine3.21_mpich4.3.0_test     latest    e27142aac67b   13 seconds ago   446MB
# alpine3.21_mpich4.3.0_base     latest    9b2b169f05f2   15 seconds ago   446MB

# openfoam mpich variant
make OS=alpine OS_VERSION=3.21 PKG=openfoam PKG_VERSION=11 MPI_TYPE=mpich MPI_VERSION=4.3.0
# REPOSITORY                     TAG       IMAGE ID       CREATED          SIZE
# alpine3.21_openfoam11_mpich4.3.0_base   latest    84b8bf20eb17   16 seconds ago       903MB

## potential armada test cases

# c mpi app
make OS=debian OS_VERSION=bullseye-slim PKG=mpi-c-app PKG_VERSION=0.0.1
# REPOSITORY                     TAG       IMAGE ID       CREATED          SIZE
# debianbullseye-slim_mpi-c-app0.0.1_base   latest          2a915b31e71f   7 seconds ago        419MB

# python mpi app
make OS=python OS_VERSION=3.9-slim PKG=mpi-sample PKG_VERSION=0.0.1
# REPOSITORY                     TAG       IMAGE ID       CREATED          SIZE
# python3.9-slim_mpi-sample0.0.1_base       latest          56c5d7d614cb   9 seconds ago    665MB
```

## deploy
```bash
# login
sudo docker login -u blik616287

# tag
sudo docker tag alpine3.21_openmpi5.0.7_base:latest blik6126287/alpine3.21_openmpi5.0.7:base
sudo docker tag alpine3.21_openmpi5.0.7_test:latest blik6126287/alpine3.21_openmpi5.0.7:test
sudo docker tag alpine3.21_mpich4.3.0_base:latest blik6126287/alpine3.21_mpich4.3.0:base
sudo docker tag alpine3.21_mpich4.3.0_test:latest blik6126287/alpine3.21_mpich4.3.0:test
sudo docker tag alpine3.21_openfoam11_openmpi5.0.7_base:latest blik6126287/alpine3.21_openfoam11:openmpi5.0.7
sudo docker tag alpine3.21_openfoam11_mpich4.3.0_base:latest blik6126287/alpine3.21_openfoam11:mpich4.3.0
sudo docker tag debianbullseye-slim_mpi-c-app0.0.1_base:latest blik6126287/debianbullseye-slim_mpi-c-app0.0.1_base:latest
sudo docker tag python3.9-slim_mpi-sample0.0.1_base:latest blik6126287/python3.9-slim_mpi-sample0.0.1_base:latest

# publish
sudo docker push blik6126287/alpine3.21_openmpi5.0.7:base
sudo docker push blik6126287/alpine3.21_openmpi5.0.7:test
sudo docker push blik6126287/alpine3.21_mpich4.3.0:base
sudo docker push blik6126287/alpine3.21_mpich4.3.0:test
sudo docker push blik6126287/alpine3.21_openfoam11:openmpi5.0.7
sudo docker push blik6126287/alpine3.21_openfoam11:mpich4.3.0
sudo docker push blik6126287/debianbullseye-slim_mpi-c-app0.0.1_base:latest
sudo docker push blik6126287/python3.9-slim_mpi-sample0.0.1_base:latest
```

## todo
-- spike gang scheduling option in armada, this might obselete my current devel line
