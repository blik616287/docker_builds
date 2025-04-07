#!/usr/bin/env python3

import uuid
import grpc
import time
import logging
from armada_client.client import ArmadaClient
from armada_client.k8s.io.api.core.v1 import generated_pb2 as core_v1
from armada_client.k8s.io.apimachinery.pkg.api.resource import generated_pb2 as api_resource
from armada_client.permissions import Permissions, Subject

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration (hardcoded)
ARMADA_HOST = "localhost"
ARMADA_PORT = "50051"
DISABLE_SSL = True
QUEUE_NAME = "binpacked-jobs"  # Custom queue name
TARGET_NODE = "ip-10-0-128-76.us-west-2.compute.internal"  # Your target node
NAMESPACE = "default"
NUM_JOBS = 40

def create_armada_client():
    """Create and return an Armada client."""
    channel = grpc.insecure_channel(f"{ARMADA_HOST}:{ARMADA_PORT}")
    return ArmadaClient(channel)

def create_or_get_queue(client):
    """Create a queue if it doesn't exist, or get an existing one."""
    queue_name = QUEUE_NAME
    
    try:
        # Try to get the queue first
        logger.info(f"Checking if queue {queue_name} exists")
        queue = client.get_queue(queue_name)
        logger.info(f"Using existing queue: {queue_name}")
        return queue_name
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            # Queue doesn't exist, create it
            logger.info(f"Queue {queue_name} not found, creating new queue")
            
            # Define permissions for the queue
            subject = Subject(kind="Group", name="users")
            permissions = Permissions(
                subjects=[subject],
                verbs=["submit", "cancel", "reprioritize", "watch"]
            )
            
            # Set resource limits for the queue
            resource_limits = {
                "cpu": 100.0,
                "memory": 200.0,
                "gpu": 0.0
            }
            
            # Create queue request
            queue_req = client.create_queue_request(
                name=queue_name,
                priority_factor=10.0,
                user_owners=["admin"],
                group_owners=["admins"],
                resource_limits=resource_limits,
                permissions=[permissions]
            )
            
            try:
                # Create the queue
                client.create_queue(queue_req)
                logger.info(f"Queue {queue_name} created successfully")
                
                # Verify the queue exists
                time.sleep(2)  # Small delay to ensure queue is registered
                queue = client.get_queue(queue_name)
                logger.info(f"Queue {queue_name} verified to exist")
                return queue_name
            except grpc.RpcError as create_error:
                logger.error(f"Failed to create queue: {create_error}")
                raise create_error
        else:
            logger.error(f"Error checking queue: {e}")
            raise e

def create_bin_packed_job_specs(client, job_set_id):
    """Create job specs for bin-packed jobs."""
    job_request_items = []
    
    for i in range(1, NUM_JOBS + 1):
        # Pod labels for identification
        pod_labels = {
            "app": "cpu-test",
            "job-set-id": job_set_id,
            "index": str(i)
        }
        
        # Create the container spec
        container = core_v1.Container(
            name="cpu-test",
            image="ubuntu",
            command=["sleep", "infinity"],
            resources=core_v1.ResourceRequirements(
                requests={
                    "cpu": api_resource.Quantity(string="1"),
                    "memory": api_resource.Quantity(string="2Gi"),
                },
                limits={
                    "cpu": api_resource.Quantity(string="1"),
                    "memory": api_resource.Quantity(string="2Gi"),
                },
            )
        )
        
        # Create node selector for the target node
        node_selector = {"kubernetes.io/hostname": TARGET_NODE}
        
        # Create pod spec
        pod_spec = core_v1.PodSpec(
            containers=[container],
            nodeSelector=node_selector,
        )
        
        # Create job request item
        job_item = client.create_job_request_item(
            priority=50,  # Default priority
            pod_spec=pod_spec,
            labels=pod_labels,
            namespace=NAMESPACE
        )
        
        job_request_items.append(job_item)
    
    return job_request_items

def submit_bin_packed_jobs(client, queue_name):
    """Submit bin-packed jobs to Armada."""
    job_set_id = f"bin-packed-{uuid.uuid4().hex[:8]}"
    logger.info(f"Creating job set {job_set_id} with {NUM_JOBS} jobs")
    
    # Create job specs
    job_request_items = create_bin_packed_job_specs(client, job_set_id)
    
    # Submit the jobs as a job set
    logger.info(f"Submitting job set to queue {queue_name}")
    
    response = client.submit_jobs(
        queue=queue_name,
        job_set_id=job_set_id,
        job_request_items=job_request_items
    )
    
    # Extract job IDs from response
    job_ids = [item.job_id for item in response.job_response_items]
    logger.info(f"Submitted job set {job_set_id} with {len(job_ids)} jobs")
    
    return job_set_id, job_ids

def main():
    """Main function to submit bin-packed jobs to Armada."""
    try:
        # Create Armada client
        client = create_armada_client()
        
        # Create or get queue
        queue_name = create_or_get_queue(client)
        time.sleep(20)
        # Submit bin-packed jobs
        job_set_id, job_ids = submit_bin_packed_jobs(client, queue_name)
        
        logger.info(f"Successfully submitted {len(job_ids)} jobs in job set {job_set_id}")
        logger.info(f"All jobs targeted to node: {TARGET_NODE}")
        logger.info(f"All jobs have 1 CPU and 2Gi memory limits")
        
    except Exception as e:
        logger.error(f"Job submission failed: {e}")
        raise

if __name__ == "__main__":
    main()
