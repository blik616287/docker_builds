#!/bin/bash

# base os with latest mpich
docker build -f alpine3.21_mpich4.3.0_base/Dockerfile -t alpine3.21_mpich4.3.0_base .

# build basic mpich test off base container
docker build -f alpine3.21_mpich4.3.0_test/Dockerfile -t alpine3.21_mpich4.3.0_test .

# run basic test
docker run alpine3.21_mpich4.3.0_test:latest
