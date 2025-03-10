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
make OS=alpine OS_VERSION=3.21 PKG=openmpi PKG_VERSION=5.0.7
make OS=alpine OS_VERSION=3.21 PKG=mpich PKG_VERSION=4.3.0
```
