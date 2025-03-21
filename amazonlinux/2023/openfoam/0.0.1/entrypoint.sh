#!/bin/bash

# Print diagnostic info
echo "Container starting up"
echo "Hostname: ${HOSTNAME}"
echo "MPI_RANK: ${MPI_RANK}"
echo "MPI_WORLD_SIZE: ${MPI_WORLD_SIZE}"
echo "JOB_SET_ID: ${JOB_SET_ID}"
echo "POD_NAME: ${POD_NAME}"

# Create shared directories
export MOUNTPOINT="/app/shared"
mkdir -p "${MOUNTPOINT}/hostfiles/${JOB_SET_ID}"
mkdir -p "${MOUNTPOINT}/ssh/${JOB_SET_ID}"
mkdir -p "${MOUNTPOINT}/status/${JOB_SET_ID}"

# Set up early error signaling
# This ensures that if the script exits at any point, the error is communicated to worker nodes
if [ "${MPI_RANK}" = "0" ]; then
    # For master node, set up trap to signal errors
    trap 'echo "$(date): Master failed with status $?" > "${MOUNTPOINT}/status/${JOB_SET_ID}/master_failed"' ERR EXIT
    # Create initial heartbeat
    echo "$(date): Master initializing" > "${MOUNTPOINT}/status/${JOB_SET_ID}/master_heartbeat"
else
    # For worker nodes, create readiness indicator
    echo "$(date): Worker ${HOSTNAME} initializing" > "${MOUNTPOINT}/status/${JOB_SET_ID}/worker_${HOSTNAME}_ready"
fi

# Generate SSH host keys if they don't exist
ssh-keygen -A

# Start SSH daemon
/usr/sbin/sshd

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
    # Update heartbeat
    echo "$(date): Master SSH setup complete" > "${MOUNTPOINT}/status/${JOB_SET_ID}/master_heartbeat"
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
    # Update worker status
    echo "$(date): Worker ${HOSTNAME} SSH setup complete" > "${MOUNTPOINT}/status/${JOB_SET_ID}/worker_${HOSTNAME}_ready"
fi

# Create a flag file for MPI hosts
mkdir -p "$MOUNTPOINT/hostfiles/$JOB_SET_ID"
IPADDR="$(ip addr show eth0 | grep -w inet | awk '{print $2}' | cut -d/ -f1 | tr '.' '-')"
NAMESPACE="$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)"
echo "${IPADDR}.${NAMESPACE}.pod.cluster.local" > "${MOUNTPOINT}/hostfiles/${JOB_SET_ID}/${HOSTNAME}"

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
  echo "$ARECORD slots=1 max_slots=1" >> "/app/hostfile"
  # Add an echo for debugging
  echo "Added host to hostfile: $ARECORD"
done

# Function to create heartbeat file (for master node)
update_heartbeat() {
  echo "Starting master heartbeat mechanism"
  while true; do
    echo "$(date): Master alive" > "$MOUNTPOINT/status/$JOB_SET_ID/master_heartbeat"
    sleep 10
  done
}

# Function to check if master is still running
check_master_health() {
  # If completion file exists, master finished successfully
  if [ -f "$MOUNTPOINT/status/$JOB_SET_ID/job_complete" ]; then
    echo "$(date): Job completion file found"
    return 0
  fi
  # If master failure file exists, master failed
  if [ -f "$MOUNTPOINT/status/$JOB_SET_ID/master_failed" ]; then
    echo "$(date): Master failure file found"
    cat "$MOUNTPOINT/status/$JOB_SET_ID/master_failed"
    return 1
  fi
  # Check if master's pod is still running by checking its heartbeat
  MASTER_HEARTBEAT_FILE="$MOUNTPOINT/status/$JOB_SET_ID/master_heartbeat"
  # If heartbeat file doesn't exist or is too old (60 seconds), consider master failed
  if [ ! -f "$MASTER_HEARTBEAT_FILE" ]; then
    echo "$(date): Master heartbeat file not found"
    return 1
  fi
  HEARTBEAT_AGE=$(($(date +%s) - $(stat -c %Y "$MASTER_HEARTBEAT_FILE")))
  if [ $HEARTBEAT_AGE -gt 60 ]; then
    echo "$(date): Master node appears to have failed (heartbeat too old: ${HEARTBEAT_AGE}s)"
    return 1
  fi
  return 0
}

