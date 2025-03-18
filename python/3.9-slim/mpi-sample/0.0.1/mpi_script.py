#!/usr/bin/env python3

from mpi4py import MPI
import numpy as np
import time
import socket
import logging


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Run the MPI application."""
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    world_size = comm.Get_size()
    # Get hostname for debugging
    hostname = socket.gethostname()
    logger.info(f"Process {rank}/{world_size} running on {hostname}")
    # Example: Distributed matrix multiplication
    if rank == 0:
        # Master process
        logger.info("Master process starting distributed task")
        # Create some sample data
        matrix_size = 1000
        a = np.random.rand(matrix_size, matrix_size)
        b = np.random.rand(matrix_size, matrix_size)
        # Calculate how many rows to send to each worker
        rows_per_worker = matrix_size // (world_size - 1)
        # Send data to workers
        for worker_rank in range(1, world_size):
            # Determine which rows this worker will process
            start_row = (worker_rank - 1) * rows_per_worker
            end_row = start_row + rows_per_worker if worker_rank < world_size - 1 else matrix_size
            # Send the assigned rows of matrix a and the entire matrix b
            comm.send((a[start_row:end_row], b), dest=worker_rank)
        # Initialize result matrix
        result = np.zeros((matrix_size, matrix_size))
        # Collect results from workers
        for worker_rank in range(1, world_size):
            start_row = (worker_rank - 1) * rows_per_worker
            end_row = start_row + rows_per_worker if worker_rank < world_size - 1 else matrix_size
            # Receive result segment from worker
            result_segment = comm.recv(source=worker_rank)
            # Insert result segment into the full result matrix
            result[start_row:end_row] = result_segment
        logger.info("Matrix multiplication completed")
        logger.info(f"Result matrix shape: {result.shape}")
        logger.info(f"Result matrix sum: {np.sum(result)}")
    else:
        # Worker processes
        logger.info(f"Worker {rank} waiting for data")
        # Receive data from master
        a_segment, b = comm.recv(source=0)
        logger.info(f"Worker {rank} received data: a_segment shape {a_segment.shape}, b shape {b.shape}")
        # Perform matrix multiplication on assigned segment
        start_time = time.time()
        result_segment = np.dot(a_segment, b)
        compute_time = time.time() - start_time
        logger.info(f"Worker {rank} completed calculation in {compute_time:.2f} seconds")
        # Send result back to master
        comm.send(result_segment, dest=0)
        logger.info(f"Worker {rank} sent results to master")
    # Wait for all processes to finish
    comm.Barrier()
    if rank == 0:
        logger.info("All processes completed successfully")


if __name__ == "__main__":
    main()
