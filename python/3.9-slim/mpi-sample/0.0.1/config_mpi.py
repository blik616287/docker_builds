import os
import uuid
import grpc
from armada_client.client import ArmadaClient
from armada_client.k8s.io.api.core.v1 import generated_pb2 as core_v1
from armada_client.k8s.io.apimachinery.pkg.api.resource import generated_pb2 as api_resource
from armada_client.permissions import Permissions, Subject
from armada_client.typings import EventType
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DISABLE_SSL = os.environ.get("DISABLE_SSL", True)
HOST = os.environ.get("ARMADA_SERVER", "localhost")
PORT = os.environ.get("ARMADA_PORT", "50051")
MPI_PROCESSES = int(os.environ.get("MPI_PROCESSES", "4"))  # Number of MPI processes
QUEUE_NAME = os.environ.get("QUEUE_NAME", f"mpi-queue-{uuid.uuid4().hex[:8]}")
PRIORITY_FACTOR = float(os.environ.get("PRIORITY_FACTOR", "10.0"))


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


def create_mpi_queue(client):
    """Create a queue for MPI jobs with appropriate settings."""
    logger.info(f"Creating queue: {QUEUE_NAME}")
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
        name=QUEUE_NAME,
        priority_factor=PRIORITY_FACTOR,
        user_owners=[os.environ.get("QUEUE_OWNER", "admin")],
        group_owners=[os.environ.get("QUEUE_GROUP", "admins")],
        resource_limits=resource_limits,
        permissions=[permissions]
    )
    # Create the queue, handling the case where it might already exist
    try:
        client.create_queue(queue_req)
        logger.info(f"Queue {QUEUE_NAME} created successfully")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.ALREADY_EXISTS:
            logger.info(f"Queue {QUEUE_NAME} already exists, updating it")
            client.update_queue(queue_req)
        else:
            logger.error(f"Failed to create queue: {e}")
            raise e
    return QUEUE_NAME


def create_mpi_pod_spec(client, rank, world_size, is_master=False):
    """
    Create a pod spec for an MPI worker or master node.

    Args:
        client: The Armada client
        rank: The MPI rank for this pod
        world_size: Total number of MPI processes
        is_master: Whether this is the master node

    Returns:
        A job request item
    """
    # Common environment variables for MPI
    mpi_env = [
        core_v1.EnvVar(name="MPI_WORLD_SIZE", value=str(world_size)),
        core_v1.EnvVar(name="MPI_RANK", value=str(rank)),
        core_v1.EnvVar(name="MPI_MASTER_ADDR", value="mpi-master"),
        core_v1.EnvVar(name="MPI_MASTER_PORT", value="29500"),
    ]
    # Container name and labels vary by role
    container_name = "mpi-master" if is_master else f"mpi-worker-{rank}"
    # Common pod metadata for service discovery
    pod_metadata = core_v1.PodMetadata(
        labels={
            "app": "mpi-job",
            "role": "master" if is_master else "worker",
            "rank": str(rank)
        }
    )
    # Define resource requirements
    # Master node might need more resources
    cpu_request = "500m" if is_master else "250m"
    memory_request = "2Gi" if is_master else "1Gi"
    # Command to run - this will be different for actual MPI jobs
    if is_master:
        command = [
            "mpirun",
            "--allow-run-as-root",
            "--hostfile", "/etc/mpi/hostfile",
            "-np", str(world_size),
            "python", "/app/mpi_script.py"
        ]
    else:
        # Workers just sleep and wait for the master to connect
        command = ["sleep", "infinity"]
    # Create the container spec
    container = core_v1.Container(
        name=container_name,
        image=os.environ.get("MPI_IMAGE", "blik6126287/python3.9-slim_mpi-sample0.0.1_base:latest"),
        args=command,
        env=mpi_env,
        security_context=core_v1.SecurityContext(run_as_user=1000),
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
    )
    # Create the pod spec
    pod_spec = core_v1.PodSpec(
        containers=[container],
        restart_policy="Never"
    )
    # Create the job request item
    return client.create_job_request_item(
        priority=int(os.environ.get("JOB_PRIORITY", "50")),
        pod_spec=pod_spec,
        pod_metadata=pod_metadata,
        namespace=os.environ.get("NAMESPACE", "default")
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
    job_set_id = f"mpi-jobset-{uuid.uuid4().hex[:8]}"
    logger.info(f"Creating MPI job set {job_set_id} with {world_size} processes")
    # Create job request items for master and workers
    job_request_items = []
    # Add master pod (rank 0)
    job_request_items.append(create_mpi_pod_spec(client, 0, world_size, is_master=True))
    # Add worker pods (ranks 1 to world_size-1)
    for rank in range(1, world_size):
        job_request_items.append(create_mpi_pod_spec(client, rank, world_size, is_master=False))
    # Submit the jobs as a job set
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


def monitor_job_set(client, queue_name, job_set_id, timeout_seconds=300):
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
    logger.info(f"Monitoring job set {job_set_id}")
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
        client.unwatch_events(event_stream)
    return False


def main():
    """Main workflow to create and run an MPI job."""
    try:
        # Create Armada client
        client = create_armada_client()
        # Create queue
        queue_name = create_mpi_queue(client)
        # Submit MPI job
        job_set_id, job_ids = submit_mpi_job(client, queue_name)
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
