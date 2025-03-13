#!/usr/bin/env python3
"""
MPI Job Submission for Kubernetes clusters using Armada.
The hostfile generation is now handled by the container's entrypoint script.
"""

import os
import uuid
import grpc
import time
import logging
from armada_client.client import ArmadaClient
from armada_client.k8s.io.api.core.v1 import generated_pb2 as core_v1
from armada_client.k8s.io.apimachinery.pkg.api.resource import generated_pb2 as api_resource
from armada_client.permissions import Permissions, Subject
from armada_client.typings import EventType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DISABLE_SSL = os.environ.get("DISABLE_SSL", "true").lower() == "true"
HOST = os.environ.get("ARMADA_SERVER", "192.168.57.13")
PORT = os.environ.get("ARMADA_PORT", "30002")
MPI_PROCESSES = int(os.environ.get("MPI_PROCESSES", "3"))
QUEUE_NAME = os.environ.get("QUEUE_NAME", "")
PRIORITY_FACTOR = float(os.environ.get("PRIORITY_FACTOR", "10.0"))
JOB_SET_PREFIX = "mpi-jobset"
MONITORING_TIMEOUT = int(os.environ.get("MONITORING_TIMEOUT", "300"))
NAMESPACE = os.environ.get("NAMESPACE", "default")


def create_armada_client():
    """Create and return an Armada client."""
    if DISABLE_SSL:
        channel = grpc.insecure_channel(f"{HOST}:{PORT}")
    else:
        channel_credentials = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(
            f"{HOST}:{PORT}",
            channel_credentials,
        )
    return ArmadaClient(channel)


def use_existing_queue(client, queue_name="default"):
    """
    Use an existing queue instead of creating a new one.

    Args:
        client: The Armada client
        queue_name: Name of an existing queue to use

    Returns:
        The name of the queue to use
    """
    logger.info(f"Verifying existing queue: {queue_name}")
    try:
        queue = client.get_queue(queue_name)
        logger.info(f"Using existing queue: {queue_name}")
        return queue_name
    except grpc.RpcError as e:
        logger.error(f"Error accessing queue {queue_name}: {e}")
        raise e


