#!/usr/bin/env python3

import os
import uuid
import grpc
import time
import logging
import argparse
from armada_client.client import ArmadaClient
from armada_client.k8s.io.api.core.v1 import generated_pb2 as core_v1
from armada_client.k8s.io.apimachinery.pkg.api.resource import generated_pb2 as api_resource
from armada_client.permissions import Permissions, Subject
from armada_client.typings import EventType


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments and combine with environment variables."""
    parser = argparse.ArgumentParser(description='Armada Client MPI Submission Script')
    # Server connection settings
    parser.add_argument('--disable-ssl', dest='disable_ssl', action='store_true',
                        help='Disable SSL for connection (default: true)')
    parser.add_argument('--host', dest='armada_server',
                        help='Armada server host (default: localhost)')
    parser.add_argument('--port', dest='armada_port',
                        help='Armada server port (default: 50051)')
    # MPI job settings
    parser.add_argument('--mpi-processes', dest='mpi_processes', type=int,
                        help='Number of MPI processes (default: 1)')
    parser.add_argument('--queue-name', dest='queue_name',
                        help='Queue name to use (default: auto-generated)')
    parser.add_argument('--priority-factor', dest='priority_factor', type=float,
                        help='Priority factor for queue (default: 10.0)')
    parser.add_argument('--job-set-prefix', dest='job_set_prefix',
                        help='Job set prefix (default: mpi-jobset)')
    parser.add_argument('--monitoring-timeout', dest='monitoring_timeout', type=int,
                        help='Timeout for job monitoring in seconds (default: 300)')
    parser.add_argument('--namespace', dest='namespace',
                        help='Kubernetes namespace (default: default)')
    parser.add_argument('--job-priority', dest='job_priority', type=int,
                        help='Job priority (default: 50)')
    # PVC settings for FSX
    parser.add_argument('--pvc-name', dest='pvc_name',
                        help='PVC name (default: fsx-claim)')
    parser.add_argument('--pvc-mount-path', dest='pvc_mount_path',
                        help='PVC mount path (default: /app/shared)')
    parser.add_argument('--pvc-volume-name', dest='pvc_volume_name',
                        help='PVC volume name (default: persistent-storage)')
    # Queue resource limits
    parser.add_argument('--queue-cpu-limit', dest='queue_cpu_limit', type=float,
                        help='Queue CPU limit (default: 100.0)')
    parser.add_argument('--queue-memory-limit', dest='queue_memory_limit', type=float,
                        help='Queue memory limit (default: 20000.0)')
    parser.add_argument('--queue-gpu-limit', dest='queue_gpu_limit', type=float,
                        help='Queue GPU limit (default: 0)')
    parser.add_argument('--queue-owner', dest='queue_owner',
                        help='Queue owner (default: admin)')
    parser.add_argument('--queue-group', dest='queue_group',
                        help='Queue group (default: admins)')
    # Container settings
    parser.add_argument('--mpi-image', dest='mpi_image',
                        help='MPI container image (default: blik6126287/amazonlinux2023_openfoam12:test)')
    parser.add_argument('--cpu-request', dest='cpu_request',
                        help='CPU request for containers (default: 1)')
    parser.add_argument('--memory-request', dest='memory_request',
                        help='Memory request for containers (default: 2Gi)')
    # Node scheduling settings
    parser.add_argument('--target-node', dest='target_node',
                        help='Target specific node for all pods (default: none)')
    parser.add_argument('--max-pods-per-node', dest='max_pods_per_node', type=int,
                        help='Maximum number of pods to schedule per node (default: 0 - no limit)')
    parser.add_argument('--disable-gang-scheduling', dest='disable_gang_scheduling', action='store_true',
                        help='Disable gang scheduling for MPI jobs')
    parser.add_argument('--node-concentration', dest='node_concentration', action='store_true',
                        help='Enable node concentration to place pods on same node')
    # Parse the arguments
    args = parser.parse_args()
    # Create a config dictionary by combining environment variables and command-line arguments
    config = {
        # Server connection settings
        'DISABLE_SSL': os.environ.get("DISABLE_SSL", "true").lower() == "true" if args.disable_ssl is None else args.disable_ssl,
        'HOST': os.environ.get("ARMADA_SERVER", "localhost") if args.armada_server is None else args.armada_server,
        'PORT': os.environ.get("ARMADA_PORT", "50051") if args.armada_port is None else args.armada_port,
        # MPI job settings
        'MPI_PROCESSES': int(os.environ.get("MPI_PROCESSES", "1")) if args.mpi_processes is None else args.mpi_processes,
        'QUEUE_NAME': os.environ.get("QUEUE_NAME", "") if args.queue_name is None else args.queue_name,
        'PRIORITY_FACTOR': float(os.environ.get("PRIORITY_FACTOR", "10.0")) if args.priority_factor is None else args.priority_factor,
        'JOB_SET_PREFIX': os.environ.get("JOB_SET_PREFIX", "mpi-jobset") if args.job_set_prefix is None else args.job_set_prefix,
        'MONITORING_TIMEOUT': int(os.environ.get("MONITORING_TIMEOUT", "300")) if args.monitoring_timeout is None else args.monitoring_timeout,
        'NAMESPACE': os.environ.get("NAMESPACE", "default") if args.namespace is None else args.namespace,
        'JOB_PRIORITY': int(os.environ.get("JOB_PRIORITY", "50")) if args.job_priority is None else args.job_priority,
        # PVC settings for FSX
        'PVC_NAME': os.environ.get("PVC_NAME", "fsx-claim") if args.pvc_name is None else args.pvc_name,
        'PVC_MOUNT_PATH': os.environ.get("PVC_MOUNT_PATH", "/app/shared") if args.pvc_mount_path is None else args.pvc_mount_path,
        'PVC_VOLUME_NAME': os.environ.get("PVC_VOLUME_NAME", "persistent-storage") if args.pvc_volume_name is None else args.pvc_volume_name,
        # Queue resource limits
        'QUEUE_CPU_LIMIT': float(os.environ.get("QUEUE_CPU_LIMIT", "100.0")) if args.queue_cpu_limit is None else args.queue_cpu_limit,
        'QUEUE_MEMORY_LIMIT': float(os.environ.get("QUEUE_MEMORY_LIMIT", "20000.0")) if args.queue_memory_limit is None else args.queue_memory_limit,
        'QUEUE_GPU_LIMIT': float(os.environ.get("QUEUE_GPU_LIMIT", "0")) if args.queue_gpu_limit is None else args.queue_gpu_limit,
        'QUEUE_OWNER': os.environ.get("QUEUE_OWNER", "admin") if args.queue_owner is None else args.queue_owner,
        'QUEUE_GROUP': os.environ.get("QUEUE_GROUP", "admins") if args.queue_group is None else args.queue_group,
        # Container settings
        'MPI_IMAGE': os.environ.get("MPI_IMAGE", "blik6126287/amazonlinux2023_openfoam12:test") if args.mpi_image is None else args.mpi_image,
        'CPU_REQUEST': os.environ.get("CPU_REQUEST", "1") if args.cpu_request is None else args.cpu_request,
        'MEMORY_REQUEST': os.environ.get("MEMORY_REQUEST", "2Gi") if args.memory_request is None else args.memory_request,
        # Node scheduling settings
        'TARGET_NODE': os.environ.get("TARGET_NODE", "") if args.target_node is None else args.target_node,
        'MAX_PODS_PER_NODE': int(os.environ.get("MAX_PODS_PER_NODE", "0")) if args.max_pods_per_node is None else args.max_pods_per_node,
        'DISABLE_GANG_SCHEDULING': os.environ.get("DISABLE_GANG_SCHEDULING", "false").lower() == "true" if args.disable_gang_scheduling is None else args.disable_gang_scheduling,
        'NODE_CONCENTRATION': os.environ.get("NODE_CONCENTRATION", "false").lower() == "true" if args.node_concentration is None else args.node_concentration,
    }
    return config


def create_armada_client(config):
    """Create and return an Armada client."""
    if config['DISABLE_SSL']:
        channel = grpc.insecure_channel(f"{config['HOST']}:{config['PORT']}")
    else:
        channel_credentials = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(
            f"{config['HOST']}:{config['PORT']}",
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


def create_mpi_queue(client, config):
    """
    Create a queue for MPI jobs with appropriate settings and verify it exists before returning.

    Args:
        client: The Armada client
        config: Configuration dictionary

    Returns:
        The name of the created queue
    """
    queue_name = config['QUEUE_NAME']
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
        "cpu": config['QUEUE_CPU_LIMIT'],
        "memory": config['QUEUE_MEMORY_LIMIT'],
        "gpu": config['QUEUE_GPU_LIMIT']
    }
    queue_req = client.create_queue_request(
        name=queue_name,
        priority_factor=config['PRIORITY_FACTOR'],
        user_owners=[config['QUEUE_OWNER']],
        group_owners=[config['QUEUE_GROUP']],
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


def create_volume_with_pvc(pvc_name, volume_name):
    """
    Create a Volume object with a PVC reference for FSX.

    Args:
        pvc_name: The name of the PVC to reference
        volume_name: The name of the volume to create

    Returns:
        A properly configured Volume object
    """
    try:
        # Directly construct the PVC volume source
        pvc_source = core_v1.PersistentVolumeClaimVolumeSource(
            claimName=pvc_name,
            readOnly=False
        )
        logger.info(f"Created PVC source with claimName={pvc_name}, readOnly=False")
        # Find the source field name in Volume
        volume_fields = [f.name for f in core_v1.Volume.DESCRIPTOR.fields]
        source_field_name = next((field for field in volume_fields if field != "name"), None)
        if not source_field_name:
            raise ValueError("Volume structure doesn't have a field other than 'name'")
        # Find the PVC field name in VolumeSource
        vs_fields = [f.name for f in core_v1.VolumeSource.DESCRIPTOR.fields]
        pvc_field_name = next((field for field in vs_fields
                               if "persistentvolumeclaim" in field.lower() or "pvc" in field.lower()), None)
        if not pvc_field_name:
            raise ValueError("VolumeSource structure doesn't have a PVC field")
        # Create VolumeSource with PVC field
        vs_kwargs = {}
        vs_kwargs[pvc_field_name] = pvc_source
        volume_source = core_v1.VolumeSource(**vs_kwargs)
        # Create Volume with name and source
        vol_kwargs = {"name": volume_name}
        vol_kwargs[source_field_name] = volume_source
        volume = core_v1.Volume(**vol_kwargs)
        logger.info(f"Created Volume '{volume_name}' with PVC claim '{pvc_name}'")
        return volume
    except Exception as e:
        logger.error(f"Failed to create volume with PVC: {e}")
        raise


def create_mpi_pod_spec(client, rank, world_size, job_set_id, config):
    """
    Create a pod spec for an MPI process (master or worker).
    Updated to include configuration options for gang scheduling and node placement.

    Args:
        client: The Armada client
        rank: The MPI rank for this pod
        world_size: Total number of MPI processes
        job_set_id: The job set ID for identification
        config: Configuration dictionary

    Returns:
        A job request item
    """
    # Role designation
    is_master = (rank == 0)
    role = "master" if is_master else "worker"
    # Pod naming based on job set ID and rank
    pod_name = f"mpi-{rank}-{job_set_id}"
    
    # Common environment variables for MPI
    mpi_env = [
        core_v1.EnvVar(name="MPI_WORLD_SIZE", value=str(world_size)),
        core_v1.EnvVar(name="MPI_RANK", value=str(rank)),
        core_v1.EnvVar(name="MPI_MASTER_PORT", value="29500"),
        core_v1.EnvVar(name="JOB_SET_ID", value=job_set_id),
        core_v1.EnvVar(name="POD_NAME", value=pod_name),
        core_v1.EnvVar(name="MPI_JOB_ID", value=job_set_id),
        # Template for direct DNS-based discovery
        core_v1.EnvVar(name="MPI_MASTER_ADDR", value=f"mpi-0-{job_set_id}"),
        # OpenMPI configurations
        core_v1.EnvVar(name="OMPI_MCA_btl", value="tcp,self"),
        core_v1.EnvVar(name="OMPI_MCA_btl_tcp_if_include", value="eth0"),
        core_v1.EnvVar(name="OMPI_MCA_plm_rsh_no_tree_spawn", value="1"),
        core_v1.EnvVar(name="OMPI_MCA_orte_keep_fqdn_hostnames", value="t"),
        # Shared mount path environment variable
        core_v1.EnvVar(name="MOUNTPOINT", value=config['PVC_MOUNT_PATH']),
    ]
    
    # Add an additional environment variable to help with non-gang scheduling if enabled
    if config['DISABLE_GANG_SCHEDULING']:
        mpi_env.append(core_v1.EnvVar(name="ARMADA_STANDALONE_JOB", value="true"))
        mpi_env.append(core_v1.EnvVar(name="ARMADA_DISABLE_GANG_SCHEDULING", value="true"))
    
    # Add node concentration environment variable if enabled
    if config['NODE_CONCENTRATION']:
        mpi_env.append(core_v1.EnvVar(name="ARMADA_NODE_CONCENTRATION", value="true"))
        if config['MAX_PODS_PER_NODE'] > 0:
            mpi_env.append(core_v1.EnvVar(name="ARMADA_MAX_PODS_PER_NODE", value=str(config['MAX_PODS_PER_NODE'])))
    
    # Container name
    container_name = "mpi-master" if is_master else f"mpi-worker-{rank}"
    
    # Common pod labels for identification
    pod_labels = {
        "app": "mpi-job",
        "job-set-id": job_set_id,
        "role": role,
        "rank": str(rank)
    }
    
    # Prepare annotations to control scheduling behavior
    pod_annotations = {}
    if config['DISABLE_GANG_SCHEDULING']:
        pod_annotations["armada.io/disable-gang-scheduling"] = "true"
    if config['NODE_CONCENTRATION']:
        pod_annotations["armada.io/node-concentration"] = "true"
        pod_annotations["armada.io/max-pods-per-node"] = str(config['MAX_PODS_PER_NODE']) if config['MAX_PODS_PER_NODE'] > 0 else "unlimited"
    
    # Create the main container spec with volumeMounts
    # Set identical resource requests and limits to satisfy Armada's requirements
    main_container = core_v1.Container(
        name=container_name,
        image=config['MPI_IMAGE'],
        imagePullPolicy="Always",
        env=mpi_env,
        resources=core_v1.ResourceRequirements(
            requests={
                "cpu": api_resource.Quantity(string=config['CPU_REQUEST']),
                "memory": api_resource.Quantity(string=config['MEMORY_REQUEST']),
                "ephemeral-storage": api_resource.Quantity(string="8Gi"),
            },
            limits={
                "cpu": api_resource.Quantity(string=config['CPU_REQUEST']),
                "memory": api_resource.Quantity(string=config['MEMORY_REQUEST']),
                "ephemeral-storage": api_resource.Quantity(string="8Gi"),
            },
        ),
        ports=[
            # SSH port for MPI communication
            core_v1.ContainerPort(containerPort=22, protocol="TCP"),
        ],
        # Use volumeMount with new volume name
        volumeMounts=[
            core_v1.VolumeMount(
                name=config['PVC_VOLUME_NAME'],
                mountPath=config['PVC_MOUNT_PATH']
            )
        ],
        # We still need privileged access for the MPI tasks
        securityContext=core_v1.SecurityContext(
            privileged=True,
            capabilities=core_v1.Capabilities(add=["SYS_ADMIN"]),
            seccompProfile=core_v1.SeccompProfile(type="Unconfined")
        )
    )
    
    try:
        # Create volume with PVC reference using the new volume name
        shared_volume = create_volume_with_pvc(config['PVC_NAME'], config['PVC_VOLUME_NAME'])
        logger.info(f"Created volume '{config['PVC_VOLUME_NAME']}' referencing PVC '{config['PVC_NAME']}'")
        
        # Prepare tolerations for pod placement
        tolerations = []
        if config['NODE_CONCENTRATION']:
            # Add toleration to enable node concentration
            tolerations.append(
                core_v1.Toleration(
                    key="armada.io/node-concentration",
                    operator="Equal",
                    value="true",
                    effect="NoSchedule"
                )
            )
        
        # Handle node selection
        node_selector = {}
        if config['TARGET_NODE']:
            node_selector["kubernetes.io/hostname"] = config['TARGET_NODE']
        
        # Create pod spec with container and volume
        pod_spec = core_v1.PodSpec(
            containers=[main_container],
            volumes=[shared_volume],
            nodeSelector=node_selector,
            tolerations=tolerations,
            # Updated fsGroup for file access
            securityContext=core_v1.PodSecurityContext(
                fsGroup=1000  # Use a non-root group for file access
            )
        )
        
        # Create job request item with annotations
        job_item = client.create_job_request_item(
            priority=config['JOB_PRIORITY'],
            pod_spec=pod_spec,
            labels=pod_labels,
            annotations=pod_annotations,
            namespace=config['NAMESPACE']
        )
        
        return job_item
    except Exception as e:
        logger.error(f"Failed to create pod spec: {e}")
        raise


def submit_mpi_job(client, queue_name, config):
    """
    Create and submit an MPI job set consisting of one master and multiple workers.
    Updated to include job set annotations in the job specifications instead of a separate parameter.

    Args:
        client: The Armada client
        queue_name: The queue to submit the job to
        config: Configuration dictionary

    Returns:
        job_set_id: The ID of the job set
        job_ids: List of job IDs, first is master, rest are workers
    """
    world_size = config['MPI_PROCESSES']
    job_set_id = f"{config['JOB_SET_PREFIX']}-{uuid.uuid4().hex[:8]}"
    logger.info(f"Creating MPI job set {job_set_id} with {world_size} processes")
    
    # Create job request items for master and workers
    job_request_items = []
    # Add master pod (rank 0)
    job_request_items.append(create_mpi_pod_spec(client, 0, world_size, job_set_id, config))
    # Add worker pods (ranks 1 to world_size-1)
    for rank in range(1, world_size):
        job_request_items.append(create_mpi_pod_spec(client, rank, world_size, job_set_id, config))
    
    # Submit the jobs as a job set
    logger.info(f"Submitting job set to queue {queue_name}")
    
    # Submit jobs without the annotations parameter (not supported in this version)
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
    
    # Log important information about the settings
    logger.info(f"Important: All pods use FSX PVC '{config['PVC_NAME']}' mounted at {config['PVC_MOUNT_PATH']}")
    logger.info(f"Make sure PVC '{config['PVC_NAME']}' exists in namespace {config['NAMESPACE']}")
    logger.info(f"The PVC should be used with ReadWriteMany access mode with proper RBAC permissions")
    logger.info(f"All pods will run with resource constraints ({config['CPU_REQUEST']} CPU, {config['MEMORY_REQUEST']} memory)")
    
    # Log scheduling configuration
    if config['DISABLE_GANG_SCHEDULING']:
        logger.info("Gang scheduling is DISABLED - pods will be scheduled independently")
    else:
        logger.info("Gang scheduling is ENABLED - pods will be scheduled as a group")
    
    if config['NODE_CONCENTRATION']:
        logger.info(f"Node concentration is ENABLED - attempting to place more pods on the same node")
        if config['MAX_PODS_PER_NODE'] > 0:
            logger.info(f"Maximum pods per node is set to {config['MAX_PODS_PER_NODE']}")
        else:
            logger.info("No maximum pods per node limit is set")
    
    if config['TARGET_NODE']:
        logger.info(f"Target node is set to: {config['TARGET_NODE']}")
    
    return job_set_id, job_ids


def monitor_job_set(client, queue_name, job_set_id, config):
    """
    Monitor the status of a job set until all jobs complete or timeout.

    Args:
        client: The Armada client
        queue_name: The queue name
        job_set_id: The job set ID to monitor
        config: Configuration dictionary

    Returns:
        True if all jobs succeeded, False otherwise
    """
    timeout_seconds = config['MONITORING_TIMEOUT']
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
    """Main workflow to create and run an MPI job with FSX shared filesystem."""
    try:
        # Parse arguments and build configuration
        config = parse_arguments()
        
        # Print configuration summary
        logger.info("Starting Armada MPI job submission with the following configuration:")
        logger.info(f"  MPI Processes: {config['MPI_PROCESSES']}")
        logger.info(f"  Target Node: {config['TARGET_NODE'] if config['TARGET_NODE'] else 'Not specified'}")
        logger.info(f"  Disable Gang Scheduling: {config['DISABLE_GANG_SCHEDULING']}")
        logger.info(f"  Node Concentration: {config['NODE_CONCENTRATION']}")
        logger.info(f"  Max Pods Per Node: {config['MAX_PODS_PER_NODE'] if config['MAX_PODS_PER_NODE'] > 0 else 'Unlimited'}")
        
        # Create Armada client
        client = create_armada_client(config)
        
        # Get queue - either create new one or use existing one
        if config['QUEUE_NAME']:
            # Try to use specified queue name
            try:
                queue_name = use_existing_queue(client, config['QUEUE_NAME'])
            except Exception as e:
                logger.warning(f"Could not use existing queue {config['QUEUE_NAME']}: {e}")
                queue_name = create_mpi_queue(client, config)
        else:
            # Create a new queue
            queue_name = create_mpi_queue(client, config)
        logger.info(f"Using queue: {queue_name}")
        
        # Add a delay to ensure queue is ready
        logger.info("Waiting 10s for queue to be fully ready")
        time.sleep(10)
        
        # Try to get the queue again to make sure it's there
        try:
            client.get_queue(queue_name)
            logger.info(f"Queue {queue_name} is ready for job submission")
        except grpc.RpcError as e:
            logger.error(f"Queue still not accessible after delay: {e}")
            raise e
        
        # Important: Using FSX PVC with ReadWriteMany capability
        logger.info(f"IMPORTANT: A PVC named {config['PVC_NAME']} must exist in namespace {config['NAMESPACE']}")
        logger.info(f"The PVC should have accessModes: ReadWriteMany")
        logger.info(f"Using FSX for shared filesystem access")
        
        # Submit MPI job
        job_set_id, job_ids = submit_mpi_job(client, queue_name, config)
        logger.info(f"MPI job set {job_set_id} submitted successfully")
        logger.info(f"Using FSX PVC {config['PVC_NAME']} mounted at {config['PVC_MOUNT_PATH']}")
        logger.info(f"All pods will run with resource constraints ({config['CPU_REQUEST']} CPU, {config['MEMORY_REQUEST']} memory)")
        
        # Monitor job execution
        success = monitor_job_set(client, queue_name, job_set_id, config)
        if success:
            logger.info("MPI job completed successfully")
        else:
            logger.error("MPI job failed")
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        raise


if __name__ == "__main__":
    main()
