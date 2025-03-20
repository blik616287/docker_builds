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
- debian
  - os version: bookworm-slim
    - pingpong  # apt resolved mpi
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

# pingpong mpi test app
make OS=debian OS_VERSION=bookworm-slim PKG=pingpong PKG_VERSION=0.0.1
# REPOSITORY                     TAG       IMAGE ID       CREATED          SIZE
debianbookworm-slim_pingpong0.0.1_base                latest              c3b6872a7c11   17 seconds ago       533MB
```

## publish
```bash
# login
sudo docker login -u blik616287

# build and deploy
make publish OS=debian OS_VERSION=bookworm-slim PKG=pingpong PKG_VERSION=0.0.1
```