def create_mpi_queue(client):
    """
    Create a queue for MPI jobs with appropriate settings and verify it exists before returning.

    Args:
        client: The Armada client

    Returns:
        The name of the created queue
    """
    queue_name = QUEUE_NAME
    if not queue_name:
        queue_name = f"mpi-queue-{uuid.uuid4().hex[:8]}"

    logger.info(f"Creating/verifying queue: {queue_name}")

    # Define permissions - allow users to submit and monitor jobs
    subject = Subject(kind="Group", name="users")
    permissions = Permissions(
        subjects=[subject],
        verbs=["submit", "cancel", "reprioritize", "watch"]
    )

    # Set resource limits for the queue
    resource_limits = {
        "cpu": float(os.environ.get("QUEUE_CPU_LIMIT", "100.0")),
        "memory": float(os.environ.get("QUEUE_MEMORY_LIMIT", "500.0")),
        "gpu": float(os.environ.get("QUEUE_GPU_LIMIT", "0"))
    }

    queue_req = client.create_queue_request(
        name=queue_name,
        priority_factor=PRIORITY_FACTOR,
        user_owners=[os.environ.get("QUEUE_OWNER", "admin")],
        group_owners=[os.environ.get("QUEUE_GROUP", "admins")],
        resource_limits=resource_limits,
        permissions=[permissions]
    )

    # Try to retrieve the queue first to see if it exists
    try:
        existing_queue = client.get_queue(queue_name)
        logger.info(f"Queue {queue_name} already exists, updating it")
        client.update_queue(queue_req)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            logger.info(f"Queue {queue_name} not found, creating new queue")
            try:
                client.create_queue(queue_req)
                logger.info(f"Queue {queue_name} created successfully")
            except grpc.RpcError as create_error:
                logger.error(f"Failed to create queue: {create_error}")
                raise create_error
        else:
            logger.error(f"Error checking queue: {e}")
            raise e

    # Verify the queue exists and is accessible
    max_retries = 5
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            logger.info(f"Verifying queue {queue_name} exists (attempt {attempt+1}/{max_retries})")
            queue = client.get_queue(queue_name)
            logger.info(f"Queue {queue_name} verified to exist")
            return queue_name
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND or e.code() == grpc.StatusCode.PERMISSION_DENIED:
                logger.warning(f"Queue not accessible yet, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff
            else:
                logger.error(f"Unexpected error verifying queue: {e}")
                raise e

    # If we've exhausted retries
    logger.error(f"Could not verify queue {queue_name} after {max_retries} attempts")
    raise Exception(f"Queue {queue_name} creation succeeded but verification failed")


def create_mpi_pod_spec(client, rank, world_size, job_set_id, volume_name):
    """
    Create a pod spec for an MPI process (master or worker).

    Args:
        client: The Armada client
        rank: The MPI rank for this pod
        world_size: Total number of MPI processes
        job_set_id: The job set ID for identification
        volume_name: Name of the shared volume for hostfile

    Returns:
        A job request item
    """
    # Role designation
    is_master = (rank == 0)
    role = "master" if is_master else "worker"

    # Common environment variables for MPI
    # The entrypoint script will use these to configure the MPI environment
    mpi_env = [
        core_v1.EnvVar(name="MPI_WORLD_SIZE", value=str(world_size)),
        core_v1.EnvVar(name="MPI_RANK", value=str(rank)),
        core_v1.EnvVar(name="MPI_MASTER_PORT", value="29500"),
        core_v1.EnvVar(name="JOB_SET_ID", value=job_set_id),
        # Path to the shared hostfile directory
        core_v1.EnvVar(name="MPI_SHARED_DIR", value="/etc/mpi/shared"),
    ]

    # Container name
    container_name = "mpi-master" if is_master else f"mpi-worker-{rank}"

    # Common pod labels for identification
    pod_labels = {
        "app": "mpi-job",
        "job-set-id": job_set_id,
        "role": role,
        "rank": str(rank)
    }

    # Define resource requirements
    cpu_request = "750m" if is_master else "650m"
    memory_request = "1Gi" if is_master else "750Mi"

    # Create the main container spec
    main_container = core_v1.Container(
        name=container_name,
        image=os.environ.get("MPI_IMAGE", "blik6126287/python3.9-slim_mpi-sample0.0.1_base:latest"),
        # The container will use its own entrypoint to handle hostfile generation and MPI execution
        env=mpi_env,
        resources=core_v1.ResourceRequirements(
            requests={
                "cpu": api_resource.Quantity(string=cpu_request),
                "memory": api_resource.Quantity(string=memory_request),
            },
            limits={
                "cpu": api_resource.Quantity(string=cpu_request),
                "memory": api_resource.Quantity(string=memory_request),
            },
        ),
        # Mount the shared volume
        volume_mounts=[
            core_v1.VolumeMount(
                name=volume_name,
                mount_path="/etc/mpi/shared"
            )
        ]
    )

    # Create pod spec with main container and shared volume
    pod_spec = core_v1.PodSpec(
        containers=[main_container],
        # Define the shared volume
        volumes=[
            core_v1.Volume(
                name=volume_name,
                empty_dir=core_v1.EmptyDirVolumeSource()
            )
        ]
    )

    # Create the job request item
    return client.create_job_request_item(
        priority=int(os.environ.get("JOB_PRIORITY", "50")),
        pod_spec=pod_spec,
        labels=pod_labels,
        namespace=NAMESPACE
    )


def submit_mpi_job(client, queue_name):
    """
    Create and submit an MPI job set consisting of one master and multiple workers.

    Args:
        client: The Armada client
        queue_name: The queue to submit the job to

    Returns:
        job_set_id: The ID of the job set
        job_ids: List of job IDs, first is master, rest are workers
    """
    world_size = MPI_PROCESSES
    job_set_id = f"{JOB_SET_PREFIX}-{uuid.uuid4().hex[:8]}"
    volume_name = f"mpi-shared-{job_set_id}"
    logger.info(f"Creating MPI job set {job_set_id} with {world_size} processes")
    logger.info(f"Using shared volume {volume_name} for hostfile")

    # Create job request items for master and workers
    job_request_items = []

    # Add master pod (rank 0)
    job_request_items.append(create_mpi_pod_spec(client, 0, world_size, job_set_id, volume_name))

    # Add worker pods (ranks 1 to world_size-1)
    for rank in range(1, world_size):
        job_request_items.append(create_mpi_pod_spec(client, rank, world_size, job_set_id, volume_name))

    # Submit the jobs as a job set
    logger.info(f"Submitting job set to queue {queue_name}")
    response = client.submit_jobs(
        queue=queue_name,
        job_set_id=job_set_id,
        job_request_items=job_request_items
    )

    # Extract job IDs from response
    job_ids = [item.job_id for item in response.job_response_items]
    logger.info(f"Submitted job set {job_set_id}")
    logger.info(f"Master job ID: {job_ids[0]}")
    logger.info(f"Worker job IDs: {job_ids[1:]}")

    return job_set_id, job_ids


def monitor_job_set(client, queue_name, job_set_id, timeout_seconds=None):
    """
    Monitor the status of a job set until all jobs complete or timeout.

    Args:
        client: The Armada client
        queue_name: The queue name
        job_set_id: The job set ID to monitor
        timeout_seconds: Maximum time to wait before timing out

    Returns:
        True if all jobs succeeded, False otherwise
    """
    if timeout_seconds is None:
        timeout_seconds = MONITORING_TIMEOUT

    logger.info(f"Monitoring job set {job_set_id} with {timeout_seconds}s timeout")

    # Allow time for the job set to be created
    time.sleep(2)

    # Get event stream for the job set
    try:
        event_stream = client.get_job_events_stream(queue=queue_name, job_set_id=job_set_id)
    except grpc.RpcError as e:
        logger.error(f"Failed to get event stream: {e}")
        return False

    # Track job states
    job_states = {}
    start_time = time.time()

    try:
        for event_grpc in event_stream:
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                logger.error(f"Monitoring timed out after {timeout_seconds} seconds")
                return False

            # Process event
            event = client.unmarshal_event_response(event_grpc)
            job_id = event.message.job_id
            event_type = event.type
            logger.info(f"Job {job_id} - {event_type}")

            # Update job state
            job_states[job_id] = event_type

            # Check for terminal events
            terminal_events = [EventType.failed, EventType.succeeded, EventType.cancelled]

            # Check if all jobs have reached terminal state
            active_jobs = [job_id for job_id, state in job_states.items()
                           if state not in terminal_events]

            if not active_jobs and job_states:
                # All jobs have reached terminal state
                failed_jobs = [job_id for job_id, state in job_states.items()
                               if state == EventType.failed or state == EventType.cancelled]

                if failed_jobs:
                    logger.error(f"Job set {job_set_id} has {len(failed_jobs)} failed jobs")
                    return False
                else:
                    logger.info(f"All jobs in job set {job_set_id} completed successfully")
                    return True
    except Exception as e:
        logger.error(f"Error monitoring job set: {e}")
        return False
    finally:
        # Close the event stream
        try:
            client.unwatch_events(event_stream)
        except Exception as e:
            logger.warning(f"Error closing event stream: {e}")

    return False


def main():
    """Main workflow to create and run an MPI job."""
    try:
        # Create Armada client
        client = create_armada_client()

        # Get queue - either create new one or use existing one
        if QUEUE_NAME:
            # Try to use specified queue name
            try:
                queue_name = use_existing_queue(client, QUEUE_NAME)
            except Exception as e:
                logger.warning(f"Could not use existing queue {QUEUE_NAME}: {e}")
                logger.info("Falling back to queue creation")
                queue_name = create_mpi_queue(client)
        else:
            # Create a new queue
            queue_name = create_mpi_queue(client)

        logger.info(f"Using queue: {queue_name}")

        # Add a delay to ensure queue is ready
        time.sleep(5)
        logger.info("Waiting for queue to be fully ready")

        # Try to get the queue again to make sure it's there
        try:
            client.get_queue(queue_name)
            logger.info(f"Queue {queue_name} is ready for job submission")
        except grpc.RpcError as e:
            logger.error(f"Queue still not accessible after delay: {e}")
            raise e

        # Submit MPI job
        job_set_id, job_ids = submit_mpi_job(client, queue_name)
        logger.info(f"MPI job set {job_set_id} submitted successfully")
        logger.info("Hostfile generation is handled by the container's entrypoint script")

        # Monitor job execution
        success = monitor_job_set(client, queue_name, job_set_id)
        if success:
            logger.info("MPI job completed successfully")
        else:
            logger.error("MPI job failed")

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        raise


if __name__ == "__main__":
    main()
