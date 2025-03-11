import os
import uuid
import grpc
import time
import logging
from armada_client.client import ArmadaClient
from armada_client.k8s.io.api.core.v1 import generated_pb2 as core_v1
from armada_client.k8s.io.apimachinery.pkg.api.resource import generated_pb2 as api_resource
from armada_client.typings import EventType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DISABLE_SSL = os.environ.get("DISABLE_SSL", "true").lower() == "true"
HOST = os.environ.get("ARMADA_SERVER", "localhost")
PORT = os.environ.get("ARMADA_PORT", "50051")
MPI_PROCESSES = int(os.environ.get("MPI_PROCESSES", "4"))  # Number of MPI processes
QUEUE_NAME = os.environ.get("QUEUE_NAME", f"mpi-c-queue-{uuid.uuid4().hex[:8]}")
JOB_SET_ID = f"mpi-c-jobset-{uuid.uuid4().hex[:8]}"
MPI_IMAGE = os.environ.get("MPI_IMAGE", "mpi-c-app:latest")  # Your MPI container image
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


def create_mpi_queue(client):
    """Create a queue for MPI jobs."""
    logger.info(f"Creating queue: {QUEUE_NAME}")
    queue_req = client.create_queue_request(
        name=QUEUE_NAME,
        priority_factor=float(os.environ.get("PRIORITY_FACTOR", "10.0"))
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


def create_master_pod_spec(client):
    """Create the master pod specification."""
    # Environment variables for MPI
    env_vars = [
        core_v1.EnvVar(name="MPI_WORLD_SIZE", value=str(MPI_PROCESSES)),
        core_v1.EnvVar(name="MPI_RANK", value="0"),
        core_v1.EnvVar(name="MPI_MASTER_ADDR", value="mpi-master"),
        core_v1.EnvVar(name="MASTER", value="true")
    ]
    # Master container running mpirun
    container = core_v1.Container(
        name="mpi-master",
        image=MPI_IMAGE,
        command=[
            "mpirun",
            "--allow-run-as-root",
            "-hostfile", "/etc/mpi/hostfile",
            "-np", str(MPI_PROCESSES),
            "./mpi_matrix_multiply"
        ],
        env=env_vars,
        security_context=core_v1.SecurityContext(run_as_user=0),  # Run as root for SSH
        resources=core_v1.ResourceRequirements(
            requests={
                "cpu": api_resource.Quantity(string="500m"),
                "memory": api_resource.Quantity(string="1Gi"),
            },
            limits={
                "cpu": api_resource.Quantity(string="1000m"),
                "memory": api_resource.Quantity(string="2Gi"),
            },
        ),
    )
    # Pod metadata with labels for service discovery
    pod_metadata = core_v1.PodMetadata(
        labels={
            "app": "mpi-job",
            "role": "master",
            "job-set-id": JOB_SET_ID
        }
    )
    # Pod spec
    pod_spec = core_v1.PodSpec(
        containers=[container],
        hostname="mpi-master",
        restart_policy="Never"
    )
    # Create the job request item
    return client.create_job_request_item(
        priority=int(os.environ.get("JOB_PRIORITY", "50")),
        pod_spec=pod_spec,
        pod_metadata=pod_metadata,
        namespace=NAMESPACE
    )


def create_worker_pod_spec(client, rank):
    """Create a worker pod specification."""
    # Environment variables for MPI
    env_vars = [
        core_v1.EnvVar(name="MPI_WORLD_SIZE", value=str(MPI_PROCESSES)),
        core_v1.EnvVar(name="MPI_RANK", value=str(rank)),
        core_v1.EnvVar(name="MPI_MASTER_ADDR", value="mpi-master"),
        core_v1.EnvVar(name="MASTER", value="false")
    ]
    # Worker container - will be SSH'd into by the master
    container = core_v1.Container(
        name=f"mpi-worker-{rank}",
        image=MPI_IMAGE,
        command=["sleep", "infinity"],  # Keep container running until master connects
        env=env_vars,
        security_context=core_v1.SecurityContext(run_as_user=0),  # Run as root for SSH
        resources=core_v1.ResourceRequirements(
            requests={
                "cpu": api_resource.Quantity(string="500m"),
                "memory": api_resource.Quantity(string="1Gi"),
            },
            limits={
                "cpu": api_resource.Quantity(string="1000m"),
                "memory": api_resource.Quantity(string="2Gi"),
            },
        ),
    )
    # Pod metadata with labels for service discovery
    pod_metadata = core_v1.PodMetadata(
        labels={
            "app": "mpi-job",
            "role": "worker",
            "rank": str(rank),
            "job-set-id": JOB_SET_ID
        }
    )
    # Pod spec
    pod_spec = core_v1.PodSpec(
        containers=[container],
        hostname=f"mpi-worker-{rank}",
        restart_policy="Never"
    )
    # Create the job request item
    return client.create_job_request_item(
        priority=int(os.environ.get("JOB_PRIORITY", "50")),
        pod_spec=pod_spec,
        pod_metadata=pod_metadata,
        namespace=NAMESPACE
    )


def submit_mpi_job(client, queue_name):
    """Submit an MPI job with one master and multiple workers."""
    logger.info(f"Creating MPI job set {JOB_SET_ID} with {MPI_PROCESSES} processes")
    # Create job request items for master and workers
    job_request_items = []
    # Add master pod (rank 0)
    job_request_items.append(create_master_pod_spec(client))
    # Add worker pods (ranks 1 to MPI_PROCESSES-1)
    for rank in range(1, MPI_PROCESSES):
        job_request_items.append(create_worker_pod_spec(client, rank))
    # Submit the job set
    response = client.submit_jobs(
        queue=queue_name,
        job_set_id=JOB_SET_ID,
        job_request_items=job_request_items
    )
    # Extract job IDs from response
    job_ids = [item.job_id for item in response.job_response_items]
    logger.info(f"Submitted job set {JOB_SET_ID}")
    logger.info(f"Master job ID: {job_ids[0]}")
    logger.info(f"Worker job IDs: {job_ids[1:]}")
    return job_ids


def monitor_job_set(client, queue_name):
    """Monitor the MPI job set execution."""
    logger.info(f"Monitoring job set {JOB_SET_ID}")
    # Allow time for the job set to be created
    time.sleep(2)
    try:
        # Get event stream for the job set
        event_stream = client.get_job_events_stream(queue=queue_name, job_set_id=JOB_SET_ID)
        # Terminal event types that indicate job completion
        terminal_events = [EventType.failed, EventType.succeeded, EventType.cancelled]
        # Track job states
        job_states = {}
        master_job_id = None
        # Monitor events
        for event_grpc in event_stream:
            event = client.unmarshal_event_response(event_grpc)
            job_id = event.message.job_id
            event_type = event.type
            # For easier tracking, identify if this is the master job
            is_master = False
            if not master_job_id and "role" in event.message.pod_spec.metadata.labels:
                if event.message.pod_spec.metadata.labels["role"] == "master":
                    master_job_id = job_id
                    is_master = True
            elif master_job_id and job_id == master_job_id:
                is_master = True
            role = "master" if is_master else "worker"
            logger.info(f"Job {job_id} ({role}) - {event_type}")
            # Update job state
            job_states[job_id] = event_type
            # If master job reaches terminal state, we check the result
            if is_master and event_type in terminal_events:
                if event_type == EventType.succeeded:
                    logger.info("Master job completed successfully!")
                    return True
                else:
                    logger.error(f"Master job terminated with state: {event_type}")
                    return False
    except Exception as e:
        logger.error(f"Error monitoring job set: {e}")
        return False
    finally:
        # Close the event stream if it exists
        if 'event_stream' in locals():
            client.unwatch_events(event_stream)
    return False


def main():
    """Main workflow to create and run a C MPI job."""
    try:
        # Create Armada client
        client = create_armada_client()
        # Create queue
        queue_name = create_mpi_queue(client)
        # Submit MPI job
        job_ids = submit_mpi_job(client, queue_name)
        # Monitor job execution
        success = monitor_job_set(client, queue_name)
        if success:
            logger.info("MPI job completed successfully")
        else:
            logger.error("MPI job failed or was cancelled")
            # Attempt to cancel any remaining jobs
            logger.info("Cancelling remaining jobs...")
            client.cancel_jobs(queue=queue_name, job_set_id=JOB_SET_ID)
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        raise


if __name__ == "__main__":
    main()
