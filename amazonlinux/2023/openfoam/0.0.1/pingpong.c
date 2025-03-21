#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>

#define PING_PONG_LIMIT 10
#define MESSAGE_SIZE 1000000

int main(int argc, char** argv) {
    // Initialize the MPI environment
    MPI_Init(&argc, &argv);

    // Get the number of processes
    int world_size;
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);

    // Get the rank of the process
    int world_rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);

    // Get the name of the processor
    char processor_name[MPI_MAX_PROCESSOR_NAME];
    int name_len;
    MPI_Get_processor_name(processor_name, &name_len);

    printf("Process %d on %s\n", world_rank, processor_name);

    // We need at least 2 processes for this test
    if (world_size < 2) {
        fprintf(stderr, "World size must be >= 2 for %s\n", argv[0]);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    // Allocate memory for the message
    char* message = (char*)malloc(MESSAGE_SIZE * sizeof(char));
    if (message == NULL) {
        fprintf(stderr, "Failed to allocate memory\n");
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    // Fill with some data
    for (int i = 0; i < MESSAGE_SIZE; i++) {
        message[i] = (char)(i % 128);
    }

    int ping_pong_count = 0;
    int partner_rank = (world_rank + 1) % 2;
    double start_time, end_time, total_time = 0;

    MPI_Barrier(MPI_COMM_WORLD);

    if (world_rank == 0) {
        printf("Starting ping-pong test (iterations: %d, message size: %d bytes)\n", 
               PING_PONG_LIMIT, MESSAGE_SIZE);
    }

    while (ping_pong_count < PING_PONG_LIMIT) {
        if (world_rank == ping_pong_count % 2) {
            // Sender
            start_time = MPI_Wtime();
            MPI_Send(message, MESSAGE_SIZE, MPI_CHAR, partner_rank, 0, MPI_COMM_WORLD);
            MPI_Recv(message, MESSAGE_SIZE, MPI_CHAR, partner_rank, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            end_time = MPI_Wtime();
            total_time += (end_time - start_time);
            printf("Process %d sent and received ping-pong %d in %f seconds\n",
                   world_rank, ping_pong_count, end_time - start_time);
        } else {
            // Receiver
            MPI_Recv(message, MESSAGE_SIZE, MPI_CHAR, partner_rank, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            MPI_Send(message, MESSAGE_SIZE, MPI_CHAR, partner_rank, 0, MPI_COMM_WORLD);
        }
        ping_pong_count++;
    }

    MPI_Barrier(MPI_COMM_WORLD);

    if (world_rank == 0) {
        double bandwidth = (MESSAGE_SIZE * PING_PONG_LIMIT * 2.0) / (total_time * 1024 * 1024);
        printf("\n=== Ping-pong Test Results ===\n");
        printf("Total time: %f seconds\n", total_time);
        printf("Average time per round-trip: %f seconds\n", total_time / PING_PONG_LIMIT);
        printf("Bandwidth: %f MB/s\n", bandwidth);
    }

    free(message);
    MPI_Finalize();
    return 0;
}
