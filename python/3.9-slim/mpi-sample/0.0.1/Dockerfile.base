FROM python:3.9-slim

# Install OpenMPI and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    openssh-server \
    openmpi-bin \
    openmpi-common \
    libopenmpi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Setup SSH for MPI
RUN mkdir -p /var/run/sshd && \
    mkdir -p /root/.ssh && \
    echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config && \
    echo "    UserKnownHostsFile /dev/null" >> /etc/ssh/ssh_config

# Install Python dependencies
RUN pip install --no-cache-dir numpy mpi4py

# Create app directory
WORKDIR /app

# Copy the MPI script and the hostfile generator
COPY mpi_script.py /app/
COPY generate_hostfile.py /app/

# Create directory for hostfile
RUN mkdir -p /etc/mpi

# Make scripts executable
RUN chmod +x /app/mpi_script.py
RUN chmod +x /app/generate_hostfile.py

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Generate hostfile\n\
python /app/generate_hostfile.py\n\
\n\
# Start SSH server if this is the master\n\
if [ "${MPI_RANK}" = "0" ]; then\n\
    service ssh start\n\
fi\n\
\n\
# Execute the command provided as arguments\n\
exec "$@"' > /app/entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["mpirun", "--allow-run-as-root", "--hostfile", "/etc/mpi/hostfile", "-np", "1", "python", "/app/mpi_script.py"]
