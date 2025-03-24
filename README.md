# docker_builds

image builder for mpi testing armada_client

## Current images
- debian
  - os version: bookworm-slim
    - pingpong
      - 0.0.1
        - tags:
          - base
          - test
- amazonlinux
  - os version: 2023
    - pingpong 
      - 0.0.1
        - tags:
          - base
          - test
    - openfoam
      - 11
        - tags:
          - base
          - test
      - 11
        - tags:
          - base
          - test

## build
```bash
# local k8s pingpong mpi test app
make OS=debian OS_VERSION=bookworm-slim PKG=pingpong PKG_VERSION=0.0.1
# aws pingpong mpi test app
make OS=amazonlinux OS_VERSION=2023 PKG=pingpong PKG_VERSION=0.0.1
# aws openfoam11
make OS=amazonlinux OS_VERSION=2023 PKG=openfoam PKG_VERSION=11
# aws openfoam12
make OS=amazonlinux OS_VERSION=2023 PKG=openfoam PKG_VERSION=12
```

## publish
```bash
# login
sudo docker login -u blik616287

# build and deploy
make publish OS=debian OS_VERSION=bookworm-slim PKG=pingpong PKG_VERSION=0.0.1
```
