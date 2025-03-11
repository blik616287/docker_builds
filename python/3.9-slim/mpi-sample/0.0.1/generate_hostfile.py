#!/usr/bin/env python3

import os
import socket


def main():
    """Generate hostfile for MPI based on environment variables."""
    # Get environment variables
    world_size = int(os.environ.get('MPI_WORLD_SIZE', '1'))
    master_addr = os.environ.get('MPI_MASTER_ADDR', 'mpi-master')
    master_port = os.environ.get('MPI_MASTER_PORT', '29500')
    # Path to hostfile
    hostfile_path = '/etc/mpi/hostfile'
    # Ensure the directory exists
    os.makedirs(os.path.dirname(hostfile_path), exist_ok=True)
    # Create hostfile
    with open(hostfile_path, 'w') as f:
        # Write the master node
        f.write(f"{master_addr} slots=1\n")
        # Add worker pods (ranks 1 to world_size-1)
        for i in range(1, world_size):
            worker_name = f"mpi-worker-{i}"
            f.write(f"{worker_name} slots=1\n")
    print(f"Generated hostfile at {hostfile_path}:")
    with open(hostfile_path, 'r') as f:
        print(f.read())
    # Print environment info for debugging
    print(f"MPI Environment Variables:")
    print(f"  MPI_WORLD_SIZE = {world_size}")
    print(f"  MPI_MASTER_ADDR = {master_addr}")
    print(f"  MPI_MASTER_PORT = {master_port}")
    print(f"  HOSTNAME = {socket.gethostname()}")


if __name__ == "__main__":
    main()