# Verify SSH connections from master to all nodes
if [ "${MPI_RANK}" = "0" ]; then
    echo "Testing SSH connections to all nodes"
    # Start the heartbeat process in the background before SSH tests
    update_heartbeat &
    HEARTBEAT_PID=$!
    # Update trap to kill heartbeat and signal either success or failure
    trap 'TRAP_STATUS=$?; if [ $TRAP_STATUS -eq 0 ]; then
            echo "$(date): Master completed successfully" > "${MOUNTPOINT}/status/${JOB_SET_ID}/job_complete";
          else
            echo "$(date): Master failed with status $TRAP_STATUS" > "${MOUNTPOINT}/status/${JOB_SET_ID}/master_failed";
          fi;
          kill $HEARTBEAT_PID 2>/dev/null;
          echo "Master cleanup done with status $TRAP_STATUS";
          exit $TRAP_STATUS' EXIT
    # Now test SSH connections with error handling that won't exit immediately
    SSH_TEST_FAILED=0
    while read -r host _; do
        echo "Testing SSH to $host"
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$host" "echo SSH connection to $host successful" < /dev/null || {
            echo "ERROR: SSH connection to $host failed"
            SSH_TEST_FAILED=1
        }
    done < /app/hostfile
    # If any SSH test failed, exit with error
    if [ $SSH_TEST_FAILED -eq 1 ]; then
        echo "One or more SSH tests failed, cannot proceed with MPI application"
        exit 1
    fi
    echo "Master node starting MPI application"
    # Run the MPI application and capture its exit status
    mpiexec --allow-run-as-root \
      -hostfile /app/hostfile \
      --prefix /usr/lib64/openmpi \
      --display-map \
      -n 2 \
      --mca plm rsh \
      --mca orte_rsh_agent ssh \
      --mca btl_tcp_if_include eth0 \
      --mca btl tcp,self \
      --mca oob tcp \
      --mca orte_keep_fqdn_hostnames t \
      /app/pingpong
    # Capture exit status
    MPI_EXIT_STATUS=$?
    echo "MPI application completed with exit status: $MPI_EXIT_STATUS"
    # Signal completion to worker nodes
    echo "$(date): Job completed with status $MPI_EXIT_STATUS" > "$MOUNTPOINT/status/$JOB_SET_ID/job_complete"
    # Exit with the same status as the MPI application
    exit $MPI_EXIT_STATUS
else
    echo "Worker node ready for MPI tasks"
    # Wait for the job completion signal from the master node
    echo "Worker node waiting for MPI job to complete..."
    # Check status every 5 seconds
    while true; do
        # First check job completion
        if [ -f "$MOUNTPOINT/status/$JOB_SET_ID/job_complete" ]; then
            echo "Worker node detected job completion:"
            cat "$MOUNTPOINT/status/$JOB_SET_ID/job_complete"
            echo "Worker exiting normally"
            exit 0
        fi
        # Then check for master failure
        if [ -f "$MOUNTPOINT/status/$JOB_SET_ID/master_failed" ]; then
            echo "Worker detected master failure:"
            cat "$MOUNTPOINT/status/$JOB_SET_ID/master_failed"
            echo "Worker exiting with error"
            exit 1
        fi
        # Then check master health via heartbeat
        if ! check_master_health; then
            echo "Master node failure detected, exiting with error"
            exit 1
        fi
        sleep 5
    done
fi
