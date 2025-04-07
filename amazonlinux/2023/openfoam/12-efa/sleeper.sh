#!/bin/bash

# Print diagnostic info
echo "Container starting up"
echo "Hostname: ${HOSTNAME}"
echo "JOB_SET_ID: ${JOB_SET_ID}"
echo "POD_NAME: ${POD_NAME}"

# If MPI job
if [ "${MPI_WORLD_SIZE}" -gt 1 ]; then
    ./setup_mpi.sh
fi

sleep infinity
