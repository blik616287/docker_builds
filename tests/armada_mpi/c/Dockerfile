FROM debian:bullseye-slim

# Install MPICH and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    mpich \
    libmpich-dev \
    build-essential \
    openssh-client \
    openssh-server \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Setup SSH for MPI
RUN mkdir -p /var/run/sshd && \
    mkdir -p /root/.ssh && \
    ssh-keygen -A && \
    echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config && \
    echo "UserKnownHostsFile /dev/null" >> /etc/ssh/ssh_config

# Setup directories
RUN mkdir -p /app /etc/mpi

# Copy our MPI program source code
COPY mpi_matrix_multiply.c /app/

# Compile the MPI program
RUN cd /app && \
    mpicc -o mpi_matrix_multiply mpi_matrix_multiply.c -O3

# Create script to generate hostfile at runtime
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
WORLD_SIZE=${MPI_WORLD_SIZE:-1}\n\
MASTER_ADDR=${MPI_MASTER_ADDR:-mpi-master}\n\
\n\
# Create hostfile\n\
echo "${MASTER_ADDR} slots=1" > /etc/mpi/hostfile\n\
\n\
# Add worker entries\n\
for ((i=1; i<${WORLD_SIZE}; i++)); do\n\
    echo "mpi-worker-${i} slots=1" >> /etc/mpi/hostfile\n\
done\n\
\n\
echo "Generated hostfile at /etc/mpi/hostfile:"\n\
cat /etc/mpi/hostfile' > /app/generate_hostfile.sh

# Make script executable
RUN chmod +x /app/generate_hostfile.sh

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Generate the hostfile\n\
/app/generate_hostfile.sh\n\
\n\
# Start SSH server if this is the master node\n\
if [ "${MPI_RANK}" = "0" ]; then\n\
    echo "Starting sshd on master node"\n\
    service ssh start\n\
    \n\
    # Print network info for debugging\n\
    ip addr show\n\
fi\n\
\n\
# Execute the command provided as arguments\n\
exec "$@"' > /app/entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Set working directory
WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["mpirun", "--allow-run-as-root", "-hostfile", "/etc/mpi/hostfile", "-np", "1", "./mpi_matrix_multiply"]
