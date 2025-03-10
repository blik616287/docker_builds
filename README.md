# docker_builds

## alpine
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

## usage
```bash
# mpi providers
make OS=alpine OS_VERSION=3.21 PKG=openmpi PKG_VERSION=5.0.7
make OS=alpine OS_VERSION=3.21 PKG=mpich PKG_VERSION=4.3.0

# openfoam mpi variants
make OS=alpine OS_VERSION=3.21 PKG=openfoam PKG_VERSION=11 MPI_TYPE=mpich MPI_VERSION=4.3.0
make OS=alpine OS_VERSION=3.21 PKG=openfoam PKG_VERSION=11 MPI_TYPE=openmpi MPI_VERSION=5.0.7

# do all the things
make build-all-variants
```
