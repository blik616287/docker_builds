#!/bin/bash

set -e

WORLD_SIZE=${MPI_WORLD_SIZE:-1}
MASTER_ADDR=${MPI_MASTER_ADDR:-mpi-master}

# Create hostfile
echo "${MASTER_ADDR} slots=1" > /etc/mpi/hostfile

# Add worker entries
for ((i=1; i<${WORLD_SIZE}; i++)); do
    echo "mpi-worker-${i} slots=1" >> /etc/mpi/hostfile
done

echo "Generated hostfile at /etc/mpi/hostfile:"
cat /etc/mpi/hostfile
