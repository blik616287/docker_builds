#!/bin/bash

set -e

# Generate the hostfile
/app/generate_hostfile.sh

# Start SSH server if this is the master node
if [ "${MPI_RANK}" = "0" ]; then
    echo "Starting sshd on master node"
    service ssh start
    # Print network info for debugging
    ip addr show
fi

# Execute the command provided as arguments
exec "$@"
