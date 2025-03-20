#!/bin/bash

# Print diagnostic info
echo "Container starting up"
echo "Hostname: $(hostname)"
echo "MPI_RANK: ${MPI_RANK}"
echo "MPI_WORLD_SIZE: ${MPI_WORLD_SIZE}"
echo "JOB_SET_ID: ${JOB_SET_ID}"
echo "POD_NAME: ${POD_NAME}"

# Create shared directories
export MOUNTPOINT="/app/shared"
mkdir -p "$MOUNTPOINT/hostfiles/$JOB_SET_ID"
mkdir -p "$MOUNTPOINT/ssh/$JOB_SET_ID"

# Start SSH daemon
service ssh start

# MASTER NODE (RANK 0) - SETUP SSH KEYS AND COORDINATION
if [ "${MPI_RANK}" = "0" ]; then
    echo "Master node (Rank 0) setting up SSH keys"
    # Generate SSH key on master
    ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa
    # Copy the SSH keys to shared directory for workers to use
    cp /root/.ssh/id_rsa "$MOUNTPOINT/ssh/$JOB_SET_ID/id_rsa"
    cp /root/.ssh/id_rsa.pub "$MOUNTPOINT/ssh/$JOB_SET_ID/id_rsa.pub"
    # Use the public key for master as well (self-access)
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
    # Create a flag file to signal SSH setup is complete
    touch "$MOUNTPOINT/ssh/$JOB_SET_ID/ssh_setup_complete"
fi

# WORKER NODES - WAIT FOR SSH SETUP TO COMPLETE
if [ "${MPI_RANK}" != "0" ]; then
    echo "Worker node waiting for SSH setup to complete"
    # Wait for SSH setup to complete on master
    while [ ! -f "$MOUNTPOINT/ssh/$JOB_SET_ID/ssh_setup_complete" ]; do
        echo "Waiting for SSH setup to complete..."
        sleep 2
    done
    # Copy SSH keys from shared volume
    cp "$MOUNTPOINT/ssh/$JOB_SET_ID/id_rsa" /root/.ssh/id_rsa
    cp "$MOUNTPOINT/ssh/$JOB_SET_ID/id_rsa.pub" /root/.ssh/id_rsa.pub
    cat "$MOUNTPOINT/ssh/$JOB_SET_ID/id_rsa.pub" >> /root/.ssh/authorized_keys
    # Set proper permissions
    chmod 600 /root/.ssh/id_rsa
    chmod 644 /root/.ssh/id_rsa.pub
    chmod 600 /root/.ssh/authorized_keys
    echo "Worker SSH setup complete"
fi

# Create a flag file for MPI hosts
mkdir -p "$MOUNTPOINT/hostfiles/$JOB_SET_ID"
echo "$(hostname -i | tr '.' '-').$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace).pod.cluster.local" > "$MOUNTPOINT/hostfiles/$JOB_SET_ID/$(hostname)"

# Wait until we have the required number of worker hosts
# We need to count only the host files, not the SSH keys or other files
while true; do
  HOST_COUNT=$(ls -1 "$MOUNTPOINT/hostfiles/$JOB_SET_ID" | wc -l)
  if [ "$HOST_COUNT" -ge "$MPI_WORLD_SIZE" ]; then
    echo "Found $HOST_COUNT host files, proceeding..."
    break
  else
    echo "Found $HOST_COUNT host files, waiting for $MPI_WORLD_SIZE..."
    sleep 5
  fi
done

# Process each host file and update /etc/hosts and hostfile
rm -rf /app/hostfile
touch /app/hostfile  # Create empty hostfile

# First, gather information about all pods and their IPs
for FILE in "$MOUNTPOINT/hostfiles/$JOB_SET_ID"/*; do
  ARECORD=$(cat "$FILE")
  echo "$ARECORD" >> "/app/hostfile"
done

# Verify SSH connections from master to all nodes
if [ "${MPI_RANK}" = "0" ]; then
    echo "Testing SSH connections to all nodes"
    while read -r host _; do
        echo "Testing SSH to $host"
        ssh -o StrictHostKeyChecking=no "$host" "echo SSH connection to $host successful" || {
            echo "ERROR: SSH connection to $host failed"
            exit 1
        }
    done < /app/hostfile
fi

# Run the MPI application if this is the master node
if [ "${MPI_RANK}" = "0" ]; then
  echo "Master node starting MPI application"
  mpirun --allow-run-as-root -hostfile /app/hostfile --map-by node -np 2 /app/pingpong
  sleep infinity
else
  echo "Worker node ready for MPI tasks"
  sleep infinity
fi
