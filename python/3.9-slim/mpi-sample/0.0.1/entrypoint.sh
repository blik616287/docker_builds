#!/bin/bash
set -e

### bunch of cargo cult in here, so please be aware the cross pod networking is broken atm
### so like 90% of this needs to be refactored
### todo: dns lookup
# $(hostname -i | tr '.' '-').$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace).pod.cluster.local

# Print diagnostic info
echo "Container starting up"
echo "Hostname: $(hostname)"
echo "MPI_RANK: ${MPI_RANK}"
echo "MPI_WORLD_SIZE: ${MPI_WORLD_SIZE}"

# Create MPI directory if it doesn't exist
mkdir -p /etc/mpi
mkdir -p /etc/mpi/shared

# mount shared storage block
mkdir -p /app/shared
mount -o rw /dev/block/shared /app/shared

# Remove any existing hostfile to start fresh
if [ -f /etc/mpi/hostfile ]; then
  echo "Removing existing hostfile"
  rm /etc/mpi/hostfile
fi

# Generate a hostfile with Kubernetes FQDN naming
echo "Generating MPI hostfile with Kubernetes FQDN naming..."

# Get actual hostname pattern from Armada
OWN_HOSTNAME=$(hostname)
echo "Current hostname: ${OWN_HOSTNAME}"

# Extract the job ID prefix
JOB_PREFIX=$(echo ${OWN_HOSTNAME} | sed -E 's/-[0-9]+$//')
echo "Job prefix: ${JOB_PREFIX}"

# Generate hostfile with Kubernetes DNS format for ALL nodes
for i in $(seq 0 $((${MPI_WORLD_SIZE}-1))); do
  # Format: {job_prefix}-{rank}.default.svc.cluster.local
  HOST="${JOB_PREFIX}-${i}.default.svc.cluster.local"
  echo "${HOST} slots=1" >> /etc/mpi/hostfile
  echo "Added ${HOST} to hostfile"
done

# Check if we're using a shared directory
if [ -n "${MPI_SHARED_DIR}" ] && [ -d "${MPI_SHARED_DIR}" ]; then
  echo "Using shared directory for hostfile: ${MPI_SHARED_DIR}"
  # Copy hostfile to shared directory
  cp /etc/mpi/hostfile ${MPI_SHARED_DIR}/hostfile
  echo "Copied hostfile to shared directory"
  # Set the shared hostfile path for MPI
  MPI_HOSTFILE_PATH="${MPI_SHARED_DIR}/hostfile"
else
  echo "No shared directory defined, using local hostfile"
  MPI_HOSTFILE_PATH="/etc/mpi/hostfile"
fi

echo "Generated hostfile (${MPI_HOSTFILE_PATH}):"
cat ${MPI_HOSTFILE_PATH}

# Master node starts MPI job
if [ "${MPI_RANK}" = "0" ]; then
  echo "I am the master node, starting MPI job..."
  # Wait for workers to be ready
  echo "Waiting 5 seconds for workers to be ready..."
  sleep 5
  # Verify connectivity to worker nodes
  for i in $(seq 1 $((${MPI_WORLD_SIZE}-1))); do
    WORKER="${JOB_PREFIX}-${i}.default.svc.cluster.local"
    echo "Testing DNS resolution for ${WORKER}..."
    if getent hosts ${WORKER} >/dev/null 2>&1; then
      echo "  ✓ DNS resolution for ${WORKER} successful"
      WORKER_IP=$(getent hosts ${WORKER} | awk '{print $1}')
      echo "    IP address: ${WORKER_IP}"
      # Test TCP connectivity to port 29500
      echo "  Testing TCP connectivity to ${WORKER_IP}:29500..."
      if timeout 2 bash -c "cat < /dev/null > /dev/tcp/${WORKER_IP}/29500" 2>/dev/null; then
        echo "    ✓ TCP connection successful"
      else
        echo "    ✗ TCP connection failed - may be normal if worker isn't listening yet"
      fi
    else
      echo "  ✗ Cannot resolve ${WORKER} via DNS"
      # Try short name without domain suffix as fallback
      SHORT_WORKER="${JOB_PREFIX}-${i}"
      echo "  Trying short name: ${SHORT_WORKER}..."
      if getent hosts ${SHORT_WORKER} >/dev/null 2>&1; then
        echo "    ✓ DNS resolution for ${SHORT_WORKER} successful"
        WORKER_IP=$(getent hosts ${SHORT_WORKER} | awk '{print $1}')
        echo "    IP address: ${WORKER_IP}"
        # Update hostfile with short name since it works
        sed -i "s/${WORKER}/${SHORT_WORKER}/" /etc/mpi/hostfile
        echo "    Updated hostfile to use short name"
      else
        echo "    ✗ Cannot resolve short name either - keeping FQDN in hostfile"
      fi
    fi
  done
  # Run MPI application
  echo "Starting MPI run with hostfile:"
  cat ${MPI_HOSTFILE_PATH}
  mpirun --allow-run-as-root \
         --hostfile ${MPI_HOSTFILE_PATH} \
         --bind-to none \
         -v \
         -np ${MPI_WORLD_SIZE} \
         python /app/mpi_script.py
else
  echo "I am worker node ${MPI_RANK}, waiting for MPI tasks..."
  # Workers wait for MPI tasks with timeout
  TIMEOUT=90
  echo "Worker ready, waiting for MPI tasks (timeout: ${TIMEOUT}s)"
  # Wait for MPI tasks or timeout
  for ((i=1; i<=$TIMEOUT; i++)); do
    if pgrep -f "python" > /dev/null || pgrep -f "mpi" > /dev/null; then
      echo "MPI task detected, worker active"
      # Wait for task completion
      while pgrep -f "python" > /dev/null || pgrep -f "mpi" > /dev/null; do
        sleep 5
      done
      echo "MPI task completed, worker shutting down"
      exit 0
    fi
    # Show countdown every 10 seconds
    if (( i % 10 == 0 )); then
      echo "Waiting for MPI tasks... ${TIMEOUT-i}s remaining"
    fi
    sleep 1
    sleep infinity
  done
  echo "Timeout reached (${TIMEOUT}s), no MPI tasks detected. Worker shutting down."
  exit 0
fi
